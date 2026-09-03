"""Exact nonhistorical rotation-1 candidate proposal for F3 recovery."""

from __future__ import annotations

from typing import Any

from .canonical_artifact import canonical_hash_json
from .f3_final_pose_search_v3 import build_f3_final_pose_recipe_universe_v3


IMPLEMENTATION_VERSION = "f3_rotation1_lift_center_candidate_proposal_v1"
STRATA = (
    {
        "label": "bottle15-left-lower",
        "asset_model_id": 15,
        "arm": "left",
        "grasp_region": "lower_body",
        "old_recipe_id": "f3-final-pose-v3-r0002",
    },
    {
        "label": "bottle5-right-lower",
        "asset_model_id": 5,
        "arm": "right",
        "grasp_region": "lower_body",
        "old_recipe_id": "f3-final-pose-v3-r1442",
    },
    {
        "label": "bottle4-left-upper",
        "asset_model_id": 4,
        "arm": "left",
        "grasp_region": "upper_body",
        "old_recipe_id": "f3-final-pose-v3-r2162",
    },
    {
        "label": "bottle13-right-upper",
        "asset_model_id": 13,
        "arm": "right",
        "grasp_region": "upper_body",
        "old_recipe_id": "f3-final-pose-v3-r3602",
    },
)


def build_f3_rotation1_candidate_proposal_v1() -> dict[str, Any]:
    universe = build_f3_final_pose_recipe_universe_v3()
    selected = []
    for stratum in STRATA:
        matches = [
            recipe
            for recipe in universe["recipes"]
            if recipe["asset"]["model_id"] == stratum["asset_model_id"]
            and recipe["arm"] == stratum["arm"]
            and recipe["grasp_region"] == stratum["grasp_region"]
            and recipe["official_contact_point_id"] == 0
            and recipe["official_rotation_candidate_index"] == 1
            and recipe["pregrasp_distance_m"] == 0.09
        ]
        if len(matches) != 1:
            raise ValueError("F3 rotation1 stratum does not resolve exactly once")
        recipe = matches[0]
        selected.append(
            {
                **stratum,
                "new_recipe_id": recipe["recipe_id"],
                "new_recipe_sha256": recipe["recipe_sha256"],
                "official_contact_point_id": 0,
                "official_rotation_candidate_index": 1,
                "pregrasp_distance_m": 0.09,
                "old_rotation0_candidate_rerun": False,
            }
        )
    value = {
        "schema_version": "cmf_f3_rotation1_candidate_proposal_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "status": "PROPOSAL_NOT_AUTHORIZATION",
        "source_recipe_universe_sha256": universe["universe_sha256"],
        "candidate_order": selected,
        "stage_a_query_limit_per_candidate": 3,
        "lift_anchored_stage_b_query_limit_per_candidate": 7,
        "maximum_planner_queries": 40,
        "maximum_planner_scenes": 8,
        "physical_gate": {
            "maximum_candidate_executions": 4,
            "one_execution_per_candidate": True,
            "minimum_distinct_physical_successes": 2,
            "automatic_retry": False,
        },
        "conditional_no_suffix_diagnostic": {
            "allowed_only_after_minimum_physical_successes": 2,
            "same_prefix_fresh_scenes": 3,
            "maximum_invocations": 1,
            "suffix_execution_count": 0,
        },
        "scientific_programs_changed": False,
        "table_frame_axes_changed": False,
        "event_center_policy": "exact_stage_a_lift_pose",
        "V_distance_m": 0.055,
        "H_distance_m": 0.05,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage0_reopened": False,
        "stage1_authorized": False,
        "formal_data": False,
    }
    value["proposal_sha256"] = canonical_hash_json(value)
    return value


__all__ = [
    "IMPLEMENTATION_VERSION",
    "STRATA",
    "build_f3_rotation1_candidate_proposal_v1",
]
