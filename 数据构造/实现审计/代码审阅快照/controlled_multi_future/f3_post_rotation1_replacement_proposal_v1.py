"""Fail-closed F3 replacements derived from the post-rotation1 CPU geometry audit."""

from __future__ import annotations

from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f3_final_pose_search_v3 import build_f3_final_pose_recipe_universe_v3


IMPLEMENTATION_VERSION = "f3_post_rotation1_centralized_replacement_proposal_v1"
SOURCE_GATE_TERMINAL_RECEIPT_SHA256 = (
    "a438128e719a2fca678154673767d8459e53c291b4abd5d1434300121593bbb8"
)
RETAINED_SURVIVOR = {
    "label": "bottle15-left-lower",
    "recipe_id": "f3-final-pose-v3-r0005",
    "recipe_sha256": "3638a9e93f5101b1e7a9370fe7c4735c5a1a062e890d7ac66d47f6f182cf333f",
    "stage_a_pass": True,
    "lift_centered_stage_b_pass": True,
    "planner_rerun_authorized": False,
}
REPLACEMENTS = (
    {
        "replaces": "bottle5-right-lower-r1445",
        "asset_model_id": 5,
        "arm": "right",
        "grasp_region": "lower_body",
        "contact_point_id": 2,
        "rotation_index": 1,
        "recipe_id": "f3-final-pose-v3-r1505",
        "recipe_sha256": "88f1c0bcb521d4fc7e9b1e64b24d94f1c7d81f1703fba19cd3f622d74c591c49",
        "failed_pregrasp_xyz_m": [0.3884232591, -0.0053896467, 0.7949262263],
        "proposed_pregrasp_xyz_m": [
            -0.029364682263148617,
            -0.00815821148505302,
            0.7855751946722513,
        ],
        "source_failure": "FINETUNE_TRAJOPT_FAIL",
    },
    {
        "replaces": "bottle4-left-upper-r2165",
        "asset_model_id": 4,
        "arm": "left",
        "grasp_region": "upper_body",
        "contact_point_id": 0,
        "rotation_index": 6,
        "recipe_id": "f3-final-pose-v3-r2180",
        "recipe_sha256": "176bc2a145a17bf13a70ec365ed144fefcb4689a6eb4379b6d8db0645f1cefb1",
        "failed_pregrasp_xyz_m": [0.0287962503, 0.1002881731, 0.7841794609],
        "proposed_pregrasp_xyz_m": [
            -0.006833898749067341,
            0.0026786209706683994,
            0.7838881406631131,
        ],
        "source_failure": "IK_FAIL",
    },
    {
        "replaces": "bottle13-right-upper-r3605",
        "asset_model_id": 13,
        "arm": "right",
        "grasp_region": "upper_body",
        "contact_point_id": 2,
        "rotation_index": 5,
        "recipe_id": "f3-final-pose-v3-r3677",
        "recipe_sha256": "3d945ce11eef1ba911621dd14238ad0eb7d91e167c6aa61a8de861cca18bde44",
        "failed_pregrasp_xyz_m": [0.3819819242, 0.0781269552, 0.8136233195],
        "proposed_pregrasp_xyz_m": [
            -0.007234217233118068,
            -0.001372276920895102,
            0.7571851244372944,
        ],
        "source_failure": "FINETUNE_TRAJOPT_FAIL",
    },
)


def build_f3_post_rotation1_replacement_proposal_v1() -> dict[str, Any]:
    universe = build_f3_final_pose_recipe_universe_v3()
    resolved = []
    for proposed in REPLACEMENTS:
        matches = [
            recipe
            for recipe in universe["recipes"]
            if recipe["recipe_sha256"] == proposed["recipe_sha256"]
            and recipe["recipe_id"] == proposed["recipe_id"]
            and recipe["asset"]["model_id"] == proposed["asset_model_id"]
            and recipe["arm"] == proposed["arm"]
            and recipe["grasp_region"] == proposed["grasp_region"]
            and recipe["official_contact_point_id"] == proposed["contact_point_id"]
            and recipe["official_rotation_candidate_index"]
            == proposed["rotation_index"]
            and recipe["pregrasp_distance_m"] == 0.09
        ]
        if len(matches) != 1:
            raise ValueError("F3 post-rotation1 replacement does not resolve exactly once")
        resolved.append({**proposed, "full_recipe": matches[0]})
    value = {
        "schema_version": "cmf_f3_post_rotation1_replacement_proposal_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "source_gate_terminal_receipt_sha256": SOURCE_GATE_TERMINAL_RECEIPT_SHA256,
        "retained_prior_survivor": RETAINED_SURVIVOR,
        "replacement_candidates": resolved,
        "selection_basis": {
            "method": (
                "CPU reconstruction of official contact frames and all ten "
                "rotate_along_axis poses, followed by deterministic minimum "
                "|x|+|y| pregrasp centrality within each failed stratum"
            ),
            "planner_or_ik_success_claimed": False,
            "physical_success_claimed": False,
            "old_failed_rotation1_rerun": False,
        },
        "bounded_gate": {
            "stage_a_query_cap": 9,
            "lift_centered_stage_b_query_cap": 21,
            "total_planner_query_cap": 30,
            "planner_scene_cap": 6,
            "minimum_new_survivors_before_physical": 1,
            "retained_plus_new_minimum_survivors": 2,
            "physical_candidate_cap": 4,
            "physical_scene_cap": 4,
            "conditional_no_suffix_scene_cap": 3,
            "no_suffix_only_after_two_physical_successes": True,
            "automatic_retry": False,
            "fallback": False,
        },
        "scientific_programs_changed": False,
        "table_frame_axes_changed": False,
        "event_center_policy": "exact_stage_a_lift_pose",
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


def validate_f3_post_rotation1_replacement_proposal_v1(
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    value = canonical_jsonable(proposal)
    expected = build_f3_post_rotation1_replacement_proposal_v1()
    checks = {
        "canonical_rebuild": value == expected,
        "proposal_only": value.get("status") == "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "three_replacements": len(value.get("replacement_candidates", [])) == 3,
        "retained_survivor_not_rerun": value.get("retained_prior_survivor", {}).get(
            "planner_rerun_authorized"
        )
        is False,
        "gpu_false": value.get("gpu_execution_authorized") is False,
        "stage1_false": value.get("stage1_authorized") is False,
    }
    result = {
        "schema_version": "cmf_f3_post_rotation1_replacement_validation_v1",
        "proposal_sha256": value.get("proposal_sha256"),
        "checks": checks,
        "pass": all(checks.values()),
        "executable": False,
    }
    result["validation_sha256"] = canonical_hash_json(result)
    return result


__all__ = [
    "IMPLEMENTATION_VERSION",
    "REPLACEMENTS",
    "RETAINED_SURVIVOR",
    "build_f3_post_rotation1_replacement_proposal_v1",
    "validate_f3_post_rotation1_replacement_proposal_v1",
]
