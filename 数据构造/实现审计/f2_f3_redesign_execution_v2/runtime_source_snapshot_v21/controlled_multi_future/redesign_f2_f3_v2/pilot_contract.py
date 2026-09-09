"""Strict pilot-root and realization contract for the V2.1 stage-C handoff."""

from __future__ import annotations

from typing import Any, Mapping

from .canonical import canonical_sha256


ROOTS = ("F2-A", "F2-B", "F3-A", "F3-B")
PROGRAMS = {"F2": ("inside", "on", "beside"), "F3": ("VVHH", "VHVH", "VHHV")}
REALIZATIONS = ("r_pc", "r_inv_path", "r_inv_motion")
ROOT_FAMILY = {"F2-A": "F2", "F2-B": "F2", "F3-A": "F3", "F3-B": "F3"}
ROOT_REALIZATION = {"F2-A": "r_inv_path", "F2-B": "r_inv_motion", "F3-A": "r_inv_path", "F3-B": "r_inv_motion"}


class PilotContractError(ValueError):
    pass


def planned_root_contract(root_id: str) -> dict[str, Any]:
    if root_id not in ROOTS:
        raise PilotContractError("unknown V2.1 pilot root")
    family = ROOT_FAMILY[root_id]
    return {
        "schema_version": "cmf_f2_f3_pilot_root_contract_v1",
        "root_id": root_id,
        "family": family,
        "scene_seed": {"F2-A": 202609081, "F2-B": 202609082, "F3-A": 202609083, "F3-B": 202609084}[root_id],
        "program_ids": list(PROGRAMS[family]),
        "realization_ids": ["r_pc", ROOT_REALIZATION[root_id]],
        "shared_prefix_required": True,
        "prefix_replay_mode": "exact_bytes",
        "suffix_online_planning_allowed": True,
        "formal_data": False,
        "stage0_data": False,
        "collection": True,
        "status": "PLANNED",
    }


def expected_cells(root_id: str) -> list[dict[str, str]]:
    contract = planned_root_contract(root_id)
    return [
        {"root_id": root_id, "family": contract["family"], "program_id": program, "realization_id": realization, "status": "PLANNED"}
        for program in contract["program_ids"]
        for realization in contract["realization_ids"]
    ]


def selected_cells(
    root_id: str,
    programs: list[str] | tuple[str, ...] | None = None,
    realizations: list[str] | tuple[str, ...] | None = None,
    cell_keys: list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, str]]:
    """Return the frozen cell order for a full root or a program subset.

    A subset is used only for a resume job whose remaining cells are joined
    with immutable receipts from the same root.  It never changes the root's
    six-cell contract.
    """
    cells = expected_cells(root_id)
    contract = planned_root_contract(root_id)
    if cell_keys is not None:
        if programs is not None or realizations is not None:
            raise PilotContractError("explicit cell keys cannot combine with program/realization subsets")
        expected_by_key = {f"{cell['program_id']}:{cell['realization_id']}": cell for cell in cells}
        requested_keys = tuple(cell_keys)
        if not requested_keys or len(set(requested_keys)) != len(requested_keys) or not set(requested_keys).issubset(expected_by_key):
            raise PilotContractError("explicit cell keys are empty, duplicated, or outside the frozen root contract")
        return [cell for cell in cells if f"{cell['program_id']}:{cell['realization_id']}" in set(requested_keys)]
    requested_programs = tuple(contract["program_ids"] if programs is None else programs)
    requested_realizations = tuple(contract["realization_ids"] if realizations is None else realizations)
    allowed_programs = set(contract["program_ids"])
    allowed_realizations = set(contract["realization_ids"])
    if not requested_programs or not set(requested_programs).issubset(allowed_programs):
        raise PilotContractError("resume program subset is outside the frozen root contract")
    if not requested_realizations or not set(requested_realizations).issubset(allowed_realizations):
        raise PilotContractError("resume realization subset is outside the frozen root contract")
    if len(set(requested_programs)) != len(requested_programs):
        raise PilotContractError("resume program subset contains duplicates")
    if len(set(requested_realizations)) != len(requested_realizations):
        raise PilotContractError("resume realization subset contains duplicates")
    selected = [
        cell
        for cell in cells
        if cell["program_id"] in set(requested_programs)
        and cell["realization_id"] in set(requested_realizations)
    ]
    if len(selected) != len(requested_programs) * len(requested_realizations):
        raise PilotContractError("resume subset did not select the frozen program/realization product")
    return selected


def reusable_cells(
    root_receipt: Mapping[str, Any],
    root_id: str,
    programs: list[str] | tuple[str, ...] | None = None,
    realizations: list[str] | tuple[str, ...] | None = None,
    *,
    cell_keys: set[tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Validate and return accepted cells that can be referenced by a resume root."""
    if cell_keys is None:
        cell_keys = {
            (cell["program_id"], cell["realization_id"])
            for cell in selected_cells(root_id, programs, realizations)
        }
    expected_all = {
        (cell["program_id"], cell["realization_id"]): cell
        for cell in expected_cells(root_id)
    }
    if not cell_keys or not cell_keys.issubset(expected_all):
        raise PilotContractError("resume reusable cell keys are outside the frozen root contract")
    expected = {key: expected_all[key] for key in cell_keys}
    source = {(cell.get("program_id"), cell.get("realization_id")): cell for cell in root_receipt.get("cells", [])}
    if root_receipt.get("root_id") != root_id or root_receipt.get("family") != ROOT_FAMILY[root_id]:
        raise PilotContractError("resume source root differs from frozen root contract")
    if not set(expected).issubset(source):
        raise PilotContractError("resume source root is missing requested cells")
    result = []
    for key in expected:
        cell = source[key]
        if cell.get("status") != "cell_pass" or cell.get("cell_local_verified") is not True:
            raise PilotContractError("resume source contains a cell without independent local verification")
        for field in ("current", "anchor", "prefix_sha256", "trace_path"):
            if field not in cell:
                raise PilotContractError(f"resume source cell is missing {field}")
        result.append(dict(cell))
    return result


def root_contract_sha256(root_id: str) -> str:
    return canonical_sha256(planned_root_contract(root_id))


def validate_cell(value: Mapping[str, Any], *, root_id: str) -> dict[str, Any]:
    expected = {(item["program_id"], item["realization_id"]): item for item in expected_cells(root_id)}
    key = (value.get("program_id"), value.get("realization_id"))
    if key not in expected or value.get("root_id") != root_id or value.get("family") != ROOT_FAMILY[root_id]:
        raise PilotContractError("pilot cell identity differs from frozen root contract")
    if value.get("status") not in {"PLANNED", "RUNNING", "FAILED", "ACCEPTED"}:
        raise PilotContractError("pilot cell status is invalid")
    return dict(value)


def build_pilot_plan() -> dict[str, Any]:
    roots = {root: {"contract": planned_root_contract(root), "contract_sha256": root_contract_sha256(root), "cells": expected_cells(root)} for root in ROOTS}
    return {
        "schema_version": "cmf_f2_f3_pilot_plan_v1",
        "task_id": "f2_f3_redesign_20260907",
        "status": "PLANNED",
        "new_input_target": 24,
        "roots": roots,
        "read_only_prior_cells": 24,
        "combined_index_target": 48,
        "formal_data": False,
        "training": False,
        "hashes": {root: root_contract_sha256(root) for root in ROOTS},
    }


# v2 overrides are intentionally at the end so the historical v1 module is
# copied verbatim above while every v2 caller sees a new, explicit contract.
ROOTS = ("F2-A-v2", "F2-B-v2", "F3-A-v2", "F3-B-v2")
ROOT_FAMILY = {root: root[:2] for root in ROOTS}
PROGRAMS = {"F2": ("inside", "on", "beside"), "F3": ("VVHH", "VHVH", "VHHV")}
ROOT_REALIZATION = {"F2-A-v2": "r_inv_path", "F2-B-v2": "r_inv_motion", "F3-A-v2": "r_inv_path", "F3-B-v2": "r_inv_motion"}


def planned_root_contract(root_id: str) -> dict[str, Any]:
    if root_id not in ROOTS:
        raise PilotContractError("unknown v2 pilot root")
    family = ROOT_FAMILY[root_id]
    realization = ROOT_REALIZATION[root_id]
    first = {"F2-A-v2": "beside:r_pc", "F2-B-v2": "inside:r_pc", "F3-A-v2": "VHVH:r_pc", "F3-B-v2": "VVHH:r_pc"}[root_id]
    remainder = [f"{program}:{item}" for program in PROGRAMS[family] for item in ("r_pc", realization) if f"{program}:{item}" != first]
    return {
        "schema_version": "cmf_f2_f3_pilot_root_contract_v2",
        "root_id": root_id,
        "family": family,
        "scene_seed": {"F2-A-v2": 202609101, "F2-B-v2": 202609102, "F3-A-v2": 202609103, "F3-B-v2": 202609104}[root_id],
        "scene_spec_id": root_id,
        "program_ids": list(PROGRAMS[family]),
        "realization_ids": ["r_pc", realization],
        "execution_order": [first, *remainder],
        "shared_prefix_required": True,
        "prefix_replay_mode": "exact_bytes",
        "suffix_online_planning_allowed": True,
        "formal_data": False,
        "stage0_data": False,
        "collection": True,
        "status": "PLANNED",
    }
