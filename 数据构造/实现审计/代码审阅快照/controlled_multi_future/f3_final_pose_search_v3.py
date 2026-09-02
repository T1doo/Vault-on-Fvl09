"""CPU-only F3 final-pose recipe universe and qualification binding.

The unsafe V2 order was planner selection followed by a 36--38 mm region
translation.  V3 freezes the translated pose first.  A later planner receipt
is valid only when its exact inputs match those final pose hashes.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

import numpy as np

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f3_asset_grasp_qualification_v2 import (
    build_f3_asset_grasp_qualification_v2,
)
from .geometry import pose_matrix, world_axis_offset_pose


SCHEMA_VERSION = "cmf_f3_final_pose_search_v3"
IMPLEMENTATION_VERSION = "controlled_multi_future_high_level_generation_repair_v2_0"
ARMS = ("left", "right")
REGIONS = ("lower_body", "upper_body")
REGION_FRACTIONS = {"lower_body": -0.15, "upper_body": 0.15}
OFFICIAL_CONTACT_POINT_IDS = tuple(range(8))
OFFICIAL_ROTATION_INDICES = tuple(range(10))
PREGRASP_DISTANCES_M = (0.06, 0.09, 0.12)
TARGET_DISTANCE_M = 0.0
FINAL_LIFT_DISTANCE_M = 0.10
EXPECTED_RECIPE_COUNT = 3840


def _pose7(value: Sequence[float], label: str) -> np.ndarray:
    pose = np.asarray(value, dtype=np.float64).reshape(-1)
    if pose.shape != (7,) or not np.all(np.isfinite(pose)):
        raise ValueError(f"{label} must be one finite pose7")
    norm = float(np.linalg.norm(pose[3:]))
    if norm <= 1e-12:
        raise ValueError(f"{label} quaternion norm must be positive")
    pose = pose.copy()
    pose[3:] /= norm
    return pose


def build_f3_final_pose_recipe_universe_v3() -> dict[str, Any]:
    old = build_f3_asset_grasp_qualification_v2()
    assets = old["selected_assets"]
    recipes = []
    for asset in assets:
        if int(asset["contact_point_count"]) < len(OFFICIAL_CONTACT_POINT_IDS):
            raise ValueError("selected F3 asset lacks the frozen eight contacts")
        for arm in ARMS:
            for region in REGIONS:
                for contact_id in OFFICIAL_CONTACT_POINT_IDS:
                    for rotation_index in OFFICIAL_ROTATION_INDICES:
                        for pregrasp_distance in PREGRASP_DISTANCES_M:
                            rank = len(recipes) + 1
                            fraction = REGION_FRACTIONS[region]
                            recipe = {
                                "rank": rank,
                                "recipe_id": f"f3-final-pose-v3-r{rank:04d}",
                                "asset": {
                                    "modelname": "001_bottle",
                                    "model_id": int(asset["model_id"]),
                                },
                                "asset_record_sha256": asset["record_sha256"],
                                "arm": arm,
                                "grasp_region": region,
                                "long_axis_model_axis": 1,
                                "region_center_fraction_from_geometric_center": fraction,
                                "region_center_offset_m": fraction
                                * float(asset["body_height_m"]),
                                "official_contact_point_id": contact_id,
                                "official_rotation_candidate_index": rotation_index,
                                "pregrasp_distance_m": pregrasp_distance,
                                "target_distance_m": TARGET_DISTANCE_M,
                                "pose_generation_order": [
                                    "official_contact_pose",
                                    "official_rotation_candidate",
                                    "region_translation",
                                    "freeze_final_pregrasp_grasp_lift",
                                    "ik_collision_planner_qualification",
                                ],
                                "post_qualification_pose_mutation_allowed": False,
                                "physical_execution_authorized": False,
                                "formal_data": False,
                                "stage0_data": False,
                                "stage1_authorized": False,
                            }
                            recipe["recipe_sha256"] = canonical_hash_json(recipe)
                            recipes.append(recipe)
    if len(recipes) != EXPECTED_RECIPE_COUNT:
        raise AssertionError("F3 V3 Cartesian universe size changed")
    value = {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "source_v2_qualification_sha256": old["qualification_sha256"],
        "selected_asset_model_ids": old["selected_asset_model_ids"],
        "axes": {
            "arms": list(ARMS),
            "regions": list(REGIONS),
            "official_contact_point_ids": list(OFFICIAL_CONTACT_POINT_IDS),
            "official_rotation_candidate_indices": list(OFFICIAL_ROTATION_INDICES),
            "pregrasp_distances_m": list(PREGRASP_DISTANCES_M),
        },
        "recipe_count": len(recipes),
        "recipes": recipes,
        "planner_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["universe_sha256"] = canonical_hash_json(value)
    return value


def freeze_f3_final_pose_v3(
    recipe: Mapping[str, Any],
    *,
    actor_pose: Sequence[float],
    raw_official_pregrasp_pose: Sequence[float],
    raw_official_grasp_pose: Sequence[float],
    raw_rotation_candidate_index: int,
) -> dict[str, Any]:
    recipe_value = canonical_jsonable(recipe)
    if recipe_value.get("recipe_sha256") != canonical_hash_json(
        {key: value for key, value in recipe_value.items() if key != "recipe_sha256"}
    ):
        raise ValueError("F3 V3 recipe hash mismatch")
    if int(raw_rotation_candidate_index) != int(
        recipe_value["official_rotation_candidate_index"]
    ):
        raise ValueError("raw F3 rotation candidate differs from recipe")
    actor = _pose7(actor_pose, "F3 actor")
    raw_pregrasp = _pose7(raw_official_pregrasp_pose, "F3 raw pregrasp")
    raw_grasp = _pose7(raw_official_grasp_pose, "F3 raw grasp")
    local_shift = np.zeros(3, dtype=np.float64)
    local_shift[int(recipe_value["long_axis_model_axis"])] = float(
        recipe_value["region_center_offset_m"]
    )
    world_shift = pose_matrix(actor)[:3, :3] @ local_shift
    final_pregrasp = raw_pregrasp.copy()
    final_grasp = raw_grasp.copy()
    final_pregrasp[:3] += world_shift
    final_grasp[:3] += world_shift
    final_lift = world_axis_offset_pose(final_grasp, FINAL_LIFT_DISTANCE_M)
    goals = {
        "pregrasp": final_pregrasp.tolist(),
        "grasp": final_grasp.tolist(),
        "lift": final_lift.tolist(),
    }
    value = {
        "schema_version": "cmf_f3_final_pose_freeze_v3",
        "recipe_id": recipe_value["recipe_id"],
        "recipe_sha256": recipe_value["recipe_sha256"],
        "raw_official_pose_hashes": {
            "pregrasp": canonical_hash_json(raw_pregrasp.tolist()),
            "grasp": canonical_hash_json(raw_grasp.tolist()),
        },
        "region_shift_world_m": world_shift.tolist(),
        "final_goal_poses": goals,
        "final_goal_pose_hashes": {
            key: canonical_hash_json(pose) for key, pose in goals.items()
        },
        "ordered_final_planner_input_sha256": canonical_hash_json(
            [goals["pregrasp"], goals["grasp"], goals["lift"]]
        ),
        "region_applied_before_planner_qualification": True,
        "post_qualification_pose_mutation_allowed": False,
    }
    value["final_pose_freeze_sha256"] = canonical_hash_json(value)
    return value


def validate_f3_final_pose_qualification_v3(
    recipe: Mapping[str, Any],
    freeze: Mapping[str, Any],
    qualification_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    recipe_value = canonical_jsonable(recipe)
    freeze_value = canonical_jsonable(freeze)
    receipt = canonical_jsonable(qualification_receipt)
    payload = dict(receipt)
    digest = payload.pop("receipt_sha256", None)
    required_statuses = {"pregrasp": "Success", "grasp": "Success", "lift": "Success"}
    checks = {
        "receipt_hash_valid": digest == canonical_hash_json(payload),
        "recipe_bound": receipt.get("recipe_sha256")
        == recipe_value.get("recipe_sha256"),
        "freeze_bound": receipt.get("final_pose_freeze_sha256")
        == freeze_value.get("final_pose_freeze_sha256"),
        "exact_ordered_input_bound": receipt.get(
            "ordered_planner_input_sha256"
        )
        == freeze_value.get("ordered_final_planner_input_sha256"),
        "exact_goal_hashes_bound": receipt.get("goal_pose_hashes")
        == freeze_value.get("final_goal_pose_hashes"),
        "all_final_targets_planner_success": receipt.get("planner_statuses")
        == required_statuses,
        "ik_collision_planner_all_checked": receipt.get(
            "ik_collision_planner_checked"
        )
        is True,
        "post_qualification_mutation_absent": receipt.get(
            "post_qualification_pose_mutation"
        )
        is False,
    }
    value = {
        "schema_version": "cmf_f3_final_pose_qualification_validation_v3",
        "recipe_id": recipe_value.get("recipe_id"),
        "checks": checks,
        "pass": all(checks.values()),
        "physical_execution_authorized": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def assert_f3_applied_pose_matches_qualification_v3(
    freeze: Mapping[str, Any], applied_goal_poses: Mapping[str, Sequence[float]]
) -> dict[str, Any]:
    frozen = canonical_jsonable(freeze)["final_goal_pose_hashes"]
    applied = {
        key: canonical_hash_json(_pose7(applied_goal_poses[key], key).tolist())
        for key in ("pregrasp", "grasp", "lift")
    }
    value = {
        "schema_version": "cmf_f3_applied_final_pose_binding_v3",
        "frozen_goal_pose_hashes": deepcopy(frozen),
        "applied_goal_pose_hashes": applied,
        "pass": applied == frozen,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    if value["pass"] is not True:
        raise ValueError("F3 applied pose changed after planner qualification")
    return value


def build_f3_targets_from_qualified_final_pose_v3(
    recipe: Mapping[str, Any],
    freeze: Mapping[str, Any],
    qualification_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    qualification = validate_f3_final_pose_qualification_v3(
        recipe, freeze, qualification_receipt
    )
    if qualification["pass"] is not True:
        raise ValueError("F3 final pose is not qualified for target construction")
    goals = canonical_jsonable(freeze)["final_goal_poses"]
    assert_f3_applied_pose_matches_qualification_v3(freeze, goals)
    grasp = _pose7(goals["grasp"], "F3 qualified grasp")
    central = grasp.copy()
    central[:3] = [0.0, -0.05, 0.95]
    positive_v = world_axis_offset_pose(central, 0.055)
    targets = [
        {"segment_id": "f3_v3_pregrasp", "pose": goals["pregrasp"]},
        {"segment_id": "f3_v3_grasp", "pose": goals["grasp"]},
        {"segment_id": "f3_v3_lift", "pose": goals["lift"]},
        {"segment_id": "f3_v3_central", "pose": central.tolist()},
        {"segment_id": "f3_v3_one_V", "pose": positive_v.tolist()},
        {"segment_id": "f3_v3_return", "pose": central.tolist()},
    ]
    value = {
        "schema_version": "cmf_f3_qualified_target_construction_v3",
        "recipe_sha256": recipe["recipe_sha256"],
        "final_pose_freeze_sha256": freeze["final_pose_freeze_sha256"],
        "qualification_validation_sha256": qualification["receipt_sha256"],
        "targets": targets,
        "targets_sha256": canonical_hash_json(targets),
        "final_pregrasp_grasp_lift_exactly_reused": True,
        "post_qualification_pose_mutation": False,
        "physical_execution_authorized": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def f3_v2_terminal_correction_v3(
    *, old_terminal_receipt_sha256: str
) -> dict[str, Any]:
    value = {
        "schema_version": "cmf_f3_v2_terminal_correction_v3",
        "old_terminal_receipt_sha256": str(old_terminal_receipt_sha256),
        "old_status_overclaim": "OFFICIAL_BOTTLE_GRASP_SEARCH_EXHAUSTED_REQUIRES_OBJECT_FAMILY_REDESIGN",
        "corrected_status": "TARGET_MUTATED_AFTER_PLANNER_QUALIFICATION_SEARCH_DESIGN_INCOMPLETE",
        "supported_claim": (
            "the eight post-selection shifted final pregrasp targets failed; "
            "the official bottle family was not exhaustively searched"
        ),
        "reexecution_required": False,
        "old_receipts_remain_factual": True,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


__all__ = [
    "EXPECTED_RECIPE_COUNT",
    "assert_f3_applied_pose_matches_qualification_v3",
    "build_f3_final_pose_recipe_universe_v3",
    "build_f3_targets_from_qualified_final_pose_v3",
    "f3_v2_terminal_correction_v3",
    "freeze_f3_final_pose_v3",
    "validate_f3_final_pose_qualification_v3",
]
