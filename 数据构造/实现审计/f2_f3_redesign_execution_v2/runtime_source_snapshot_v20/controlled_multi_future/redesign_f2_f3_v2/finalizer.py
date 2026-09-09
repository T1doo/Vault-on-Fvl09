"""Independent disk finalizer for v2 cells and roots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from ..signals import closed_loop_event_metrics
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
        can_name = "f2_redesign_can"
        stand_top_fraction = _contact_fraction(trace_path, can_name, "f2_redesign_stand")
        expected_support = spec["f2"]["support_identity_by_relation"][expected_relation]
        expected_support_fraction = _contact_fraction(trace_path, can_name, expected_support)
        result["checks"]["f2_support"] = {"expected_support": expected_support, "fraction": expected_support_fraction, "pass": expected_support_fraction >= 0.8}
        relation = verify_expected_relation(program_id=expected_relation, pose=pose, spec=spec, contact={"stand_top_contact": stand_top_fraction >= 0.5})
        relation["stand_top_contact_fraction"] = stand_top_fraction
        result["checks"]["f2_relation"] = relation
        result["checks"]["f2_trace"] = _f2_trace_check(trace_path, receipt, spec, expected_relation)
    if spec["family"] == "F3":
        result["checks"]["f3_trace"] = _f3_trace_check(trace_path, receipt, spec)
    result["pass"] = all(value.get("pass", False) if isinstance(value, dict) else bool(value) for value in result["checks"].values())
    result["finalizer_sha256"] = canonical_sha256(result)
    atomic_write_json(cell_dir / "independent_finalizer_v2.json", result)
    return result


def _trace_structure(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as data:
        n = int(data["step_index"].shape[0]); effective = data["controller_effective_setpoint"]; q = data["joint_qpos"]; v = data["joint_qvel"]
        checks = {"step_index": bool(np.array_equal(data["step_index"], np.arange(n))), "250hz": bool(np.allclose(np.diff(data["timestamp"]), 0.004, atol=1e-7, rtol=0)), "effective_26": effective.shape == (n, 26), "qpos_38": q.shape == (n, 38), "qvel_38": v.shape == (n, 38), "finite_core": bool(np.isfinite(effective).all() and np.isfinite(q).all() and np.isfinite(v).all()), "initial_one": bool(data["initial_state"][0]) and int(np.count_nonzero(data["initial_state"])) == 1, "pass": True}
    checks["pass"] = all(checks.values()); return checks


def _contact_fraction(path: Path, first: str, second: str, window: int = 50) -> float:
    with np.load(path, allow_pickle=False) as data:
        rows = data["contact_pairs_json"][-window:]
    matched = []
    for encoded in rows:
        pairs = json.loads(str(encoded))
        matched.append(any({str(item.get("body_a", "")), str(item.get("body_b", ""))} == {first, second} for item in pairs))
    return float(np.mean(matched)) if matched else 0.0


def _contact_fraction_range(path: Path, first: str, second: str, start: int, end: int) -> float:
    with np.load(path, allow_pickle=False) as data:
        rows = data["contact_pairs_json"][max(0, int(start)): int(end) + 1]
    values = []
    for encoded in rows:
        pairs = json.loads(str(encoded))
        values.append(any({str(item.get("body_a", "")), str(item.get("body_b", ""))} == {first, second} for item in pairs))
    return float(np.mean(values)) if values else 0.0


def _trace_event_metrics(path: Path, start: int, end: int, axis: str) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as data:
        eef = np.asarray(data["eef_pose"][start: end + 1, :3], dtype=float)
        obj = np.asarray(data["object_pose"][start: end + 1], dtype=float)
        contact = np.asarray(data["selected_gripper_contact"][start: end + 1], dtype=bool)
    main_axis = 2 if axis == "V" else 0
    eef_metrics = closed_loop_event_metrics(eef, eef[0], main_axis)
    obj_metrics = closed_loop_event_metrics(obj[:, :3], obj[0, :3], main_axis)
    breaks = int(np.count_nonzero(contact[:-1] & ~contact[1:])) if len(contact) > 1 else int(not bool(contact[0]))
    return {
        "axis": axis,
        "row_count": int(len(eef)),
        "eef_positive_amplitude": eef_metrics["positive_amplitude"],
        "eef_negative_amplitude": eef_metrics["negative_amplitude"],
        "eef_max_off_axis": eef_metrics["max_off_axis"],
        "eef_return_error": eef_metrics["return_error"],
        "bottle_positive_amplitude": obj_metrics["positive_amplitude"],
        "bottle_negative_amplitude": obj_metrics["negative_amplitude"],
        "bottle_max_off_axis": obj_metrics["max_off_axis"],
        "bottle_return_error": obj_metrics["return_error"],
        "bottle_orientation_drift": max(_quat_distance(obj[0, 3:], value[3:]) for value in obj),
        "selected_gripper_contact_fraction": float(contact.mean()) if len(contact) else 0.0,
        "contact_break_count": breaks,
    }


def _motion_gate(metrics: dict[str, Any]) -> dict[str, bool]:
    return {
        "eef_positive_amplitude": metrics["eef_positive_amplitude"] >= 0.040,
        "eef_negative_amplitude": metrics["eef_negative_amplitude"] >= 0.040,
        "bottle_positive_amplitude": metrics["bottle_positive_amplitude"] >= 0.040,
        "bottle_negative_amplitude": metrics["bottle_negative_amplitude"] >= 0.040,
        "eef_off_axis": metrics["eef_max_off_axis"] <= 0.015,
        "bottle_off_axis": metrics["bottle_max_off_axis"] <= 0.015,
        "eef_return": metrics["eef_return_error"] <= 0.015,
        "bottle_return": metrics["bottle_return_error"] <= 0.015,
        "bottle_orientation": metrics["bottle_orientation_drift"] <= 0.050,
        "selected_gripper_contact": metrics["selected_gripper_contact_fraction"] >= 0.950,
        "contact_breaks": metrics["contact_break_count"] == 0,
    }


def _f3_trace_check(path: Path, receipt: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    evidence = receipt.get("prefix_event_evidence")
    if not isinstance(evidence, dict) or not isinstance(evidence.get("start_row"), int) or not isinstance(evidence.get("end_row"), int):
        return {"pass": False, "reason": "shared first-V evidence missing from receipt"}
    shared_metrics = _trace_event_metrics(path, evidence["start_row"], evidence["end_row"], "V")
    events.append({"label": "shared_V", "start_row": evidence["start_row"], "end_row": evidence["end_row"], "metrics": shared_metrics, "checks": _motion_gate(shared_metrics)})
    suffix = receipt.get("expected_suffix_event_order")
    segments = receipt.get("event_segments")
    if not isinstance(suffix, list) or not isinstance(segments, list) or len(segments) != 3:
        return {"pass": False, "shared_V": events, "reason": "suffix event evidence missing"}
    for expected_axis, segment in zip(suffix, segments):
        if segment.get("axis") != expected_axis:
            return {"pass": False, "shared_V": events, "reason": "event order metadata mismatch"}
        metrics = _trace_event_metrics(path, int(segment["start_row"]), int(segment["end_row"]), str(expected_axis))
        events.append({"label": f"suffix_{expected_axis}", "start_row": int(segment["start_row"]), "end_row": int(segment["end_row"]), "metrics": metrics, "checks": _motion_gate(metrics)})
    with np.load(path, allow_pickle=False) as data:
        tail = slice(max(0, len(data["step_index"]) - 50), None)
        obj_speed = np.linalg.norm(data["object_linear_velocity"][tail], axis=1)
        eef_speed = np.linalg.norm(data["eef_linear_velocity"][tail], axis=1)
        eef_angular = np.linalg.norm(data["eef_angular_velocity"][tail], axis=1)
        gripper = np.asarray(data["gripper_command"][tail, 0], dtype=float)
        selected_contact = np.asarray(data["selected_gripper_contact"][tail], dtype=bool)
        object_pose = np.asarray(data["object_pose"], dtype=float)
        object_return_position = float(np.linalg.norm(object_pose[-1, :3] - object_pose[0, :3]))
        object_return_orientation = _quat_distance(object_pose[-1, 3:], object_pose[0, 3:])
    support_fraction = _contact_fraction(path, "f3_redesign_bottle", "f3_redesign_support_pad")
    terminal = {
        "object_return_position_m": object_return_position,
        "object_return_orientation_rad": object_return_orientation,
        "object_stable_window": bool(np.all(obj_speed <= 0.020)),
        "eef_linear_stationary": bool(np.all(eef_speed <= 0.010)),
        "eef_angular_stationary": bool(np.all(eef_angular <= 0.050)),
        "support_contact_window": support_fraction >= 0.95,
        "gripper_open_window": bool(np.all(gripper >= 0.9)),
        "empty_hand_window": bool(not np.any(selected_contact)),
    }
    rest = _f3_rest_check(path, receipt, spec)
    terminal["object_return"] = object_return_position <= 0.030 and object_return_orientation <= 0.020
    terminal["pass"] = all(terminal.values()) and rest.get("pass", False)
    return {"pass": terminal["pass"] and all(all(event["checks"].values()) for event in events), "events": events, "terminal": terminal, "rest": rest}


def _f2_trace_check(path: Path, receipt: dict[str, Any], spec: dict[str, Any], expected_relation: str) -> dict[str, Any]:
    support_end = int(receipt.get("support_end_trace_row", -1))
    if support_end < 0:
        return {"pass": False, "reason": "support boundary missing"}
    support = spec["f2"]["support_identity_by_relation"][expected_relation]
    support_fraction = _contact_fraction_range(path, "f2_redesign_can", support, max(0, support_end - 59), support_end)
    stand_top_fraction = _contact_fraction_range(path, "f2_redesign_can", "f2_redesign_stand", max(0, support_end - 59), support_end)
    with np.load(path, allow_pickle=False) as data:
        tail = slice(max(0, len(data["step_index"]) - 50), None)
        speed = np.linalg.norm(data["object_linear_velocity"][tail], axis=1)
        angular = np.linalg.norm(data["object_angular_velocity"][tail], axis=1)
        eef_speed = np.linalg.norm(data["eef_linear_velocity"][tail], axis=1)
        eef_angular = np.linalg.norm(data["eef_angular_velocity"][tail], axis=1)
        open_values = np.asarray(data["gripper_command"][tail, 0], dtype=float)
        selected_contact = np.asarray(data["selected_gripper_contact"][tail], dtype=bool)
        pose = data["object_pose"][-1]
        eef_final = np.asarray(data["eef_pose"][-1], dtype=float)
    relation = verify_expected_relation(program_id=expected_relation, pose=pose, spec=spec, contact={"stand_top_contact": stand_top_fraction >= 0.5})
    checks = {
        "relation": relation.get("pass", False),
        "expected_support_window": support_fraction >= 0.8,
        "unexpected_stand_top_absent": stand_top_fraction < 0.5,
        "object_stable_window": bool(np.all(speed <= 0.020) and np.all(angular <= 0.050)),
        "release_open_window": bool(np.all(open_values >= 0.9)),
        "release_contact_absent": bool(np.all(~selected_contact)),
        "eef_stationary_window": bool(np.all(eef_speed <= 0.010) and np.all(eef_angular <= 0.050)),
        "exit_target_reached": isinstance(receipt.get("exit_target"), list) and len(receipt["exit_target"]) == 7 and float(np.linalg.norm(eef_final[:3] - np.asarray(receipt["exit_target"][:3], dtype=float))) <= 0.030 and _quat_distance(eef_final[3:], receipt["exit_target"][3:]) <= 0.020,
    }
    return {"pass": all(checks.values()), "checks": checks, "relation": relation, "support_fraction": support_fraction, "stand_top_fraction": stand_top_fraction}


def _f3_rest_check(path: Path, receipt: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    target = receipt.get("rest_target")
    if not isinstance(target, list) or len(target) != 7:
        return {"pass": False, "reason": "predeclared rest target missing"}
    capture_metadata = path.parent / "current" / "capture_metadata.json"
    if not capture_metadata.is_file():
        return {"pass": False, "reason": "action-before-observation rest binding missing"}
    metadata_target = json.loads(capture_metadata.read_text(encoding="utf-8")).get("rest_target")
    binding_pass = metadata_target == target
    with np.load(path, allow_pickle=False) as data:
        eef = data["eef_pose"][-1]; object_pose = data["object_pose"][-1]; anchor = data["object_pose"][0]
        result = {"object_return_position_m": float(np.linalg.norm(object_pose[:3] - anchor[:3])), "object_return_orientation_rad": _quat_distance(object_pose[3:], anchor[3:]), "eef_rest_position_m": float(np.linalg.norm(eef[:3] - np.asarray(target[:3]))), "eef_rest_orientation_rad": _quat_distance(eef[3:], target[3:]), "rest_target": target, "rest_binding_in_action_before_observation_metadata": binding_pass}
        result["pass"] = binding_pass and result["eef_rest_position_m"] <= spec["f3"]["rest_position_tolerance_m"] and result["eef_rest_orientation_rad"] <= spec["f3"]["rest_orientation_tolerance_rad"]
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
        cell_dir = Path(cell["trace_path"]).parent
        cell_results.append(finalize_cell(cell_dir=cell_dir, spec=spec, expected_relation=cell.get("program_id") if spec["family"] == "F2" else None))
    variants = []
    for program in spec["candidate_set_schema"]["relations" if spec["family"] == "F2" else "programs"]:
        pair = [cell for cell in cells if cell.get("program_id") == program]
        if len(pair) != 2: variants.append({"program_id": program, "pass": False, "reason": "missing two realizations"}); continue
        baseline = next((cell for cell in pair if cell.get("realization_id") == "r_pc"), None); alternative = next((cell for cell in pair if cell.get("realization_id") != "r_pc"), None)
        variants.append({"program_id": program, "baseline": baseline.get("realization_id"), "alternative": alternative.get("realization_id"), **_variant_check(baseline, alternative)})
    current_bundles = [Path(cell["trace_path"]).parent / "current" for cell in cells]
    initial_sigs = [json.loads((bundle / "capture_metadata.json").read_text(encoding="utf-8"))["state_sha256"] for bundle in current_bundles]
    image_sigs = [json.loads((bundle / "capture_metadata.json").read_text(encoding="utf-8"))["camera_images"] for bundle in current_bundles]
    same_images = all(image_sigs[0] == value for value in image_sigs[1:])
    result = {"schema_version": "cmf_f2_f3_independent_root_finalizer_v2", "root_id": root.get("root_id"), "scene_spec_sha256": spec["spec_sha256"], "cell_finalizers": cell_results, "variant_checks": variants, "same_root_t0_state": len(set(initial_sigs)) == 1, "same_root_t0_rgb": same_images, "pass": len(cell_results) == 6 and all(item.get("pass") for item in cell_results) and all(item.get("pass") for item in variants) and len(set(initial_sigs)) == 1 and same_images, "runner_pass_ignored": True, "research_eligibility": "ELIGIBLE_ONLY_IF_THIS_RESULT_AND_SOURCE_CAPTURE_AUDIT_PASS"}
    result["finalizer_sha256"] = canonical_sha256(result); atomic_write_json(root_dir / "independent_root_finalizer_v2.json", result); return result
