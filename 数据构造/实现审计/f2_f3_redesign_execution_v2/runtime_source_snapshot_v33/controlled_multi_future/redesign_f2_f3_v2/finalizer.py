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
from .observations import MODEL_CAMERAS, read_bundle
from .pilot_contract import frozen_realization_requirements


_F3_SUFFIX_BY_PROGRAM = {
    "VVHH": ("V", "H", "H"),
    "VHVH": ("H", "V", "H"),
    "VHHV": ("H", "H", "V"),
}
_PREFIX_FIELDS = (
    "effective_setpoint",
    "requested_command",
    "component_mask",
    "left_gripper_joint_drive_target",
    "right_gripper_joint_drive_target",
    "left_gripper_joint_drive_velocity_target",
    "right_gripper_joint_drive_velocity_target",
)
_VOLATILE_ANCHOR_KEYS = {
    "path", "root_id", "cell_key", "job", "pid", "ppid", "pgid",
    "receipt", "receipt_sha256", "sha256", "elapsed", "elapsed_seconds",
    "timestamp", "started_at", "finished_at", "run_id", "task_id",
    "worker_id", "trace_path", "output",
}


def _strip_runtime_identity(value: Any, key: str | None = None) -> Any:
    """Remove run/file identity while preserving the physical anchor payload."""
    if key in _VOLATILE_ANCHOR_KEYS:
        return None
    if isinstance(value, dict):
        return {
            name: cleaned
            for name, item in value.items()
            if name not in _VOLATILE_ANCHOR_KEYS
            for cleaned in (_strip_runtime_identity(item, name),)
        }
    if isinstance(value, list):
        return [_strip_runtime_identity(item) for item in value]
    return value


def _anchor_signature(bundle_path: Path) -> str:
    anchor = json.loads((bundle_path / "anchor.json").read_text(encoding="utf-8"))
    return canonical_sha256(_strip_runtime_identity(anchor))


def _prefix_artifact_hash(path: Path) -> str:
    with np.load(path, allow_pickle=False) as artifact:
        return canonical_sha256({name: np.asarray(artifact[name]).tolist() for name in _PREFIX_FIELDS})


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
        return {"fields": fields, "artifact_sha256": _prefix_artifact_hash(artifact_path), "pass": all(v["exact_bytes"] for v in fields.values())}


def _trace_row0_check(trace_path: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    """Compare the persisted t0 bundle with the actual first trace row."""
    state = bundle.get("state", {})
    checks: dict[str, bool] = {}
    try:
        with np.load(trace_path, allow_pickle=False) as trace:
            if int(trace["step_index"].shape[0]) < 1:
                return {"pass": False, "reason": "trace has no row0", "fields": checks}

            def compare(trace_key: str, state_key: str, *, required: bool = True) -> None:
                present = trace_key in trace and state_key in state
                checks[f"{trace_key}__{state_key}__present"] = present if required else True
                if not present:
                    return
                actual = np.asarray(trace[trace_key][0])
                expected = np.asarray(state[state_key])
                checks[f"{trace_key}__{state_key}"] = actual.shape == expected.shape and actual.dtype.kind in "fiu" and expected.dtype.kind in "fiu" and np.array_equal(actual, expected)

            compare("joint_qpos", "joint_qpos")
            compare("joint_qvel", "joint_qvel")
            compare("joint_qf", "joint_qf")
            compare("eef_pose", "eef_pose")
            compare("gripper_command", "gripper_command")
            compare("left_gripper_joint_drive_target", "left_gripper_drive_target")
            compare("right_gripper_joint_drive_target", "right_gripper_drive_target")
            compare("left_gripper_joint_drive_velocity_target", "left_gripper_drive_velocity_target")
            compare("right_gripper_joint_drive_velocity_target", "right_gripper_drive_velocity_target")

            role_poses = state.get("role_object_pose", {})
            if not isinstance(role_poses, dict) or not role_poses:
                checks["role_object_pose_bundle_present"] = False
            else:
                checks["role_object_pose_bundle_present"] = True
                for role, expected in sorted(role_poses.items()):
                    key = f"role_object_pose__{role}"
                    present = key in trace
                    checks[f"{key}__present"] = present
                    if present:
                        actual = np.asarray(trace[key][0])
                        expected_array = np.asarray(expected)
                        checks[key] = actual.shape == expected_array.shape and np.array_equal(actual, expected_array)
                dynamic_role = "main_can" if "main_can" in role_poses else "bottle" if "bottle" in role_poses else None
                checks["object_pose_dynamic_role"] = dynamic_role is not None and "object_pose" in trace and np.array_equal(np.asarray(trace["object_pose"][0]), np.asarray(role_poses[dynamic_role]))
    except (KeyError, OSError, ValueError, TypeError):
        return {"pass": False, "reason": "trace row0 or bundle state is unreadable", "fields": checks}
    return {"pass": bool(checks) and all(checks.values()), "fields": checks}


def finalize_cell(*, cell_dir: Path, spec: dict[str, Any], expected_relation: str | None = None, artifact_path: Path | None = None) -> dict[str, Any]:
    receipt = json.loads((cell_dir / "cell_receipt.json").read_text(encoding="utf-8"))
    trace_path = Path(receipt["trace_path"])
    bundle_path = cell_dir / "current"
    result: dict[str, Any] = {"schema_version": "cmf_f2_f3_independent_cell_finalizer_v2", "cell": f"{receipt.get('root_id')}:{receipt.get('program_id')}:{receipt.get('realization_id')}", "runner_pass_ignored": receipt.get("status"), "trace_sha256": sha256_file(trace_path), "checks": {}}
    try:
        bundle = read_bundle(bundle_path)
    except (OSError, KeyError, ValueError, TypeError) as exc:
        result["checks"]["t0_bundle"] = {"pass": False, "reason": f"bundle_read_failed:{type(exc).__name__}:{exc}"}
        result["pass"] = False
        result["finalizer_sha256"] = canonical_sha256(result)
        atomic_write_json(cell_dir / "independent_finalizer_v2.json", result)
        return result
    result["checks"]["t0_bundle"] = bundle["checks"]
    result["checks"]["trace_structure"] = _trace_structure(trace_path)
    result["checks"]["trace_row0_bundle_link"] = _trace_row0_check(trace_path, bundle)
    artifact = artifact_path or (cell_dir.parent / "prefix_artifact.npz")
    if artifact.is_file() and receipt.get("prefix_end_trace_row") is not None:
        prefix_check = _prefix_check(trace_path, artifact, int(receipt["prefix_end_trace_row"]))
        result["checks"]["actual_prefix"] = prefix_check
        result["checks"]["prefix_receipt_binding"] = {
            "receipt_prefix_sha256": receipt.get("prefix_sha256"),
            "artifact_prefix_sha256": prefix_check.get("artifact_sha256"),
            "pass": isinstance(receipt.get("prefix_sha256"), str) and receipt.get("prefix_sha256") == prefix_check.get("artifact_sha256"),
        }
    else:
        result["checks"]["actual_prefix"] = {"pass": False, "reason": "missing root prefix artifact"}
        result["checks"]["prefix_receipt_binding"] = {"pass": False, "reason": "missing root prefix artifact"}
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


def _f3_event_layout_check(path: Path, receipt: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """Validate event identity and trace intervals from the frozen program."""
    program_id = receipt.get("program_id")
    allowed_programs = tuple(spec.get("candidate_set_schema", {}).get("programs", ()))
    expected = _F3_SUFFIX_BY_PROGRAM.get(str(program_id)) if str(program_id) in allowed_programs else None
    evidence = receipt.get("prefix_event_evidence")
    suffix = receipt.get("expected_suffix_event_order")
    segments = receipt.get("event_segments")
    checks: dict[str, bool] = {
        "program_is_frozen": expected is not None,
        "shared_evidence_shape": isinstance(evidence, dict),
        "suffix_is_frozen": isinstance(suffix, list) and tuple(suffix) == tuple(expected or ()),
        "three_suffix_segments": isinstance(segments, list) and len(segments) == 3,
    }
    if not isinstance(evidence, dict) or not isinstance(segments, list) or expected is None:
        return {"pass": False, "program_id": program_id, "expected_suffix": list(expected or ()), "checks": checks, "reason": "frozen event metadata is missing or unknown"}
    try:
        with np.load(path, allow_pickle=False) as trace:
            trace_length = int(trace["step_index"].shape[0])
    except (OSError, KeyError, ValueError):
        return {"pass": False, "program_id": program_id, "expected_suffix": list(expected), "checks": {**checks, "trace_readable": False}, "reason": "trace cannot be read for event interval validation"}

    def _is_int(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    shared_start = evidence.get("start_row")
    shared_end = evidence.get("end_row")
    checks["shared_interval_valid"] = _is_int(shared_start) and _is_int(shared_end) and 0 <= shared_start <= shared_end < trace_length
    previous_end = shared_end if _is_int(shared_end) else -1
    interval_details: list[dict[str, Any]] = []
    for index, (expected_axis, segment) in enumerate(zip(expected, segments), start=1):
        if not isinstance(segment, dict):
            interval_details.append({"event_index": index, "pass": False, "reason": "segment is not an object"})
            continue
        start = segment.get("start_row")
        end = segment.get("end_row")
        checks_for_segment = {
            "event_index": segment.get("event_index") == index,
            "axis": segment.get("axis") == expected_axis,
            "start_end_int": _is_int(start) and _is_int(end),
            "within_trace": _is_int(start) and _is_int(end) and 0 <= start <= end < trace_length,
            "after_previous": _is_int(start) and start > previous_end,
            "nontrivial_interval": _is_int(start) and _is_int(end) and end - start + 1 >= 2,
        }
        interval_details.append({"event_index": index, "expected_axis": expected_axis, "start_row": start, "end_row": end, "checks": checks_for_segment, "pass": all(checks_for_segment.values())})
        if _is_int(end):
            previous_end = end
    checks["segments"] = all(item.get("pass") is True for item in interval_details) and len(interval_details) == 3
    checks["suffix_has_no_reordered_metadata"] = len({(item.get("event_index"), item.get("axis"), item.get("start_row"), item.get("end_row")) for item in segments if isinstance(item, dict)}) == 3
    return {"pass": all(value is True for key, value in checks.items() if key != "segments") and checks["segments"], "program_id": program_id, "expected_suffix": list(expected), "trace_length": trace_length, "checks": checks, "intervals": interval_details}


def _f3_trace_check(path: Path, receipt: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    evidence = receipt.get("prefix_event_evidence")
    if not isinstance(evidence, dict) or not isinstance(evidence.get("start_row"), int) or not isinstance(evidence.get("end_row"), int):
        return {"pass": False, "reason": "shared first-V evidence missing from receipt"}
    layout = _f3_event_layout_check(path, receipt, spec)
    if not layout.get("pass"):
        return {"pass": False, "event_layout": layout, "reason": "frozen F3 event interval validation failed"}
    shared_metrics = _trace_event_metrics(path, evidence["start_row"], evidence["end_row"], "V")
    events.append({"label": "shared_V", "start_row": evidence["start_row"], "end_row": evidence["end_row"], "metrics": shared_metrics, "checks": _motion_gate(shared_metrics)})
    suffix = layout["expected_suffix"]
    segments = receipt["event_segments"]
    for expected_axis, segment in zip(suffix, segments):
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
    }
    terminal_checks = {
        "object_return": object_return_position <= 0.030 and object_return_orientation <= 0.020,
        "object_stable_window": bool(np.all(obj_speed <= 0.020)),
        "eef_linear_stationary": bool(np.all(eef_speed <= 0.010)),
        "eef_angular_stationary": bool(np.all(eef_angular <= 0.050)),
        "support_contact_window": support_fraction >= 0.95,
        "gripper_open_window": bool(np.all(gripper >= 0.9)),
        "empty_hand_window": bool(not np.any(selected_contact)),
    }
    rest = _f3_rest_check(path, receipt, spec)
    terminal["object_return"] = terminal_checks["object_return"]
    terminal["checks"] = terminal_checks
    terminal["pass"] = all(terminal_checks.values()) and rest.get("pass", False)
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
    root_id = str(alternative.get("root_id", baseline.get("root_id", "")))
    realization_id = str(alternative.get("realization_id", ""))
    try:
        frozen = frozen_realization_requirements(root_id, realization_id)
    except (KeyError, ValueError):
        frozen = {}
    contract = alternative.get("realization_contract", {})
    variant_contract_pass = contract.get("variant_name") == frozen.get("variant_name") and contract.get("kind") == frozen.get("kind") and contract.get("variant_applied") is True
    if kind == "path":
        actual_waypoints = alternative.get("variant_waypoints_actual", [])
        labels = tuple(item.get("label") for item in actual_waypoints if isinstance(item, dict))
        waypoint_contract_pass = (
            isinstance(actual_waypoints, list)
            and len(actual_waypoints) == int(frozen.get("waypoint_count", -1))
            and labels == tuple(frozen.get("required_waypoint_labels", ()))
            and all(isinstance(item.get("target"), list) and len(item["target"]) == 7 and isinstance(item.get("trace_row"), int) for item in actual_waypoints if isinstance(item, dict))
        )
        waypoint_trace_pass = False
        if waypoint_contract_pass:
            try:
                with np.load(apath, allow_pickle=False) as trace:
                    n = int(trace["eef_pose"].shape[0])
                    waypoint_trace_pass = all(
                        0 <= int(item["trace_row"]) < n
                        and float(np.linalg.norm(np.asarray(trace["eef_pose"][int(item["trace_row"])][:3]) - np.asarray(item["target"][:3]))) <= 0.040
                        and _quat_distance(trace["eef_pose"][int(item["trace_row"])][3:], item["target"][3:]) <= 0.050
                        for item in actual_waypoints
                    )
            except (OSError, KeyError, ValueError, TypeError):
                waypoint_trace_pass = False
        waypoint_contract_pass = waypoint_contract_pass and waypoint_trace_pass
        changed = command_changed and a_path_length > b_path_length + 1e-5 and variant_contract_pass and waypoint_contract_pass
    elif kind == "motion":
        b_segments = baseline.get("event_segments", [])
        a_segments = alternative.get("event_segments", [])
        b_holds = [item.get("hold_frames") for item in b_segments]
        a_holds = [item.get("hold_frames") for item in a_segments]
        expected_base = list(frozen.get("baseline_hold_frames", ()))
        expected_alt = list(frozen.get("alternative_hold_frames", ()))
        holds_match = [tuple(value or ()) for value in b_holds] == [tuple(expected_base)] * len(b_holds) and [tuple(value or ()) for value in a_holds] == [tuple(expected_alt)] * len(a_holds)
        # The frozen motion variant is defined by its declared hold schedule
        # and changed effective suffix.  Planner retiming can shorten one
        # event's sampled path even while the physical control has a longer
        # hold, so requiring every event's total row count to be larger would
        # reject a valid declared variant for an implementation artifact.
        durations_match = len(b_segments) == 3 and len(a_segments) == 3 and any(int(a_segments[i].get("duration_rows", 0)) != int(b_segments[i].get("duration_rows", 0)) for i in range(3))
        changed = command_changed and (len(a_suffix) != len(b_suffix) or durations_match) and variant_contract_pass and holds_match
    else:
        changed = False
    return {"kind": kind, "same_prefix_actual": prefix_equal, "suffix_command_changed": command_changed, "baseline_suffix_rows": int(len(b_suffix)), "alternative_suffix_rows": int(len(a_suffix)), "baseline_suffix_path_length_m": b_path_length, "alternative_suffix_path_length_m": a_path_length, "frozen_variant_contract": frozen, "variant_contract_pass": variant_contract_pass, "variant_effect_observed": changed, "pass": bool(prefix_equal and changed)}


def finalize_root(*, root_dir: Path, spec: dict[str, Any]) -> dict[str, Any]:
    root = json.loads((root_dir / "root_receipt.json").read_text(encoding="utf-8"))
    cells = [cell for cell in root.get("cells", []) if cell.get("status") == "cell_pass"]
    if len(cells) != 6:
        result = {"schema_version": "cmf_f2_f3_independent_root_finalizer_v2", "root_id": root.get("root_id"), "pass": False, "reason": "root is incomplete or has a failed cell", "cell_count": len(cells)}
        atomic_write_json(root_dir / "independent_root_finalizer_v2.json", result); return result
    cell_results = []
    for cell in cells:
        cell_dir = Path(cell["trace_path"]).parent
        cell_results.append(finalize_cell(cell_dir=cell_dir, spec=spec, expected_relation=cell.get("program_id") if spec["family"] == "F2" else None, artifact_path=root_dir / "prefix_artifact.npz"))
    variants = []
    for program in spec["candidate_set_schema"]["relations" if spec["family"] == "F2" else "programs"]:
        pair = [cell for cell in cells if cell.get("program_id") == program]
        if len(pair) != 2: variants.append({"program_id": program, "pass": False, "reason": "missing two realizations"}); continue
        baseline = next((cell for cell in pair if cell.get("realization_id") == "r_pc"), None); alternative = next((cell for cell in pair if cell.get("realization_id") != "r_pc"), None)
        variants.append({"program_id": program, "baseline": baseline.get("realization_id"), "alternative": alternative.get("realization_id"), **_variant_check(baseline, alternative)})
    current_bundles = [Path(cell["trace_path"]).parent / "current" for cell in cells]
    metadata_values = [json.loads((bundle / "capture_metadata.json").read_text(encoding="utf-8")) for bundle in current_bundles]
    initial_sigs = [value.get("state_sha256") for value in metadata_values]
    image_sigs = [value.get("camera_images") for value in metadata_values]
    anchor_sigs = [_anchor_signature(bundle) for bundle in current_bundles]
    camera_contract = [value.get("required_camera_names") == list(MODEL_CAMERAS) and set(value.get("camera_names", [])) == set(MODEL_CAMERAS) and set(value.get("camera_images", {})) == set(MODEL_CAMERAS) for value in metadata_values]
    prefix_receipt_hashes = [cell.get("prefix_sha256") for cell in cells]
    prefix_artifact = root_dir / "prefix_artifact.npz"
    prefix_artifact_hash = _prefix_artifact_hash(prefix_artifact) if prefix_artifact.is_file() else None
    prefix_binding = bool(prefix_artifact_hash and all(isinstance(value, str) and value == prefix_artifact_hash for value in prefix_receipt_hashes))
    same_images = bool(image_sigs) and all(image_sigs[0] == value for value in image_sigs[1:])
    same_anchor = bool(anchor_sigs) and len(set(anchor_sigs)) == 1
    same_state = bool(initial_sigs) and len(set(initial_sigs)) == 1
    result = {"schema_version": "cmf_f2_f3_independent_root_finalizer_v2", "root_id": root.get("root_id"), "scene_spec_sha256": spec["spec_sha256"], "cell_finalizers": cell_results, "variant_checks": variants, "prefix_artifact_sha256": prefix_artifact_hash, "prefix_receipt_hashes": prefix_receipt_hashes, "prefix_binding": prefix_binding, "same_root_t0_state": same_state, "same_root_t0_rgb": same_images, "same_root_anchor": same_anchor, "required_camera_contract": camera_contract, "required_camera_contract_pass": all(camera_contract), "pass": len(cell_results) == 6 and all(item.get("pass") for item in cell_results) and all(item.get("pass") for item in variants) and same_state and same_images and same_anchor and all(camera_contract) and prefix_binding, "runner_pass_ignored": True, "research_eligibility": "ELIGIBLE_ONLY_IF_THIS_RESULT_AND_SOURCE_CAPTURE_AUDIT_PASS"}
    result["finalizer_sha256"] = canonical_sha256(result); atomic_write_json(root_dir / "independent_root_finalizer_v2.json", result); return result
