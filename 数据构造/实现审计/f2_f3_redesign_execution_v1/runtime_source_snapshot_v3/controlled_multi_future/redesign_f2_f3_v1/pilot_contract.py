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


def selected_cells(root_id: str, programs: list[str] | tuple[str, ...] | None = None) -> list[dict[str, str]]:
    """Return the frozen cell order for a full root or a program subset.

    A subset is used only for a resume job whose remaining cells are joined
    with immutable receipts from the same root.  It never changes the root's
    six-cell contract.
    """
    cells = expected_cells(root_id)
    if programs is None:
        return cells
    allowed = set(PROGRAMS[ROOT_FAMILY[root_id]])
    requested = tuple(programs)
    if not requested or not set(requested).issubset(allowed):
        raise PilotContractError("resume program subset is outside the frozen root contract")
    if len(set(requested)) != len(requested):
        raise PilotContractError("resume program subset contains duplicates")
    selected = [cell for cell in cells if cell["program_id"] in set(requested)]
    if len(selected) != len(requested) * len(planned_root_contract(root_id)["realization_ids"]):
        raise PilotContractError("resume program subset did not select complete realization pairs")
    return selected


def reusable_cells(root_receipt: Mapping[str, Any], root_id: str, programs: list[str] | tuple[str, ...]) -> list[dict[str, Any]]:
    """Validate and return accepted cells that can be referenced by a resume root."""
    expected = {(cell["program_id"], cell["realization_id"]): cell for cell in selected_cells(root_id, programs)}
    source = {(cell.get("program_id"), cell.get("realization_id")): cell for cell in root_receipt.get("cells", [])}
    if root_receipt.get("root_id") != root_id or root_receipt.get("family") != ROOT_FAMILY[root_id]:
        raise PilotContractError("resume source root differs from frozen root contract")
    if set(source) < set(expected):
        raise PilotContractError("resume source root is missing requested cells")
    result = []
    for key in expected:
        cell = source[key]
        if cell.get("status") != "cell_pass":
            raise PilotContractError("resume source contains a non-passing reusable cell")
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
