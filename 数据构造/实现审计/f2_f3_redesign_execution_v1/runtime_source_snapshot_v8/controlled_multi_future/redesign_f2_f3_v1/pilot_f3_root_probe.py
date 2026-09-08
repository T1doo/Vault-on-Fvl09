"""F3 pilot-root runner: six real qualification/collection cells for F3-A."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import sapien

from envs.utils.action import ArmTag
from ..family_runners_v3_1 import _must_action, _move_arm, _wait_and_record
from ..probes.lifecycle import cleanup_status, initialize_cleanup_fields, managed_scene
from ..probes.scene_inspection import _args
from ..runtime_v2_contracts import PROVISIONAL_RUNTIME_THRESHOLDS
from ..signals import closed_loop_event_metrics
from ..verifiers.f3 import verify_realized_motion_metrics, verify_return_equivalence
from .canonical import atomic_write_json, canonical_sha256, sha256_file
from .pilot_contract import expected_cells, planned_root_contract, reusable_cells, selected_cells
from .scene import RedesignF3Scene


def _pose(actor):
    value = actor.get_pose()
    return np.asarray(value.p.tolist() + value.q.tolist(), dtype=np.float64)


def _eef(scene):
    return np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)


def _quat_distance(first, second) -> float:
    a = np.asarray(first, dtype=np.float64)
    b = np.asarray(second, dtype=np.float64)
    a /= np.linalg.norm(a)
    b /= np.linalg.norm(b)
    return float(2.0 * np.arccos(np.clip(abs(float(np.dot(a, b))), -1.0, 1.0)))


def _motion_metrics(rows: list[dict[str, Any]], axis: str) -> dict[str, Any]:
    main_axis = 2 if axis == "V" else 0
    eef = np.asarray([row["eef"][:3] for row in rows], dtype=np.float64)
    bottle = np.asarray([row["actor_pose"][:3] for row in rows], dtype=np.float64)
    eef_metrics = closed_loop_event_metrics(eef, eef[0], main_axis)
    bottle_metrics = closed_loop_event_metrics(bottle, bottle[0], main_axis)
    contacts = np.asarray([bool(row.get("selected_gripper_contact", False)) for row in rows], dtype=bool)
    quaternions = [row["actor_pose"][3:] for row in rows]
    breaks = int(np.count_nonzero(contacts[:-1] & ~contacts[1:])) if len(contacts) > 1 else int(not bool(contacts[0]))
    return {
        "axis": axis,
        "row_count": len(rows),
        "eef_positive_amplitude": eef_metrics["positive_amplitude"],
        "eef_negative_amplitude": eef_metrics["negative_amplitude"],
        "eef_max_off_axis": eef_metrics["max_off_axis"],
        "eef_return_error": eef_metrics["return_error"],
        "bottle_positive_amplitude": bottle_metrics["positive_amplitude"],
        "bottle_negative_amplitude": bottle_metrics["negative_amplitude"],
        "bottle_max_off_axis": bottle_metrics["max_off_axis"],
        "bottle_return_error": bottle_metrics["return_error"],
        "bottle_orientation_drift": max(_quat_distance(quaternions[0], value) for value in quaternions),
        "selected_gripper_contact_fraction": float(np.mean(contacts)),
        "contact_break_count": breaks,
    }


def _reduced_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        result.append({
            "eef": np.asarray(row["eef"], dtype=np.float64).tolist(),
            "actor_pose": np.asarray(row["actor_pose"], dtype=np.float64).tolist(),
            "controller_effective_setpoint": np.asarray(row["effective_setpoint"], dtype=np.float64).tolist(),
            "requested_command": np.asarray(row["requested_command"], dtype=np.float64).tolist(),
        })
    return result


def _command_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = ("effective_setpoint", "requested_command", "component_mask", "left_gripper_joint_drive_target", "right_gripper_joint_drive_target", "left_gripper_joint_drive_velocity_target", "right_gripper_joint_drive_velocity_target")
    return [{key: np.asarray(row[key]).tolist() for key in keys} for row in rows]


def _command_hash_from_artifact(artifact: Any) -> str:
    keys = ("effective_setpoint", "requested_command", "component_mask", "left_gripper_joint_drive_target", "right_gripper_joint_drive_target", "left_gripper_joint_drive_velocity_target", "right_gripper_joint_drive_velocity_target")
    return canonical_sha256({key: np.asarray(artifact[key]).tolist() for key in keys})


def _command_hash_from_rows(rows: list[dict[str, Any]]) -> str:
    keys = ("effective_setpoint", "requested_command", "component_mask", "left_gripper_joint_drive_target", "right_gripper_joint_drive_target", "left_gripper_joint_drive_velocity_target", "right_gripper_joint_drive_velocity_target")
    return canonical_sha256({key: [np.asarray(row[key]).tolist() for row in rows] for key in keys})


def _closed_loop_event(scene, realization: str, axis: str, label: str, receipt: dict[str, Any]) -> None:
    """Execute a symmetric event about one frozen realized center pose."""
    main_axis = 2 if axis == "V" else 0
    center = _eef(scene)
    holds = (20, 20, 20) if realization != "r_inv_motion" else (30, 35, 30)
    for phase, offset, hold in zip(("negative", "positive", "return"), (-0.05, 0.05, 0.0), holds):
        target = center.copy()
        target[main_axis] += offset
        _move_arm(scene, target, f"{label}_{phase}")
        receipt["action_segment_count"] += 1
        _wait_and_record(scene, hold)


def run_cell(*, output: Path, root_id: str, program_id: str, realization_id: str, seed: int, prefix_artifact: Path | None = None, collection: bool = True) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    receipt: dict[str, Any] = {
        "schema_version": "cmf_f3_pilot_cell_v1",
        "root_id": root_id,
        "family": "F3",
        "program_id": program_id,
        "realization_id": realization_id,
        "collection": collection,
        "formal_data": False,
        "stage0_data": False,
        "status": "running",
        "action_segment_count": 0,
        "solver_problem_count": 0,
    }
    if realization_id == "r_pc":
        receipt["realization_contract"] = {"kind": "baseline", "variant_applied": True, "path_variant": "direct_event_sequence", "motion_variant": "planner_default"}
    elif realization_id == "r_inv_path":
        receipt["realization_contract"] = {"kind": "path", "variant_applied": False, "path_variant": "post_prefix_y_detour_30mm_round_trip", "motion_variant": "planner_default"}
    elif realization_id == "r_inv_motion":
        receipt["realization_contract"] = {"kind": "motion", "variant_applied": True, "path_variant": "direct_event_sequence", "motion_variant": "displacement_controller_for_vh_events"}
    else:
        raise ValueError(f"unknown F3 realization: {realization_id}")
    initialize_cleanup_fields(receipt)
    started = time.monotonic()
    args = _args("F3", output / "scene"); args.update({"seed": seed, "task_name": f"cmf_f3_pilot_{root_id}", "render_freq": 0, "save_data": False, "collect_data": False, "need_plan": True})
    try:
        with managed_scene(RedesignF3Scene, args, receipt, f"f3-pilot-{program_id}-{realization_id}") as scene:
            scene.initialize_trace(scene.bottle, "left", scene.role_actors)
            current = _pose(scene.bottle).tolist(); anchor = current[:]
            receipt["current"] = current; receipt["anchor"] = anchor
            if prefix_artifact is None:
                grasp = scene.grasp_actor(scene.bottle, ArmTag("left"), pre_grasp_dis=0.09, grasp_dis=0.0, gripper_pos=0.0, contact_point_id=0)
                _must_action(scene, grasp, "pilot_grasp"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 250)
                eef_before_lift = _eef(scene); lift = eef_before_lift.copy(); lift[2] += 0.025; _move_arm(scene, lift, "pilot_micro_lift"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 50)
                # The first complete V is the shared prefix for all three programs.
                prefix_event_start = len(scene.trace) - 1
                _closed_loop_event(scene, realization_id, "V", "prefix_V", receipt)
                prefix_end = len(scene.trace) - 1
                prefix_hash = _command_hash_from_rows(scene.trace[: prefix_end + 1])
                prefix_metrics = _motion_metrics(scene.trace[prefix_event_start:prefix_end + 1], "V")
                receipt["prefix_event_evidence"] = {"start_row": prefix_event_start, "end_row": prefix_end, "metrics": prefix_metrics, "verifier": verify_realized_motion_metrics({"shared_V": prefix_metrics}, PROVISIONAL_RUNTIME_THRESHOLDS)}
            else:
                artifact = np.load(prefix_artifact, allow_pickle=False)
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
                prefix_end = len(scene.trace) - 1
                prefix_hash = _command_hash_from_artifact(artifact)
                lift = _eef(scene); eef_before_lift = lift.copy(); eef_before_lift[2] -= 0.025
            receipt["prefix_end_trace_row"] = prefix_end; receipt["prefix_sha256"] = prefix_hash
            if realization_id == "r_inv_path":
                detour = _eef(scene); detour[1] -= 0.03
                _move_arm(scene, detour, "path_variant_y_detour"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 20)
                detour_return = detour.copy(); detour_return[1] += 0.03
                _move_arm(scene, detour_return, "path_variant_y_return"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 20)
                receipt["realization_contract"]["variant_applied"] = True
            suffix = {"VVHH": ("V", "H", "H"), "VHVH": ("H", "V", "H"), "VHHV": ("H", "H", "V")}[program_id]
            receipt["expected_suffix_event_order"] = list(suffix)
            receipt["event_segments"] = []
            for index, axis in enumerate(suffix):
                event_start = len(scene.trace) - 1
                _closed_loop_event(scene, realization_id, axis, f"suffix_{index}_{axis}", receipt)
                event_end = len(scene.trace) - 1
                metrics = _motion_metrics(scene.trace[event_start:event_end + 1], axis)
                receipt["event_segments"].append({"event_index": index + 1, "axis": axis, "start_row": event_start, "end_row": event_end, "metrics": metrics})
            event_metrics = {f"suffix_{item['event_index']}_{item['axis']}": item["metrics"] for item in receipt["event_segments"]}
            receipt["event_verifier"] = verify_realized_motion_metrics(event_metrics, PROVISIONAL_RUNTIME_THRESHOLDS)
            carried_object = _pose(scene.bottle)
            carried_eef = _eef(scene)
            current_object_pose = sapien.Pose(carried_object[:3], carried_object[3:])
            current_eef_pose = sapien.Pose(carried_eef[:3], carried_eef[3:])
            relative_object_from_eef = current_eef_pose.inv() * current_object_pose
            desired_object_pose = sapien.Pose(anchor[:3], anchor[3:])
            desired_eef_pose = desired_object_pose * relative_object_from_eef.inv()
            return_support = np.asarray(desired_eef_pose.p.tolist() + desired_eef_pose.q.tolist(), dtype=np.float64)
            return_above = return_support.copy(); return_above[2] += 0.025
            receipt["return_target_binding"] = {"carried_eef": carried_eef.tolist(), "carried_object": carried_object.tolist(), "relative_object_from_eef": relative_object_from_eef.p.tolist() + relative_object_from_eef.q.tolist(), "desired_object": anchor, "return_above": return_above.tolist(), "return_support": return_support.tolist()}
            _move_arm(scene, return_above, "pilot_return_height_bound"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 30)
            _move_arm(scene, return_support, "pilot_return_support_bound"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 100)
            support_end = len(scene.trace) - 1
            _must_action(scene, scene.open_gripper(ArmTag("left"), pos=1.0), "pilot_open"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 50)
            _wait_and_record(scene, 200)
            exit_target = _eef(scene); exit_target[2] += 0.05; exit_target[0] += 0.10; _move_arm(scene, exit_target, "pilot_empty_hand_exit"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 50)
            _wait_and_record(scene, 200)
            rows = scene.trace; exit_rows = rows[-50:]; support_rows = rows[max(0, support_end - 49): support_end + 1]
            can_name = scene.bottle.get_name()
            def pair_has(row, first, second):
                return any(first in {str(pair.get("body_a", "")), str(pair.get("body_b", ""))} and second in {str(pair.get("body_a", "")), str(pair.get("body_b", ""))} for pair in row.get("contact_pairs", []))
            support_fraction = float(np.mean([pair_has(row, can_name, "f3_redesign_support_pad") for row in support_rows])) if support_rows else 0.0
            exit_contact = float(np.mean([row.get("selected_gripper_contact", False) for row in exit_rows])) if exit_rows else 1.0
            final_support = np.asarray([pair_has(row, can_name, "f3_redesign_support_pad") for row in exit_rows], dtype=bool)
            final_object_speeds = np.asarray([np.linalg.norm(row["actor_linear_velocity"]) for row in exit_rows], dtype=np.float64)
            final_eef_speeds = np.asarray([np.linalg.norm(row["eef_linear_velocity"]) for row in exit_rows], dtype=np.float64)
            final_eef_angular_speeds = np.asarray([np.linalg.norm(row["eef_angular_velocity"]) for row in exit_rows], dtype=np.float64)
            final_pose = _pose(scene.bottle)
            final_position_error = float(np.linalg.norm(final_pose[:3] - np.asarray(anchor[:3], dtype=np.float64)))
            final_orientation_error = _quat_distance(final_pose[3:], np.asarray(anchor[3:], dtype=np.float64))
            gripper_open = bool(exit_rows and np.mean([float(row["gripper_command"][0]) for row in exit_rows]) >= 0.9)
            receipt["terminal_verifier"] = verify_return_equivalence(position_error=final_position_error, orientation_error=final_orientation_error, rest_position_error=final_position_error, rest_orientation_error=final_orientation_error, stable_speed_samples=final_object_speeds, support_contact_samples=final_support, gripper_open=gripper_open, thresholds=PROVISIONAL_RUNTIME_THRESHOLDS, eef_linear_speed=float(np.max(final_eef_speeds)) if len(final_eef_speeds) else float("inf"), eef_angular_speed=float(np.max(final_eef_angular_speeds)) if len(final_eef_angular_speeds) else float("inf"))
            receipt["terminal_metrics"] = {"final_bottle_pose": final_pose.tolist(), "position_error_m": final_position_error, "orientation_error_rad": final_orientation_error, "max_object_linear_speed_mps": float(np.max(final_object_speeds)) if len(final_object_speeds) else None, "max_eef_linear_speed_mps": float(np.max(final_eef_speeds)) if len(final_eef_speeds) else None, "max_eef_angular_speed_rps": float(np.max(final_eef_angular_speeds)) if len(final_eef_angular_speeds) else None, "support_contact_fraction": float(np.mean(final_support)) if len(final_support) else 0.0, "gripper_open": gripper_open}
            receipt["solver_problem_count"] = int(getattr(scene, "planner_query_count", 0))
            prefix_contact_fraction = float(np.mean([bool(row.get("selected_gripper_contact", False)) for row in rows[max(0, prefix_end - 49):prefix_end + 1]]))
            prefix_event_pass = receipt.get("prefix_event_evidence", {}).get("verifier", {}).get("pass", True)
            receipt["gates"] = {"prefix_present": bool(prefix_hash), "prefix_contact_stable": prefix_contact_fraction >= 0.95, "prefix_first_V_realized": bool(prefix_event_pass), "support_identity_before_release": support_fraction >= 0.8, "empty_hand_exit": exit_contact == 0.0, "trace_complete": len(rows) > prefix_end, "realized_event_order": [item["axis"] for item in receipt["event_segments"]] == list(suffix), "realized_event_metrics": bool(receipt["event_verifier"]["pass"]), "terminal_return_release_stable": bool(receipt["terminal_verifier"]["pass"]), "realization_variant_applied": bool(receipt["realization_contract"]["variant_applied"])}
            receipt["prefix_contact_fraction"] = prefix_contact_fraction
            receipt["support_contact_fraction"] = support_fraction; receipt["exit_contact_fraction"] = exit_contact
            trace_path = output / "trace.npz"; receipt["trace"] = scene.save_trace(trace_path); receipt["trace_path"] = str(trace_path)
            receipt["status"] = "cell_pass" if all(receipt["gates"].values()) else "cell_failed_gates"
    except BaseException as exc:
        receipt["status"] = "cell_failed_execution"; receipt["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if "scene" in locals() and scene is not None and getattr(scene, "trace", None) and "trace_path" not in receipt:
            try:
                trace_path = output / "trace.npz"; receipt["trace"] = scene.save_trace(trace_path); receipt["trace_path"] = str(trace_path)
            except BaseException as exc:
                receipt["trace_save_error"] = {"type": type(exc).__name__, "message": str(exc)}
        receipt["status"] = cleanup_status(receipt, receipt["status"]); receipt["elapsed_seconds"] = time.monotonic() - started; atomic_write_json(output / "cell_receipt.json", receipt)
    return receipt


def run_root(
    output_root: str | Path,
    root_id: str = "F3-A",
    existing_root: str | Path | None = None,
    programs: list[str] | tuple[str, ...] | None = None,
    realizations: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    root_output = Path(output_root); root_output.mkdir(parents=True, exist_ok=True); contract = planned_root_contract(root_id); cells = []
    full_cells = expected_cells(root_id)
    run_cells = selected_cells(root_id, programs, realizations)
    run_keys = {(cell["program_id"], cell["realization_id"]) for cell in run_cells}
    if existing_root is not None and programs is None and realizations is None:
        raise ValueError("resume root requires an explicit program or realization subset")
    if existing_root is None and len(run_keys) != len(full_cells):
        raise ValueError("a partial root run requires an existing root for immutable reuse")
    reused: dict[tuple[str, str], dict[str, Any]] = {}
    source_receipt_sha = None
    prefix_artifact = None
    if existing_root is not None:
        source_root = Path(existing_root)
        source_receipt_path = source_root / "root_receipt.json"
        source = json.loads(source_receipt_path.read_text(encoding="utf-8"))
        reuse_keys = {(cell["program_id"], cell["realization_id"]) for cell in full_cells} - run_keys
        reused_list = reusable_cells(source, root_id, cell_keys=reuse_keys)
        reused = {(cell["program_id"], cell["realization_id"]): cell for cell in reused_list}
        source_receipt_sha = sha256_file(source_receipt_path)
        prefix_artifact = source_root / "prefix_artifact.npz"
        if not prefix_artifact.is_file():
            raise ValueError("resume root is missing its immutable prefix artifact")
    for index, cell in enumerate(full_cells):
        key = (cell["program_id"], cell["realization_id"])
        if key in reused:
            cells.append(reused[key])
            continue
        if key not in run_keys:
            raise ValueError(f"cell {key} is neither selected for execution nor available for reuse")
        cell_dir = root_output / f"{cell['program_id']}_{cell['realization_id']}"
        receipt = run_cell(output=cell_dir, root_id=root_id, program_id=cell["program_id"], realization_id=cell["realization_id"], seed=contract["scene_seed"], prefix_artifact=prefix_artifact)
        cells.append(receipt)
        if prefix_artifact is None and receipt.get("status") == "cell_pass":
            trace = np.load(cell_dir / "trace.npz", allow_pickle=False); n = int(receipt["prefix_end_trace_row"]) + 1
            prefix_artifact = root_output / "prefix_artifact.npz"
            np.savez(prefix_artifact, effective_setpoint=trace["controller_effective_setpoint"][:n], requested_command=trace["requested_command"][:n], component_mask=trace["component_masks"][:n], left_gripper_joint_drive_target=trace["left_gripper_joint_drive_target"][:n], right_gripper_joint_drive_target=trace["right_gripper_joint_drive_target"][:n], left_gripper_joint_drive_velocity_target=trace["left_gripper_joint_drive_velocity_target"][:n], right_gripper_joint_drive_velocity_target=trace["right_gripper_joint_drive_velocity_target"][:n])
    current = {json.dumps(item.get("current"), sort_keys=True) for item in cells}; anchors = {json.dumps(item.get("anchor"), sort_keys=True) for item in cells}; prefixes = {item.get("prefix_sha256") for item in cells}
    accepted = len(cells) == 6 and all(item.get("status") == "cell_pass" for item in cells) and len(current) == 1 and len(anchors) == 1 and len(prefixes) == 1
    new_cell_count = len(run_keys)
    receipt = {"schema_version": "cmf_f3_pilot_root_receipt_v1", "root_id": root_id, "family": "F3", "contract": contract, "cells": cells, "current_equivalence": len(current) == 1, "anchor_equivalence": len(anchors) == 1, "prefix_exact_replay": len(prefixes) == 1, "accepted": accepted, "status": "ACCEPTED" if accepted else "INCOMPLETE", "collection": True, "collection_count": new_cell_count, "run_programs": list(dict.fromkeys(cell["program_id"] for cell in run_cells)), "run_realizations": list(dict.fromkeys(cell["realization_id"] for cell in run_cells)), "new_cell_keys": [f"{key[0]}:{key[1]}" for key in sorted(run_keys)], "new_cell_count": new_cell_count, "reused_cell_count": len(reused), "reused_from_root_receipt": source_receipt_sha, "reused_cell_keys": [f"{key[0]}:{key[1]}" for key in reused]}
    atomic_write_json(root_output / "root_receipt.json", receipt); return receipt


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", required=True); parser.add_argument("--root-id", default="F3-A"); parser.add_argument("--existing-root"); parser.add_argument("--programs"); parser.add_argument("--realizations"); args = parser.parse_args()
    programs = [item for item in args.programs.split(",") if item] if args.programs else None
    realizations = [item for item in args.realizations.split(",") if item] if args.realizations else None
    result = run_root(args.output, args.root_id, args.existing_root, programs, realizations); raise SystemExit(0 if result["accepted"] else 1)


if __name__ == "__main__": main()
