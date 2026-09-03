"""Lift-anchored F3 V/H event-center implementation candidate."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from .canonical_artifact import canonical_hash_json
from .geometry import world_axis_offset_pose


IMPLEMENTATION_VERSION = "f3_lift_anchored_event_center_v1"
V_DISTANCE_M = 0.055
H_DISTANCE_M = 0.05
SEGMENT_NAMES = (
    "central_1",
    "V_plus",
    "V_minus",
    "central_2",
    "H_plus",
    "H_minus",
    "central_3",
)


def build_f3_lift_anchored_stage_b_targets_v1(
    stage_a_lift_pose: Any,
) -> list[dict[str, Any]]:
    lift = np.asarray(stage_a_lift_pose, dtype=np.float64).reshape(-1)
    if lift.shape != (7,) or not np.all(np.isfinite(lift)):
        raise ValueError("F3 lift-anchored center requires one finite pose7")
    central = lift.copy()
    values = (
        ("central_1", central),
        ("V_plus", world_axis_offset_pose(central, V_DISTANCE_M, axis=(0, 0, 1))),
        ("V_minus", world_axis_offset_pose(central, -V_DISTANCE_M, axis=(0, 0, 1))),
        ("central_2", central),
        ("H_plus", world_axis_offset_pose(central, H_DISTANCE_M, axis=(1, 0, 0))),
        ("H_minus", world_axis_offset_pose(central, -H_DISTANCE_M, axis=(1, 0, 0))),
        ("central_3", central),
    )
    return [
        {"segment_id": f"f3_lift_center_v1_{name}", "pose": pose.tolist()}
        for name, pose in values
    ]


def audit_f3_lift_anchored_stage_b_targets_v1(
    stage_a_lift_pose: Any,
    targets: list[Mapping[str, Any]],
) -> dict[str, Any]:
    lift = np.asarray(stage_a_lift_pose, dtype=np.float64).reshape(7)
    values = [np.asarray(item.get("pose"), dtype=np.float64).reshape(7) for item in targets]
    names = [str(item.get("segment_id", "")).rsplit("_", 2)[-2:] for item in targets]
    position = [item[:3] for item in values]
    checks = {
        "exact_segment_count": len(values) == 7,
        "first_target_equals_stage_a_lift": len(values) == 7
        and np.array_equal(values[0], lift),
        "all_orientations_equal_lift": len(values) == 7
        and all(np.array_equal(item[3:], lift[3:]) for item in values),
        "central_endpoints_equal": len(values) == 7
        and np.array_equal(values[0], values[3])
        and np.array_equal(values[0], values[6]),
        "V_is_table_z_only": len(values) == 7
        and np.allclose(position[1] - position[0], [0.0, 0.0, V_DISTANCE_M])
        and np.allclose(position[2] - position[0], [0.0, 0.0, -V_DISTANCE_M]),
        "H_is_table_x_only": len(values) == 7
        and np.allclose(position[4] - position[0], [H_DISTANCE_M, 0.0, 0.0])
        and np.allclose(position[5] - position[0], [-H_DISTANCE_M, 0.0, 0.0]),
    }
    result = {
        "schema_version": "cmf_f3_lift_anchored_stage_b_target_audit_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "stage_a_lift_pose": lift.tolist(),
        "stage_a_lift_pose_sha256": canonical_hash_json(lift.tolist()),
        "targets": [dict(item) for item in targets],
        "checks": checks,
        "pass": all(checks.values()),
        "scientific_programs_changed": False,
        "table_frame_axes_changed": False,
        "V_distance_m": V_DISTANCE_M,
        "H_distance_m": H_DISTANCE_M,
        "fixed_global_central_position_removed": True,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    result["receipt_sha256"] = canonical_hash_json(result)
    return result


def build_f3_planner_recovery_contract_v1() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_f3_planner_recovery_contract_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "stage_b_center_policy": "exact_stage_a_lift_pose",
        "candidate_policy": {
            "current_four_strata_are_terminal_evidence_not_rerunnable": True,
            "new_candidate_universe_requires_impact_review_and_freeze": True,
            "planner_assisted_rotation_choice_must_freeze_before_physical": True,
            "blind_seed_search": False,
        },
        "qualification": {
            "maximum_physical_candidates": 4,
            "one_attempt_per_candidate": True,
            "minimum_distinct_physical_successes": 2,
            "same_prefix_three_fresh_scene_no_suffix_only_after_physical_success": True,
            "automatic_retry": False,
        },
        "status": "IMPLEMENTED_CENTER_FIX_AWAITING_CANDIDATE_FREEZE_AND_GPU_AUTHORIZATION",
        "stage0_reopened": False,
        "stage1_authorized": False,
        "formal_data": False,
    }
    value["contract_sha256"] = canonical_hash_json(value)
    return value


__all__ = [
    "H_DISTANCE_M",
    "IMPLEMENTATION_VERSION",
    "SEGMENT_NAMES",
    "V_DISTANCE_M",
    "audit_f3_lift_anchored_stage_b_targets_v1",
    "build_f3_lift_anchored_stage_b_targets_v1",
    "build_f3_planner_recovery_contract_v1",
]
