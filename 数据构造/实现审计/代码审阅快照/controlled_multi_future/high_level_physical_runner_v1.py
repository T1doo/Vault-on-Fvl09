"""One-attempt F2/F3 physical qualification for high-level candidates."""

from __future__ import annotations

import hashlib
from pathlib import Path
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np

from .anchor import capture_anchor, quaternion_angular_error
from .canonical_artifact import canonical_hash_json, canonical_write_json
from .f2_preload_entry_evidence_gate_v11 import (
    audit_f2_preload_entry_evidence_gate_v11,
)
from .f2_release_gates_v10 import (
    audit_f2_final_inside_success_gate_v10,
    audit_f2_release_safety_gate_v10,
)
from .f3_asset_grasp_qualification_v2 import REQUIRED_LEVEL2_GATES
from .f3_physical_contact_signal_v8 import (
    classify_contact_pair_physical_hit_v8,
)
from .family_runners_v3_1 import (
    _actor_geometry_center_pose,
    _actor_half_extents,
    _actor_local_geometry_bounds,
    _arm_eef_pose,
    _arm_gripper_open,
    _arm_original_pose,
    _arm_tag,
    _entity,
    _execute_control,
    _gripper_below_eef_envelope,
    _must_action,
    _plan_chain,
    _planner_reset,
    _pose,
    _wait_and_record,
)
from .family_runners_v3_3 import (
    _realized_event_metrics,
    get_family_controller_v3_3,
)
from .geometry import (
    obb_corners,
    pose_matrix,
    relative_pose,
    world_axis_offset_pose,
)
from .high_level_planner_runner_v1 import (
    _planner_payload,
    _targets_payload,
    build_f2_stage_a_targets_v1,
    build_f3_level1_targets_v1,
    build_f4_stage_b_targets_v1,
)
from .high_level_runtime_specs_v1 import (
    IMPLEMENTATION_VERSION,
    job_budget_v1,
    validate_f2_runtime_spec_v1,
    validate_f3_runtime_spec_v1,
    validate_f4_runtime_spec_v1,
)
from .runtime_v2_contracts import PROVISIONAL_RUNTIME_THRESHOLDS
from .verifiers.f3 import verify_realized_motion_metrics
from .verifiers.f1 import verify_true_cavity_obb


def _complete_contact_signal(row: Mapping[str, Any]) -> bool:
    try:
        return all(
            classify_contact_pair_physical_hit_v8(pair)["evidence_complete"]
            is True
            for pair in row["contact_pairs"]
        )
    except (KeyError, TypeError, ValueError):
        return False


def _inside_opening_geometry(
    scene,
    binding: Mapping[str, Any],
    *,
    can_actor_pose=None,
    box_actor_pose=None,
) -> dict[str, Any]:
    can_local_center, can_half = _actor_local_geometry_bounds(scene.can)
    can_origin = (
        _pose(scene.can)
        if can_actor_pose is None
        else np.asarray(can_actor_pose, dtype=np.float64).reshape(7)
    )
    box_pose = (
        _pose(scene.box)
        if box_actor_pose is None
        else np.asarray(box_actor_pose, dtype=np.float64).reshape(7)
    )
    can_geometry = _actor_geometry_center_pose(
        scene.can, actor_pose=can_origin
    )
    corners = obb_corners(can_geometry, can_half)
    homogeneous = np.concatenate(
        (corners, np.ones((len(corners), 1), dtype=np.float64)), axis=1
    )
    local = (np.linalg.inv(pose_matrix(box_pose)) @ homogeneous.T).T[:, :3]
    cavity = binding["strict_cavity_contract"]
    lower = np.asarray(cavity["lower_m"], dtype=np.float64)
    upper = np.asarray(cavity["upper_m"], dtype=np.float64)
    axes = (0, 2)
    rim_clearance = float(np.min(local[:, 1]) - upper[1])
    center_local = relative_pose(box_pose, can_geometry)
    center_margins = np.concatenate(
        (
            center_local[list(axes)] - lower[list(axes)],
            upper[list(axes)] - center_local[list(axes)],
        )
    )
    overlap = np.concatenate(
        (
            np.max(local[:, axes], axis=0) - lower[list(axes)],
            upper[list(axes)] - np.min(local[:, axes], axis=0),
        )
    )
    signed = np.concatenate(
        (
            np.min(local[:, axes], axis=0) - lower[list(axes)],
            upper[list(axes)] - np.max(local[:, axes], axis=0),
        )
    )
    return {
        "opening_projection_inside": bool(np.min(signed) >= 0.0),
        "opening_projection_signed_margin_m": float(np.min(signed)),
        "opening_center_inside": bool(np.min(center_margins) >= 0.0),
        "opening_center_signed_margin_m": float(np.min(center_margins)),
        "opening_projection_overlaps": bool(np.min(overlap) > 0.0),
        "opening_projection_overlap_signed_m": float(np.min(overlap)),
        "rim_clearance_m": rim_clearance,
        "rim_clearance_pass": rim_clearance >= 0.02,
        "can_geometry_center_pose": can_geometry.tolist(),
        "geometry_evidence_complete": True,
        "local_geometry_center_m": np.asarray(can_local_center).tolist(),
    }


def _generic_gripper_assembly_names(scene, arm: str) -> dict[str, Any]:
    selected = _gripper_below_eef_envelope(scene, arm=arm)[
        "selected_gripper_links"
    ]
    palm = str(getattr(scene.robot, f"{arm}_move_group"))
    links = {
        link.get_name() for link in getattr(scene.robot, f"{arm}_entity").get_links()
    }
    if palm not in links or not set(selected).issubset(links):
        raise RuntimeError("selected arm gripper topology is incomplete")
    return {
        "arm": arm,
        "selected_contact_signal_link_names": sorted(selected),
        "move_group_palm_link_name": palm,
        "allowed_gripper_assembly_body_names": sorted(set(selected) | {palm}),
        "right_arm_is_symmetric_runtime_topology_audit": arm == "right",
    }


def _execute_planned_segment(scene, controls, targets, index: int, arm: str):
    target = targets[index]
    start = len(scene.trace) - 1
    _execute_control(
        scene, controls[index], target["segment_id"], arm=arm
    )
    end = len(scene.trace) - 1
    realized = _arm_eef_pose(scene, arm)
    goal = np.asarray(target["pose"], dtype=np.float64)
    return {
        "segment_id": target["segment_id"],
        "start_trace_row": start,
        "end_trace_row": end,
        "planner_status": controls[index].get("status"),
        "tracking_position_error_m": float(np.linalg.norm(realized[:3] - goal[:3])),
        "tracking_orientation_error_rad": quaternion_angular_error(
            realized[3:], goal[3:]
        ),
    }


def _f2_relation_predicates(scene, binding: Mapping[str, Any]) -> dict[str, bool]:
    can_geometry = _actor_geometry_center_pose(scene.can)
    can_half = _actor_half_extents(scene.can)
    inside = verify_true_cavity_obb(
        can_geometry,
        can_half,
        _pose(scene.box),
        binding["strict_cavity_contract"],
    )["pass_true_cavity_obb"]
    corners = obb_corners(can_geometry, can_half)
    scale_target = np.asarray(scene.scale.get_functional_point(0), dtype=np.float64)
    support_half = np.asarray(
        binding["layout_payload"]["on_region_half_xy_m"], dtype=np.float64
    )
    on = bool(
        np.all(np.abs(corners[:, :2] - scale_target[None, :2]) <= support_half[None, :])
        and abs(float(np.min(corners[:, 2]) - scale_target[2])) <= 0.02
    )
    stand_center = _actor_geometry_center_pose(scene.stand)
    radial = float(np.linalg.norm(can_geometry[:2] - stand_center[:2]))
    beside = bool(0.12 <= radial <= 0.23 and not inside and not on)
    return {"inside": bool(inside), "on": on, "beside": beside}


def execute_f2_inside_physical_v1(scene, spec: Mapping[str, Any]) -> dict[str, Any]:
    arm = spec["arm"]
    binding = spec["f2_asset_layout_binding_v3"]
    targets, target_audit = build_f2_stage_a_targets_v1(scene, spec)
    _planner_reset(
        scene,
        planner_seed=20260829,
        variant_id=f"f2_inside_physical:{spec['slot_id']}",
        arm=arm,
    )
    planned = _plan_chain(
        scene,
        targets,
        query_limit=job_budget_v1("f2_inside_physical")["planner_query_limit"],
        arm=arm,
    )
    if planned.get("pass") is not True:
        return {
            "planner_result": _planner_payload(planned),
            "target_construction": target_audit,
            "sequence_complete": False,
            "strict_inside_verifier_pass": False,
            "gates": {
                "planner_success": False,
                "preload_entry_v11": False,
                "release_safety_v10": False,
                "final_inside_v10": False,
            },
        }
    controls = planned["controls"]
    executions = []
    executions.append(_execute_planned_segment(scene, controls, targets, 0, arm))
    executions.append(_execute_planned_segment(scene, controls, targets, 1, arm))
    _must_action(
        scene,
        scene.close_gripper(_arm_tag(arm), pos=0.0),
        "f2_hierarchical_close",
    )
    _wait_and_record(scene, 250)
    for index in (2, 3, 4):
        executions.append(_execute_planned_segment(scene, controls, targets, index, arm))
    topology = _generic_gripper_assembly_names(scene, arm)
    can_name = _entity(scene.can).get_name()
    box_name = _entity(scene.box).get_name()
    _wait_and_record(scene, 60)
    hold_rows = scene.trace[-60:]
    entry_rows = [
        {
            **row,
            "contact_signal_complete": _complete_contact_signal(row),
        }
        for row in hold_rows
    ]
    opening = _inside_opening_geometry(scene, binding)
    preload_gate = audit_f2_preload_entry_evidence_gate_v11(
        entry_rows,
        can_actor_name=can_name,
        selected_contact_signal_link_names=topology[
            "selected_contact_signal_link_names"
        ],
        allowed_gripper_assembly_body_names=topology[
            "allowed_gripper_assembly_body_names"
        ],
        final_geometry_gate=opening,
    )
    if preload_gate.get("pass") is not True:
        return {
            "planner_result": _planner_payload(planned),
            "target_construction": target_audit,
            "execution_receipts": executions,
            "gripper_topology": topology,
            "preload_entry_gate_v11": preload_gate,
            "sequence_complete": False,
            "strict_inside_verifier_pass": False,
            "gates": {
                "planner_success": True,
                "preload_entry_v11": False,
                "release_safety_v10": False,
                "final_inside_v10": False,
            },
        }
    qpos = np.asarray(
        scene.trace[-1][f"realized_{arm}_gripper_joint_qpos"], dtype=np.float64
    ).reshape(2)
    balanced = float(np.mean(qpos))
    partial_open = (balanced - (-0.01)) / (0.045 - (-0.01))
    if not 0.0 < partial_open < 1.0:
        raise RuntimeError("F2 balanced partial-open target is outside (0,1)")
    _must_action(
        scene,
        scene.open_gripper(_arm_tag(arm), pos=partial_open),
        "f2_hierarchical_balanced_partial_open",
    )
    _wait_and_record(scene, 50)
    safety_rows_raw = scene.trace[-50:]
    safety_rows = [
        {
            "actor_linear_velocity": row["actor_linear_velocity"],
            "actor_angular_velocity": row["actor_angular_velocity"],
            "contact_pairs": row["contact_pairs"],
            "contact_signal_complete": _complete_contact_signal(row),
        }
        for row in safety_rows_raw
    ]
    safety_geometry = [
        _inside_opening_geometry(
            scene,
            binding,
            can_actor_pose=row["role_actor_poses"]["main_can"],
            box_actor_pose=row["role_actor_poses"]["box"],
        )
        for row in safety_rows_raw
    ]
    safety_gate = audit_f2_release_safety_gate_v10(
        safety_rows,
        safety_geometry,
        can_actor_name=can_name,
        selected_finger_link_names=topology[
            "selected_contact_signal_link_names"
        ],
        box_actor_name=box_name,
    )
    if safety_gate.get("pass") is not True:
        return {
            "planner_result": _planner_payload(planned),
            "target_construction": target_audit,
            "execution_receipts": executions,
            "gripper_topology": topology,
            "preload_entry_gate_v11": preload_gate,
            "release_safety_gate_v10": safety_gate,
            "sequence_complete": False,
            "strict_inside_verifier_pass": False,
            "gates": {
                "planner_success": True,
                "preload_entry_v11": True,
                "release_safety_v10": False,
                "final_inside_v10": False,
            },
        }
    _must_action(
        scene,
        scene.open_gripper(_arm_tag(arm), pos=1.0),
        "f2_hierarchical_full_open",
    )
    final_start = len(scene.trace) - 1
    _wait_and_record(scene, 250)
    final_rows_raw = scene.trace[final_start + 1 :]
    if len(final_rows_raw) != 250:
        raise RuntimeError("F2 physical final settle is not exactly 250 frames")
    executions.append(_execute_planned_segment(scene, controls, targets, 5, arm))
    _wait_and_record(scene, 75)
    relations = _f2_relation_predicates(scene, binding)
    rest = _arm_original_pose(scene, arm)
    actual_rest = _arm_eef_pose(scene, arm)
    rest_pass = bool(
        np.linalg.norm(actual_rest[:3] - rest[:3])
        <= PROVISIONAL_RUNTIME_THRESHOLDS["rest_position_error_m"]
        and quaternion_angular_error(actual_rest[3:], rest[3:])
        <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"]
    )
    final_rows = [
        {
            "actor_linear_velocity": row["actor_linear_velocity"],
            "actor_angular_velocity": row["actor_angular_velocity"],
            "contact_pairs": row["contact_pairs"],
            "contact_signal_complete": _complete_contact_signal(row),
        }
        for row in final_rows_raw
    ]
    final_gate = audit_f2_final_inside_success_gate_v10(
        final_rows,
        true_cavity_obb_pass=relations["inside"],
        relation_predicates=relations,
        gripper_full_open=_arm_gripper_open(scene, arm),
        arm_rest_pass=rest_pass,
        can_actor_name=can_name,
        box_actor_name=box_name,
    )
    return {
        "planner_result": _planner_payload(planned),
        "target_construction": target_audit,
        "execution_receipts": executions,
        "gripper_topology": topology,
        "balanced_partial_open": {
            "actual_finger_qpos_m": qpos.tolist(),
            "balanced_drive_target_m": balanced,
            "partial_open_normalized_target": partial_open,
        },
        "preload_entry_gate_v11": preload_gate,
        "release_safety_gate_v10": safety_gate,
        "final_inside_success_gate_v10": final_gate,
        "relation_predicates": relations,
        "sequence_complete": final_gate.get("pass") is True,
        "strict_inside_verifier_pass": final_gate.get("pass") is True,
        "gates": {
            "planner_success": True,
            "preload_entry_v11": True,
            "release_safety_v10": True,
            "final_inside_v10": final_gate.get("pass") is True,
        },
    }


def build_f3_level2_targets_v1(scene, spec: Mapping[str, Any]):
    level1, audit = build_f3_level1_targets_v1(scene, spec)
    central = np.asarray(level1[3]["pose"], dtype=np.float64)
    v_negative = world_axis_offset_pose(central, -0.055)
    targets = level1[:5] + [
        {"segment_id": "f3_level2_V_minus", "pose": v_negative},
        {"segment_id": "f3_level2_return", "pose": central},
    ]
    # Replace the level-1 return with a V-/return pair.
    return _targets_payload(targets), {
        **audit,
        "level2_closed_loop_sequence": ["V_plus", "V_minus", "return"],
    }


def _pair_is_physical_hit_between(
    pair: Mapping[str, Any], first: set[str], second: set[str]
) -> bool:
    bodies = {str(pair.get("body_a")), str(pair.get("body_b"))}
    if not (bodies & first and bodies & second):
        return False
    return classify_contact_pair_physical_hit_v8(pair)[
        "physical_hit_for_gate"
    ] is True


def execute_f3_level2_physical_v1(scene, spec: Mapping[str, Any]) -> dict[str, Any]:
    candidate = spec["f3_asset_grasp_tuple_v2"]
    arm = spec["arm"]
    targets, target_audit = build_f3_level2_targets_v1(scene, spec)
    _planner_reset(
        scene,
        planner_seed=20260829,
        variant_id=f"f3_level2_physical:{spec['slot_id']}",
        arm=arm,
    )
    planned = _plan_chain(
        scene,
        targets,
        query_limit=job_budget_v1("f3_level2_physical")["planner_query_limit"],
        arm=arm,
    )
    gates = {name: False for name in REQUIRED_LEVEL2_GATES}
    if planned.get("pass") is not True:
        return {
            "planner_result": _planner_payload(planned),
            "target_construction": target_audit,
            "gates": gates,
            "sequence_complete": False,
        }
    gates["planner_success"] = True
    controls = planned["controls"]
    executions = []
    executions.append(_execute_planned_segment(scene, controls, targets, 0, arm))
    executions.append(_execute_planned_segment(scene, controls, targets, 1, arm))
    _must_action(
        scene,
        scene.close_gripper(
            _arm_tag(arm), pos=float(candidate["close_normalized_target"])
        ),
        "f3_asset_grasp_close",
    )
    _wait_and_record(scene, int(candidate["post_close_settle_frames"]))
    post_close_transform = relative_pose(
        _arm_eef_pose(scene, arm), _pose(scene.bottle)
    )
    executions.append(_execute_planned_segment(scene, controls, targets, 2, arm))
    lift_end = len(scene.trace) - 1
    executions.append(_execute_planned_segment(scene, controls, targets, 3, arm))
    _wait_and_record(scene, 250)
    pre_v_transform = relative_pose(
        _arm_eef_pose(scene, arm), _pose(scene.bottle)
    )
    event_start = len(scene.trace) - 1
    for index in (4, 5, 6):
        executions.append(_execute_planned_segment(scene, controls, targets, index, arm))
    event_end = len(scene.trace) - 1
    _wait_and_record(scene, 250)
    final_transform = relative_pose(
        _arm_eef_pose(scene, arm), _pose(scene.bottle)
    )
    event_rows = scene.trace[event_start : event_end + 1]
    metrics = _realized_event_metrics(event_rows, axis="V")
    motion = verify_realized_motion_metrics(
        {"event_0_V": metrics}, PROVISIONAL_RUNTIME_THRESHOLDS
    )
    event_checks = motion["event_checks"]["event_0_V"]
    bottle_name = _entity(scene.bottle).get_name()
    selected_links = set(
        _gripper_below_eef_envelope(scene, arm=arm)["selected_gripper_links"]
    )
    transport_rows = scene.trace[lift_end:]
    contact_rows = [
        any(
            _pair_is_physical_hit_between(
                pair, {bottle_name}, selected_links
            )
            for pair in row["contact_pairs"]
        )
        for row in transport_rows
    ]
    pad_name = _entity(scene.pad).get_name()
    off_support = all(
        not any(
            _pair_is_physical_hit_between(
                pair, {bottle_name}, {pad_name, "table"}
            )
            for pair in row["contact_pairs"]
        )
        for row in transport_rows
    )
    translation_drift = float(
        max(
            np.linalg.norm(pre_v_transform[:3] - post_close_transform[:3]),
            np.linalg.norm(final_transform[:3] - post_close_transform[:3]),
        )
    )
    orientation_drift = float(
        max(
            quaternion_angular_error(pre_v_transform[3:], post_close_transform[3:]),
            quaternion_angular_error(final_transform[3:], post_close_transform[3:]),
        )
    )
    stable_rows = scene.trace[-50:]
    linear = [
        float(np.linalg.norm(row["role_actor_linear_velocities"]["bottle"]))
        for row in stable_rows
    ]
    angular = [
        float(np.linalg.norm(row["role_actor_angular_velocities"]["bottle"]))
        for row in stable_rows
    ]
    gates.update(
        {
            "selected_gripper_contact_continuity": bool(contact_rows)
            and all(contact_rows),
            "bottle_off_support_after_lift": off_support,
            "grasp_transform_translation_stable": translation_drift <= 0.005,
            "grasp_transform_orientation_stable": orientation_drift <= 0.05,
            "bottle_linear_stability": max(linear)
            <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
            "bottle_angular_stability": max(angular)
            <= PROVISIONAL_RUNTIME_THRESHOLDS[
                "eef_stationary_angular_speed_rps"
            ],
            "eef_tracking": event_checks["eef_off_axis"]
            and executions[-1]["tracking_position_error_m"]
            <= PROVISIONAL_RUNTIME_THRESHOLDS["position_error_m"]
            and executions[-1]["tracking_orientation_error_rad"]
            <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
            "shared_v_realized_amplitude": all(
                event_checks[name]
                for name in (
                    "eef_positive_amplitude",
                    "eef_negative_amplitude",
                    "bottle_positive_amplitude",
                    "bottle_negative_amplitude",
                )
            ),
            "shared_v_closed_loop_return": event_checks["eef_return"]
            and event_checks["bottle_return"],
        }
    )
    return {
        "planner_result": _planner_payload(planned),
        "target_construction": target_audit,
        "execution_receipts": executions,
        "motion_metrics": metrics,
        "motion_gate": motion,
        "selected_contact_fraction_after_lift": float(np.mean(contact_rows))
        if contact_rows
        else 0.0,
        "grasp_transform_translation_drift_m": translation_drift,
        "grasp_transform_orientation_drift_rad": orientation_drift,
        "maximum_final_linear_speed_mps": max(linear),
        "maximum_final_angular_speed_rps": max(angular),
        "gates": gates,
        "sequence_complete": all(gates.values()),
    }


def execute_f4_a_only_physical_v1(
    scene, spec: Mapping[str, Any]
) -> dict[str, Any]:
    controller = get_family_controller_v3_3("F4")
    controller.initialize_prefix_replay_trace(scene)
    prefix = controller.plan_and_execute_canonical_prefix(
        scene,
        controller.canonical_prefix_contract([]),
        capture_anchor=capture_anchor,
    )
    prefix_pass = (
        prefix.get("prefix_physical_acceptance", {}).get("pass") is True
    )
    if not prefix_pass:
        return {
            "prefix": prefix,
            "planner_result": None,
            "execution_receipts": [],
            "verifier": {"prefix_physical_acceptance": False},
            "sequence_complete": False,
        }
    common_after_prefix = _pose(scene.common_x).copy()
    non_targets_before = {
        role: _pose(getattr(scene, role.lower())).copy()
        for role in ("B", "C")
    }
    scene.initialize_trace(
        scene.a, spec["arm"], role_actors=scene.role_actors
    )
    scene.planner_query_limit = 32
    targets, target_audit = build_f4_stage_b_targets_v1(scene, spec)
    a_targets = targets[:10]
    reset = _planner_reset(
        scene,
        planner_seed=20260830,
        variant_id=f"f4_high_level_a_only:{spec['slot_id']}",
        arm=spec["arm"],
    )
    planned = _plan_chain(
        scene, a_targets, query_limit=32, arm=spec["arm"]
    )
    if planned.get("pass") is not True:
        return {
            "prefix": prefix,
            "target_construction": target_audit,
            "planner_reset_receipt": reset,
            "planner_result": _planner_payload(planned),
            "execution_receipts": [],
            "verifier": {"a_only_planner_chain": False},
            "sequence_complete": False,
        }
    controls = planned["controls"]
    execution_receipts = []
    for index in (0, 1, 2):
        execution_receipts.append(
            _execute_planned_segment(
                scene, controls, a_targets, index, spec["arm"]
            )
        )
    _must_action(
        scene,
        scene.close_gripper(_arm_tag(spec["arm"]), pos=0.0),
        "f4_high_level_A_close_gripper",
    )
    for index in (3, 4, 5, 6, 7):
        execution_receipts.append(
            _execute_planned_segment(
                scene, controls, a_targets, index, spec["arm"]
            )
        )
    _must_action(
        scene,
        scene.open_gripper(_arm_tag(spec["arm"]), pos=1.0),
        "f4_high_level_A_release",
    )
    for index in (8, 9):
        execution_receipts.append(
            _execute_planned_segment(
                scene, controls, a_targets, index, spec["arm"]
            )
        )
    _wait_and_record(scene, 75)
    slot = controller._slot_state_receipt(
        scene, role="A", actor=scene.a, slot=scene.slot_a
    )
    common_displacement = float(
        np.linalg.norm(_pose(scene.common_x)[:3] - common_after_prefix[:3])
    )
    non_target_displacements = {
        role: float(
            np.linalg.norm(
                _pose(getattr(scene, role.lower()))[:3]
                - non_targets_before[role][:3]
            )
        )
        for role in ("B", "C")
    }
    neutral = np.asarray(a_targets[-1]["pose"], dtype=np.float64)
    realized = _arm_eef_pose(scene, spec["arm"])
    neutral_position_error = float(
        np.linalg.norm(realized[:3] - neutral[:3])
    )
    neutral_orientation_error = quaternion_angular_error(
        realized[3:], neutral[3:]
    )
    checks = {
        "common_x_prefix_physical_acceptance": prefix_pass,
        "a_only_planner_chain": planned.get("pass") is True,
        "a_slot_state": slot["pass"] is True,
        "common_x_preserved": common_displacement
        <= PROVISIONAL_RUNTIME_THRESHOLDS["non_target_displacement_m"],
        "B_C_preserved": all(
            value
            <= PROVISIONAL_RUNTIME_THRESHOLDS[
                "non_target_displacement_m"
            ]
            for value in non_target_displacements.values()
        ),
        "selected_gripper_open": _arm_gripper_open(scene, spec["arm"]),
        "selected_arm_neutral_position": neutral_position_error
        <= PROVISIONAL_RUNTIME_THRESHOLDS["neutral_position_error_m"],
        "selected_arm_neutral_orientation": neutral_orientation_error
        <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
    }
    return {
        "prefix": prefix,
        "target_construction": target_audit,
        "planner_reset_receipt": reset,
        "planner_result": _planner_payload(planned),
        "execution_receipts": execution_receipts,
        "verifier": {
            "checks": checks,
            "A_slot_state": slot,
            "common_x_displacement_m": common_displacement,
            "non_target_displacements_m": non_target_displacements,
            "neutral_position_error_m": neutral_position_error,
            "neutral_orientation_error_rad": neutral_orientation_error,
            "pass": all(checks.values()),
        },
        "sequence_complete": all(checks.values()),
    }


class HighLevelPhysicalRunnerV1:
    def __init__(self, adapter):
        self.adapter = adapter

    @staticmethod
    def _save_trace(scene, path: Path) -> dict[str, Any]:
        value = dict(scene.save_trace(path))
        value["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        return value

    def run(self, *, output_dir: Path, planned_spec: Mapping[str, Any]) -> dict[str, Any]:
        family = str(planned_spec.get("family"))
        if family == "F2":
            spec = validate_f2_runtime_spec_v1(planned_spec)
            if spec["purpose"] != "f2_inside_physical":
                raise ValueError("physical runner received invalid F2 purpose")
            execute = execute_f2_inside_physical_v1
            trace_actor_name = "can"
        elif family == "F3":
            spec = validate_f3_runtime_spec_v1(planned_spec)
            if spec["purpose"] != "f3_level2_physical":
                raise ValueError("physical runner received invalid F3 purpose")
            execute = execute_f3_level2_physical_v1
            trace_actor_name = "bottle"
        elif family == "F4":
            spec = validate_f4_runtime_spec_v1(planned_spec)
            if spec["purpose"] != "f4_single_role_physical":
                raise ValueError("physical runner received invalid F4 purpose")
            execute = execute_f4_a_only_physical_v1
            trace_actor_name = "common_x"
        else:
            raise ValueError("physical runner family is unsupported")
        if self.adapter.planned_spec != spec:
            raise ValueError("physical runner adapter/spec binding mismatch")
        budget = job_budget_v1(spec["purpose"])
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        started = time.time()
        context = self.adapter.scene(
            spec,
            phase=f"{spec['purpose']}:{spec['slot_id']}",
            program=None,
        )
        scene = None
        receipt: dict[str, Any] = {
            "schema_version": "cmf_high_level_physical_candidate_terminal_v1",
            "implementation_version": IMPLEMENTATION_VERSION,
            "family": family,
            "purpose": spec["purpose"],
            "slot_id": spec["slot_id"],
            "planned_scope_spec_sha256": spec["planned_scope_spec_sha256"],
            "budget_receipt_sha256": budget["budget_receipt_sha256"],
            "candidate_id": (
                spec["candidate"]["candidate_id"]
                if family == "F2"
                else spec["f3_asset_grasp_tuple_v2"]["tuple_id"]
                if family == "F3"
                else spec["f4_stage_b_candidate_v1"]["candidate_id"]
            ),
            "candidate_sha256": (
                spec["candidate_sha256"]
                if family == "F2"
                else spec["f3_asset_grasp_tuple_sha256"]
                if family == "F3"
                else spec["f4_stage_b_candidate_sha256"]
            ),
            "arm": spec["arm"],
            "fresh_scene_count": 0,
            "physical_execution_count": 1,
            "planner_query_count": 0,
            "status": "running",
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
        }
        canonical_write_json(output_dir / "receipt.json", receipt, mode=0o600)
        try:
            with context as handle:
                scene = handle.scene
                receipt["fresh_scene_count"] = 1
                receipt["current"] = self.adapter.capture_current(scene)
                if family == "F4":
                    render_binding = getattr(
                        scene, "_cmf_render_device_binding_v1", None
                    )
                    if (
                        not isinstance(render_binding, Mapping)
                        or render_binding.get("pass") is not True
                    ):
                        raise RuntimeError(
                            "F4 physical scene lacks render-device binding"
                        )
                    receipt["render_device_binding"] = dict(render_binding)
                trace_actor = getattr(scene, trace_actor_name)
                scene.initialize_trace(
                    trace_actor, spec["arm"], role_actors=scene.role_actors
                )
                scene.planner_query_limit = int(budget["planner_query_limit"])
                result = execute(scene, spec)
                receipt["physical_result"] = result
                receipt["planner_query_count"] = int(scene.planner_query_count)
                receipt["trace_source"] = self._save_trace(
                    scene, output_dir / "physical_trace.npz"
                )
                passed = (
                    result.get("strict_inside_verifier_pass") is True
                    if family == "F2"
                    else result.get("sequence_complete") is True
                )
                receipt["status"] = (
                    "physical_candidate_pass"
                    if passed
                    else "physical_candidate_failed_gates"
                )
        except BaseException as exc:
            receipt["status"] = "physical_candidate_failed_execution_or_infrastructure"
            receipt["error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            if scene is not None:
                receipt["planner_query_count"] = int(
                    getattr(scene, "planner_query_count", 0)
                )
                if hasattr(scene, "trace") and scene.trace:
                    receipt["partial_trace_source"] = self._save_trace(
                        scene, output_dir / "partial_trace.npz"
                    )
        cleanup = context.cleanup_receipt
        receipt["cleanup"] = cleanup
        receipt["cleanup_safety_pass"] = (
            isinstance(cleanup, Mapping)
            and cleanup.get("cleanup_safety_pass") is True
            and int(cleanup.get("orphan_process_count", -1)) == 0
        )
        receipt["orphan_process_count"] = (
            int(cleanup.get("orphan_process_count", -1))
            if isinstance(cleanup, Mapping)
            else -1
        )
        receipt["budget_checks"] = {
            "fresh_scene_within_limit": receipt["fresh_scene_count"]
            <= budget["fresh_scene_limit"],
            "planner_queries_within_limit": receipt["planner_query_count"]
            <= budget["planner_query_limit"],
            "physical_execution_exactly_one": receipt[
                "physical_execution_count"
            ]
            == 1,
        }
        if not receipt["cleanup_safety_pass"]:
            receipt["status"] = "physical_candidate_failed_cleanup_uncertain"
        receipt["pass"] = (
            receipt["status"] == "physical_candidate_pass"
            and receipt["cleanup_safety_pass"]
            and all(receipt["budget_checks"].values())
        )
        receipt["elapsed_seconds"] = time.time() - started
        receipt["receipt_sha256"] = canonical_hash_json(receipt)
        canonical_write_json(output_dir / "receipt.json", receipt, mode=0o600)
        return receipt


__all__ = [
    "HighLevelPhysicalRunnerV1",
    "build_f3_level2_targets_v1",
    "execute_f2_inside_physical_v1",
    "execute_f3_level2_physical_v1",
    "execute_f4_a_only_physical_v1",
]
