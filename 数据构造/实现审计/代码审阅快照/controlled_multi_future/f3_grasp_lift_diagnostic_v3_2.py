"""Real post-grasp lift diagnostic for F3 runtime-v3_2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
import traceback

import numpy as np

from .anchor import quaternion_angular_error
from .family_runners_v3_1 import (
    _arm_tag_left,
    _entity,
    _execute_control,
    _move_left,
    _must_action,
    _plan_left,
    _pose,
    _wait_and_record,
)
from .geometry import relative_pose, world_axis_offset_pose
from .planner_dtype_v3_2 import planner_array, planner_dtype_receipt
from .probes.runtime_trace import _gripper_joint_qpos


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _state(scene, label: str) -> dict:
    row = scene.trace[-1]
    eef = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
    bottle = _pose(scene.bottle)
    return {
        "label": label,
        "step_index": int(row["step_index"]),
        "robot_qpos": planner_array(scene.robot.left_entity.get_qpos(), label=f"{label} qpos").tolist(),
        "robot_qvel": np.asarray(scene.robot.left_entity.get_qvel(), dtype=np.float64).tolist(),
        "eef_pose": eef.tolist(),
        "bottle_pose": bottle.tolist(),
        "T_eef_actor": relative_pose(eef, bottle).tolist(),
        "gripper_command": np.asarray(row["gripper_command"], dtype=np.float64).tolist(),
        "actual_gripper_joint_qpos": _gripper_joint_qpos(scene.robot, "left").tolist(),
        "selected_gripper_contact": bool(row["selected_gripper_contact"]),
        "selected_gripper_contact_count": int(row["selected_gripper_contact_count"]),
        "selected_gripper_contact_impulse": float(row["selected_gripper_contact_impulse"]),
        "bottle_linear_velocity": np.asarray(row["actor_linear_velocity"], dtype=np.float64).tolist(),
        "bottle_angular_velocity": np.asarray(row["actor_angular_velocity"], dtype=np.float64).tolist(),
        "contact_pairs": row["contact_pairs"],
    }


def _plan_and_execute_lift(scene, *, distance_m: float, segment_id: str) -> dict:
    actual_start_qpos = planner_array(
        scene.robot.left_entity.get_qpos(),
        label=f"{segment_id} actual post-grasp qpos",
    )
    start_eef = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
    goal = world_axis_offset_pose(start_eef, distance_m)
    control = _plan_left(
        scene,
        goal,
        last_qpos=actual_start_qpos,
        source=segment_id,
    )
    status = control.get("status") if isinstance(control, dict) else "Fail"
    receipt = {
        "segment_id": segment_id,
        "distance_m": float(distance_m),
        "planner_status": status,
        "planner_start_qpos": actual_start_qpos.tolist(),
        "planner_goal_eef_pose": planner_array(goal, shape=(7,), label=f"{segment_id} goal").tolist(),
        "dtype_contract": planner_dtype_receipt(
            qpos=actual_start_qpos,
            goal_pose=goal,
            control=control if isinstance(control, dict) else None,
        ),
    }
    if status != "Success":
        return receipt
    positions = planner_array(control["position"], label=f"{segment_id} positions")
    receipt["planner_terminal_arm_qpos"] = positions[-1].tolist()
    _execute_control(scene, control, segment_id)
    receipt["executed"] = True
    receipt["actual_terminal_qpos"] = planner_array(
        scene.robot.left_entity.get_qpos(), label=f"{segment_id} actual terminal qpos"
    ).tolist()
    return receipt


class F3GraspLiftDiagnosticV3_2:
    def __init__(self, adapter):
        self.adapter = adapter

    def run(self, *, output_dir: Path, planned_root_slot_spec, program) -> dict:
        started = time.time()
        output_dir.mkdir(parents=True, exist_ok=False)
        receipt = {
            "schema_version": "cmf_f3_grasp_lift_diagnostic_v3_2",
            "implementation_version": "controlled_multi_future_runtime_v3_2",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "program_id": program["program_id"],
            "execution_attempt_count": 1,
            "planner_query_limit": 16,
            "states": [],
            "lift_segments": [],
            "status": "running",
        }
        _write(output_dir / "planned_root_slot_spec.json", planned_root_slot_spec)
        context = self.adapter.scene(planned_root_slot_spec, phase="f3_v3_2_grasp_lift", program=program)
        handle = None
        scene = None
        try:
            with context as entered:
                handle = entered
                scene = entered.scene
                receipt["reference_current"] = self.adapter.capture_current(scene)
                receipt["reference_anchor"] = self.adapter.capture_anchor(scene)
                task = self.adapter.audit_task_physical_feasibility(scene, program)
                receipt["task_physical_receipt"] = task
                if not (task.get("task_feasible") is True and task.get("physical_feasible") is True):
                    raise RuntimeError("F3 v3.2 diagnostic task/physical feasibility failed")

                scene.initialize_trace(scene.bottle, "left", role_actors=scene.role_actors)
                scene.planner_query_limit = 16
                pregrasp, grasp = scene.choose_grasp_pose(
                    scene.bottle,
                    arm_tag=_arm_tag_left(),
                    pre_dis=0.09,
                    target_dis=0,
                )
                _move_left(scene, pregrasp, "diagnostic_pregrasp")
                receipt["states"].append(_state(scene, "after_pregrasp"))
                _move_left(scene, grasp, "diagnostic_grasp_pose")
                receipt["states"].append(_state(scene, "at_grasp_pose"))
                _must_action(scene, scene.close_gripper(_arm_tag_left(), pos=0.0), "diagnostic_close_gripper")
                _wait_and_record(scene, 25)
                post_grasp = _state(scene, "post_grasp_hold")
                receipt["states"].append(post_grasp)

                first = _plan_and_execute_lift(
                    scene,
                    distance_m=0.04,
                    segment_id="post_grasp_lift_4cm",
                )
                receipt["lift_segments"].append(first)
                if first.get("planner_status") != "Success" or first.get("executed") is not True:
                    raise RuntimeError("post-grasp 4cm lift failed")
                _wait_and_record(scene, 25)
                after_4cm = _state(scene, "after_4cm_lift_hold")
                receipt["states"].append(after_4cm)

                second = _plan_and_execute_lift(
                    scene,
                    distance_m=0.04,
                    segment_id="post_grasp_lift_8cm",
                )
                receipt["lift_segments"].append(second)
                if second.get("planner_status") != "Success" or second.get("executed") is not True:
                    raise RuntimeError("post-grasp 8cm cumulative lift failed")
                _wait_and_record(scene, 25)
                after_8cm = _state(scene, "after_8cm_lift_hold")
                receipt["states"].append(after_8cm)

                third = _plan_and_execute_lift(
                    scene,
                    distance_m=0.04,
                    segment_id="post_grasp_lift_to_full_height",
                )
                receipt["lift_segments"].append(third)
                if third.get("planner_status") != "Success" or third.get("executed") is not True:
                    raise RuntimeError("post-grasp full lift failed")
                _wait_and_record(scene, 25)
                after_full = _state(scene, "after_full_lift_hold")
                receipt["states"].append(after_full)

                initial_transform = np.asarray(post_grasp["T_eef_actor"], dtype=np.float64)
                final_transform = np.asarray(after_full["T_eef_actor"], dtype=np.float64)
                bottle_z_delta = float(after_full["bottle_pose"][2] - post_grasp["bottle_pose"][2])
                checks = {
                    "post_grasp_contact": post_grasp["selected_gripper_contact"],
                    "contact_after_4cm": after_4cm["selected_gripper_contact"],
                    "contact_after_8cm": after_8cm["selected_gripper_contact"],
                    "contact_after_full_lift": after_full["selected_gripper_contact"],
                    "bottle_lift_delta": bottle_z_delta >= 0.10,
                    "grasp_translation_stable": float(np.linalg.norm(initial_transform[:3] - final_transform[:3])) <= 0.005,
                    "grasp_orientation_stable": quaternion_angular_error(initial_transform[3:], final_transform[3:]) <= 0.05,
                }
                receipt["checks"] = checks
                receipt["bottle_lift_delta_m"] = bottle_z_delta
                receipt["attachment_audit"] = {
                    "official_left_plan_path_attachment_used": False,
                    "official_api_limitation": "RoboTwin left_plan_path use_attach argument is not forwarded in the fixed baseline",
                    "carried_object_collision_wrapper": "vertical lift only; original support contact excluded; no other physical facility intersects the audited vertical column",
                }
                receipt["status"] = "passed_f3_grasp_lift_diagnostic" if all(checks.values()) else "failed_verifier"
        except BaseException as exc:
            receipt["status"] = "failed_execution" if receipt["status"] == "running" else receipt["status"]
            receipt["error"] = {"type": type(exc).__name__, "message": str(exc)}
            receipt["traceback"] = traceback.format_exc()
        finally:
            if scene is not None and hasattr(scene, "trace"):
                trace_path = output_dir / "trace_source.npz"
                trace_info = scene.save_trace(trace_path)
                receipt["trace_source"] = {
                    **trace_info,
                    "sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
                }
            cleanup = handle.cleanup_receipt if handle is not None else getattr(context, "cleanup_receipt", None)
            receipt["cleanup"] = cleanup
            if not isinstance(cleanup, dict) or cleanup.get("cleanup_safety_pass") is not True or cleanup.get("orphan_process_count") != 0:
                receipt["status"] = "failed_cleanup_uncertain"
            receipt["planner_query_count"] = int(getattr(scene, "planner_query_count", 0)) if scene is not None else 0
            receipt["elapsed_seconds"] = time.time() - started
            _write(output_dir / "receipt.json", receipt)
        return receipt
