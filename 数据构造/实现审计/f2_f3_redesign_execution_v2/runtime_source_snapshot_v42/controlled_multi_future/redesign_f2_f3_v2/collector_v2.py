"""Corrected F2/F3 collector with action-before-observation and partial roots.

The mature motion routines are reused, while all scientific-facing outputs
are produced by this versioned collector and independently finalized from
disk.  This module is not called by the old v1 entry points.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

import numpy as np
from .canonical import atomic_write_json, canonical_sha256, sha256_file
from .f2_geometry_v2 import _world_geometry, build_beside_geometry_target_route, build_beside_route_waypoints, verify_expected_relation
from .observations import capture_t0
from .pilot_contract import expected_cells, frozen_realization_requirements, planned_root_contract, reusable_cells, selected_cells
from .scene_spec import candidate_set_for, scene_spec
from .f3_retiming import retime_planner_control
from ..signals import closed_loop_event_metrics


def _pose(actor: Any) -> np.ndarray:
    value = actor.get_pose()
    return np.asarray(value.p.tolist() + value.q.tolist(), dtype=np.float64)


def _eef(scene: Any) -> np.ndarray:
    return np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)


def _move_arm(scene: Any, pose: Any, label: str, receipt: dict[str, Any], *, time_scale: float = 1.0) -> None:
    from ..family_runners_v3_1 import _execute_control
    from ..planner_dtype_v3_2 import planner_array
    control = scene.left_move_to_pose(pose=planner_array(pose, shape=(7,), label=f"{label} goal pose"))
    details = {"label": label, "type": type(control).__name__, "status": control.get("status") if isinstance(control, dict) else None}
    if isinstance(control, dict):
        for key in ("error", "message", "reason", "success"):
            if key in control and isinstance(control[key], (str, int, float, bool, type(None))):
                details[key] = control[key]
        if control.get("planner_diagnostics") is not None:
            details["planner_diagnostics"] = control["planner_diagnostics"]
    if isinstance(control, dict) and float(time_scale) > 1.0 and control.get("status") == "Success":
        control = retime_planner_control(control, factor=float(time_scale))
        details["time_dilation"] = control.get("_cmf_time_dilation")
    receipt.setdefault("planner_control_calls", []).append(details)
    meter_output = receipt.get("_meter_output")
    if meter_output:
        _write_execution_meter(Path(meter_output), "planner_query", label=label, planner_status=details.get("status"), solver_problem_count=int(getattr(scene, "planner_query_count", 0)), action_segment_count=int(receipt.get("action_segment_count", 0)))
    try:
        _execute_control(scene, control, label, arm="left")
    except BaseException as exc:
        if meter_output:
            _write_execution_meter(Path(meter_output), "planner_failed", label=label, error_type=type(exc).__name__, solver_problem_count=int(getattr(scene, "planner_query_count", 0)))
        raise


def _hash_rows(rows: list[dict[str, Any]]) -> str:
    keys = ("effective_setpoint", "requested_command", "component_mask", "left_gripper_joint_drive_target", "right_gripper_joint_drive_target", "left_gripper_joint_drive_velocity_target", "right_gripper_joint_drive_velocity_target")
    return canonical_sha256({key: [np.asarray(row[key]).tolist() for row in rows] for key in keys})


def _hash_artifact(path: Path) -> str:
    with np.load(path, allow_pickle=False) as artifact:
        keys = ("effective_setpoint", "requested_command", "component_mask", "left_gripper_joint_drive_target", "right_gripper_joint_drive_target", "left_gripper_joint_drive_velocity_target", "right_gripper_joint_drive_velocity_target")
        return canonical_sha256({key: np.asarray(artifact[key]).tolist() for key in keys})


def _without_self_hash(value: dict[str, Any], field: str = "receipt_sha256") -> dict[str, Any]:
    """Return a shallow receipt copy suitable for canonical self-hashing."""
    result = dict(value)
    result.pop(field, None)
    return result


def _write_root_checkpoint(*, root_output: Path, root_id: str, contract: dict[str, Any], spec: dict[str, Any], cells: list[dict[str, Any]], order: list[str], source_sha: str | None, stop_reason: str | None, stage: str) -> None:
    payload: dict[str, Any] = {
        "schema_version": "cmf_f2_f3_root_checkpoint_v2",
        "root_id": root_id,
        "family": contract["family"],
        "scene_spec_sha256": spec["spec_sha256"],
        "execution_order": order,
        "cells": cells,
        "source_root_receipt_sha256": source_sha,
        "stop_reason": stop_reason,
        "stage": stage,
    }
    payload["checkpoint_sha256"] = canonical_sha256(payload)
    atomic_write_json(root_output / "root_checkpoint.json", payload)


def _write_execution_meter(output: Path, stage: str, **details: Any) -> None:
    """Persist stage evidence before a final cell receipt exists."""
    path = output / "execution_meter.json"
    prior: dict[str, Any] = {}
    if path.is_file():
        try:
            prior = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            prior = {"read_error": True}
    events = list(prior.get("events", [])) if isinstance(prior.get("events", []), list) else []
    events.append({"stage": stage, "wall_time": time.time(), **details})
    value = {"schema_version": "cmf_f2_f3_execution_meter_v1", "events": events, "latest_stage": stage, **details}
    atomic_write_json(path, value)


def _offset_pose(pose: Any, translation_delta: Any) -> np.ndarray:
    """Apply a Cartesian offset to a 7-D pose while preserving its quaternion."""
    value = np.asarray(pose, dtype=float)
    delta = np.asarray(translation_delta, dtype=float)
    if value.shape != (7,) or delta.shape != (3,):
        raise ValueError("pose offset expects a 7-D pose and 3-D translation")
    result = value.copy()
    result[:3] += delta
    return result


def _motion_verifier(events: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    from ..verifiers.f3 import verify_realized_motion_metrics
    return verify_realized_motion_metrics(events, thresholds)


def _quat_distance(first: Any, second: Any) -> float:
    a = np.asarray(first, dtype=float); b = np.asarray(second, dtype=float)
    a /= np.linalg.norm(a); b /= np.linalg.norm(b)
    return float(2 * np.arccos(np.clip(abs(float(np.dot(a, b))), -1, 1)))


def _motion_metrics(rows: list[dict[str, Any]], axis: str) -> dict[str, Any]:
    main_axis = 2 if axis == "V" else 0
    eef = np.asarray([row["eef"][:3] for row in rows], dtype=float)
    bottle = np.asarray([row["actor_pose"][:3] for row in rows], dtype=float)
    eef_metrics = closed_loop_event_metrics(eef, eef[0], main_axis)
    bottle_metrics = closed_loop_event_metrics(bottle, bottle[0], main_axis)
    contact = np.asarray([bool(row.get("selected_gripper_contact", False)) for row in rows], dtype=bool)
    breaks = int(np.count_nonzero(contact[:-1] & ~contact[1:])) if len(contact) > 1 else int(not bool(contact[0]))
    return {"axis": axis, "row_count": len(rows), "eef_positive_amplitude": eef_metrics["positive_amplitude"], "eef_negative_amplitude": eef_metrics["negative_amplitude"], "eef_max_off_axis": eef_metrics["max_off_axis"], "eef_return_error": eef_metrics["return_error"], "bottle_positive_amplitude": bottle_metrics["positive_amplitude"], "bottle_negative_amplitude": bottle_metrics["negative_amplitude"], "bottle_max_off_axis": bottle_metrics["max_off_axis"], "bottle_return_error": bottle_metrics["return_error"], "bottle_orientation_drift": max(_quat_distance(rows[0]["actor_pose"][3:], row["actor_pose"][3:]) for row in rows), "selected_gripper_contact_fraction": float(contact.mean()), "contact_break_count": breaks}


def _closed_loop_event(scene: Any, realization: str, axis: str, label: str, receipt: dict[str, Any], *, time_scale: float = 1.0) -> None:
    main_axis = 2 if axis == "V" else 0; center = _eef(scene); amplitude = 0.047
    holds = (20, 20, 20) if realization != "r_inv_motion" else (25, 30, 25)
    receipt["event_command_amplitude_m"] = amplitude
    receipt.setdefault("event_hold_records", []).append({"label": label, "axis": axis, "hold_frames": list(holds)})
    for phase, offset, hold in zip(("negative", "positive", "return"), (-amplitude, amplitude, 0.0), holds):
        target = center.copy(); target[main_axis] += offset; _move_arm(scene, target, f"{label}_{phase}", receipt, time_scale=time_scale); receipt["action_segment_count"] += 1; _wait_and_record_for_event(scene, hold)


def _wait_and_record_for_event(scene: Any, frames: int) -> None:
    from ..family_runners_v3_1 import _wait_and_record
    _wait_and_record(scene, frames)


def _replay_prefix(scene: Any, artifact_path: Path) -> int:
    with np.load(artifact_path, allow_pickle=False) as artifact:
        for index in range(1, len(artifact["effective_setpoint"])):
            scene.replay_effective_setpoint_step(
                artifact["effective_setpoint"][index],
                requested_command=artifact["requested_command"][index],
                component_mask=artifact["component_mask"][index],
                left_gripper_joint_drive_target=artifact["left_gripper_joint_drive_target"][index],
                right_gripper_joint_drive_target=artifact["right_gripper_joint_drive_target"][index],
                left_gripper_joint_drive_velocity_target=artifact["left_gripper_joint_drive_velocity_target"][index],
                right_gripper_joint_drive_velocity_target=artifact["right_gripper_joint_drive_velocity_target"][index],
            )
        return len(artifact["effective_setpoint"]) - 1


def _pair_has(row: dict[str, Any], first: str, second: str) -> bool:
    return any(first in {str(pair.get("body_a", "")), str(pair.get("body_b", ""))} and second in {str(pair.get("body_a", "")), str(pair.get("body_b", ""))} for pair in row.get("contact_pairs", []))


def _f2_cell(*, output: Path, root_id: str, program_id: str, realization_id: str, artifact: Path | None, collection: bool, f2_layout_id: str | None = None, f2_route_mode: str | None = None, f2_lift_clearance_m: float | None = None) -> dict[str, Any]:
    from envs.utils.action import ArmTag
    from ..family_runners_v3_1 import _must_action, _planner_reset, _wait_and_record
    from ..probes.lifecycle import cleanup_status, initialize_cleanup_fields, managed_scene
    from ..probes.scene_inspection import _args
    from .f2_scene import RedesignF2Scene
    spec = scene_spec(root_id, f2_layout_id=f2_layout_id); contract = planned_root_contract(root_id)
    route_mode = str(f2_route_mode or "three_segment_high")
    if route_mode not in {"three_segment_high", "side_then_geometry_target"}:
        raise ValueError(f"unknown F2 route mode: {route_mode}")
    lift_clearance = 0.16 if f2_lift_clearance_m is None else float(f2_lift_clearance_m)
    if not np.isfinite(lift_clearance) or lift_clearance <= 0:
        raise ValueError("f2_lift_clearance_m must be a positive finite number")
    receipt: dict[str, Any] = {"schema_version": "cmf_f2_cell_v2", "root_id": root_id, "family": "F2", "program_id": program_id, "realization_id": realization_id, "collection": collection, "formal_data": False, "stage0_data": False, "status": "RUNNING", "action_segment_count": 0, "solver_problem_count": 0, "layout_id": spec["f2"]["layout_id"], "route_mode": route_mode, "lift_clearance_m": lift_clearance, "scene_spec_sha256": spec["spec_sha256"], "candidate_set": candidate_set_for(spec)}
    initialize_cleanup_fields(receipt); started = time.monotonic(); scene = None
    receipt["_meter_output"] = str(output)
    receipt["realization_contract"] = {**frozen_realization_requirements(root_id, realization_id), "path_variant": "direct_high_lateral" if realization_id != "r_inv_path" else "post_prefix_y_detour_40mm", "motion_variant": "planner_default" if realization_id != "r_inv_motion" else "post_lateral_35_and_post_descent_40_frame_holds", "variant_applied": realization_id == "r_pc"}
    output.mkdir(parents=True, exist_ok=False); _write_execution_meter(output, "cell_started", root_id=root_id, cell_key=f"{program_id}:{realization_id}")
    args = _args("F2", output / "scene"); args.update({"seed": spec["scene_seed"], "task_name": f"cmf_f2_v2_{root_id}", "f2_layout_id": spec["f2"]["layout_id"], "scene_variant": spec["layout_variant"], "render_freq": 0, "save_data": False, "collect_data": False, "need_plan": True})
    try:
        with managed_scene(RedesignF2Scene, args, receipt, f"f2-v2-{root_id}-{program_id}-{realization_id}") as scene:
            scene._cmf_scene_spec = spec
            # The v2 repair contract requires raw planner diagnostics to be
            # retained before RoboTwin collapses a MotionGen failure to Fail.
            # This flag is consumed only by the conditional planner audit
            # path; it does not alter normal F1/F4 planner behavior.
            setattr(scene.robot, "_cmf_planner_audit", True)
            _write_execution_meter(output, "scene_created", scene_class=type(scene).__name__)
            scene.initialize_trace(scene.can, "left", scene.role_actors)
            receipt["current"] = _pose(scene.can).tolist(); receipt["anchor"] = receipt["current"][:]
            receipt["t0_capture"] = capture_t0(scene=scene, output=output / "current", root_id=root_id, cell_key=f"{program_id}:{realization_id}", spec=spec, rest_target=None, trace_row=scene.trace[0])
            _write_execution_meter(output, "t0_captured", t0_capture=True)
            _planner_reset(scene, planner_seed=spec["scene_seed"], variant_id=f"cmf-f2-v2-{root_id}-{program_id}-{realization_id}", arm="left")
            _write_execution_meter(output, "action_started", action_segment_count=receipt["action_segment_count"])
            if artifact is None:
                grasp = scene.grasp_actor(scene.can, ArmTag("left"), pre_grasp_dis=0.09, grasp_dis=0.0, gripper_pos=0.0, contact_point_id=0); _must_action(scene, grasp, "v2_grasp"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 250)
                before = _eef(scene); lift = before.copy(); lift[2] += lift_clearance
                for fraction in (0.25, 0.50, 0.75, 1.0):
                    _move_arm(scene, before + (lift - before) * fraction, f"v2_lift_{fraction:.2f}", receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 20)
                carry = lift.copy(); carry[0] += 0.14; carry[1] -= 0.20; _move_arm(scene, carry, "v2_carry", receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 30); _wait_and_record(scene, 250)
                prefix_end = len(scene.trace) - 1; prefix_hash = _hash_rows(scene.trace[: prefix_end + 1])
            else:
                prefix_end = _replay_prefix(scene, artifact); prefix_hash = _hash_artifact(artifact); _wait_and_record(scene, 50); carry = _eef(scene)
            receipt.update({"prefix_end_trace_row": prefix_end, "prefix_sha256": prefix_hash})
            receipt["prefix_anchor_contact_fraction"] = float(np.mean([bool(row.get("selected_gripper_contact", False)) for row in scene.trace[max(0, prefix_end - 49): prefix_end + 1]]))
            receipt["prefix_anchor_contact_stable"] = receipt["prefix_anchor_contact_fraction"] >= 0.8
            if artifact is not None and not receipt["prefix_anchor_contact_stable"]: raise RuntimeError("v2 frozen prefix lost gripper contact")
            carried = _pose(scene.can); carried_support, _, _ = _world_geometry(carried, spec["f2"]); offset = carried_support - carry[:3]; f2 = spec["f2"]
            if program_id == "inside": desired = np.asarray(f2["box_center_xyz"], dtype=float); desired[2] = f2["box_support_z"]; support_name = "f2_redesign_box_bottom"
            elif program_id == "on": desired = np.asarray(f2["scale_center_xyz"], dtype=float); desired[2] = f2["scale_top_z"]; support_name = "f2_redesign_scale"
            else: desired = np.asarray([*f2["beside_target_xy"], f2["beside_table_z"]], dtype=float); support_name = "table"
            target = carry.copy(); target[:3] = desired - offset; receipt["target_binding"] = {"carried_object": carried.tolist(), "carried_eef": carry.tolist(), "support_point_world": carried_support.tolist(), "support_offset": offset.tolist(), "desired_support_point": desired.tolist(), "support_identity": support_name, "target_eef": target.tolist()}; receipt["support_identity"] = support_name
            high = target.copy(); high[2] = carry[2]
            direct_geometry_route = None
            if program_id == "beside" and route_mode == "side_then_geometry_target":
                direct_geometry_route = build_beside_geometry_target_route(carry, target, route_offset_m=0.12, lateral_axis=1)
            if realization_id == "r_inv_path":
                detour_start = carry.copy(); detour_start[1] -= 0.04
                # The direct-geometry route has no reachable high target at
                # the old X/Y corner.  Its path realization detours to the
                # cleared side waypoint at the same safe height, then uses
                # the evidence-driven side-to-target transition below.
                detour_base = direct_geometry_route["side_at_current"] if direct_geometry_route is not None else high.tolist()
                detour_end = np.asarray(detour_base, dtype=np.float64); detour_end[1] -= 0.04
                receipt["realization_contract"]["path_variant_waypoints"] = {"start": detour_start.tolist(), "target_offset": detour_end.tolist(), "target": (target if direct_geometry_route is not None else high).tolist()}
                _move_arm(scene, detour_start, f"v2_{program_id}_path_detour_start", receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 20)
                receipt.setdefault("variant_waypoints_actual", []).append({"label": "detour_start", "target": detour_start.tolist(), "trace_row": len(scene.trace) - 1})
                _move_arm(scene, detour_end, f"v2_{program_id}_path_detour_target_offset", receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 20); receipt["realization_contract"]["variant_applied"] = True
                receipt.setdefault("variant_waypoints_actual", []).append({"label": "detour_target_offset", "target": detour_end.tolist(), "trace_row": len(scene.trace) - 1})
            if program_id == "beside":
                # Route around the reference while carrying the object.  The
                # first two waypoints must be different: the first preserves
                # the current X, the second moves to target X at the cleared
                # Y, and the third returns to the target Y.  This used to
                # construct both points from ``high`` and silently repeat one
                # failed remote goal.
                if route_mode == "side_then_geometry_target":
                    route = direct_geometry_route or build_beside_geometry_target_route(carry, target, route_offset_m=0.12, lateral_axis=1)
                    route_far = np.asarray(route["side_at_current"], dtype=np.float64)
                    route_target = np.asarray(route["target"], dtype=np.float64)
                    receipt["beside_route_waypoints"] = {"side_at_current": route_far.tolist(), "target": route_target.tolist(), "clearance_height_m": float(route_far[2]), "route_offset_m": route["route_offset_m"], "lateral_axis": route["lateral_axis"], "evidence_basis": "S0/S1 diagnostic: old high side_at_target IK_FAIL; collision-bottom geometry target Success"}
                    route_steps = (("beside_side_at_current", route_far), ("beside_geometry_target", route_target))
                else:
                    route = build_beside_route_waypoints(carry, high, route_offset_m=0.12, lateral_axis=1)
                    route_far = np.asarray(route["side_at_current"], dtype=np.float64)
                    route_target = np.asarray(route["side_at_target"], dtype=np.float64)
                    route_final = np.asarray(route["target"], dtype=np.float64)
                    receipt["beside_route_waypoints"] = {"side_at_current": route_far.tolist(), "side_at_target": route_target.tolist(), "target": route_final.tolist(), "clearance_height_m": float(route_final[2]), "route_offset_m": route["route_offset_m"], "lateral_axis": route["lateral_axis"]}
                    route_steps = (("beside_side_at_current", route_far), ("beside_side_at_target", route_target), ("beside_target_y", route_final))
                for label, waypoint in route_steps:
                    _move_arm(scene, waypoint, f"v2_{program_id}_{label}", receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 20)
            else:
                _move_arm(scene, high, f"v2_{program_id}_lateral", receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 30)
            if realization_id == "r_inv_path":
                receipt.setdefault("variant_waypoints_actual", []).append({"label": "target", "target": (target if direct_geometry_route is not None else high).tolist(), "trace_row": len(scene.trace) - 1})
            if realization_id == "r_inv_motion": _wait_and_record(scene, 35); receipt["realization_contract"]["variant_applied"] = True
            if program_id == "beside" and route_mode == "side_then_geometry_target":
                # The evidence-driven route already ends at the collision-
                # derived support target; repeating the same descent would
                # hide whether the direct transition was reachable.
                support_end = len(scene.trace) - 1
            else:
                _move_arm(scene, target, f"v2_{program_id}_descent", receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 60); support_end = len(scene.trace) - 1
            if realization_id == "r_inv_motion": _wait_and_record(scene, 40); support_end = len(scene.trace) - 1
            receipt["support_end_trace_row"] = support_end
            receipt["release_start_trace_row"] = support_end + 1
            _must_action(scene, scene.open_gripper(ArmTag("left"), pos=1.0), "v2_open"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 50)
            if program_id == "beside":
                exit_target = np.asarray(scene.robot.left_original_pose, dtype=float)
            else:
                exit_target = _offset_pose(_eef(scene), [-0.15, 0.0, 0.10])
            receipt["exit_target"] = exit_target.tolist()
            _move_arm(scene, exit_target, "v2_empty_hand_exit", receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 70)
            rows = scene.trace; support_rows = rows[max(0, support_end - 59): support_end + 1]; exit_rows = rows[-50:]; can_name = scene.can.get_name()
            support_fraction = float(np.mean([_pair_has(row, can_name, support_name) for row in support_rows])); exit_contact = float(np.mean([bool(row.get("selected_gripper_contact", False)) for row in exit_rows]))
            stand_top = bool(np.mean([_pair_has(row, can_name, "f2_redesign_stand") for row in support_rows]) >= 0.5)
            relation = verify_expected_relation(program_id=program_id, pose=_pose(scene.can), spec=spec, contact={"stand_top_contact": stand_top})
            receipt["relation_verifier"] = relation; receipt["events"] = {"support_fraction": support_fraction, "exit_contact_fraction": exit_contact, "final_can_pose": _pose(scene.can).tolist(), "stand_top_contact": stand_top}
            receipt["gates"] = {"relation": relation["pass"], "support_identity": support_fraction >= 0.8, "empty_hand_exit": exit_contact == 0.0, "prefix_present": bool(prefix_hash), "prefix_anchor_contact_stable": receipt["prefix_anchor_contact_stable"], "trace_complete": len(rows) > prefix_end}
            receipt["solver_problem_count"] = int(getattr(scene, "planner_query_count", 0))
            receipt["trace"] = scene.save_trace(output / "trace.npz"); receipt["trace_path"] = str(output / "trace.npz"); receipt["status"] = "cell_pass" if all(receipt["gates"].values()) else "cell_failed_gates"
    except BaseException as exc:
        receipt["status"] = "cell_failed_execution"; receipt["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if scene is not None and getattr(scene, "trace", None) and "trace_path" not in receipt:
            try:
                receipt["solver_problem_count"] = int(getattr(scene, "planner_query_count", 0))
                receipt["trace"] = scene.save_trace(output / "trace.npz"); receipt["trace_path"] = str(output / "trace.npz")
            except BaseException as exc: receipt["trace_save_error"] = {"type": type(exc).__name__, "message": str(exc)}
        receipt["status"] = cleanup_status(receipt, receipt["status"]); receipt["elapsed_seconds"] = time.monotonic() - started
        _write_execution_meter(output, "cell_finished", status=receipt["status"], solver_problem_count=receipt.get("solver_problem_count", 0), action_segment_count=receipt.get("action_segment_count", 0), trace_path=receipt.get("trace_path"))
        atomic_write_json(output / "cell_receipt.json", receipt)
    return receipt


def _f3_cell(*, output: Path, root_id: str, program_id: str, realization_id: str, artifact: Path | None, prefix_meta: Path | None, collection: bool) -> dict[str, Any]:
    import sapien
    from envs.utils.action import ArmTag
    from ..family_runners_v3_1 import _must_action, _planner_reset, _wait_and_record
    from ..probes.lifecycle import cleanup_status, initialize_cleanup_fields, managed_scene
    from ..probes.scene_inspection import _args
    from .scene import RedesignF3Scene

    spec = scene_spec(root_id)
    time_scale = float(os.environ.get("CMF_F3_TIME_SCALE", "1.0"))
    if not np.isfinite(time_scale) or time_scale < 1.0:
        raise ValueError("CMF_F3_TIME_SCALE must be finite and >= 1")
    receipt: dict[str, Any] = {"schema_version": "cmf_f3_cell_v2", "root_id": root_id, "family": "F3", "program_id": program_id, "realization_id": realization_id, "collection": collection, "formal_data": False, "stage0_data": False, "status": "RUNNING", "action_segment_count": 0, "solver_problem_count": 0, "scene_spec_sha256": spec["spec_sha256"], "candidate_set": candidate_set_for(spec), "time_scale_factor": time_scale, "realization_contract": {**frozen_realization_requirements(root_id, realization_id), "path_variant": "direct_event_sequence" if realization_id != "r_inv_path" else "post_prefix_y_detour_30mm_round_trip", "motion_variant": "planner_default" if realization_id != "r_inv_motion" else "absolute_symmetric_planner_events_with_extended_holds", "variant_applied": realization_id in {"r_pc", "r_inv_motion"}}}
    initialize_cleanup_fields(receipt); started = time.monotonic(); scene = None
    receipt["_meter_output"] = str(output)
    output.mkdir(parents=True, exist_ok=False); _write_execution_meter(output, "cell_started", root_id=root_id, cell_key=f"{program_id}:{realization_id}")
    args = _args("F3", output / "scene"); args.update({"seed": spec["scene_seed"], "task_name": f"cmf_f3_v2_{root_id}", "scene_variant": spec["layout_variant"], "render_freq": 0, "save_data": False, "collect_data": False, "need_plan": True})
    try:
        with managed_scene(RedesignF3Scene, args, receipt, f"f3-v2-{root_id}-{program_id}-{realization_id}") as scene:
            scene._cmf_scene_spec = spec
            setattr(scene.robot, "_cmf_planner_audit", True)
            _write_execution_meter(output, "scene_created", scene_class=type(scene).__name__)
            scene.initialize_trace(scene.bottle, "left", scene.role_actors); anchor = _pose(scene.bottle); receipt["current"] = anchor.tolist(); receipt["anchor"] = anchor.tolist(); receipt["rest_target"] = np.asarray(scene.robot.left_original_pose, dtype=float).tolist()
            receipt["t0_capture"] = capture_t0(scene=scene, output=output / "current", root_id=root_id, cell_key=f"{program_id}:{realization_id}", spec=spec, rest_target=receipt["rest_target"], trace_row=scene.trace[0])
            _write_execution_meter(output, "t0_captured", t0_capture=True)
            _planner_reset(scene, planner_seed=spec["scene_seed"], variant_id=f"cmf-f3-v2-{root_id}-{program_id}-{realization_id}", arm="left")
            _write_execution_meter(output, "action_started", action_segment_count=receipt["action_segment_count"])
            if artifact is None:
                grasp = scene.grasp_actor(scene.bottle, ArmTag("left"), pre_grasp_dis=0.09, grasp_dis=0.0, gripper_pos=0.0, contact_point_id=0); _must_action(scene, grasp, "v2_grasp"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 250); before = _eef(scene); lift = before.copy(); lift[2] += 0.025; _move_arm(scene, lift, "v2_micro_lift", receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 50); central = _eef(scene); central[2] += 0.05; _move_arm(scene, central, "v2_central_clearance", receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 50); start = len(scene.trace) - 1; _closed_loop_event(scene, realization_id, "V", "v2_prefix_V", receipt, time_scale=time_scale); prefix_end = len(scene.trace) - 1; prefix_hash = _hash_rows(scene.trace[: prefix_end + 1]); prefix_metrics = _motion_metrics(scene.trace[start: prefix_end + 1], "V"); receipt["prefix_event_evidence"] = {"start_row": start, "end_row": prefix_end, "metrics": prefix_metrics, "verifier": _motion_verifier({"shared_V": prefix_metrics}, {"motion_min_axis_amplitude_m": 0.04, "motion_max_off_axis_m": 0.015, "motion_max_return_error_m": 0.015, "motion_max_orientation_drift": 0.05, "motion_min_contact_fraction": 0.95, "motion_max_contact_break_count": 0})}
            else:
                prefix_len = _replay_prefix(scene, artifact); prefix_end = len(scene.trace) - 1; prefix_hash = _hash_artifact(artifact); _wait_and_record(scene, 50); carry = _eef(scene); evidence = json.loads(prefix_meta.read_text()) if prefix_meta and prefix_meta.is_file() else None
                if evidence:
                    start = int(evidence["start_row"]); metrics = _motion_metrics(scene.trace[start: prefix_end + 1], "V"); receipt["prefix_event_evidence"] = {"start_row": start, "end_row": prefix_end, "metrics": metrics, "verifier": _motion_verifier({"shared_V": metrics}, {"motion_min_axis_amplitude_m": 0.04, "motion_max_off_axis_m": 0.015, "motion_max_return_error_m": 0.015, "motion_max_orientation_drift": 0.05, "motion_min_contact_fraction": 0.95, "motion_max_contact_break_count": 0})}
            receipt.update({"prefix_end_trace_row": prefix_end, "prefix_sha256": prefix_hash}); receipt["prefix_anchor_contact_fraction"] = float(np.mean([bool(row.get("selected_gripper_contact", False)) for row in scene.trace[max(0, prefix_end - 49): prefix_end + 1]])); receipt["prefix_anchor_contact_stable"] = receipt["prefix_anchor_contact_fraction"] >= 0.95
            if artifact is not None and not receipt["prefix_anchor_contact_stable"]: raise RuntimeError("v2 F3 frozen prefix lost contact")
            if realization_id == "r_inv_path":
                detour = _eef(scene); detour[1] -= 0.03; back = detour.copy(); back[1] += 0.03; receipt["realization_contract"]["path_variant_waypoints"] = {"start": detour.tolist(), "target_offset": back.tolist(), "target": back.tolist()}; _move_arm(scene, detour, "v2_path_detour", receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 20); receipt.setdefault("variant_waypoints_actual", []).append({"label": "detour_start", "target": detour.tolist(), "trace_row": len(scene.trace) - 1}); _move_arm(scene, back, "v2_path_return", receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 20); receipt.setdefault("variant_waypoints_actual", []).append({"label": "detour_target_offset", "target": back.tolist(), "trace_row": len(scene.trace) - 1}); receipt.setdefault("variant_waypoints_actual", []).append({"label": "target", "target": back.tolist(), "trace_row": len(scene.trace) - 1}); receipt["realization_contract"]["variant_applied"] = True
            suffix = {"VVHH": ("V", "H", "H"), "VHVH": ("H", "V", "H"), "VHHV": ("H", "H", "V")}[program_id]; receipt["expected_suffix_event_order"] = list(suffix); receipt["event_segments"] = []; _wait_and_record_for_event(scene, 1)
            for index, axis in enumerate(suffix):
                start = len(scene.trace) - 1; _closed_loop_event(scene, realization_id, axis, f"v2_suffix_{index}_{axis}", receipt, time_scale=time_scale); end = len(scene.trace) - 1; hold_record = receipt.get("event_hold_records", [])[-1]; receipt["event_segments"].append({"event_index": index + 1, "axis": axis, "start_row": start, "end_row": end, "duration_rows": end - start + 1, "duration_seconds": float((end - start) * scene.simulator_timestep_seconds), "hold_frames": hold_record.get("hold_frames"), "metrics": _motion_metrics(scene.trace[start: end + 1], axis)})
                if index < len(suffix) - 1: _wait_and_record_for_event(scene, 1)
            receipt["event_verifier"] = _motion_verifier({f"suffix_{e['event_index']}_{e['axis']}": e["metrics"] for e in receipt["event_segments"]}, {"motion_min_axis_amplitude_m": 0.04, "motion_max_off_axis_m": 0.015, "motion_max_return_error_m": 0.015, "motion_max_orientation_drift": 0.05, "motion_min_contact_fraction": 0.95, "motion_max_contact_break_count": 0})
            carried = _pose(scene.bottle); carried_eef = _eef(scene); relative = sapien.Pose(carried_eef[:3], carried_eef[3:]).inv() * sapien.Pose(carried[:3], carried[3:]); desired = sapien.Pose(anchor[:3], anchor[3:]); return_eef = np.asarray((desired * relative.inv()).p.tolist() + (desired * relative.inv()).q.tolist()); above = return_eef.copy(); above[2] += 0.025; _move_arm(scene, above, "v2_return_height", receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 30); _move_arm(scene, return_eef, "v2_return_support", receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 100); _must_action(scene, scene.open_gripper(ArmTag("left"), pos=1.0), "v2_open"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 50); _wait_and_record(scene, 200); _move_arm(scene, np.asarray(receipt["rest_target"], dtype=float), "v2_rest_target", receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 200)
            rows = scene.trace; tail = rows[-50:]; pad = "f3_redesign_support_pad"; bottle = scene.bottle.get_name(); support = np.asarray([_pair_has(row, bottle, pad) for row in tail], dtype=bool); obj_speed = np.asarray([np.linalg.norm(row["actor_linear_velocity"]) for row in tail]); eef_speed = np.asarray([np.linalg.norm(row["eef_linear_velocity"]) for row in tail]); eef_ang = np.asarray([np.linalg.norm(row["eef_angular_velocity"]) for row in tail]); final = _pose(scene.bottle); eef_final = _eef(scene); rest = np.asarray(receipt["rest_target"]); receipt["terminal_metrics"] = {"object_return_position_m": float(np.linalg.norm(final[:3] - anchor[:3])), "object_return_orientation_rad": float(2 * np.arccos(np.clip(abs(np.dot(final[3:] / np.linalg.norm(final[3:]), anchor[3:] / np.linalg.norm(anchor[3:]))), -1, 1))), "eef_rest_position_m": float(np.linalg.norm(eef_final[:3] - rest[:3])), "eef_rest_orientation_rad": float(2 * np.arccos(np.clip(abs(np.dot(eef_final[3:] / np.linalg.norm(eef_final[3:]), rest[3:] / np.linalg.norm(rest[3:]))), -1, 1))), "max_object_speed_mps": float(obj_speed.max()), "max_eef_speed_mps": float(eef_speed.max()), "max_eef_angular_speed_rps": float(eef_ang.max()), "support_fraction": float(support.mean()), "gripper_open_fraction": float(np.mean([float(row["gripper_command"][0]) >= 0.9 for row in tail]))}
            receipt["gates"] = {"prefix_present": bool(prefix_hash), "prefix_contact_stable": receipt["prefix_anchor_contact_stable"], "shared_V_realized": bool(receipt.get("prefix_event_evidence", {}).get("verifier", {}).get("pass", False)), "event_order": [item["axis"] for item in receipt["event_segments"]] == list(suffix), "event_metrics": bool(receipt["event_verifier"]["pass"]), "object_return": receipt["terminal_metrics"]["object_return_position_m"] <= 0.03 and receipt["terminal_metrics"]["object_return_orientation_rad"] <= 0.02, "arm_rest": receipt["terminal_metrics"]["eef_rest_position_m"] <= spec["f3"]["rest_position_tolerance_m"] and receipt["terminal_metrics"]["eef_rest_orientation_rad"] <= spec["f3"]["rest_orientation_tolerance_rad"], "object_stable": receipt["terminal_metrics"]["max_object_speed_mps"] <= 0.02, "eef_stationary": receipt["terminal_metrics"]["max_eef_speed_mps"] <= 0.01 and receipt["terminal_metrics"]["max_eef_angular_speed_rps"] <= 0.05, "support_window": bool(np.all(support)), "gripper_open": receipt["terminal_metrics"]["gripper_open_fraction"] == 1.0}
            receipt["solver_problem_count"] = int(getattr(scene, "planner_query_count", 0))
            receipt["trace"] = scene.save_trace(output / "trace.npz"); receipt["trace_path"] = str(output / "trace.npz"); receipt["status"] = "cell_pass" if all(receipt["gates"].values()) else "cell_failed_gates"
    except BaseException as exc:
        receipt["status"] = "cell_failed_execution"; receipt["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if scene is not None and getattr(scene, "trace", None) and "trace_path" not in receipt:
            try:
                receipt["solver_problem_count"] = int(getattr(scene, "planner_query_count", 0))
                receipt["trace"] = scene.save_trace(output / "trace.npz"); receipt["trace_path"] = str(output / "trace.npz")
            except BaseException as exc: receipt["trace_save_error"] = {"type": type(exc).__name__, "message": str(exc)}
        receipt["status"] = cleanup_status(receipt, receipt["status"]); receipt["elapsed_seconds"] = time.monotonic() - started
        _write_execution_meter(output, "cell_finished", status=receipt["status"], solver_problem_count=receipt.get("solver_problem_count", 0), action_segment_count=receipt.get("action_segment_count", 0), trace_path=receipt.get("trace_path"))
        atomic_write_json(output / "cell_receipt.json", receipt)
    return receipt


def _save_prefix(root_output: Path, receipt: dict[str, Any]) -> Path | None:
    checks = {
        "cell_status_pass": receipt.get("status") == "cell_pass",
        "prefix_hash_present": isinstance(receipt.get("prefix_sha256"), str) and bool(receipt.get("prefix_sha256")),
        "prefix_end_present": isinstance(receipt.get("prefix_end_trace_row"), int) and receipt.get("prefix_end_trace_row") >= 0,
        "prefix_contact_stable": receipt.get("prefix_anchor_contact_stable") is True,
    }
    if receipt.get("family") == "F3":
        evidence = receipt.get("prefix_event_evidence")
        checks["shared_prefix_event_verified"] = isinstance(evidence, dict) and evidence.get("verifier", {}).get("pass") is True
    receipt["prefix_verification"] = {**checks, "pass": all(checks.values())}
    if not receipt["prefix_verification"]["pass"]:
        return None
    trace_path = receipt.get("trace_path"); end = receipt.get("prefix_end_trace_row")
    if not trace_path or end is None: return None
    n = int(end) + 1; artifact = root_output / "prefix_artifact.npz"
    with np.load(trace_path, allow_pickle=False) as trace:
        required = ("controller_effective_setpoint", "requested_command", "component_masks", "left_gripper_joint_drive_target", "right_gripper_joint_drive_target", "left_gripper_joint_drive_velocity_target", "right_gripper_joint_drive_velocity_target")
        if n > int(trace["step_index"].shape[0]) or any(key not in trace for key in required):
            receipt["prefix_verification"].update({"pass": False, "trace_fields_present": False})
            return None
        np.savez_compressed(artifact, effective_setpoint=trace["controller_effective_setpoint"][:n], requested_command=trace["requested_command"][:n], component_mask=trace["component_masks"][:n], left_gripper_joint_drive_target=trace["left_gripper_joint_drive_target"][:n], right_gripper_joint_drive_target=trace["right_gripper_joint_drive_target"][:n], left_gripper_joint_drive_velocity_target=trace["left_gripper_joint_drive_velocity_target"][:n], right_gripper_joint_drive_velocity_target=trace["right_gripper_joint_drive_velocity_target"][:n])
    artifact_hash = _hash_artifact(artifact)
    receipt["prefix_verification"].update({"artifact_sha256": artifact_hash, "receipt_hash_matches_artifact": artifact_hash == receipt.get("prefix_sha256")})
    receipt["prefix_verification"]["pass"] = bool(receipt["prefix_verification"].get("pass") and receipt["prefix_verification"]["receipt_hash_matches_artifact"])
    if not receipt["prefix_verification"]["pass"]:
        return None
    if receipt.get("prefix_event_evidence"):
        atomic_write_json(root_output / "prefix_evidence.json", receipt["prefix_event_evidence"])
    return artifact


def run_root(*, output: str | Path, root_id: str, cell_keys: list[str] | None = None, existing_root: str | Path | None = None, collection: bool = True, f2_layout_id: str | None = None, f2_route_mode: str | None = None, f2_lift_clearance_m: float | None = None) -> dict[str, Any]:
    root_output = Path(output); root_output.mkdir(parents=True, exist_ok=False); contract = planned_root_contract(root_id); spec = scene_spec(root_id, f2_layout_id=f2_layout_id if contract["family"] == "F2" else None); expected = expected_cells(root_id); expected_keys = [f"{c['program_id']}:{c['realization_id']}" for c in expected]
    requested = expected_keys if cell_keys is None else list(cell_keys)
    if not requested or len(set(requested)) != len(requested) or not set(requested).issubset(set(expected_keys)): raise ValueError("requested cell keys are outside the frozen v2 root")
    reused: dict[str, dict[str, Any]] = {}; source_sha = None; artifact = None; prefix_meta = None
    if existing_root is not None:
        source_root = Path(existing_root); source = json.loads((source_root / "root_receipt.json").read_text());
        if source.get("root_id") != root_id or source.get("scene_spec_sha256") != spec["spec_sha256"]: raise ValueError("resume source root does not match v2 root spec")
        source_sha = sha256_file(source_root / "root_receipt.json")
        source_keys = {(c.get("program_id"), c.get("realization_id")) for c in source.get("cells", []) if c.get("status") == "cell_pass"}
        omitted_keys = {(c["program_id"], c["realization_id"]) for c in expected if f"{c['program_id']}:{c['realization_id']}" not in set(requested)}
        reusable_keys = source_keys & omitted_keys
        reusable = reusable_cells(source, root_id, cell_keys=reusable_keys) if reusable_keys else []
        reused = {f"{c['program_id']}:{c['realization_id']}": c for c in reusable}; source_artifact = source_root / "prefix_artifact.npz"
        if not source_artifact.is_file(): raise ValueError("resume source root lacks prefix artifact")
        artifact = root_output / "prefix_artifact.npz"; shutil.copyfile(source_artifact, artifact); source_meta = source_root / "prefix_evidence.json"
        if source_meta.is_file(): prefix_meta = root_output / "prefix_evidence.json"; shutil.copyfile(source_meta, prefix_meta)
    generated: dict[str, dict[str, Any]] = {}
    stop_reason: str | None = None
    order = [key for key in contract["execution_order"] if key in requested]
    _write_root_checkpoint(root_output=root_output, root_id=root_id, contract=contract, spec=spec, cells=[], order=order, source_sha=source_sha, stop_reason=None, stage="STARTED")
    for key in order:
        if key in reused: continue
        program, realization = key.split(":", 1); cell_dir = root_output / key.replace(":", "_")
        if contract["family"] == "F2":
            cell_kwargs = {"output": cell_dir, "root_id": root_id, "program_id": program, "realization_id": realization, "artifact": artifact, "collection": collection}
            # Preserve the CPU mock seam and historical v4 default while
            # making the explicitly selected v5 candidate part of the call
            # contract for physical qualification.
            if f2_layout_id is not None:
                cell_kwargs["f2_layout_id"] = spec["f2"]["layout_id"]
            if f2_route_mode is not None:
                cell_kwargs["f2_route_mode"] = f2_route_mode
            if f2_lift_clearance_m is not None:
                cell_kwargs["f2_lift_clearance_m"] = f2_lift_clearance_m
            receipt = _f2_cell(**cell_kwargs)
        else: receipt = _f3_cell(output=cell_dir, root_id=root_id, program_id=program, realization_id=realization, artifact=artifact, prefix_meta=prefix_meta, collection=collection)
        generated[key] = receipt
        if receipt.get("status") != "cell_pass":
            stop_reason = f"cell_execution_failed:{key}"
            _write_root_checkpoint(root_output=root_output, root_id=root_id, contract=contract, spec=spec, cells=list(generated.values()), order=order, source_sha=source_sha, stop_reason=stop_reason, stage="CELL_EXECUTION_FAILED")
            break
        if artifact is None:
            artifact = _save_prefix(root_output, receipt)
            prefix_meta = root_output / "prefix_evidence.json" if (root_output / "prefix_evidence.json").is_file() else None
            if artifact is None:
                receipt["status"] = "cell_failed_prefix"
                receipt["error"] = {"type": "PrefixVerificationError", "message": receipt.get("prefix_verification", {}).get("reason", "prefix evidence failed")}
                atomic_write_json(cell_dir / "cell_receipt.json", receipt)
                stop_reason = f"prefix_verification_failed:{key}"
                _write_root_checkpoint(root_output=root_output, root_id=root_id, contract=contract, spec=spec, cells=list(generated.values()), order=order, source_sha=source_sha, stop_reason=stop_reason, stage="PREFIX_VERIFICATION_FAILED")
                break
        from .finalizer import finalize_cell
        try:
            independent = finalize_cell(cell_dir=cell_dir, spec=spec, expected_relation=program if contract["family"] == "F2" else None, artifact_path=artifact)
        except TypeError as exc:
            # Keep the CPU mock seam used by older regression fixtures while
            # requiring the real finalizer to bind the current root artifact.
            if "artifact_path" in str(exc):
                try:
                    independent = finalize_cell(cell_dir=cell_dir, spec=spec, expected_relation=program if contract["family"] == "F2" else None)
                except BaseException as fallback_exc:
                    independent = {"schema_version": "cmf_f2_f3_independent_cell_finalizer_v2", "pass": False, "error": {"type": type(fallback_exc).__name__, "message": str(fallback_exc)}}
            else:
                independent = {"schema_version": "cmf_f2_f3_independent_cell_finalizer_v2", "pass": False, "error": {"type": type(exc).__name__, "message": str(exc)}}
        except BaseException as exc:
            independent = {"schema_version": "cmf_f2_f3_independent_cell_finalizer_v2", "pass": False, "error": {"type": type(exc).__name__, "message": str(exc)}}
            atomic_write_json(cell_dir / "independent_finalizer_v2.json", independent)
        receipt["cell_local_verified"] = bool(independent.get("pass"))
        receipt["independent_cell_finalizer_path"] = str(cell_dir / "independent_finalizer_v2.json")
        if not receipt["cell_local_verified"] and independent.get("error"):
            receipt["independent_finalizer_error"] = independent["error"]
        atomic_write_json(cell_dir / "cell_receipt.json", receipt)
        if not receipt["cell_local_verified"]:
            stop_reason = f"independent_cell_finalizer_failed:{key}"
            _write_root_checkpoint(root_output=root_output, root_id=root_id, contract=contract, spec=spec, cells=list(generated.values()), order=order, source_sha=source_sha, stop_reason=stop_reason, stage="CELL_FINALIZER_FAILED")
            break
        _write_root_checkpoint(root_output=root_output, root_id=root_id, contract=contract, spec=spec, cells=list(generated.values()), order=order, source_sha=source_sha, stop_reason=None, stage="CELL_VERIFIED")
    cells = []
    for key in expected_keys:
        if key in generated: cells.append(generated[key])
        elif key in reused: cells.append(reused[key])
        else: cells.append({"schema_version": "cmf_pending_cell_v2", "root_id": root_id, "family": contract["family"], "program_id": key.split(":")[0], "realization_id": key.split(":")[1], "status": "PENDING"})
    complete = len(cells) == 6 and all(c.get("status") == "cell_pass" and c.get("cell_local_verified") is True for c in cells)
    root_receipt = {"schema_version": "cmf_f2_f3_root_v2", "root_id": root_id, "family": contract["family"], "layout_id": spec.get("f2", {}).get("layout_id") if contract["family"] == "F2" else None, "route_mode": f2_route_mode if contract["family"] == "F2" else None, "contract": contract, "scene_spec": spec, "scene_spec_sha256": spec["spec_sha256"], "cells": cells, "execution_order": order, "completed_cell_keys": [f"{c.get('program_id')}:{c.get('realization_id')}" for c in cells if c.get("status") == "cell_pass" and c.get("cell_local_verified") is True], "execution_complete": complete, "root_complete": False, "accepted": False, "status": "INCOMPLETE", "new_cell_count": len(generated), "collection_count": sum(c.get("collection") is True for c in generated.values()), "reused_from_root_receipt_sha256": source_sha, "candidate_set": candidate_set_for(spec), "current_anchor_cross_branch": "PENDING_UNTIL_SIX_CELLS", "stop_reason": stop_reason}
    root_receipt["receipt_sha256"] = canonical_sha256(_without_self_hash(root_receipt)); atomic_write_json(root_output / "root_receipt.json", root_receipt)
    _write_root_checkpoint(root_output=root_output, root_id=root_id, contract=contract, spec=spec, cells=cells, order=order, source_sha=source_sha, stop_reason=stop_reason, stage="ROOT_CHECKPOINT")
    if complete:
        from .finalizer import finalize_root
        try:
            root_finalizer = finalize_root(root_dir=root_output, spec=spec)
        except BaseException as exc:
            root_finalizer = {"schema_version": "cmf_f2_f3_independent_root_finalizer_v2", "root_id": root_id, "pass": False, "error": {"type": type(exc).__name__, "message": str(exc)}}
            atomic_write_json(root_output / "independent_root_finalizer_v2.json", root_finalizer)
        root_receipt["independent_root_finalizer"] = root_finalizer
        root_receipt["root_independent_verified"] = bool(root_finalizer.get("pass"))
        root_receipt["root_complete"] = bool(root_finalizer.get("pass"))
        root_receipt["accepted"] = bool(root_finalizer.get("pass"))
        root_receipt["status"] = "ACCEPTED" if root_receipt["accepted"] else "INCOMPLETE_INDEPENDENT_FINALIZER"
        root_receipt["receipt_sha256"] = canonical_sha256(_without_self_hash(root_receipt))
        atomic_write_json(root_output / "root_receipt.json", root_receipt)
        _write_root_checkpoint(root_output=root_output, root_id=root_id, contract=contract, spec=spec, cells=cells, order=order, source_sha=source_sha, stop_reason=stop_reason, stage="ROOT_FINALIZER_COMPLETE" if root_receipt["accepted"] else "ROOT_FINALIZER_FAILED")
    return root_receipt


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", required=True); parser.add_argument("--root-id", required=True, choices=("F2-A-v2", "F2-B-v2", "F3-A-v2", "F3-B-v2")); parser.add_argument("--cell-keys"); parser.add_argument("--existing-root"); parser.add_argument("--no-collection", action="store_true"); parser.add_argument("--f2-layout-id", choices=("v4_beside_y_workspace", "v5_beside_y_lower")); parser.add_argument("--f2-route-mode", choices=("three_segment_high", "side_then_geometry_target")); parser.add_argument("--f2-lift-clearance-m", type=float); args = parser.parse_args(); keys = args.cell_keys.split(",") if args.cell_keys else None; result = run_root(output=args.output, root_id=args.root_id, cell_keys=keys, existing_root=args.existing_root, collection=not args.no_collection, f2_layout_id=args.f2_layout_id, f2_route_mode=args.f2_route_mode, f2_lift_clearance_m=args.f2_lift_clearance_m); print(json.dumps({"root_id": result["root_id"], "status": result["status"], "completed_cell_keys": result["completed_cell_keys"], "receipt_sha256": result["receipt_sha256"]}, ensure_ascii=False)); failures = any(cell.get("status") not in {"cell_pass", "PENDING"} for cell in result["cells"]); partial_ok = result["status"] == "INCOMPLETE" and not failures and not result.get("stop_reason"); raise SystemExit(0 if result["accepted"] or partial_ok else 1)


if __name__ == "__main__": main()
