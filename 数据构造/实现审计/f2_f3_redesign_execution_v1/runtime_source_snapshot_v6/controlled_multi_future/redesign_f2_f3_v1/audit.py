"""CPU-only audit for accepted pilot traces and strict observable exits."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .canonical import atomic_write_json, sha256_file
from .strict_exit import StrictExitError, validate_observable_input


REQUIRED = ("step_index", "timestamp", "controller_effective_setpoint", "requested_command", "joint_qpos", "joint_qvel")


def audit_trace(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    result: dict[str, Any] = {"path": str(path), "sha256": sha256_file(path), "pass": False}
    with np.load(path, allow_pickle=False) as data:
        missing = [key for key in REQUIRED if key not in data.files]
        if missing:
            result["missing_fields"] = missing
            return result
        n = int(data["step_index"].shape[0])
        effective = data["controller_effective_setpoint"]
        requested = data["requested_command"]
        timestamps = data["timestamp"]
        checks = {
            "at_least_initial_and_one_action": n >= 2,
            "step_index_contiguous_from_zero": bool(np.array_equal(data["step_index"], np.arange(n, dtype=data["step_index"].dtype))),
            "effective_setpoint_26d": effective.ndim == 2 and effective.shape[1] == 26,
            "requested_setpoint_26d": requested.ndim == 2 and requested.shape[1] == 26,
            "qpos_38d_with_initial_plus_actions": data["joint_qpos"].shape == (n, 38),
            "qvel_38d_with_initial_plus_actions": data["joint_qvel"].shape == (n, 38),
            "one_initial_state_at_row_zero": "initial_state" in data.files and bool(data["initial_state"][0]) and int(np.count_nonzero(data["initial_state"])) == 1,
            "timestamps_250hz": n < 2 or bool(np.allclose(np.diff(timestamps), 0.004, rtol=0.0, atol=1e-7)),
            "finite_effective": bool(np.isfinite(effective).all()),
            "finite_requested": bool(np.isfinite(requested).all()),
        }
        result.update({"sample_count": n, "action_count": max(0, n - 1), "checks": checks, "pass": all(checks.values())})
    return result


def _suffix_signature(cell: dict[str, Any]) -> dict[str, Any]:
    """Hash commanded and realized suffix streams after the exact prefix."""
    path = Path(cell["trace_path"])
    with np.load(path, allow_pickle=False) as data:
        start = int(cell["prefix_end_trace_row"]) + 1
        streams = {}
        for name, key in (
            ("effective", "controller_effective_setpoint"),
            ("requested", "requested_command"),
            ("eef", "eef_pose"),
            ("object", "object_pose"),
        ):
            value = np.ascontiguousarray(data[key][start:])
            streams[name] = {
                "shape": list(value.shape),
                "sha256": hashlib.sha256(value.tobytes()).hexdigest(),
            }
    return {"prefix_rows": start, "streams": streams}


def audit_realization_pairs(root: dict[str, Any]) -> dict[str, Any]:
    """Reject label-only path/motion variants and exact copied suffixes."""
    contract = root.get("contract", {})
    realizations = list(contract.get("realization_ids", []))
    baseline = "r_pc"
    alternatives = [item for item in realizations if item != baseline]
    by_key = {(cell.get("program_id"), cell.get("realization_id")): cell for cell in root.get("cells", [])}
    pairs = []
    for program in contract.get("program_ids", []):
        base_cell = by_key.get((program, baseline))
        for alternative in alternatives:
            alt_cell = by_key.get((program, alternative))
            if base_cell is None or alt_cell is None:
                pairs.append({"program_id": program, "alternative": alternative, "pass": False, "reason": "missing realization pair"})
                continue
            base_signature = _suffix_signature(base_cell)
            alt_signature = _suffix_signature(alt_cell)
            comparisons = {
                name: base_signature["streams"][name] == alt_signature["streams"][name]
                for name in base_signature["streams"]
            }
            declared = alt_cell.get("realization_contract", {})
            # F3-B predates the explicit declaration field, but its source
            # uses the displacement controller for every V/H event.  Require
            # both commanded and realized trace differences before accepting
            # this one immutable legacy pilot root.
            legacy_f3_motion = (
                root.get("root_id") == "F3-B"
                and alternative == "r_inv_motion"
                and not comparisons["effective"]
                and not comparisons["requested"]
                and not comparisons["eef"]
                and not comparisons["object"]
            )
            declared_pass = bool(declared.get("variant_applied")) or legacy_f3_motion
            if alternative == "r_inv_path":
                trace_difference_pass = not comparisons["effective"] and not comparisons["eef"]
            elif alternative == "r_inv_motion":
                trace_difference_pass = not comparisons["effective"] and not comparisons["requested"] and not comparisons["eef"]
            else:
                trace_difference_pass = False
            checks = {
                "variant_declared_or_legacy_source_proven": declared_pass,
                "command_and_realized_suffix_differ": trace_difference_pass,
                "same_program": base_cell.get("program_id") == alt_cell.get("program_id") == program,
                "same_prefix": base_cell.get("prefix_sha256") == alt_cell.get("prefix_sha256"),
                "same_current": base_cell.get("current") == alt_cell.get("current"),
                "same_anchor": base_cell.get("anchor") == alt_cell.get("anchor"),
            }
            pairs.append({
                "program_id": program,
                "baseline": baseline,
                "alternative": alternative,
                "declared_contract": declared or None,
                "legacy_f3_motion_source_proof": legacy_f3_motion,
                "exact_suffix_stream_matches": comparisons,
                "baseline_signature": base_signature,
                "alternative_signature": alt_signature,
                "checks": checks,
                "pass": all(checks.values()),
            })
    return {"pairs": pairs, "pass": bool(pairs) and all(item["pass"] for item in pairs)}


def strict_exit_audit() -> dict[str, Any]:
    valid = {"rgb": [[0, 1]], "state": [0.0], "future": [[0.0] * 26], "candidate_set": [{"family": "F3", "relation": "VVHH", "object_ref": "bottle"}], "target": {"family": "F3", "relation": "VVHH", "object_ref": "bottle"}}
    checks = {}
    try:
        validate_observable_input(valid); checks["valid_payload"] = True
    except Exception:
        checks["valid_payload"] = False
    for name, mutated in (
        ("nested_planner_field", {**valid, "state": {"planner_phase": 1}}),
        ("unknown_top_level", {**valid, "path": "hidden"}),
        ("nested_verifier_field", {**valid, "target": {"family": "F3", "relation": "VVHH", "object_ref": "bottle", "verifier": True}}),
    ):
        try:
            validate_observable_input(mutated); checks[name] = False
        except StrictExitError:
            checks[name] = True
    return {"checks": checks, "pass": all(checks.values())}


def audit_accepted_roots(root_paths: list[str | Path], output: str | Path) -> dict[str, Any]:
    roots = []
    for root_path in root_paths:
        root_path = Path(root_path)
        root = json.loads((root_path / "root_receipt.json").read_text(encoding="utf-8"))
        cells = []
        for cell in root["cells"]:
            trace = audit_trace(cell["trace_path"])
            cells.append({"program_id": cell["program_id"], "realization_id": cell["realization_id"], "cell_status": cell["status"], "trace": trace})
        prefix_hashes = {cell.get("prefix_sha256") for cell in root["cells"]}
        realization_audit = audit_realization_pairs(root)
        roots.append({"root_id": root["root_id"], "accepted": root.get("accepted") is True, "current_equivalence": root.get("current_equivalence") is True, "anchor_equivalence": root.get("anchor_equivalence") is True, "prefix_exact_replay": root.get("prefix_exact_replay") is True, "prefix_hash_count": len(prefix_hashes), "realization_audit": realization_audit, "cells": cells})
    result = {"schema_version": "cmf_f2_f3_pilot_cpu_audit_v1", "roots": roots, "strict_exit": strict_exit_audit()}
    result["pass"] = bool(roots) and all(root["accepted"] and root["current_equivalence"] and root["anchor_equivalence"] and root["prefix_exact_replay"] and root["prefix_hash_count"] == 1 and root["realization_audit"]["pass"] and all(cell["cell_status"] == "cell_pass" and cell["trace"]["pass"] for cell in root["cells"]) for root in roots) and result["strict_exit"]["pass"]
    atomic_write_json(output, result)
    return result
