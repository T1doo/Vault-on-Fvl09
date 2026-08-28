"""Finite nonformal runtime-v2 probes for the reviewed F1--F4 repairs.

This module does not authorize a run.  It requires an explicit CLI approval
flag, may use only an independently fresh-idle physical GPU0--7 selected by the
workspace guard, and always emits
``formal_data=false``/``stage0_data=false`` receipts.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
import traceback

import numpy as np

from envs.utils.action import ArmTag

from ..geometry import (
    actor_target_to_eef_pose,
    footprint_inside_local_region,
    obb_corners,
    quaternion_orientation_error,
    select_first_verified_pose,
    swept_path_collisions,
    transform_local_point,
    world_axis_offset_pose,
    world_z_yaw_pose,
)
from ..runtime_v2_contracts import (
    FAMILY_IMPLEMENTATION_VERSIONS,
    IMPLEMENTATION_VERSION,
    PLASTICBOX_BASE3_CAVITY,
    PROBE_PLANNER_QUERY_LIMITS,
    PROVISIONAL_RUNTIME_THRESHOLDS,
    RUNTIME_V2_PROBE_VARIANTS,
    TRAY_BASE0_SUPPORT_REGION,
)
from ..signals import closed_loop_event_metrics, top_surface_region
from ..verifiers import (
    verify_beside_final_state,
    verify_common_prefix,
    verify_realized_motion_metrics,
    verify_return_equivalence,
    verify_staged_non_target_displacement,
    verify_true_cavity_obb,
)
from .lifecycle import cleanup_status, initialize_cleanup_fields, managed_scene
from .runtime_trace import DenseTraceMixin, PlannerQueryLimitExceeded


class PlannerFailure(RuntimeError):
    pass


class PhysicalPreflightFailure(RuntimeError):
    pass


_SCENE_RESOURCES = None
BLOCK_HALF_EXTENTS = np.asarray([0.022, 0.022, 0.022], dtype=np.float64)


def _scene_resources():
    global _SCENE_RESOURCES
    if _SCENE_RESOURCES is None:
        from .scene_inspection import F1Scene, F2Scene, F3Scene, F4Scene, _args

        _SCENE_RESOURCES = (
            {
                "F1": type("TraceF1RuntimeV2", (DenseTraceMixin, F1Scene), {}),
                "F2": type("TraceF2RuntimeV2", (DenseTraceMixin, F2Scene), {}),
                "F3": type("TraceF3RuntimeV2", (DenseTraceMixin, F3Scene), {}),
                "F4": type("TraceF4RuntimeV2", (DenseTraceMixin, F4Scene), {}),
            },
            _args,
        )
    return _SCENE_RESOURCES


def _entity(actor):
    return actor.actor if hasattr(actor, "actor") else actor


def _actor_name(actor):
    return _entity(actor).get_name()


def _pose(actor):
    value = actor.get_pose()
    return np.asarray(value.p.tolist() + value.q.tolist(), dtype=np.float64)


def _position_map(actors):
    return {name: actor.get_pose().p.copy() for name, actor in actors.items()}


def _settle(scene, frames=60):
    for _ in range(frames):
        scene.scene.step()


def _wait_and_record(scene, frames):
    for _ in range(frames):
        scene.scene.step()
        scene._record()


def _must_move(scene, action, label):
    if not scene.move(action) or not scene.plan_success:
        raise PlannerFailure(f"planner/execution failed at {label}")


def _execute_left_control(scene, control, label):
    if control is None or not isinstance(control, dict) or control.get("status") != "Success":
        raise PlannerFailure(f"left-arm planner query failed at {label}")
    scene.take_dense_action({"left_arm": control, "left_gripper": None, "right_arm": None, "right_gripper": None})


def _move_left_pose(scene, pose, label):
    control = scene.left_move_to_pose(pose=np.asarray(pose, dtype=np.float64).tolist())
    _execute_left_control(scene, control, label)
    return control


def _save_partial_trace(scene, output, receipt):
    if hasattr(scene, "trace"):
        info = scene.save_trace(output / "trace.npz")
        receipt["partial_output_status"] = "trace_complete" if scene.plan_success else "trace_partial_after_failure"
        receipt["trace"] = info


def _outer_half_extents(actor, fallback=None):
    config = getattr(actor, "config", None)
    if config and "extents" in config and "scale" in config:
        return np.asarray(config["extents"], dtype=np.float64) * np.asarray(config["scale"], dtype=np.float64) / 2.0
    if fallback is None:
        raise ValueError(f"no audited half extents for {_actor_name(actor)}")
    return np.asarray(fallback, dtype=np.float64).reshape(3)


def _world_aabb(actor, fallback=None):
    pose = _pose(actor)
    config = getattr(actor, "config", None)
    if config and "center" in config and "scale" in config:
        center = np.asarray(config["center"], dtype=np.float64) * np.asarray(config["scale"], dtype=np.float64)
        pose[:3] = transform_local_point(pose, center)
    corners = obb_corners(pose, _outer_half_extents(actor, fallback))
    return {"lower": corners.min(axis=0).tolist(), "upper": corners.max(axis=0).tolist()}


def _support_contact_series(rows, actor_name, support_names):
    names = tuple(str(name).lower() for name in support_names)
    result = []
    for row in rows:
        found = False
        for pair in row["contact_pairs"]:
            bodies = (str(pair["body_a"]), str(pair["body_b"]))
            if actor_name not in bodies:
                continue
            other = bodies[1] if bodies[0] == actor_name else bodies[0]
            if any(name in other.lower() for name in names):
                found = True
                break
        result.append(found)
    return result


def _stable_speed_series(rows):
    return [float(np.linalg.norm(row["actor_linear_velocity"])) for row in rows]


def _phase(stage_positions, name, actors):
    stage_positions[name] = _position_map(actors)


def _contact_break_count(values):
    seen = False
    previous = False
    breaks = 0
    for raw in values:
        value = bool(raw)
        seen = seen or value
        if seen and previous and not value:
            breaks += 1
        previous = value
    return breaks


def _motion_event(scene, name, axis, center_eef, center_bottle):
    arm = ArmTag("left")
    scene.mark(name + "_start")
    moves, main_axis = (
        (((0, 0, 0.05), (0, 0, -0.10), (0, 0, 0.05)), 2)
        if axis == "V"
        else (((0.05, 0, 0), (-0.10, 0, 0), (0.05, 0, 0)), 0)
    )
    for index, (x, y, z) in enumerate(moves):
        _must_move(scene, scene.move_by_displacement(arm_tag=arm, x=x, y=y, z=z), f"{name}_{index}")
    scene.mark(name + "_end")
    start, end = scene.markers[name + "_start"], scene.markers[name + "_end"]
    rows = scene.trace[start:end + 1]
    eef = np.asarray([row["eef"][:3] for row in rows])
    bottle = np.asarray([row["actor_pose"][:3] for row in rows])
    contacts = [row["selected_gripper_contact"] for row in rows]
    eef_metrics = closed_loop_event_metrics(eef, center_eef, main_axis)
    bottle_metrics = closed_loop_event_metrics(bottle, center_bottle, main_axis)
    q0 = rows[0]["actor_pose"][3:]
    orientation_drift = max(1.0 - abs(float(np.dot(q0, row["actor_pose"][3:]))) for row in rows)
    return {
        "axis": axis,
        **{f"eef_{key}": value for key, value in eef_metrics.items() if key in ("positive_amplitude", "negative_amplitude", "max_off_axis", "return_error")},
        **{f"bottle_{key}": value for key, value in bottle_metrics.items() if key in ("positive_amplitude", "negative_amplitude", "max_off_axis", "return_error")},
        "bottle_orientation_drift": float(orientation_drift),
        "selected_gripper_contact_fraction": float(np.mean(contacts)) if contacts else 0.0,
        "contact_break_count": _contact_break_count(contacts),
        "event_duration": max(0, len(rows) - 1) / 250.0,
    }


def run_f1(output, receipt):
    scenes, scene_args = _scene_resources()
    result = None
    with managed_scene(scenes["F1"], scene_args("F1", output), receipt, "F1-runtime-v2") as scene:
        try:
            all_blocks = {"red": scene.red, "green": scene.green, "blue": scene.blue}
            non_targets = {"green": scene.green, "blue": scene.blue}
            _settle(scene)
            baseline = _position_map(non_targets)
            stages = {"settled_baseline": _position_map(non_targets)}
            scene.initialize_trace(scene.red, "left")
            scene.planner_query_limit = PROBE_PLANNER_QUERY_LIMITS["F1"]
            rest = np.asarray(scene.robot.left_original_pose, dtype=np.float64)
            receipt["attempt_counts"]["execution_attempt_count"] = 1
            arm = ArmTag("left")
            _must_move(scene, scene.grasp_actor(scene.red, arm_tag=arm, pre_grasp_dis=0.09), "grasp_red")
            _phase(stages, "after_grasp", non_targets)
            _must_move(scene, scene.move_by_displacement(arm_tag=arm, z=0.12), "lift_red")
            _phase(stages, "after_lift", non_targets)

            current_eef = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
            current_actor = _pose(scene.red)
            target_actor = current_actor.copy()
            target_actor[:3] = transform_local_point(_pose(scene.box), PLASTICBOX_BASE3_CAVITY["target_center_local_m"])
            release_eef = actor_target_to_eef_pose(current_eef, current_actor, target_actor)
            pre_place_eef = world_axis_offset_pose(release_eef, 0.10)
            safe_eef = current_eef.copy()
            safe_eef[2] = max(1.02, current_eef[2])
            above_eef = pre_place_eef.copy()
            above_eef[2] = safe_eef[2]
            actor_safe = current_actor.copy()
            actor_safe[:3] += safe_eef[:3] - current_eef[:3]
            actor_above = target_actor.copy()
            actor_above[:3] += above_eef[:3] - release_eef[:3]
            swept = swept_path_collisions(
                [current_actor[:3], actor_safe[:3], actor_above[:3], target_actor[:3]],
                BLOCK_HALF_EXTENTS + 0.01,
                {name: _world_aabb(actor, BLOCK_HALF_EXTENTS) for name, actor in non_targets.items()},
            )
            receipt["cpu_precheck"] = {
                "implementation_version": FAMILY_IMPLEMENTATION_VERSIONS["F1"],
                "cavity": PLASTICBOX_BASE3_CAVITY,
                "target_actor_pose": target_actor.tolist(),
                "release_eef_pose": release_eef.tolist(),
                "pre_place_eef_pose": pre_place_eef.tolist(),
                "safe_waypoint_eef_pose": safe_eef.tolist(),
                "swept_path": swept,
                "all_scene_blocks": sorted(all_blocks),
            }
            if not swept["pass"]:
                raise PhysicalPreflightFailure(str(swept["collisions"]))
            scene.mark("safe_transport_start")
            _move_left_pose(scene, safe_eef, "safe_vertical_waypoint")
            _move_left_pose(scene, above_eef, "safe_horizontal_waypoint")
            _phase(stages, "after_transport", non_targets)
            _move_left_pose(scene, pre_place_eef, "pre_place")
            _move_left_pose(scene, release_eef, "release_pose")
            _must_move(scene, scene.open_gripper(arm, pos=1.0), "release")
            _wait_and_record(scene, 75)
            _phase(stages, "after_release", non_targets)
            _move_left_pose(scene, pre_place_eef, "vertical_retreat")
            _phase(stages, "after_retreat", non_targets)
            _move_left_pose(scene, rest, "actual_rest")
            _phase(stages, "after_rest", non_targets)
            _wait_and_record(scene, 75)
            _phase(stages, "after_final_stability_window", non_targets)
            inside = verify_true_cavity_obb(_pose(scene.red), BLOCK_HALF_EXTENTS, _pose(scene.box), PLASTICBOX_BASE3_CAVITY)
            non_target = verify_staged_non_target_displacement(baseline, stages, PROVISIONAL_RUNTIME_THRESHOLDS["non_target_displacement_m"])
            final_rows = scene.trace[-PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"]:]
            stable = _stable_speed_series(final_rows)
            support = _support_contact_series(final_rows, _actor_name(scene.red), (_actor_name(scene.box),))
            rest_error = float(np.linalg.norm(np.asarray(scene.robot.get_left_ee_pose()[:3]) - rest[:3]))
            rest_orientation_error = quaternion_orientation_error(scene.robot.get_left_ee_pose()[3:], rest[3:])
            eef_linear_speed = float(np.linalg.norm(scene.trace[-1]["eef_linear_velocity"]))
            eef_angular_speed = float(np.linalg.norm(scene.trace[-1]["eef_angular_velocity"]))
            checks = {
                "true_inside": inside["pass_true_cavity_obb"],
                "non_target_stability": non_target["pass"],
                "stable_window": len(stable) == PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"] and max(stable) <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
                "support_contact_window": bool(support) and all(support),
                "gripper_open": bool(scene.is_left_gripper_open()),
                "rest_position": rest_error <= PROVISIONAL_RUNTIME_THRESHOLDS["rest_position_error_m"],
                "rest_orientation": rest_orientation_error <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
                "eef_linear_stationary": eef_linear_speed <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_linear_speed_mps"],
                "eef_angular_stationary": eef_angular_speed <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"],
            }
            result = {
                "implementation_version": FAMILY_IMPLEMENTATION_VERSIONS["F1"],
                "variant": "transport_true_inside",
                "plan_success": bool(scene.plan_success),
                "true_inside_verifier": inside,
                "non_target_verifier": non_target,
                "stable_speed_window_mps": stable,
                "support_contact_window": support,
                "rest_return_error_m": rest_error,
                "rest_return_orientation_error": rest_orientation_error,
                "final_eef_linear_speed_mps": eef_linear_speed,
                "final_eef_angular_speed_rps": eef_angular_speed,
                "left_gripper_open": bool(scene.is_left_gripper_open()),
                "semantic_verifier": {"pass": all(checks.values()), "checks": checks},
                "markers": scene.markers,
                "planner_query_count": scene.planner_query_count,
            }
        finally:
            receipt["attempt_counts"]["planner_query_count"] = getattr(scene, "planner_query_count", 0)
            _save_partial_trace(scene, output, receipt)
    return result


def run_f2(output, receipt):
    scenes, scene_args = _scene_resources()
    result = None
    with managed_scene(scenes["F2"], scene_args("F2", output), receipt, "F2-runtime-v2") as scene:
        try:
            _settle(scene)
            scene.initialize_trace(scene.can, "left")
            scene.planner_query_limit = PROBE_PLANNER_QUERY_LIMITS["F2"]
            rest = np.asarray(scene.robot.left_original_pose, dtype=np.float64)
            receipt["attempt_counts"]["execution_attempt_count"] = 1
            arm = ArmTag("left")
            _must_move(scene, scene.grasp_actor(scene.can, arm_tag=arm, pre_grasp_dis=0.08), "grasp_can")
            _must_move(scene, scene.move_by_displacement(arm_tag=arm, z=0.12), "lift_can")
            current_eef = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
            current_actor = _pose(scene.can)
            safe_eef = current_eef.copy()
            safe_eef[2] = max(1.02, current_eef[2])
            _move_left_pose(scene, safe_eef, "safe_vertical_waypoint")
            actor_safe = current_actor.copy()
            actor_safe[:3] += safe_eef[:3] - current_eef[:3]
            stand = scene.stand.get_pose().p
            target_xyz = np.asarray([stand[0], stand[1] + 0.15, 0.79], dtype=np.float64)
            obstacles = {name: _world_aabb(actor) for name, actor in {"box": scene.box, "scale": scene.scale, "stand": scene.stand}.items()}
            can_half = _outer_half_extents(scene.can)
            candidates = []
            controls = {}
            for index, yaw in enumerate((0.0, np.pi / 2.0, -np.pi / 2.0)):
                target_actor = current_actor.copy()
                target_actor[:3] = target_xyz
                target_actor = world_z_yaw_pose(target_actor, yaw)
                release_eef = actor_target_to_eef_pose(np.asarray(scene.robot.get_left_ee_pose()), _pose(scene.can), target_actor)
                pre_eef = world_axis_offset_pose(release_eef, 0.10)
                actor_above = target_actor.copy()
                actor_above[:3] += pre_eef[:3] - release_eef[:3]
                swept = swept_path_collisions([actor_safe[:3], actor_above[:3], target_actor[:3]], can_half + 0.01, obstacles)
                workspace_pass = bool(-0.45 <= pre_eef[0] <= 0.45 and -0.35 <= pre_eef[1] <= 0.20 and 0.75 <= pre_eef[2] <= 1.20)
                item = {
                    "candidate_id": f"upright_yaw_{index}",
                    "yaw_radians": float(yaw),
                    "target_actor_pose": target_actor.tolist(),
                    "pre_place_eef_pose": pre_eef.tolist(),
                    "release_eef_pose": release_eef.tolist(),
                    "workspace_pass": workspace_pass,
                    "swept_collision_free": swept["pass"],
                    "swept_path": swept,
                    "planner_status": "not_queried_geometry_failure",
                }
                if workspace_pass and swept["pass"]:
                    control = scene.preflight_left_pose(pre_eef)
                    item["planner_status"] = control.get("status") if isinstance(control, dict) else "Failed"
                    controls[item["candidate_id"]] = control
                candidates.append(item)
            decision = select_first_verified_pose(candidates)
            receipt["cpu_precheck"] = {
                "implementation_version": FAMILY_IMPLEMENTATION_VERSIONS["F2"],
                "main_object": "071_can/base1",
                "arm": "left",
                "reference": "074_displaystand/base3",
                "target_xyz": target_xyz.tolist(),
                "candidate_decision": decision,
                "reachability_source": "real GPU planner preflight; no hard-coded reach boolean",
            }
            if not decision["pass"]:
                raise PhysicalPreflightFailure("no beside actor-to-EEF candidate passed geometry and planner preflight")
            selected = decision["selected"]
            _execute_left_control(scene, controls[selected["candidate_id"]], "selected_pre_place")
            _move_left_pose(scene, selected["release_eef_pose"], "release_pose")
            _must_move(scene, scene.open_gripper(arm, pos=1.0), "release")
            _wait_and_record(scene, 100)
            _move_left_pose(scene, selected["pre_place_eef_pose"], "vertical_retreat")
            _move_left_pose(scene, rest, "actual_rest")
            _wait_and_record(scene, 75)
            stable_rows = scene.trace[-PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"]:]
            can_pose = _pose(scene.can)
            inside = verify_true_cavity_obb(can_pose, can_half, _pose(scene.box), PLASTICBOX_BASE3_CAVITY)["pass_true_cavity_obb"]
            scale_target = np.asarray(scene.scale.get_functional_point(0), dtype=np.float64)
            on = top_surface_region(can_pose[:3], scale_target[:3], [0.07, 0.07], 0.06)
            radial = float(np.linalg.norm(can_pose[:2] - scene.stand.get_pose().p[:2]))
            beside = bool(0.12 <= radial <= 0.23 and can_pose[2] <= 0.83)
            speeds = _stable_speed_series(stable_rows)
            support = _support_contact_series(stable_rows, _actor_name(scene.can), ("table",))
            rest_error = float(np.linalg.norm(np.asarray(scene.robot.get_left_ee_pose()[:3]) - rest[:3]))
            rest_orientation_error = quaternion_orientation_error(scene.robot.get_left_ee_pose()[3:], rest[3:])
            eef_linear_speed = float(np.linalg.norm(scene.trace[-1]["eef_linear_velocity"]))
            eef_angular_speed = float(np.linalg.norm(scene.trace[-1]["eef_angular_velocity"]))
            semantic = verify_beside_final_state(
                inside=inside,
                on=on,
                beside=beside,
                support_contact=bool(support) and all(support),
                stable_speed_window=bool(speeds) and max(speeds) <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
                gripper_open=scene.is_left_gripper_open(),
                rest_position_error=rest_error,
                rest_orientation_error=rest_orientation_error,
                eef_linear_speed=eef_linear_speed,
                eef_angular_speed=eef_angular_speed,
                thresholds=PROVISIONAL_RUNTIME_THRESHOLDS,
            )
            result = {
                "implementation_version": FAMILY_IMPLEMENTATION_VERSIONS["F2"],
                "variant": "actor_to_eef_stand",
                "modelname": "071_can",
                "model_id": 1,
                "arm": "left",
                "reference": "074_displaystand/base3",
                "selected_candidate": selected,
                "exclusive_predicate_inputs": {"inside": inside, "on": on, "beside": beside},
                "reference_radial_distance_m": radial,
                "stable_speed_window_mps": speeds,
                "support_contact_window": support,
                "rest_return_error_m": rest_error,
                "rest_return_orientation_error": rest_orientation_error,
                "final_eef_linear_speed_mps": eef_linear_speed,
                "final_eef_angular_speed_rps": eef_angular_speed,
                "left_gripper_open": bool(scene.is_left_gripper_open()),
                "semantic_verifier": semantic,
                "plan_success": bool(scene.plan_success),
                "markers": scene.markers,
                "planner_query_count": scene.planner_query_count,
            }
        finally:
            receipt["attempt_counts"]["planner_query_count"] = getattr(scene, "planner_query_count", 0)
            _save_partial_trace(scene, output, receipt)
    return result


def run_f3(output, receipt):
    scenes, scene_args = _scene_resources()
    result = None
    with managed_scene(scenes["F3"], scene_args("F3", output), receipt, "F3-runtime-v2") as scene:
        try:
            _settle(scene)
            start_actor = _pose(scene.bottle)
            rest = np.asarray(scene.robot.left_original_pose, dtype=np.float64)
            scene.initialize_trace(scene.bottle, "left")
            scene.planner_query_limit = PROBE_PLANNER_QUERY_LIMITS["F3"]
            receipt["attempt_counts"]["execution_attempt_count"] = 1
            arm = ArmTag("left")
            _must_move(scene, scene.grasp_actor(scene.bottle, arm_tag=arm, pre_grasp_dis=0.09), "grasp_bottle")
            _must_move(scene, scene.move_by_displacement(arm_tag=arm, z=0.12), "lift_bottle")
            current = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
            neutral = np.concatenate(([-0.08, -0.05, 0.95], current[3:]))
            _move_left_pose(scene, neutral, "central_pose")
            center_eef = np.asarray(scene.robot.get_left_ee_pose()[:3])
            center_bottle = scene.bottle.get_pose().p.copy()
            metrics = {
                "repair_V": _motion_event(scene, "repair_V", "V", center_eef, center_bottle),
                "repair_H": _motion_event(scene, "repair_H", "H", center_eef, center_bottle),
            }
            held_eef = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
            held_actor = _pose(scene.bottle)
            release_eef = actor_target_to_eef_pose(held_eef, held_actor, start_actor)
            pre_place_eef = world_axis_offset_pose(release_eef, 0.10)
            receipt["cpu_precheck"] = {
                "implementation_version": FAMILY_IMPLEMENTATION_VERSIONS["F3"],
                "target_semantics": "exact original bottle actor pose; no functional-point substitution",
                "target_actor_pose": start_actor.tolist(),
                "frozen_eef_to_actor_from": {"eef": held_eef.tolist(), "actor": held_actor.tolist()},
                "pre_place_eef_pose": pre_place_eef.tolist(),
                "release_eef_pose": release_eef.tolist(),
                "retreat_axis": "world_z",
                "rest_target": rest.tolist(),
            }
            _move_left_pose(scene, pre_place_eef, "return_pre_place")
            _move_left_pose(scene, release_eef, "return_release_pose")
            _must_move(scene, scene.open_gripper(arm, pos=1.0), "release")
            _wait_and_record(scene, 125)
            _move_left_pose(scene, pre_place_eef, "vertical_retreat")
            _move_left_pose(scene, rest, "actual_rest")
            _wait_and_record(scene, 75)
            stable_rows = scene.trace[-PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"]:]
            final_actor = _pose(scene.bottle)
            position_error = float(np.linalg.norm(final_actor[:3] - start_actor[:3]))
            orientation_error = float(1.0 - abs(np.dot(final_actor[3:], start_actor[3:])))
            rest_error = float(np.linalg.norm(np.asarray(scene.robot.get_left_ee_pose()[:3]) - rest[:3]))
            rest_orientation_error = quaternion_orientation_error(scene.robot.get_left_ee_pose()[3:], rest[3:])
            speeds = _stable_speed_series(stable_rows)
            support = _support_contact_series(stable_rows, _actor_name(scene.bottle), (_actor_name(scene.pad),))
            eef_linear_speed = float(np.linalg.norm(scene.trace[-1]["eef_linear_velocity"]))
            eef_angular_speed = float(np.linalg.norm(scene.trace[-1]["eef_angular_velocity"]))
            return_semantic = verify_return_equivalence(
                position_error=position_error,
                orientation_error=orientation_error,
                rest_position_error=rest_error,
                rest_orientation_error=rest_orientation_error,
                stable_speed_samples=speeds,
                support_contact_samples=support,
                gripper_open=scene.is_left_gripper_open(),
                thresholds=PROVISIONAL_RUNTIME_THRESHOLDS,
                eef_linear_speed=eef_linear_speed,
                eef_angular_speed=eef_angular_speed,
            )
            motion_semantic = verify_realized_motion_metrics(metrics, PROVISIONAL_RUNTIME_THRESHOLDS)
            semantic = {
                "pass": return_semantic["pass"] and motion_semantic["pass"],
                "return_equivalence": return_semantic,
                "realized_motion": motion_semantic,
            }
            result = {
                "implementation_version": FAMILY_IMPLEMENTATION_VERSIONS["F3"],
                "variant": "return_equivalence",
                "plan_success": bool(scene.plan_success),
                "metrics": metrics,
                "bottle_return_position_error_m": position_error,
                "bottle_return_orientation_error": orientation_error,
                "rest_return_error_m": rest_error,
                "rest_return_orientation_error": rest_orientation_error,
                "stable_speed_window_mps": speeds,
                "support_contact_window": support,
                "final_eef_linear_speed_mps": eef_linear_speed,
                "final_eef_angular_speed_rps": eef_angular_speed,
                "left_gripper_open": bool(scene.is_left_gripper_open()),
                "semantic_verifier": semantic,
                "markers": scene.markers,
                "planner_query_count": scene.planner_query_count,
            }
        finally:
            receipt["attempt_counts"]["planner_query_count"] = getattr(scene, "planner_query_count", 0)
            _save_partial_trace(scene, output, receipt)
    return result


def run_f4(output, receipt):
    scenes, scene_args = _scene_resources()
    result = None
    with managed_scene(scenes["F4"], scene_args("F4", output), receipt, "F4-runtime-v2") as scene:
        try:
            _settle(scene)
            non_targets = {"A": scene.a, "B": scene.b, "C": scene.c}
            baseline = _position_map(non_targets)
            initial_non_target_poses = {name: _pose(actor).tolist() for name, actor in non_targets.items()}
            stages = {"settled_baseline": _position_map(non_targets)}
            scene.initialize_trace(scene.common_x, "left")
            scene.planner_query_limit = PROBE_PLANNER_QUERY_LIMITS["F4"]
            receipt["attempt_counts"]["execution_attempt_count"] = 1
            current = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
            neutral = np.concatenate(([-0.15, -0.04, 0.95], current[3:]))
            _move_left_pose(scene, neutral, "initial_neutral")
            neutral_realized = np.asarray(scene.robot.get_left_ee_pose()[:3])
            neutral_start_eef = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
            neutral_start_velocity = np.concatenate((scene.trace[-1]["eef_linear_velocity"], scene.trace[-1]["eef_angular_velocity"]))
            neutral_start_gripper = float(scene.robot.get_normal_real_gripper_val()[0])
            common_initial_pose = _pose(scene.common_x).tolist()
            arm = ArmTag("left")
            _must_move(scene, scene.grasp_actor(scene.common_x, arm_tag=arm, pre_grasp_dis=0.09), "grasp_common_X")
            _phase(stages, "after_grasp", non_targets)
            _must_move(scene, scene.move_by_displacement(arm_tag=arm, z=0.10), "lift_common_X")
            _phase(stages, "after_lift", non_targets)
            held_eef = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
            held_actor = _pose(scene.common_x)
            target_actor = held_actor.copy()
            target_actor[:3] = transform_local_point(_pose(scene.tray), TRAY_BASE0_SUPPORT_REGION["target_center_local_m"])
            release_eef = actor_target_to_eef_pose(held_eef, held_actor, target_actor)
            pre_place_eef = world_axis_offset_pose(release_eef, 0.10)
            safe_eef = held_eef.copy()
            safe_eef[2] = max(1.03, held_eef[2])
            above_eef = pre_place_eef.copy()
            above_eef[2] = safe_eef[2]
            actor_safe = held_actor.copy()
            actor_safe[:3] += safe_eef[:3] - held_eef[:3]
            actor_above = target_actor.copy()
            actor_above[:3] += above_eef[:3] - release_eef[:3]
            swept = swept_path_collisions(
                [held_actor[:3], actor_safe[:3], actor_above[:3], target_actor[:3]],
                BLOCK_HALF_EXTENTS + 0.01,
                {name: _world_aabb(actor, BLOCK_HALF_EXTENTS) for name, actor in non_targets.items()},
            )
            receipt["cpu_precheck"] = {
                "implementation_version": FAMILY_IMPLEMENTATION_VERSIONS["F4"],
                "scope": "common-X only; ordered Gate stops before A/B/C programs",
                "tray_support_region": TRAY_BASE0_SUPPORT_REGION,
                "target_actor_pose": target_actor.tolist(),
                "release_eef_pose": release_eef.tolist(),
                "pre_place_eef_pose": pre_place_eef.tolist(),
                "safe_waypoint_eef_pose": safe_eef.tolist(),
                "swept_path": swept,
            }
            if not swept["pass"]:
                raise PhysicalPreflightFailure(str(swept["collisions"]))
            _move_left_pose(scene, safe_eef, "safe_vertical_waypoint")
            _move_left_pose(scene, above_eef, "safe_horizontal_waypoint")
            _phase(stages, "after_transport", non_targets)
            _move_left_pose(scene, pre_place_eef, "pre_place")
            _move_left_pose(scene, release_eef, "release_pose")
            _must_move(scene, scene.open_gripper(arm, pos=1.0), "release")
            _wait_and_record(scene, 125)
            _phase(stages, "after_release", non_targets)
            _move_left_pose(scene, pre_place_eef, "vertical_retreat")
            _phase(stages, "after_retreat", non_targets)
            _move_left_pose(scene, neutral, "branch_neutral")
            _phase(stages, "after_neutral", non_targets)
            _wait_and_record(scene, 75)
            _phase(stages, "after_final_stability_window", non_targets)
            stable_rows = scene.trace[-PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"]:]
            footprint = footprint_inside_local_region(
                _pose(scene.common_x),
                BLOCK_HALF_EXTENTS,
                _pose(scene.tray),
                TRAY_BASE0_SUPPORT_REGION["lower_m"],
                TRAY_BASE0_SUPPORT_REGION["upper_m"],
                TRAY_BASE0_SUPPORT_REGION["horizontal_axes"],
            )
            non_target = verify_staged_non_target_displacement(baseline, stages, PROVISIONAL_RUNTIME_THRESHOLDS["non_target_displacement_m"])
            speeds = _stable_speed_series(stable_rows)
            support = _support_contact_series(stable_rows, _actor_name(scene.common_x), (_actor_name(scene.tray),))
            neutral_error = float(np.linalg.norm(np.asarray(scene.robot.get_left_ee_pose()[:3]) - neutral_realized))
            neutral_orientation_error = quaternion_orientation_error(scene.robot.get_left_ee_pose()[3:], neutral[3:])
            eef_linear_speed = float(np.linalg.norm(scene.trace[-1]["eef_linear_velocity"]))
            eef_angular_speed = float(np.linalg.norm(scene.trace[-1]["eef_angular_velocity"]))
            semantic = verify_common_prefix(
                footprint_result=footprint,
                support_contact_samples=support,
                stable_speed_samples=speeds,
                neutral_return_error=neutral_error,
                neutral_orientation_error=neutral_orientation_error,
                non_target_result=non_target,
                gripper_open=scene.is_left_gripper_open(),
                thresholds=PROVISIONAL_RUNTIME_THRESHOLDS,
                eef_linear_speed=eef_linear_speed,
                eef_angular_speed=eef_angular_speed,
            )
            result = {
                "implementation_version": FAMILY_IMPLEMENTATION_VERSIONS["F4"],
                "variant": "common_prefix_mapping",
                "plan_success": bool(scene.plan_success),
                "common_X": {
                    "start_eef_pose": neutral_start_eef.tolist(),
                    "end_eef_pose": np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64).tolist(),
                    "start_eef_velocity": neutral_start_velocity.tolist(),
                    "end_eef_velocity": np.concatenate((scene.trace[-1]["eef_linear_velocity"], scene.trace[-1]["eef_angular_velocity"])).tolist(),
                    "start_gripper_state": neutral_start_gripper,
                    "end_gripper_state": float(scene.robot.get_normal_real_gripper_val()[0]),
                    "object_initial_pose": common_initial_pose,
                    "object_final_pose": _pose(scene.common_x).tolist(),
                    "tray_footprint": footprint,
                    "support_contact_window": support,
                    "stable_speed_window_mps": speeds,
                    "neutral_return_error_m": neutral_error,
                    "neutral_return_orientation_error": neutral_orientation_error,
                    "gripper_open": bool(scene.is_left_gripper_open()),
                    "final_eef_linear_speed_mps": eef_linear_speed,
                    "final_eef_angular_speed_rps": eef_angular_speed,
                },
                "non_target_verifier": non_target,
                "non_target_initial_poses": initial_non_target_poses,
                "non_target_final_poses": {name: _pose(actor).tolist() for name, actor in non_targets.items()},
                "semantic_verifier": semantic,
                "ordered_gate_next_steps_run": [],
                "markers": scene.markers,
                "planner_query_count": scene.planner_query_count,
            }
        finally:
            receipt["attempt_counts"]["planner_query_count"] = getattr(scene, "planner_query_count", 0)
            _save_partial_trace(scene, output, receipt)
    return result


RUNNERS = {"F1": run_f1, "F2": run_f2, "F3": run_f3, "F4": run_f4}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=tuple(RUNNERS), required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--physical-index", type=int, choices=tuple(range(8)), required=True)
    parser.add_argument("--expected-uuid", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--approved-runtime-v2-probe", action="store_true")
    args = parser.parse_args()
    if not args.approved_runtime_v2_probe:
        parser.error("runtime-v2 GPU probe requires a new explicit user authorization")
    if args.variant not in RUNTIME_V2_PROBE_VARIANTS[args.family]:
        parser.error(f"variant for {args.family} must be one of {RUNTIME_V2_PROBE_VARIANTS[args.family]}")
    started = time.time()
    receipt = {
        "schema_version": "cmf_action_feasibility_runtime_v2",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "family_implementation_version": FAMILY_IMPLEMENTATION_VERSIONS[args.family],
        "purpose": "nonformal_feasibility",
        "formal_data": False,
        "stage0_data": False,
        "attempt_limit": 1,
        "timeout_seconds": {"F1": 1200, "F2": 1200, "F3": 1800, "F4": 1800}[args.family],
        "family": args.family,
        "variant": args.variant,
        "physical_gpu_index": args.physical_index,
        "expected_gpu_uuid": args.expected_uuid,
        "pid": os.getpid(),
        "status": "running",
        "attempt_counts": {"feasibility_query_count": 1, "planner_query_count": 0, "execution_attempt_count": 0, "recovery_attempt_count": 0},
        "planner_query_limit": PROBE_PLANNER_QUERY_LIMITS[args.family],
    }
    initialize_cleanup_fields(receipt)
    code = 1
    try:
        if os.environ.get("CUDA_VISIBLE_DEVICES") != args.expected_uuid:
            raise RuntimeError("CUDA_VISIBLE_DEVICES does not match expected UUID")
        args.output.mkdir(parents=True, exist_ok=False)
        result = RUNNERS[args.family](args.output, receipt)
        if result is None:
            raise RuntimeError("probe returned no result")
        receipt["result"] = result
        passed = result.get("plan_success") is True and result.get("semantic_verifier", {}).get("pass") is True
        receipt["semantic_probe_pass"] = passed
        receipt["status"] = "passed_nonformal_action_probe" if passed else "failed_nonformal_action_probe"
        code = 0 if passed else 1
    except (PhysicalPreflightFailure, PlannerQueryLimitExceeded) as exc:
        receipt.update({"status": "aborted_with_reason", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
    except PlannerFailure as exc:
        receipt.update({"status": "failed_planner", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
    except BaseException as exc:
        receipt.update({"status": "failed_execution", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
    finally:
        receipt["status"] = cleanup_status(receipt, receipt["status"])
        receipt["elapsed_seconds"] = time.time() - started
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
