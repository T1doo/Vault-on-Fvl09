"""Versioned, finite, nonformal F1--F4 repair and program probes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
import traceback

import numpy as np
import transforms3d as t3d

from envs.utils.action import ArmTag
from .lifecycle import cleanup_status, initialize_cleanup_fields, managed_scene
from .runtime_trace import DenseTraceMixin
from ..signals import closed_loop_event_metrics, first_stable_true_frame
from ..probe_contracts import HISTORICAL_FAMILY_VARIANTS as VARIANTS, result_passed


class PlannerFailure(RuntimeError):
    pass


_SCENE_RESOURCES = None


def _scene_resources():
    """Delay CuRobo/SAPIEN task imports until an actual GPU probe starts."""
    global _SCENE_RESOURCES
    if _SCENE_RESOURCES is None:
        from .scene_inspection import F1Scene, F2Scene, F2PotScene, F3Scene, F4Scene, _args

        _SCENE_RESOURCES = ({
            "F1": type("TraceF1", (DenseTraceMixin, F1Scene), {}),
            "F2": type("TraceF2", (DenseTraceMixin, F2Scene), {}),
            "F2_POT": type("TraceF2Pot", (DenseTraceMixin, F2PotScene), {}),
            "F3": type("TraceF3", (DenseTraceMixin, F3Scene), {}),
            "F4": type("TraceF4", (DenseTraceMixin, F4Scene), {}),
        }, _args)
    return _SCENE_RESOURCES


def _must_move(scene, action, label):
    if not scene.move(action) or not scene.plan_success:
        raise PlannerFailure(f"planner/execution failed at {label}")


def _pose(actor):
    value = actor.get_pose()
    return np.asarray(value.p.tolist() + value.q.tolist(), dtype=np.float64)


def _position_map(actors):
    return {name: actor.get_pose().p.copy() for name, actor in actors.items()}


def _displacements(initial, actors):
    return {name: float(np.linalg.norm(actor.get_pose().p - initial[name])) for name, actor in actors.items()}


def _save_partial_trace(scene, output, receipt):
    if hasattr(scene, "trace"):
        info = scene.save_trace(output / "trace.npz")
        receipt["partial_output_status"] = "trace_complete" if scene.plan_success else "trace_partial_after_failure"
        receipt["trace"] = info


def _box_precheck(scene, variant):
    config = scene.box.config
    scale = np.asarray(config["scale"], dtype=np.float64)
    extents = np.asarray(config["extents"], dtype=np.float64) * scale
    center = np.asarray(config["center"], dtype=np.float64) * scale
    points = [scene.box.get_functional_point(index) for index in range(len(config.get("functional_matrix", [])))]
    target = points[1] if variant == "fp1" else np.mean(np.asarray(points), axis=0).tolist()
    if variant == "interior":
        target = list(target)
        target[2] = max(float(target[2]), 0.764)
        target[3:] = [1.0, 0.0, 0.0, 0.0]
    return {
        "repair_version": "f1_block_inside_box_repair_v1",
        "variant": variant,
        "box_model_id": 3,
        "box_local_functional_points": points,
        "box_outer_extents_m": extents.tolist(),
        "box_local_center_m": center.tolist(),
        "block_half_size_m": [0.022, 0.022, 0.022],
        "block_current_grasp_orientation": scene.red.get_pose().q.tolist(),
        "computed_pre_place_pose": target,
        "computed_final_place_pose": target,
        "collision_clearance_m": 0.01,
    }, target


def _block_inside_outer_obb(scene, actor, margin=0.004):
    box_pose = scene.box.get_pose().to_transformation_matrix()
    actor_pose = actor.get_pose().to_transformation_matrix()
    half = 0.022
    corners = np.asarray([[x, y, z, 1.0] for x in (-half, half) for y in (-half, half) for z in (-half, half)])
    local = (np.linalg.inv(box_pose) @ (actor_pose @ corners.T)).T[:, :3]
    config = scene.box.config
    scale = np.asarray(config["scale"], dtype=np.float64)
    center = np.asarray(config["center"], dtype=np.float64) * scale
    half_extents = np.asarray(config["extents"], dtype=np.float64) * scale / 2.0 - margin
    passed = bool(np.all(local >= center - half_extents) and np.all(local <= center + half_extents))
    return {"pass_provisional_outer_obb": passed, "local_corner_min": local.min(axis=0).tolist(), "local_corner_max": local.max(axis=0).tolist(), "outer_lower": (center - half_extents).tolist(), "outer_upper": (center + half_extents).tolist()}


def run_f1(output, variant, receipt):
    if variant not in ("fp1", "interior"):
        raise ValueError("F1 variant must be fp1 or interior")
    result = None
    scenes, scene_args = _scene_resources()
    with managed_scene(scenes["F1"], scene_args("F1", output), receipt, f"F1-{variant}") as scene:
        try:
            actors = {"red": scene.red, "green": scene.green, "blue": scene.blue}
            initial = _position_map(actors)
            scene.initialize_trace(scene.red, "left")
            receipt["cpu_precheck"], target = _box_precheck(scene, variant)
            arm = ArmTag("left")
            receipt["attempt_counts"]["execution_attempt_count"] = 1
            _must_move(scene, scene.grasp_actor(scene.red, arm_tag=arm, pre_grasp_dis=0.09), "grasp_red")
            _must_move(scene, scene.move_by_displacement(arm_tag=arm, z=0.10), "lift_red")
            before = scene.planner_query_count
            scene.mark("place_start")
            _must_move(scene, scene.place_actor(scene.red, arm_tag=arm, target_pose=target, constrain="free", pre_dis=0.10, dis=0.02), f"place_{variant}")
            receipt["repair_planner_query_count"] = scene.planner_query_count - before
            _must_move(scene, scene.move_by_displacement(arm_tag=arm, z=0.08), "withdraw")
            _must_move(scene, scene.back_to_origin(arm_tag=arm), "rest")
            result = {
                "repair_version": "f1_block_inside_box_repair_v1", "variant": variant,
                "plan_success": bool(scene.plan_success), "inside_verifier": _block_inside_outer_obb(scene, scene.red),
                "non_target_displacement_m": _displacements(initial, {"green": scene.green, "blue": scene.blue}),
                "left_gripper_open": bool(scene.is_left_gripper_open()), "trace_steps": len(scene.trace),
                "markers": scene.markers, "planner_query_count": scene.planner_query_count,
            }
        finally:
            receipt["attempt_counts"]["planner_query_count"] = getattr(scene, "planner_query_count", 0)
            _save_partial_trace(scene, output, receipt)
    return result


def _f2_sector_precheck(scene):
    stand = scene.stand.get_pose().p
    candidates = {
        "sector1": np.asarray([stand[0], stand[1] + 0.15, 0.79]),
        "sector2": np.asarray([stand[0] + 0.11, stand[1] + 0.11, 0.79]),
    }
    facilities = {"box": scene.box.get_pose().p, "scale": scene.scale.get_pose().p, "stand": stand}
    details = {}
    for name, point in candidates.items():
        details[name] = {
            "target_xyz": point.tolist(), "stand_radial_distance_m": float(np.linalg.norm(point[:2] - stand[:2])),
            "facility_xy_clearance_m": {key: float(np.linalg.norm(point[:2] - pose[:2])) for key, pose in facilities.items()},
            "inside_region": False, "on_region": False,
            "table_bounds_provisional_pass": bool(-0.35 <= point[0] <= 0.35 and -0.35 <= point[1] <= 0.10),
            "left_arm_reach_provisional": True,
        }
    return details, candidates


def run_f2(output, variant, receipt):
    if variant not in ("sector1", "sector2", "pot_left"):
        raise ValueError("F2 variant must be sector1, sector2, or pot_left")
    result = None
    scenes, scene_args = _scene_resources()
    scene_key = "F2_POT" if variant == "pot_left" else "F2"
    with managed_scene(scenes[scene_key], scene_args("F2", output), receipt, f"F2-{variant}") as scene:
        try:
            scene.initialize_trace(scene.can, "left")
            if variant == "pot_left":
                reference = scene.pot.get_pose().p
                target_xyz = np.asarray([reference[0] - 0.18, reference[1], 0.79])
                clearances = {
                    "box": float(np.linalg.norm(target_xyz[:2] - scene.box.get_pose().p[:2])),
                    "scale": float(np.linalg.norm(target_xyz[:2] - scene.scale.get_pose().p[:2])),
                    "pot": float(np.linalg.norm(target_xyz[:2] - reference[:2])),
                }
                receipt["cpu_precheck"] = {
                    "repair_version": "f2_beside_reference_pot_audit_v2",
                    "selected_reference": "060_kitchenpot/base0",
                    "selected_model_directory": "100015",
                    "main_object": "071_can/base1",
                    "arm": "left",
                    "pot_fixed_root_project_wrapper": True,
                    "target_xyz": target_xyz.tolist(),
                    "facility_xy_clearance_m": clearances,
                }
            else:
                sectors, candidates = _f2_sector_precheck(scene)
                receipt["cpu_precheck"] = {"repair_version": "f2_beside_clearance_repair_v1", "candidate_sectors": sectors, "selected_sector": variant}
                target_xyz = candidates[variant]
            target = target_xyz.tolist() + scene.can.get_pose().q.tolist()
            arm = ArmTag("left")
            receipt["attempt_counts"]["execution_attempt_count"] = 1
            _must_move(scene, scene.grasp_actor(scene.can, arm_tag=arm, pre_grasp_dis=0.08), "grasp_can")
            _must_move(scene, scene.move_by_displacement(arm_tag=arm, z=0.10), "lift_can")
            before = scene.planner_query_count
            scene.mark("beside_place_start")
            _must_move(scene, scene.place_actor(scene.can, arm_tag=arm, target_pose=target, constrain="free", pre_dis=0.08, dis=0.01), f"beside_{variant}")
            receipt["repair_planner_query_count"] = scene.planner_query_count - before
            _must_move(scene, scene.move_by_displacement(arm_tag=arm, z=0.08), "withdraw")
            _must_move(scene, scene.back_to_origin(arm_tag=arm), "rest")
            can = scene.can.get_pose().p
            reference = scene.pot.get_pose().p if variant == "pot_left" else scene.stand.get_pose().p
            radial = float(np.linalg.norm(can[:2] - reference[:2]))
            result = {
                "repair_version": "f2_beside_reference_pot_audit_v2" if variant == "pot_left" else "f2_beside_clearance_repair_v1", "variant": variant,
                "modelname": "071_can", "model_id": 1, "arm": "left", "plan_success": bool(scene.plan_success),
                "reference": "060_kitchenpot/base0" if variant == "pot_left" else "074_displaystand/base3",
                "beside_annulus_provisional": bool(0.12 <= radial <= 0.23 and can[2] <= 0.83),
                "reference_radial_distance_m": radial, "left_gripper_open": bool(scene.is_left_gripper_open()),
                "trace_steps": len(scene.trace), "markers": scene.markers, "planner_query_count": scene.planner_query_count,
            }
        finally:
            receipt["attempt_counts"]["planner_query_count"] = getattr(scene, "planner_query_count", 0)
            _save_partial_trace(scene, output, receipt)
    return result


def _contact_break_count(values):
    seen = False
    breaks = 0
    previous = False
    for value in values:
        value = bool(value)
        if value:
            seen = True
        if seen and previous and not value:
            breaks += 1
        previous = value
    return breaks


def _f3_event(scene, name, axis, center_eef, center_bottle):
    arm = ArmTag("left")
    scene.mark(name + "_start")
    if axis == "V":
        moves = ((0, 0, 0.05), (0, 0, -0.10), (0, 0, 0.05))
        main_axis = 2
    else:
        moves = ((0.05, 0, 0), (-0.10, 0, 0), (0.05, 0, 0))
        main_axis = 0
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
        "eef_positive_amplitude": eef_metrics["positive_amplitude"], "eef_negative_amplitude": eef_metrics["negative_amplitude"],
        "eef_max_off_axis": eef_metrics["max_off_axis"], "eef_return_error": eef_metrics["return_error"],
        "bottle_positive_amplitude": bottle_metrics["positive_amplitude"], "bottle_negative_amplitude": bottle_metrics["negative_amplitude"],
        "bottle_max_off_axis": bottle_metrics["max_off_axis"], "bottle_return_error": bottle_metrics["return_error"],
        "bottle_orientation_drift": float(orientation_drift),
        "selected_gripper_contact_fraction": float(np.mean(contacts)) if contacts else 0.0,
        "contact_break_count": _contact_break_count(contacts), "event_duration": len(rows) / 250.0,
    }


def _reverse_arm_control(control):
    return {"position": np.asarray(control["position"])[::-1].copy(), "velocity": -np.asarray(control["velocity"])[::-1].copy()}


def _execute_left_control(scene, control):
    if control is None or not scene.plan_success:
        raise PlannerFailure("left-arm planner query failed")
    scene.take_dense_action({"left_arm": control, "left_gripper": None, "right_arm": None, "right_gripper": None})


def run_f3(output, variant, receipt):
    if variant not in ("pad_center", "bottle_fp"):
        raise ValueError("F3 variant must be pad_center or bottle_fp")
    result = None
    scenes, scene_args = _scene_resources()
    with managed_scene(scenes["F3"], scene_args("F3", output), receipt, f"F3-{variant}") as scene:
        try:
            start = scene.bottle.get_pose()
            scene.initialize_trace(scene.bottle, "left")
            arm = ArmTag("left")
            receipt["attempt_counts"]["execution_attempt_count"] = 1
            _must_move(scene, scene.grasp_actor(scene.bottle, arm_tag=arm, pre_grasp_dis=0.09), "grasp_bottle")
            _must_move(scene, scene.move_by_displacement(arm_tag=arm, z=0.12), "lift_bottle")
            rest = list(scene.robot.left_original_pose)
            current = scene.robot.get_left_ee_pose()
            neutral = [-0.08, -0.05, 0.95] + current[3:]
            control_neutral = scene.left_move_to_pose(pose=neutral)
            _execute_left_control(scene, control_neutral)
            center_eef = np.asarray(scene.robot.get_left_ee_pose()[:3])
            center_bottle = scene.bottle.get_pose().p.copy()
            metrics = {"repair_V": _f3_event(scene, "repair_V", "V", center_eef, center_bottle), "repair_H": _f3_event(scene, "repair_H", "H", center_eef, center_bottle)}
            release_actor_pose = start.p.tolist() + start.q.tolist()
            if variant == "pad_center":
                local_axis = t3d.quaternions.quat2mat(start.q).T @ np.asarray([0.0, 0.0, -1.0])
                functional_point_id = None
                pre_axis = local_axis.tolist()
            else:
                functional_point_id = 0
                pre_axis = "fp"
            pre_pose = scene.get_place_pose(scene.bottle, arm, release_actor_pose, functional_point_id=functional_point_id, constrain="free", pre_dis=0.10, pre_dis_axis=pre_axis)
            release_pose = scene.get_place_pose(scene.bottle, arm, release_actor_pose, functional_point_id=functional_point_id, constrain="free", pre_dis=0.008, pre_dis_axis=pre_axis)
            receipt["cpu_precheck"] = {
                "repair_version": "f3_return_pad_repair_v1", "variant": variant, "pad_local_target": start.p.tolist(),
                "bottle_center_offset_m": float(start.p[2] - scene.pad.get_pose().p[2]), "release_orientation": start.q.tolist(),
                "pre_place_eef_pose": pre_pose, "release_eef_pose": release_pose,
            }
            before = scene.planner_query_count
            scene.mark("return_pre_place_start")
            control_pre = scene.left_move_to_pose(pose=pre_pose)
            _execute_left_control(scene, control_pre)
            control_down = scene.left_move_to_pose(pose=release_pose)
            _execute_left_control(scene, control_down)
            receipt["repair_planner_query_count"] = scene.planner_query_count - before
            _must_move(scene, scene.open_gripper(arm, pos=1.0), "release")
            for _ in range(75):
                scene.scene.step()
                scene._record()
            _execute_left_control(scene, _reverse_arm_control(control_down))
            _execute_left_control(scene, _reverse_arm_control(control_pre))
            _execute_left_control(scene, _reverse_arm_control(control_neutral))
            final = scene.bottle.get_pose()
            result = {
                "repair_version": "f3_return_pad_repair_v1", "variant": variant, "plan_success": bool(scene.plan_success), "metrics": metrics,
                "bottle_return_position_error_m": float(np.linalg.norm(final.p - start.p)),
                "bottle_return_orientation_error": float(1.0 - abs(np.dot(final.q, start.q))),
                "bottle_stable_linear_speed_mps": float(np.linalg.norm(scene.trace[-1]["actor_linear_velocity"])),
                "left_gripper_open": bool(scene.is_left_gripper_open()),
                "rest_return_error_m": float(np.linalg.norm(np.asarray(scene.robot.get_left_ee_pose()[:3]) - np.asarray(rest[:3]))),
                "trace_steps": len(scene.trace), "markers": scene.markers, "planner_query_count": scene.planner_query_count,
            }
        finally:
            receipt["attempt_counts"]["planner_query_count"] = getattr(scene, "planner_query_count", 0)
            _save_partial_trace(scene, output, receipt)
    return result


F4_ORDERS = {"common": "", "A": "A", "B": "B", "C": "C", "common_ab": "AB", "ABC": "ABC", "ACB": "ACB", "BAC": "BAC"}


def _f4_slot_target(role):
    return {"A": [-0.15, -0.17, 0.764, 0, 1, 0, 0], "B": [0.0, -0.17, 0.764, 0, 1, 0, 0], "C": [0.15, -0.17, 0.764, 0, 1, 0, 0]}[role]


def _slot_pass(scene, role):
    actor = scene.role_actors[role]
    target = np.asarray(_f4_slot_target(role)[:2])
    return bool(np.linalg.norm(actor.get_pose().p[:2] - target) < 0.04 and actor.get_pose().p[2] < 0.82)


def _f4_neutral(scene, neutral, neutral_realized):
    _must_move(scene, scene.move_to_pose(ArmTag("left"), neutral), "neutral_return")
    return float(np.linalg.norm(np.asarray(scene.robot.get_left_ee_pose()[:3]) - neutral_realized))


def _f4_place(scene, role, neutral, neutral_realized):
    actor = scene.role_actors[role]
    scene.trace_actor = actor
    all_objects = {name: scene.role_actors[name] for name in ("A", "B", "C")}
    initial = {name: _pose(value) for name, value in all_objects.items()}
    initial_eef = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
    initial_eef_velocity = np.concatenate((scene.trace[-1]["eef_linear_velocity"], scene.trace[-1]["eef_angular_velocity"]))
    initial_gripper = scene.robot.get_normal_real_gripper_val()[0]
    before_slots = {name: _slot_pass(scene, name) for name in ("A", "B", "C")}
    scene.mark(f"block_{role}_start")
    arm = ArmTag("left")
    _must_move(scene, scene.grasp_actor(actor, arm_tag=arm, pre_grasp_dis=0.09), f"grasp_{role}")
    _must_move(scene, scene.move_by_displacement(arm_tag=arm, z=0.08), f"lift_{role}")
    _must_move(scene, scene.place_actor(actor, arm_tag=arm, target_pose=_f4_slot_target(role), functional_point_id=0, constrain="align", pre_dis=0.08, dis=0.02), f"place_{role}")
    _must_move(scene, scene.move_by_displacement(arm_tag=arm, z=0.08), f"withdraw_{role}")
    neutral_error = _f4_neutral(scene, neutral, neutral_realized)
    for _ in range(40):
        scene.scene.step()
        scene._record()
    scene.mark(f"block_{role}_end")
    final_eef_velocity = np.concatenate((scene.trace[-1]["eef_linear_velocity"], scene.trace[-1]["eef_angular_velocity"]))
    after_slots = {name: _slot_pass(scene, name) for name in ("A", "B", "C")}
    start_i, end_i = scene.markers[f"block_{role}_start"], scene.markers[f"block_{role}_end"]
    target_xy = np.asarray(_f4_slot_target(role)[:2])
    values = [bool(np.linalg.norm(row["actor_pose"][:2] - target_xy) < 0.04 and row["actor_pose"][2] < 0.82) for row in scene.trace[start_i:end_i + 1]]
    return {
        "role": role, "start_eef_pose": initial_eef.tolist(), "end_eef_pose": np.asarray(scene.robot.get_left_ee_pose()).tolist(),
        "start_eef_velocity": initial_eef_velocity.tolist(), "end_eef_velocity": final_eef_velocity.tolist(),
        "start_gripper_state": float(initial_gripper), "end_gripper_state": float(scene.robot.get_normal_real_gripper_val()[0]),
        "object_initial_pose": initial[role].tolist(), "object_final_pose": _pose(actor).tolist(),
        "other_object_displacement_m": {name: float(np.linalg.norm(_pose(all_objects[name])[:3] - initial[name][:3])) for name in all_objects if name != role},
        "slot_predicate_before": before_slots, "slot_predicate_after": after_slots,
        "completed_slots_preserved": all(after_slots[name] for name, passed in before_slots.items() if passed),
        "neutral_return_error_m": neutral_error,
        "completion_frame_provisional": first_stable_true_frame(values, min(20, len(values))) if values else None,
    }


def _f4_common(scene, neutral, neutral_realized):
    scene.trace_actor = scene.common_x
    arm = ArmTag("left")
    scene.mark("common_X_start")
    _must_move(scene, scene.grasp_actor(scene.common_x, arm_tag=arm, pre_grasp_dis=0.09), "grasp_common_X")
    _must_move(scene, scene.move_by_displacement(arm_tag=arm, z=0.08), "lift_common_X")
    target = scene.tray.get_functional_point(0)
    _must_move(scene, scene.place_actor(scene.common_x, arm_tag=arm, target_pose=target, constrain="free", pre_dis=0.10, dis=0.02), "place_common_X")
    _must_move(scene, scene.move_by_displacement(arm_tag=arm, z=0.08), "withdraw_common_X")
    neutral_error = _f4_neutral(scene, neutral, neutral_realized)
    scene.mark("common_X_end")
    return {"target": target, "tray_xy_error_m": float(np.linalg.norm(scene.common_x.get_pose().p[:2] - np.asarray(target[:2]))), "neutral_return_error_m": neutral_error, "gripper_open": bool(scene.is_left_gripper_open())}


def run_f4(output, variant, receipt):
    if variant not in F4_ORDERS:
        raise ValueError(f"unsupported F4 variant {variant}")
    result = None
    scenes, scene_args = _scene_resources()
    with managed_scene(scenes["F4"], scene_args("F4", output), receipt, f"F4-{variant}") as scene:
        try:
            first_actor = scene.common_x if variant.startswith("common") or variant in ("ABC", "ACB", "BAC") else scene.role_actors[F4_ORDERS[variant][0]]
            scene.initialize_trace(first_actor, "left")
            q = scene.robot.get_left_ee_pose()[3:]
            neutral = [-0.15, -0.04, 0.95] + q
            _must_move(scene, scene.move_to_pose(ArmTag("left"), neutral), "initial_neutral")
            neutral_realized = np.asarray(scene.robot.get_left_ee_pose()[:3])
            receipt["attempt_counts"]["execution_attempt_count"] = 1
            common_result = None
            if variant == "common" or variant == "common_ab" or variant in ("ABC", "ACB", "BAC"):
                common_result = _f4_common(scene, neutral, neutral_realized)
            blocks = [_f4_place(scene, role, neutral, neutral_realized) for role in F4_ORDERS[variant]]
            result = {
                "probe_version": "f4_full_program_probe_v1", "variant": variant, "plan_success": bool(scene.plan_success),
                "common_X": common_result, "blocks": blocks,
                "all_completed_slots_preserved": all(item["completed_slots_preserved"] for item in blocks),
                "final_slot_predicates": {name: _slot_pass(scene, name) for name in ("A", "B", "C")},
                "left_gripper_open": bool(scene.is_left_gripper_open()), "trace_steps": len(scene.trace),
                "markers": scene.markers, "planner_query_count": scene.planner_query_count,
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
    args = parser.parse_args()
    parser.error("bounded repair v1 is terminal and preserved for evidence only; use action_feasibility_v2 after a new explicit probe authorization")
    if args.variant not in VARIANTS[args.family]:
        parser.error(f"variant for {args.family} must be one of {VARIANTS[args.family]}")
    started = time.time()
    receipt = {
        "schema_version": "cmf_action_feasibility_v2", "purpose": "nonformal_feasibility",
        "formal_data": False, "stage0_data": False, "attempt_limit": 1,
        "timeout_seconds": {"F1": 900, "F2": 900, "F3": 1800, "F4": 2700}[args.family],
        "family": args.family, "variant": args.variant, "physical_gpu_index": args.physical_index,
        "expected_gpu_uuid": args.expected_uuid, "pid": os.getpid(), "status": "running",
        "attempt_counts": {"feasibility_query_count": 1, "planner_query_count": 0, "execution_attempt_count": 0, "recovery_attempt_count": 0},
    }
    initialize_cleanup_fields(receipt)
    code = 1
    try:
        if os.environ.get("CUDA_VISIBLE_DEVICES") != args.expected_uuid:
            raise RuntimeError("CUDA_VISIBLE_DEVICES does not match expected UUID")
        args.output.mkdir(parents=True, exist_ok=False)
        result = RUNNERS[args.family](args.output, args.variant, receipt)
        if result is None:
            raise RuntimeError("probe returned no result")
        receipt["result"] = result
        passed = result_passed(args.family, result)
        receipt["semantic_probe_pass"] = passed
        receipt["status"] = "passed_nonformal_action_probe" if passed else "failed_nonformal_action_probe"
        code = 0 if passed else 1
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
