"""Fail-closed F2 development-root proposal from the passed top-contact micro Gate."""

from __future__ import annotations

from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_inside_control_search_v2 import build_f2_grasp_recipe_universe_v2
from .f2_recovery_planner_manifest_v1 import build_f2_recovery_planner_manifest_v1


IMPLEMENTATION_VERSION = "f2_top_contact_development_root_proposal_v1"
SOURCE_GATE_TERMINAL_RECEIPT_SHA256 = (
    "72d206826288b432d3170397697b26076384e6a3e9ad1515c1fc75f7a9857874"
)
SELECTED = {
    "main_object_model_id": 0,
    "plastic_box_model_id": 2,
    "electronic_scale_model_id": 0,
    "beside_reference_model_id": 0,
    "arm": "left",
    "official_contact_point_id": 8,
    "official_rotation_candidate_index": 0,
    "pregrasp_distance_m": 0.09,
    "axial_grasp_offset_m": 0.0,
    "recipe_id": "f2-final-grasp-v2-r000725",
    "recipe_sha256": "f7270daf416afb1b84e230be7dd2418ac0e5a31d2461943da3bd77c6777cfe5e",
    "source_stage_a_spec_sha256": (
        "5cc8e10a0b4e8fabe0a835c352ba0b2c81ea6c5c6c841dd38a83531ebfdcaed4"
    ),
    "source_stage_a_terminal_receipt_sha256": (
        "8325086ad32dc1c2f7dc41602cc455be0da6737d7b9318776623ad7a47e4db43"
    ),
    "source_pose_freeze_sha256": (
        "8f45dfc03ce1b31554054286dcb5c076c68083b568898ea4bebf53c15288ce0f"
    ),
    "source_physical_scene_receipt_sha256": (
        "c3ac8155fcff909383c2ed72fe178edc10d4ca66a541a3a9b5d5f765f991bc47"
    ),
    "preclose_tracking_gate_pass": True,
    "post_lift_grasp_transform_gate_pass": True,
}


def _resolve_selected_recipe() -> dict[str, Any]:
    panel = build_f2_recovery_planner_manifest_v1()
    universe = build_f2_grasp_recipe_universe_v2(
        [
            {
                "main_object_model_id": 0,
                "plastic_box_model_id": 2,
                "official_can_contact_point_count": 16,
                "geometry_certificate_sha256": panel["certificates_by_pair"][
                    "can0-box2"
                ]["certificate_sha256"],
            }
        ]
    )
    matches = [
        recipe
        for recipe in universe["recipes"]
        if recipe["recipe_id"] == SELECTED["recipe_id"]
        and recipe["recipe_sha256"] == SELECTED["recipe_sha256"]
        and recipe["arm"] == SELECTED["arm"]
        and recipe["official_contact_point_id"]
        == SELECTED["official_contact_point_id"]
        and recipe["official_rotation_candidate_index"]
        == SELECTED["official_rotation_candidate_index"]
        and recipe["pregrasp_distance_m"] == SELECTED["pregrasp_distance_m"]
        and recipe["axial_grasp_offset_m"] == SELECTED["axial_grasp_offset_m"]
    ]
    if len(matches) != 1:
        raise ValueError("selected F2 top-contact recipe does not resolve exactly once")
    return matches[0]


def build_f2_top_contact_development_root_proposal_v1() -> dict[str, Any]:
    recipe = _resolve_selected_recipe()
    value = {
        "schema_version": "cmf_f2_top_contact_development_root_proposal_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "source_gate_terminal_receipt_sha256": SOURCE_GATE_TERMINAL_RECEIPT_SHA256,
        "selected_candidate": {**SELECTED, "full_recipe": recipe},
        "candidate_selection_rule": (
            "lexicographically first of the two distinct top-contact physical "
            "micro successes; left arm matches the frozen F2 family arm"
        ),
        "program_ids": ["F2-inside", "F2-on", "F2-beside"],
        "same_current_and_anchor_required": True,
        "canonical_prefix": {
            "arm": "left",
            "exact_frozen_pregrasp_and_grasp": True,
            "close_forbidden_above_position_error_m": 0.005,
            "close_forbidden_above_orientation_error_rad": 0.05,
            "lift_distance_m": 0.12,
            "selected_contact_identity_and_continuity_required": True,
            "grasp_transform_translation_atol_m": 0.005,
            "grasp_transform_orientation_atol_rad": 0.05,
        },
        "suffixes": {
            "reuse_existing_inside_on_beside_programs": True,
            "reuse_existing_targets_thresholds_and_verifiers": True,
            "inside_release_safety_gate_unchanged": True,
            "fallback": False,
        },
        "budget": {
            "root_invocation_cap": 1,
            "canonical_prefix_planner_query_cap": 3,
            "suffix_planner_query_cap_per_program": 24,
            "aggregate_planner_query_cap": 75,
            "fresh_scene_cap": 8,
            "robot_action_scene_cap": 4,
            "branch_execution_cap": 3,
            "raw_trajectory_cap": 3,
            "debug_video_cap": 3,
            "accepted_development_root_cap": 1,
            "accepted_development_trajectory_cap": 3,
            "formal_trajectory_cap": 0,
            "timeout_seconds": 28800,
        },
        "root_atomic_acceptance": (
            "accept only if all three branches, receipts, family verifiers, "
            "same-current, same-anchor, prefix replay, cleanup and orphan audit pass"
        ),
        "partial_success_enters_denominator": False,
        "automatic_retry": False,
        "second_root": False,
        "scientific_family_contract_changed": False,
        "candidate_universe_changed": True,
        "impact_review_required": True,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage0_reopened": False,
        "stage1_authorized": False,
        "formal_data": False,
    }
    value["proposal_sha256"] = canonical_hash_json(value)
    return value


def validate_f2_top_contact_development_root_proposal_v1(
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    value = canonical_jsonable(proposal)
    expected = build_f2_top_contact_development_root_proposal_v1()
    checks = {
        "canonical_rebuild": value == expected,
        "proposal_only": value.get("status") == "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "exact_three_programs": value.get("program_ids")
        == ["F2-inside", "F2-on", "F2-beside"],
        "one_root": value.get("budget", {}).get("root_invocation_cap") == 1,
        "formal_zero": value.get("budget", {}).get("formal_trajectory_cap") == 0,
        "gpu_false": value.get("gpu_execution_authorized") is False,
        "stage1_false": value.get("stage1_authorized") is False,
    }
    result = {
        "schema_version": "cmf_f2_top_contact_development_root_validation_v1",
        "proposal_sha256": value.get("proposal_sha256"),
        "checks": checks,
        "pass": all(checks.values()),
        "executable": False,
    }
    result["validation_sha256"] = canonical_hash_json(result)
    return result


__all__ = [
    "IMPLEMENTATION_VERSION",
    "SELECTED",
    "build_f2_top_contact_development_root_proposal_v1",
    "validate_f2_top_contact_development_root_proposal_v1",
]

