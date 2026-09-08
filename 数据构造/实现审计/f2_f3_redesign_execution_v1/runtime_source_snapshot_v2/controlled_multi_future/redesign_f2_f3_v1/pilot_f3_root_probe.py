"""F3 pilot-root runner: six real qualification/collection cells for F3-A."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from envs.utils.action import ArmTag
from ..family_runners_v3_1 import _must_action, _move_arm, _wait_and_record
from ..probes.lifecycle import cleanup_status, initialize_cleanup_fields, managed_scene
from ..probes.scene_inspection import _args
from .canonical import atomic_write_json, canonical_sha256
from .pilot_contract import expected_cells, planned_root_contract
from .scene import RedesignF3Scene


def _pose(actor):
    value = actor.get_pose()
    return np.asarray(value.p.tolist() + value.q.tolist(), dtype=np.float64)


def _eef(scene):
    return np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)


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


def _move_event(scene, realization: str, dx: float, dz: float, label: str, receipt: dict[str, Any]) -> None:
    if realization == "r_inv_motion":
        _must_action(scene, scene.move_by_displacement(ArmTag("left"), x=dx, z=dz), label)
    else:
        target = _eef(scene); target[0] += dx; target[2] += dz; _move_arm(scene, target, label)
    receipt["action_segment_count"] += 1
    _wait_and_record(scene, 20)


def run_cell(*, output: Path, root_id: str, program_id: str, realization_id: str, seed: int, prefix_artifact: Path | None = None) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    receipt: dict[str, Any] = {
        "schema_version": "cmf_f3_pilot_cell_v1",
        "root_id": root_id,
        "family": "F3",
        "program_id": program_id,
        "realization_id": realization_id,
        "collection": True,
        "formal_data": False,
        "stage0_data": False,
        "status": "running",
        "action_segment_count": 0,
        "solver_problem_count": 0,
    }
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
                _move_event(scene, realization_id, 0.0, -0.05, "prefix_V_negative", receipt)
                _move_event(scene, realization_id, 0.0, 0.10, "prefix_V_positive", receipt)
                _move_event(scene, realization_id, 0.0, -0.05, "prefix_V_return", receipt)
                prefix_end = len(scene.trace) - 1
                prefix_hash = _command_hash_from_rows(scene.trace[: prefix_end + 1])
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
            suffix = {"VVHH": ("V", "H", "H"), "VHVH": ("H", "V", "H"), "VHHV": ("H", "H", "V")}[program_id]
            for index, axis in enumerate(suffix):
                if axis == "V":
                    _move_event(scene, realization_id, 0.0, -0.05, f"suffix_{index}_V_negative", receipt); _move_event(scene, realization_id, 0.0, 0.10, f"suffix_{index}_V_positive", receipt); _move_event(scene, realization_id, 0.0, -0.05, f"suffix_{index}_V_return", receipt)
                else:
                    _move_event(scene, realization_id, -0.05, 0.0, f"suffix_{index}_H_negative", receipt); _move_event(scene, realization_id, 0.10, 0.0, f"suffix_{index}_H_positive", receipt); _move_event(scene, realization_id, -0.05, 0.0, f"suffix_{index}_H_return", receipt)
            _move_arm(scene, lift, "pilot_return_height"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 20)
            _move_arm(scene, eef_before_lift, "pilot_return_support"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 50)
            support_end = len(scene.trace) - 1
            _must_action(scene, scene.open_gripper(ArmTag("left"), pos=1.0), "pilot_open"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 50)
            exit_target = _eef(scene); exit_target[2] += 0.05; exit_target[0] += 0.10; _move_arm(scene, exit_target, "pilot_empty_hand_exit"); receipt["action_segment_count"] += 1; _wait_and_record(scene, 50)
            rows = scene.trace; exit_rows = rows[-50:]; support_rows = rows[max(0, support_end - 49): support_end + 1]
            can_name = scene.bottle.get_name()
            def pair_has(row, first, second):
                return any(first in {str(pair.get("body_a", "")), str(pair.get("body_b", ""))} and second in {str(pair.get("body_a", "")), str(pair.get("body_b", ""))} for pair in row.get("contact_pairs", []))
            support_fraction = float(np.mean([pair_has(row, can_name, "f3_redesign_support_pad") for row in support_rows])) if support_rows else 0.0
            exit_contact = float(np.mean([row.get("selected_gripper_contact", False) for row in exit_rows])) if exit_rows else 1.0
            receipt["solver_problem_count"] = int(getattr(scene, "planner_query_count", 0))
            receipt["gates"] = {"prefix_present": bool(prefix_hash), "support_identity": support_fraction >= 0.8, "empty_hand_exit": exit_contact == 0.0, "trace_complete": len(rows) > prefix_end, "program_order": program_id in {"VVHH", "VHVH", "VHHV"}}
            receipt["support_contact_fraction"] = support_fraction; receipt["exit_contact_fraction"] = exit_contact
            trace_path = output / "trace.npz"; receipt["trace"] = scene.save_trace(trace_path); receipt["trace_path"] = str(trace_path)
            receipt["status"] = "cell_pass" if all(receipt["gates"].values()) else "cell_failed_gates"
    except BaseException as exc:
        receipt["status"] = "cell_failed_execution"; receipt["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        receipt["status"] = cleanup_status(receipt, receipt["status"]); receipt["elapsed_seconds"] = time.monotonic() - started; atomic_write_json(output / "cell_receipt.json", receipt)
    return receipt


def run_root(output_root: str | Path, root_id: str = "F3-A") -> dict[str, Any]:
    root_output = Path(output_root); root_output.mkdir(parents=True, exist_ok=True); contract = planned_root_contract(root_id); cells = []; prefix_artifact = None
    for index, cell in enumerate(expected_cells(root_id)):
        cell_dir = root_output / f"{cell['program_id']}_{cell['realization_id']}"
        receipt = run_cell(output=cell_dir, root_id=root_id, program_id=cell["program_id"], realization_id=cell["realization_id"], seed=contract["scene_seed"], prefix_artifact=prefix_artifact)
        cells.append(receipt)
        if index == 0 and receipt.get("status") == "cell_pass":
            trace = np.load(cell_dir / "trace.npz", allow_pickle=False); n = int(receipt["prefix_end_trace_row"]) + 1
            prefix_artifact = root_output / "prefix_artifact.npz"
            np.savez(prefix_artifact, effective_setpoint=trace["controller_effective_setpoint"][:n], requested_command=trace["requested_command"][:n], component_mask=trace["component_masks"][:n], left_gripper_joint_drive_target=trace["left_gripper_joint_drive_target"][:n], right_gripper_joint_drive_target=trace["right_gripper_joint_drive_target"][:n], left_gripper_joint_drive_velocity_target=trace["left_gripper_joint_drive_velocity_target"][:n], right_gripper_joint_drive_velocity_target=trace["right_gripper_joint_drive_velocity_target"][:n])
    current = {json.dumps(item.get("current"), sort_keys=True) for item in cells}; anchors = {json.dumps(item.get("anchor"), sort_keys=True) for item in cells}; prefixes = {item.get("prefix_sha256") for item in cells}
    accepted = len(cells) == 6 and all(item.get("status") == "cell_pass" for item in cells) and len(current) == 1 and len(anchors) == 1 and len(prefixes) == 1
    receipt = {"schema_version": "cmf_f3_pilot_root_receipt_v1", "root_id": root_id, "family": "F3", "contract": contract, "cells": cells, "current_equivalence": len(current) == 1, "anchor_equivalence": len(anchors) == 1, "prefix_exact_replay": len(prefixes) == 1, "accepted": accepted, "status": "ACCEPTED" if accepted else "INCOMPLETE"}
    atomic_write_json(root_output / "root_receipt.json", receipt); return receipt


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", required=True); parser.add_argument("--root-id", default="F3-A"); args = parser.parse_args(); result = run_root(args.output, args.root_id); raise SystemExit(0 if result["accepted"] else 1)


if __name__ == "__main__": main()
