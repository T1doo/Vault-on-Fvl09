"""Independent disk finalizer for v2 cells and roots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .canonical import atomic_write_json, canonical_sha256, sha256_file
from .f2_geometry_v2 import verify_expected_relation
from .observations import read_bundle


def _quat_distance(a: Any, b: Any) -> float:
    x = np.asarray(a, dtype=float); y = np.asarray(b, dtype=float); x /= np.linalg.norm(x); y /= np.linalg.norm(y)
    return float(2 * np.arccos(np.clip(abs(np.dot(x, y)), -1, 1)))


def _prefix_check(trace_path: Path, artifact_path: Path, end_row: int) -> dict[str, Any]:
    with np.load(trace_path, allow_pickle=False) as trace, np.load(artifact_path, allow_pickle=False) as artifact:
        mapping = {"effective_setpoint": "controller_effective_setpoint", "requested_command": "requested_command", "component_mask": "component_masks", "left_gripper_joint_drive_target": "left_gripper_joint_drive_target", "right_gripper_joint_drive_target": "right_gripper_joint_drive_target", "left_gripper_joint_drive_velocity_target": "left_gripper_joint_drive_velocity_target", "right_gripper_joint_drive_velocity_target": "right_gripper_joint_drive_velocity_target"}
        fields = {}
        for dst, src in mapping.items():
            a = np.asarray(trace[src][: end_row + 1]); b = np.asarray(artifact[dst])
            fields[dst] = {"shape_trace": list(a.shape), "shape_artifact": list(b.shape), "exact_bytes": a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes(), "max_abs_difference": float(np.max(np.abs(a.astype(float) - b.astype(float)))) if a.size and a.shape == b.shape else None}
        return {"fields": fields, "pass": all(v["exact_bytes"] for v in fields.values())}


def finalize_cell(*, cell_dir: Path, spec: dict[str, Any], expected_relation: str | None = None) -> dict[str, Any]:
    receipt = json.loads((cell_dir / "cell_receipt.json").read_text(encoding="utf-8"))
    trace_path = Path(receipt["trace_path"])
    bundle_path = cell_dir / "current"
    result: dict[str, Any] = {"schema_version": "cmf_f2_f3_independent_cell_finalizer_v2", "cell": f"{receipt.get('root_id')}:{receipt.get('program_id')}:{receipt.get('realization_id')}", "runner_pass_ignored": receipt.get("status"), "trace_sha256": sha256_file(trace_path), "checks": {}}
    bundle = read_bundle(bundle_path)
    result["checks"]["t0_bundle"] = bundle["checks"]
    result["checks"]["trace_structure"] = _trace_structure(trace_path)
    artifact = cell_dir.parent / "prefix_artifact.npz"
    if artifact.is_file() and receipt.get("prefix_end_trace_row") is not None:
        result["checks"]["actual_prefix"] = _prefix_check(trace_path, artifact, int(receipt["prefix_end_trace_row"]))
    else:
        result["checks"]["actual_prefix"] = {"pass": False, "reason": "missing root prefix artifact"}
    if expected_relation and spec["family"] == "F2":
        with np.load(trace_path, allow_pickle=False) as data:
            pose = data["object_pose"][-1]
        result["checks"]["f2_relation"] = verify_expected_relation(program_id=expected_relation, pose=pose, spec=spec, contact={"stand_top_contact": receipt.get("support_identity") == "f2_redesign_stand"})
    if spec["family"] == "F3":
        result["checks"]["f3_rest"] = _f3_rest_check(trace_path, receipt, spec)
    result["pass"] = all(value.get("pass", False) if isinstance(value, dict) else bool(value) for value in result["checks"].values())
    result["finalizer_sha256"] = canonical_sha256(result)
    atomic_write_json(cell_dir / "independent_finalizer_v2.json", result)
    return result


def _trace_structure(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as data:
        n = int(data["step_index"].shape[0]); effective = data["controller_effective_setpoint"]; q = data["joint_qpos"]; v = data["joint_qvel"]
        checks = {"step_index": bool(np.array_equal(data["step_index"], np.arange(n))), "250hz": bool(np.allclose(np.diff(data["timestamp"]), 0.004, atol=1e-7, rtol=0)), "effective_26": effective.shape == (n, 26), "qpos_38": q.shape == (n, 38), "qvel_38": v.shape == (n, 38), "initial_one": bool(data["initial_state"][0]) and int(np.count_nonzero(data["initial_state"])) == 1, "pass": True}
    checks["pass"] = all(checks.values()); return checks


def _f3_rest_check(path: Path, receipt: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    target = receipt.get("rest_target")
    if not isinstance(target, list) or len(target) != 7:
        return {"pass": False, "reason": "predeclared rest target missing"}
    with np.load(path, allow_pickle=False) as data:
        eef = data["eef_pose"][-1]; object_pose = data["object_pose"][-1]; anchor = data["object_pose"][0]
        result = {"object_return_position_m": float(np.linalg.norm(object_pose[:3] - anchor[:3])), "object_return_orientation_rad": _quat_distance(object_pose[3:], anchor[3:]), "eef_rest_position_m": float(np.linalg.norm(eef[:3] - np.asarray(target[:3]))), "eef_rest_orientation_rad": _quat_distance(eef[3:], target[3:]), "rest_target": target}
        result["pass"] = result["eef_rest_position_m"] <= spec["f3"]["rest_position_tolerance_m"] and result["eef_rest_orientation_rad"] <= spec["f3"]["rest_orientation_tolerance_rad"]
        return result


def _variant_check(baseline: dict[str, Any], alternative: dict[str, Any]) -> dict[str, Any]:
    """Prove an r_inv suffix changed in the declared way from real arrays."""
    bpath = Path(baseline["trace_path"]); apath = Path(alternative["trace_path"])
    bprefix = int(baseline["prefix_end_trace_row"]); aprefix = int(alternative["prefix_end_trace_row"])
    with np.load(bpath, allow_pickle=False) as b, np.load(apath, allow_pickle=False) as a:
        bprefix_array = b["controller_effective_setpoint"][: bprefix + 1]
        aprefix_array = a["controller_effective_setpoint"][: aprefix + 1]
        prefix_equal = bprefix_array.shape == aprefix_array.shape and bprefix_array.tobytes() == aprefix_array.tobytes()
        b_suffix = b["controller_effective_setpoint"][bprefix + 1 :]
        a_suffix = a["controller_effective_setpoint"][aprefix + 1 :]
        command_changed = b_suffix.shape != a_suffix.shape or b_suffix.tobytes() != a_suffix.tobytes()
        b_eef = b["eef_pose"][bprefix + 1 :, :3]; a_eef = a["eef_pose"][aprefix + 1 :, :3]
        b_path_length = float(np.linalg.norm(np.diff(b_eef, axis=0), axis=1).sum()) if len(b_eef) > 1 else 0.0
        a_path_length = float(np.linalg.norm(np.diff(a_eef, axis=0), axis=1).sum()) if len(a_eef) > 1 else 0.0
    kind = str(alternative.get("realization_contract", {}).get("kind", ""))
    if kind == "path":
        changed = command_changed and a_path_length > b_path_length + 1e-5
    elif kind == "motion":
        changed = command_changed and len(a_suffix) != len(b_suffix)
    else:
        changed = False
    return {"kind": kind, "same_prefix_actual": prefix_equal, "suffix_command_changed": command_changed, "baseline_suffix_rows": int(len(b_suffix)), "alternative_suffix_rows": int(len(a_suffix)), "baseline_suffix_path_length_m": b_path_length, "alternative_suffix_path_length_m": a_path_length, "variant_effect_observed": changed, "pass": bool(prefix_equal and changed)}


def finalize_root(*, root_dir: Path, spec: dict[str, Any]) -> dict[str, Any]:
    root = json.loads((root_dir / "root_receipt.json").read_text(encoding="utf-8"))
    cells = [cell for cell in root.get("cells", []) if cell.get("status") == "cell_pass"]
    if len(cells) != 6:
        result = {"schema_version": "cmf_f2_f3_independent_root_finalizer_v2", "root_id": root.get("root_id"), "pass": False, "reason": "root is incomplete or has a failed cell", "cell_count": len(cells)}
        atomic_write_json(root_dir / "independent_root_finalizer_v2.json", result); return result
    cell_results = []
    for cell in cells:
        cell_dir = root_dir / f"{cell['program_id']}_{cell['realization_id']}"
        cell_results.append(finalize_cell(cell_dir=cell_dir, spec=spec, expected_relation=cell.get("program_id") if spec["family"] == "F2" else None))
    variants = []
    for program in spec["candidate_set_schema"]["relations" if spec["family"] == "F2" else "programs"]:
        pair = [cell for cell in cells if cell.get("program_id") == program]
        if len(pair) != 2: variants.append({"program_id": program, "pass": False, "reason": "missing two realizations"}); continue
        baseline = next((cell for cell in pair if cell.get("realization_id") == "r_pc"), None); alternative = next((cell for cell in pair if cell.get("realization_id") != "r_pc"), None)
        variants.append({"program_id": program, "baseline": baseline.get("realization_id"), "alternative": alternative.get("realization_id"), **_variant_check(baseline, alternative)})
    initial_sigs = [json.loads((root_dir / f"{cell['program_id']}_{cell['realization_id']}" / "current" / "capture_metadata.json").read_text())["state_sha256"] for cell in cells]
    result = {"schema_version": "cmf_f2_f3_independent_root_finalizer_v2", "root_id": root.get("root_id"), "scene_spec_sha256": spec["spec_sha256"], "cell_finalizers": cell_results, "variant_checks": variants, "same_root_t0_state": len(set(initial_sigs)) == 1, "pass": len(cell_results) == 6 and all(item.get("pass") for item in cell_results) and all(item.get("pass") for item in variants) and len(set(initial_sigs)) == 1, "runner_pass_ignored": True, "research_eligibility": "ELIGIBLE_ONLY_IF_THIS_RESULT_AND_SOURCE_CAPTURE_AUDIT_PASS"}
    result["finalizer_sha256"] = canonical_sha256(result); atomic_write_json(root_dir / "independent_root_finalizer_v2.json", result); return result
