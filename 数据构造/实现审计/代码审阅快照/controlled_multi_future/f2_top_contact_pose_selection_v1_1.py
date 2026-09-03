"""Exact pre-authorization proposal for F2 top-contact grasp recovery."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_precontact_tracking_recovery_v1 import (
    ASSET_ARM_ORDER,
    ORIENTATION_ATOL_RAD,
    POSITION_ATOL_M,
)


IMPLEMENTATION_VERSION = "f2_top_contact_pose_selection_v1_1"
TOP_CONTACT_IDS = tuple(range(8, 16))
ROTATION_INDICES = tuple(range(10))
HISTORICAL_FAILED_TUPLE = {
    "official_contact_point_id": 0,
    "official_rotation_candidate_index": 0,
    "pregrasp_distance_m": 0.09,
    "axial_grasp_offset_m": 0.0,
}


def audit_f2_top_contact_asset_metadata_v1_1(
    model_data: Mapping[str, Any],
    *,
    model_id: int,
) -> dict[str, Any]:
    value = canonical_jsonable(model_data)
    poses = value.get("contact_points_pose")
    groups = value.get("contact_points_group")
    checks = {
        "sixteen_or_more_contact_poses": isinstance(poses, list)
        and len(poses) >= 16,
        "exact_top_contact_group": isinstance(groups, list)
        and len(groups) >= 2
        and groups[1] == list(TOP_CONTACT_IDS),
        "all_top_contact_poses_are_finite_4x4": isinstance(poses, list)
        and len(poses) >= 16
        and all(
            np.asarray(poses[index], dtype=np.float64).shape == (4, 4)
            and np.all(np.isfinite(np.asarray(poses[index], dtype=np.float64)))
            for index in TOP_CONTACT_IDS
        ),
    }
    result = {
        "schema_version": "cmf_f2_top_contact_asset_metadata_audit_v1_1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "model_id": int(model_id),
        "top_contact_ids": list(TOP_CONTACT_IDS),
        "checks": checks,
        "pass": all(checks.values()),
    }
    result["receipt_sha256"] = canonical_hash_json(result)
    return result


def build_f2_top_contact_selection_proposal_v1_1() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_f2_top_contact_selection_proposal_v1_1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "status": "PROPOSAL_NOT_AUTHORIZATION",
        "scientific_family_contract_changed": False,
        "program_ids": ["F2-inside", "F2-on", "F2-beside"],
        "strata": [
            {
                "main_object_model_id": can,
                "plastic_box_model_id": box,
                "arm": arm,
                "top_contact_ids_in_order": list(TOP_CONTACT_IDS),
                "rotation_indices_in_order": list(ROTATION_INDICES),
                "historical_side_contact_tuple_excluded": HISTORICAL_FAILED_TUPLE,
            }
            for can, box, arm in ASSET_ARM_ORDER
        ],
        "selection": {
            "scene_layout": "unchanged_v5_layout_to_isolate_grasp_policy",
            "official_top_contact_group_only": True,
            "per_contact_one_ten_rotation_planner_batch": True,
            "maximum_batch_calls_per_stratum": len(TOP_CONTACT_IDS),
            "rank_order": "contact_id_then_rotation_index",
            "select_lowest_planner_success": True,
            "selected_pose_frozen_before_chained_stage_a": True,
            "selected_stage_a_segments": ["pregrasp", "grasp", "25mm_lift"],
            "no_fallback_after_selected_stage_a_failure": True,
            "all_failed_batch_and_chain_receipts_retained": True,
        },
        "planner_budget": {
            "selection_batch_calls_per_stratum": 8,
            "selected_chained_queries_per_stratum": 3,
            "maximum_per_stratum": 11,
            "maximum_four_strata": 44,
        },
        "physical_gate": {
            "maximum_candidates": 4,
            "one_attempt_per_stratum": True,
            "preclose_tracking_position_atol_m": POSITION_ATOL_M,
            "preclose_tracking_orientation_atol_rad": ORIENTATION_ATOL_RAD,
            "close_forbidden_until_tracking_pass": True,
            "insertion_forbidden_until_tracking_contact_and_lift_pass": True,
            "minimum_distinct_successes_to_freeze": 2,
            "stop_after_two_consecutive_same_failure_categories": True,
        },
        "automatic_retry": False,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage0_reopened": False,
        "stage1_authorized": False,
        "formal_data": False,
    }
    value["proposal_sha256"] = canonical_hash_json(value)
    return value


__all__ = [
    "HISTORICAL_FAILED_TUPLE",
    "IMPLEMENTATION_VERSION",
    "ROTATION_INDICES",
    "TOP_CONTACT_IDS",
    "audit_f2_top_contact_asset_metadata_v1_1",
    "build_f2_top_contact_selection_proposal_v1_1",
]
