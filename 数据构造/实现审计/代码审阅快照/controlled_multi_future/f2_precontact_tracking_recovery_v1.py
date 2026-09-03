"""Evidence-driven F2 pre-contact tracking recovery contract."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from .canonical_artifact import canonical_hash_json, canonical_jsonable


IMPLEMENTATION_VERSION = "f2_precontact_tracking_recovery_v1"
POSITION_ATOL_M = 0.005
ORIENTATION_ATOL_RAD = 0.05
ASSET_ARM_ORDER = (
    (0, 2, "left"),
    (0, 2, "right"),
    (5, 8, "left"),
    (5, 8, "right"),
)


def audit_f2_preclose_tracking_gate_v1(
    approach_execution_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = [canonical_jsonable(item) for item in approach_execution_receipts]
    expected = ["f2_v2_pregrasp", "f2_v2_grasp"]
    checks = {
        "exact_pregrasp_grasp_order": [
            item.get("segment_id") for item in rows
        ]
        == expected,
        "planner_status_success": len(rows) == 2
        and all(item.get("planner_status") == "Success" for item in rows),
        "position_tracking": len(rows) == 2
        and all(
            float(item.get("tracking_position_error_m", np.inf))
            <= POSITION_ATOL_M
            for item in rows
        ),
        "orientation_tracking": len(rows) == 2
        and all(
            float(item.get("tracking_orientation_error_rad", np.inf))
            <= ORIENTATION_ATOL_RAD
            for item in rows
        ),
    }
    result = {
        "schema_version": "cmf_f2_preclose_tracking_gate_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "thresholds": {
            "position_atol_m": POSITION_ATOL_M,
            "orientation_atol_rad": ORIENTATION_ATOL_RAD,
        },
        "approach_execution_receipts": rows,
        "checks": checks,
        "pass": all(checks.values()),
        "close_gripper_allowed": all(checks.values()),
        "failure_category": None
        if all(checks.values())
        else "PRECONTACT_ARM_TRACKING_FAILURE",
    }
    result["receipt_sha256"] = canonical_hash_json(result)
    return result


def build_f2_grasp_redesign_contract_v1() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_f2_grasp_redesign_contract_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scientific_family_contract_changed": False,
        "program_ids": ["F2-inside", "F2-on", "F2-beside"],
        "asset_arm_order": [
            {
                "main_object_model_id": can,
                "plastic_box_model_id": box,
                "arm": arm,
            }
            for can, box, arm in ASSET_ARM_ORDER
        ],
        "target_construction": {
            "policy": "planner_assisted_official_grasp_candidates_then_exact_pose_freeze",
            "side_contact_rotation0_only": False,
            "candidate_pose_freeze_before_physical": True,
            "layout_may_shift_only_through_new_versioned_scene_spec": True,
            "inside_suffix_or_release_tuning_before_grasp_pass": False,
        },
        "physical_sequence": [
            "execute_pregrasp",
            "tracking_gate_before_grasp",
            "execute_grasp",
            "tracking_gate_before_close",
            "close",
            "contact_identity_and_continuity_gate",
            "25mm_micro_lift",
            "post_lift_transform_gate",
            "controlled_insertion_only_after_all_grasp_gates",
        ],
        "limits": {
            "maximum_physical_candidates": 4,
            "one_attempt_per_asset_arm": True,
            "stop_after_two_consecutive_same_failure_categories": True,
            "minimum_distinct_successes_to_freeze": 2,
            "automatic_retry": False,
        },
        "status": "IMPLEMENTED_CONTRACT_AWAITING_NEW_GPU_AUTHORIZATION",
        "stage0_reopened": False,
        "stage1_authorized": False,
        "formal_data": False,
    }
    value["contract_sha256"] = canonical_hash_json(value)
    return value


__all__ = [
    "ASSET_ARM_ORDER",
    "IMPLEMENTATION_VERSION",
    "ORIENTATION_ATOL_RAD",
    "POSITION_ATOL_M",
    "audit_f2_preclose_tracking_gate_v1",
    "build_f2_grasp_redesign_contract_v1",
]
