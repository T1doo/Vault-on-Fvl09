"""Exact F2/F3/F4 planner qualification manifests for V2.3."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_hierarchical_template_search_v1 import (
    build_f2_hierarchical_template_search_v1,
)
from .f2_inside_control_search_v2 import (
    build_f2_geometry_certificate_v4,
    build_f2_grasp_recipe_universe_v2,
)
from .f3_final_pose_search_v3 import build_f3_final_pose_recipe_universe_v3
from .f4_hierarchical_template_search_v1 import (
    build_f4_hierarchical_template_search_v1,
    build_f4_stage_b_candidates_v1,
    select_f4_stage_a_source_v1,
)
from .f4_program_planner_integration_v2 import PROGRAMS
from .high_level_runtime_specs_v1 import build_f2_runtime_spec_v1


F2_CONTACT_IDS = tuple(range(16))
F2_ROTATION_INDICES = (0, 5)
F2_AXIAL_OFFSET_M = 0.0
F2_PREGRASP_DISTANCE_M = 0.09
F3_CONTACT_IDS = (0, 2, 4, 6)
F3_ROTATION_INDICES = (0, 5)
F3_PREGRASP_DISTANCE_M = 0.09


def _self_hashed(value: Mapping[str, Any], key: str, label: str) -> dict[str, Any]:
    result = canonical_jsonable(value)
    payload = dict(result)
    digest = payload.pop(key, None)
    if digest != canonical_hash_json(payload):
        raise ValueError(f"V2.3 {label} hash mismatch")
    return result


def build_f2_planner_panel_manifest_v1() -> dict[str, Any]:
    search = build_f2_hierarchical_template_search_v1()
    robust_pair = search["collapsed_pairs"][0]
    if (robust_pair["main_object_model_id"], robust_pair["plastic_box_model_id"]) != (0, 2):
        raise ValueError("F2 deterministic robust-margin pair changed")
    certificate = build_f2_geometry_certificate_v4(
        main_object_model_id=0, plastic_box_model_id=2
    )
    arm_candidates = {
        item["arm"]: item
        for item in search["inside_candidates"]
        if item["main_object_model_id"] == 0
        and item["plastic_box_model_id"] == 2
    }
    if set(arm_candidates) != {"left", "right"}:
        raise ValueError("F2 robust pair lacks both arm candidates")
    bindings = {
        arm: build_f2_runtime_spec_v1(
            arm_candidates[arm]["candidate_id"], purpose="f2_stage_a_planner"
        )["f2_asset_layout_binding_v3"]
        for arm in ("left", "right")
    }
    universe = build_f2_grasp_recipe_universe_v2(
        [
            {
                "main_object_model_id": 0,
                "plastic_box_model_id": 2,
                "official_can_contact_point_count": 16,
                "geometry_certificate_sha256": certificate["certificate_sha256"],
            }
        ]
    )
    recipes = [
        item
        for item in universe["recipes"]
        if item["official_contact_point_id"] in F2_CONTACT_IDS
        and item["official_rotation_candidate_index"] in F2_ROTATION_INDICES
        and item["axial_grasp_offset_m"] == F2_AXIAL_OFFSET_M
        and item["pregrasp_distance_m"] == F2_PREGRASP_DISTANCE_M
    ]
    if len(recipes) != 64:
        raise AssertionError("F2 exact planner panel must contain 64 recipes")
    ordered = []
    for rank, recipe in enumerate(recipes, start=1):
        item = {
            "panel_rank": rank,
            "recipe_id": recipe["recipe_id"],
            "recipe_sha256": recipe["recipe_sha256"],
            "arm": recipe["arm"],
            "contact_point_id": recipe["official_contact_point_id"],
            "rotation_index": recipe["official_rotation_candidate_index"],
            "axial_grasp_offset_m": recipe["axial_grasp_offset_m"],
            "pregrasp_distance_m": recipe["pregrasp_distance_m"],
            "binding_sha256": bindings[recipe["arm"]]["binding_sha256"],
            "recipe": recipe,
        }
        item["entry_sha256"] = canonical_hash_json(item)
        ordered.append(item)
    value = {
        "schema_version": "cmf_f2_planner_panel_manifest_v1",
        "selection_rule": (
            "max strict_inside_margin, then max contact count, then max workspace "
            "margin, then ascending can_id/box_id"
        ),
        "selected_can_id": 0,
        "selected_box_id": 2,
        "selected_pair_sha256": robust_pair["pair_sha256"],
        "strict_inside_margin_m": robust_pair["strict_inside_margin_m"],
        "certificate": certificate,
        "certificate_sha256": certificate["certificate_sha256"],
        "bindings_by_arm": bindings,
        "binding_sha256s_by_arm": {
            arm: bindings[arm]["binding_sha256"] for arm in bindings
        },
        "contact_ids": list(F2_CONTACT_IDS),
        "rotation_indices": list(F2_ROTATION_INDICES),
        "axial_grasp_offset_m": F2_AXIAL_OFFSET_M,
        "pregrasp_distance_m": F2_PREGRASP_DISTANCE_M,
        "ordered_recipes": ordered,
        "ordered_recipe_ids": [item["recipe_id"] for item in ordered],
        "ordered_recipe_sha256s": [item["recipe_sha256"] for item in ordered],
        "recipe_count": 64,
        "planner_query_limit": 192,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["panel_sha256"] = canonical_hash_json(value)
    return value


def _f3_scene_binding(recipe: Mapping[str, Any]) -> dict[str, Any]:
    source_x = -0.18 if recipe["arm"] == "left" else 0.18
    bottle_pose = [source_x, -0.06, 0.785, 0.0, 0.0, 1.0, 0.0]
    layout = {
        "bottle_pose": bottle_pose,
        "original_pad_pose": [source_x, -0.06, 0.745, 1.0, 0.0, 0.0, 0.0],
        "central_marker_pose": [0.0, -0.05, 0.95, 1.0, 0.0, 0.0, 0.0],
        "asset": recipe["asset"],
    }
    scene_spec = {
        "family": "F3",
        "arm": recipe["arm"],
        "layout": layout,
        "generator": "F3Scene.load_actors exact deterministic layout",
    }
    robot_config = {
        "robot": "aloha-agilex",
        "planner_start_state_dtype": "float32",
        "selected_arm": recipe["arm"],
    }
    return {
        "scene_spec_sha256": canonical_hash_json(scene_spec),
        "scene_layout_sha256": canonical_hash_json(layout),
        "bottle_asset_sha256": recipe["asset_record_sha256"],
        "bottle_actor_pose_sha256": canonical_hash_json(bottle_pose),
        "robot_config_sha256": canonical_hash_json(robot_config),
    }


def build_f3_stage_a_panel_manifest_v1() -> dict[str, Any]:
    universe = build_f3_final_pose_recipe_universe_v3()
    recipes = [
        item
        for item in universe["recipes"]
        if item["official_contact_point_id"] in F3_CONTACT_IDS
        and item["official_rotation_candidate_index"] in F3_ROTATION_INDICES
        and item["pregrasp_distance_m"] == F3_PREGRASP_DISTANCE_M
    ]
    if len(recipes) != 128:
        raise AssertionError("F3 exact Stage-A panel must contain 128 recipes")
    ordered = []
    for rank, recipe in enumerate(recipes, start=1):
        item = {
            "panel_rank": rank,
            "recipe_id": recipe["recipe_id"],
            "recipe_sha256": recipe["recipe_sha256"],
            "stratum": {
                "asset_model_id": recipe["asset"]["model_id"],
                "arm": recipe["arm"],
                "region": recipe["grasp_region"],
            },
            "contact_point_id": recipe["official_contact_point_id"],
            "rotation_index": recipe["official_rotation_candidate_index"],
            "scene_binding": _f3_scene_binding(recipe),
            "recipe": recipe,
        }
        item["entry_sha256"] = canonical_hash_json(item)
        ordered.append(item)
    value = {
        "schema_version": "cmf_f3_stage_a_panel_manifest_v1",
        "source_universe_sha256": universe["universe_sha256"],
        "asset_model_ids": universe["selected_asset_model_ids"],
        "arms": ["left", "right"],
        "regions": ["lower_body", "upper_body"],
        "geometry_diverse_contact_ids": list(F3_CONTACT_IDS),
        "frozen_rotation_indices": list(F3_ROTATION_INDICES),
        "pregrasp_distance_m": F3_PREGRASP_DISTANCE_M,
        "ordered_recipes": ordered,
        "ordered_recipe_ids": [item["recipe_id"] for item in ordered],
        "ordered_recipe_sha256s": [item["recipe_sha256"] for item in ordered],
        "recipe_count": 128,
        "stage_a_planner_query_limit": 384,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["panel_sha256"] = canonical_hash_json(value)
    return value


def build_f3_stage_b_selection_policy_v1(
    panel: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source = build_f3_stage_a_panel_manifest_v1() if panel is None else _self_hashed(
        panel, "panel_sha256", "F3 Stage-A panel"
    )
    strata = []
    for asset_id in source["asset_model_ids"]:
        for arm in source["arms"]:
            for region in source["regions"]:
                strata.append(
                    {"asset_model_id": asset_id, "arm": arm, "region": region}
                )
    value = {
        "schema_version": "cmf_f3_stage_b_selection_policy_v1",
        "stage_a_panel_sha256": source["panel_sha256"],
        "ordered_strata": strata,
        "stratum_count": 16,
        "selection_per_stratum": "lowest panel-rank Stage-A pass, at most one",
        "empty_stratum_fill_allowed": False,
        "maximum_stage_b_survivors": 16,
        "stage_b_queries_per_survivor": 7,
        "stage_b_planner_query_limit": 112,
        "physical_execution_authorized": False,
    }
    value["policy_sha256"] = canonical_hash_json(value)
    return value


def build_f4_program_panel_manifest_v1() -> dict[str, Any]:
    contract = build_f4_hierarchical_template_search_v1()
    gates = contract["stage_a_required_gates"]
    synthetic_cpu_terminal = select_f4_stage_a_source_v1(
        contract,
        [
            {
                "candidate_id": item["candidate_id"],
                "candidate_sha256": item["candidate_sha256"],
                "checks": {gate: item["rank"] == 1 for gate in gates},
                "cleanup_safety_pass": True,
                "orphan_process_count": 0,
            }
            for item in contract["stage_a_candidates"]
        ],
    )
    source = synthetic_cpu_terminal["selected_source_grasp"]
    stage_b = build_f4_stage_b_candidates_v1(contract, synthetic_cpu_terminal)
    jobs = []
    for candidate in stage_b["candidates"]:
        for program_id, order in PROGRAMS.items():
            item = {
                "candidate_rank": candidate["rank"],
                "candidate_id": candidate["candidate_id"],
                "candidate_sha256": candidate["candidate_sha256"],
                "program_id": program_id,
                "program_order": list(order),
                "source_candidate_sha256": source["candidate_sha256"],
            }
            item["job_sha256"] = canonical_hash_json(item)
            jobs.append(item)
    value = {
        "schema_version": "cmf_f4_program_panel_manifest_v1",
        "source_candidate": source,
        "source_candidate_sha256": source["candidate_sha256"],
        "candidates": stage_b["candidates"],
        "candidate_count": 8,
        "candidate_rank_order": [item["candidate_id"] for item in stage_b["candidates"]],
        "program_order_within_candidate": list(PROGRAMS),
        "ordered_jobs": jobs,
        "job_count": 24,
        "queries_per_job": 30,
        "maximum_planner_queries": 720,
        "selection_rule": "lowest candidate rank with ABC then ACB then BAC all pass",
        "stop_issuing_higher_rank_after_first_complete_pass": True,
        "synthetic_stage_a_used_only_to_rebuild_cpu_hv2_candidates": True,
        "stage_a_planner_pass_claimed": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["panel_sha256"] = canonical_hash_json(value)
    return value


def validate_panel_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    schema = value.get("schema_version")
    key = "policy_sha256" if schema == "cmf_f3_stage_b_selection_policy_v1" else "panel_sha256"
    return _self_hashed(value, key, str(schema))


__all__ = [
    "build_f2_planner_panel_manifest_v1",
    "build_f3_stage_a_panel_manifest_v1",
    "build_f3_stage_b_selection_policy_v1",
    "build_f4_program_panel_manifest_v1",
    "validate_panel_manifest",
]
