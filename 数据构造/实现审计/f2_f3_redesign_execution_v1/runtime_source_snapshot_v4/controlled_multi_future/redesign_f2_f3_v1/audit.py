"""CPU-only audit for accepted pilot traces and strict observable exits."""

from __future__ import annotations

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
            "effective_setpoint_26d": effective.ndim == 2 and effective.shape[1] == 26,
            "requested_setpoint_26d": requested.ndim == 2 and requested.shape[1] == 26,
            "qpos_n_plus_one_shape": data["joint_qpos"].shape[0] == n,
            "qvel_n_plus_one_shape": data["joint_qvel"].shape[0] == n,
            "timestamps_250hz": n < 2 or bool(np.allclose(np.diff(timestamps), 0.004, rtol=0.0, atol=1e-7)),
            "finite_effective": bool(np.isfinite(effective).all()),
            "finite_requested": bool(np.isfinite(requested).all()),
        }
        result.update({"sample_count": n, "action_count": max(0, n - 1), "checks": checks, "pass": all(checks.values())})
    return result


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
        roots.append({"root_id": root["root_id"], "accepted": root.get("accepted") is True, "current_equivalence": root.get("current_equivalence") is True, "anchor_equivalence": root.get("anchor_equivalence") is True, "prefix_exact_replay": root.get("prefix_exact_replay") is True, "prefix_hash_count": len(prefix_hashes), "cells": cells})
    result = {"schema_version": "cmf_f2_f3_pilot_cpu_audit_v1", "roots": roots, "strict_exit": strict_exit_audit()}
    result["pass"] = bool(roots) and all(root["accepted"] and root["current_equivalence"] and root["anchor_equivalence"] and root["prefix_exact_replay"] and root["prefix_hash_count"] == 1 and all(cell["cell_status"] == "cell_pass" and cell["trace"]["pass"] for cell in root["cells"]) for root in roots) and result["strict_exit"]["pass"]
    atomic_write_json(output, result)
    return result
