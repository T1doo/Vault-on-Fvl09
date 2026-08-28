"""Dependency-light contracts for the proposed runtime-v3 implementation.

This module changes implementation mechanics only.  It does not authorize a
GPU probe, Stage 0, formal collection, or any scientific-design change.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np


DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3"
RAW_LAYOUT_VERSION = "controller_effective_setpoint_v1_layout_v2_1"
STAGE0_AUTHORIZED = False
GPU_PROBE_AUTHORIZED = False
FORMAL_DATA = False
STAGE0_DATA = False


F1_TARGET_ORDER = ("red", "green", "blue")
F1_COMMON_PREFIX = {
    "prefix_id": "f1_cluster_common_pregrasp_v1",
    "target_role_visible": False,
    "steps": [
        {"op": "open_gripper", "arm": "left"},
        {"op": "move_to_cluster_common_pregrasp_region", "arm": "left"},
        {"op": "hold_branch_neutral", "arm": "left"},
    ],
    "branch_boundary": "after_hold_branch_neutral_before_target_specific_grasp",
}


def f1_branch_spec(target_role: str) -> dict:
    if target_role not in F1_TARGET_ORDER:
        raise ValueError(f"target_role must be one of {F1_TARGET_ORDER}")
    return {
        "program_id": f"F1-{target_role}",
        "target_role": target_role,
        "non_target_roles": [role for role in F1_TARGET_ORDER if role != target_role],
        "arm": "left",
        "container": "062_plasticbox/base3",
        "fresh_scene_required": True,
        "canonical_prefix_id": F1_COMMON_PREFIX["prefix_id"],
    }


def validate_f1_three_branch_coverage(branch_receipts: Sequence[Mapping[str, object]]) -> dict:
    if len(branch_receipts) != 3:
        raise ValueError("F1 v3 requires exactly three branch receipts")
    roles = [item.get("target_role") for item in branch_receipts]
    if tuple(roles) != F1_TARGET_ORDER:
        raise ValueError(f"F1 branch order must be exactly {F1_TARGET_ORDER}")
    for key in ("scene_spec_sha256", "reference_current_sha256", "canonical_prefix_sha256"):
        values = {item.get(key) for item in branch_receipts}
        if None in values or len(values) != 1:
            raise ValueError(f"all F1 branches must share one {key}")
    passed = [item.get("semantic_probe_pass") is True for item in branch_receipts]
    return {
        "pass": all(passed),
        "branch_pass": dict(zip(F1_TARGET_ORDER, passed)),
        "f1_three_branch_feasibility_pass": all(passed),
    }


# Six complete, ordered candidates.  Position/yaw/height are paired before any
# planner query; this is not an adaptive Cartesian-product search.
F2_POSE_CANDIDATES = (
    {"candidate_id": "p0_y0_h0", "stand_relative_xy_m": [0.00, 0.15], "upright_yaw_id": "asset_yaw_0", "preplace_height_rule": "obstacle_top_plus_min_margin"},
    {"candidate_id": "p0_y1_h1", "stand_relative_xy_m": [0.00, 0.15], "upright_yaw_id": "asset_yaw_1", "preplace_height_rule": "facility_top_plus_extended_margin"},
    {"candidate_id": "p1_y0_h1", "stand_relative_xy_m": [-0.08, 0.13], "upright_yaw_id": "asset_yaw_0", "preplace_height_rule": "facility_top_plus_extended_margin"},
    {"candidate_id": "p1_y1_h0", "stand_relative_xy_m": [-0.08, 0.13], "upright_yaw_id": "asset_yaw_1", "preplace_height_rule": "obstacle_top_plus_min_margin"},
    {"candidate_id": "p2_y0_h0", "stand_relative_xy_m": [-0.12, 0.10], "upright_yaw_id": "asset_yaw_0", "preplace_height_rule": "obstacle_top_plus_min_margin"},
    {"candidate_id": "p2_y1_h1", "stand_relative_xy_m": [-0.12, 0.10], "upright_yaw_id": "asset_yaw_1", "preplace_height_rule": "facility_top_plus_extended_margin"},
)


def validate_f2_candidate_identity(candidate: Mapping[str, object]) -> None:
    if candidate.get("main_object") != "071_can/base1":
        raise ValueError("F2 v4 may not change the main object")
    if candidate.get("arm") != "left":
        raise ValueError("F2 v4 may not switch arms")
    if candidate.get("reference") != "074_displaystand/base3":
        raise ValueError("F2 v4 may not silently replace the stand")


def select_first_f2_verified_candidate(results: Sequence[Mapping[str, object]]) -> dict:
    expected_ids = [item["candidate_id"] for item in F2_POSE_CANDIDATES]
    actual_ids = [item.get("candidate_id") for item in results]
    if actual_ids != expected_ids[:len(actual_ids)] or len(results) > len(expected_ids):
        raise ValueError("F2 candidate results must be a fixed-order prefix of the preregistered six")
    planner_seeds = {item.get("planner_seed") for item in results}
    planner_start_states = {item.get("planner_start_state_sha256") for item in results}
    if results and (None in planner_seeds or len(planner_seeds) != 1):
        raise ValueError("F2 candidates must share one preregistered planner seed")
    if results and (None in planner_start_states or len(planner_start_states) != 1):
        raise ValueError("F2 candidates must share one planner start-state hash")
    selected = None
    evaluated = []
    for result in results:
        validate_f2_candidate_identity(result)
        checks = {
            "upright_axis_audited": result.get("upright_axis_audited") is True,
            "release_planner": result.get("release_planner_status") == "Success",
            "preplace_planner": result.get("preplace_planner_status") == "Success",
            "joint_limit_margin": result.get("joint_limit_margin_pass") is True,
            "carried_swept_geometry": result.get("carried_swept_geometry_pass") is True,
            "facility_distance": result.get("facility_distance_pass") is True,
        }
        item = dict(result)
        item["checks"] = checks
        item["verified"] = all(checks.values())
        evaluated.append(item)
        if selected is None and item["verified"]:
            selected = item
    exhausted = len(results) == len(expected_ids) and selected is None
    return {
        "pass": selected is not None,
        "selected": selected,
        "evaluated": evaluated,
        "terminal_if_exhausted": "f2_stand_layout_impact_review_v5" if exhausted else None,
    }


F3_RELEASE_SAMPLE_POINTS = (
    "before_release",
    "after_release_1",
    "after_release_5",
    "after_release_10",
    "after_release_25",
    "after_release_50",
    "after_release_125",
    "after_release_250",
    "after_rest",
)

F3_INITIAL_ANCHOR_REQUIREMENTS = {
    "bottle_footprint_inside_pad": True,
    "bottle_pad_contact_required": True,
    "linear_speed_mps_must_be_below_provisional_bound": True,
    "angular_speed_rps_must_be_below_provisional_bound": True,
    "stable_window_required_before_anchor": True,
}

F3_VERIFIER_INVARIANTS = {
    "position_threshold": "inherit_runtime_v2_without_relaxation",
    "orientation_threshold": "inherit_runtime_v2_without_relaxation",
    "post_release_dynamics_may_not_be_reclassified_as_transform_error": True,
}

F3_REQUIRED_SAMPLE_FIELDS = (
    "bottle_position_error_m",
    "bottle_orientation_error",
    "eef_tracking_error_m",
    "bottle_linear_speed_mps",
    "bottle_angular_speed_rps",
    "bottle_footprint_inside_pad",
    "bottle_pad_contact_count",
    "bottle_pad_contact_normal",
    "bottle_pad_contact_impulse",
    "selected_gripper_contact",
    "actual_gripper_joint_qpos",
)


def validate_f3_release_samples(samples: Mapping[str, Mapping[str, object]]) -> None:
    if tuple(samples) != F3_RELEASE_SAMPLE_POINTS:
        raise ValueError("F3 diagnostic sample points must use the preregistered order")
    for name, sample in samples.items():
        missing = [field for field in F3_REQUIRED_SAMPLE_FIELDS if field not in sample]
        if missing:
            raise ValueError(f"F3 sample {name} missing {missing}")


def classify_f3_release_dynamics(
    samples: Mapping[str, Mapping[str, object]],
    *,
    pre_release_position_tolerance_m: float,
    pre_release_orientation_tolerance: float,
) -> dict:
    validate_f3_release_samples(samples)
    before = samples["before_release"]
    before_accurate = (
        float(before["bottle_position_error_m"]) <= pre_release_position_tolerance_m
        and float(before["bottle_orientation_error"]) <= pre_release_orientation_tolerance
    )
    later = [samples[name] for name in F3_RELEASE_SAMPLE_POINTS[1:]]
    later_exceeds = any(
        float(item["bottle_position_error_m"]) > pre_release_position_tolerance_m
        or float(item["bottle_orientation_error"]) > pre_release_orientation_tolerance
        for item in later
    )
    if not before_accurate:
        classification = "pre_release_offset"
        correction_allowed = True
        next_gate = "one_deterministic_actor_to_eef_correction"
    elif later_exceeds:
        classification = "post_release_dynamics"
        correction_allowed = False
        next_gate = "pad_initial_pose_physics_impact_review"
    else:
        classification = "return_equivalence_holds"
        correction_allowed = False
        next_gate = "no_repair_needed"
    speeds = np.asarray([float(item["bottle_linear_speed_mps"]) for item in later], dtype=float)
    return {
        "classification": classification,
        "actor_to_eef_correction_allowed": correction_allowed,
        "next_gate": next_gate,
        "speed_convergence": {
            "initial_mps": float(speeds[0]),
            "final_mps": float(speeds[-1]),
            "net_decrease_mps": float(speeds[0] - speeds[-1]),
            "monotonic_nonincreasing": bool(np.all(np.diff(speeds) <= 1e-9)),
        },
    }


def minimum_f4_safe_actor_center_height(obstacle_top_z: Sequence[float], common_half_height_m: float, clearance_m: float) -> float:
    tops = np.asarray(obstacle_top_z, dtype=float).reshape(-1)
    if tops.size == 0 or common_half_height_m <= 0 or clearance_m <= 0:
        raise ValueError("F4 safe-height inputs must be non-empty and positive")
    return float(np.max(tops) + common_half_height_m + clearance_m)


F4_ROUTE_ORDER = ("route1_minimum_height_segmented", "route2_carry_neutral_fallback")


def f4_route_specs(safe_actor_center_z: float) -> list[dict]:
    return [
        {
            "route_id": F4_ROUTE_ORDER[0],
            "waypoints": ["source_vertical_to_safe_z", "center_high", "above_tray", "preplace", "release"],
            "safe_actor_center_z": float(safe_actor_center_z),
            "carry_orientation_rule": "preserve_audited_grasp_orientation",
            "changes_tray_pose": False,
        },
        {
            "route_id": F4_ROUTE_ORDER[1],
            "waypoints": ["source_to_carry_neutral", "center_high", "above_tray", "preplace", "release"],
            "safe_actor_center_z": float(safe_actor_center_z),
            "carry_orientation_rule": "audited_branch_neutral_carry_orientation",
            "changes_tray_pose": False,
        },
    ]


def adjudicate_f4_routes(route_results: Sequence[Mapping[str, object]]) -> dict:
    ids = [item.get("route_id") for item in route_results]
    if ids != list(F4_ROUTE_ORDER[:len(ids)]) or len(route_results) > 2:
        raise ValueError("F4 route results must follow the fixed Route-1/Route-2 order")
    for item in route_results:
        if item.get("changes_tray_pose") is not False:
            raise ValueError("F4 v3 routes may not change tray pose")
        if item.get("all_segment_endpoint_preflight_pass") not in (True, False):
            raise ValueError("every F4 route must report all segment endpoint preflights")
    selected = next((dict(item) for item in route_results if item.get("semantic_probe_pass") is True and item.get("all_segment_endpoint_preflight_pass") is True), None)
    if selected is not None and selected["route_id"] != ids[0]:
        previous = route_results[0]
        if previous.get("terminal_status") not in ("failed_planner", "failed_execution", "failed_verifier"):
            raise ValueError("Route 2 is allowed only after a terminal Route-1 failure")
    exhausted = len(route_results) == 2 and selected is None
    return {
        "pass": selected is not None,
        "selected": selected,
        "terminal_if_exhausted": "f4_tray_layout_impact_review_v4" if exhausted else None,
    }


RUNTIME_V3_BUDGET_PROPOSAL = {
    "status": "proposed_for_user_review",
    "approved": False,
    "frozen": False,
    "F1": {"execution_limit": 3, "planner_query_limit_per_branch": 12, "timeout_seconds_per_branch": 1200, "recovery": 0},
    "F2": {"pose_candidate_limit": 6, "execution_limit": 1, "planner_query_limit_total": 16, "timeout_seconds": 1200, "recovery": 0},
    "F3": {"diagnostic_execution_limit": 1, "conditional_correction_execution_limit": 1, "planner_query_limit_per_run": 16, "timeout_seconds_per_run": 1800, "recovery": 0},
    "F4": {"route_limit": 2, "execution_limit_per_route": 1, "planner_query_limit_per_route": 16, "timeout_seconds_per_route": 1800, "recovery": 0},
}
