"""Stage-A/Stage-B-bound F3 shared-V physical micro qualification."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f3_asset_grasp_qualification_v2 import (
    build_f3_asset_grasp_qualification_v2,
)
from .f3_planner_integration_v3_1 import (
    build_f3_stage_b_targets_v3_1,
    finalize_f3_candidate_qualification_v3_1,
    validate_f3_stage_a_planner_spec_v3_1,
    validate_f3_stage_a_terminal_v3_1,
    validate_f3_stage_b_planner_spec_v3_1,
)
from .high_level_physical_runner_v1 import execute_f3_level2_physical_v1
from .high_level_runtime_specs_v1 import build_f3_runtime_spec_v1


PURPOSE = "f3_shared_v_physical_micro_v1"
PLANNER_QUERY_LIMIT = 7


def _self_hashed(value: Mapping[str, Any], key: str, label: str) -> dict[str, Any]:
    result = canonical_jsonable(value)
    payload = dict(result)
    digest = payload.pop(key, None)
    if digest != canonical_hash_json(payload):
        raise ValueError(f"F3 shared-V {label} hash mismatch")
    return result


def build_f3_shared_v_physical_spec_v1(
    stage_a_spec: Mapping[str, Any],
    stage_a_terminal: Mapping[str, Any],
    stage_b_spec: Mapping[str, Any],
    stage_b_terminal: Mapping[str, Any],
    *,
    slot_id: str,
    planner_reset_nonce: int,
) -> dict[str, Any]:
    spec_a = validate_f3_stage_a_planner_spec_v3_1(stage_a_spec)
    terminal_a = validate_f3_stage_a_terminal_v3_1(stage_a_terminal, spec_a)
    spec_b = validate_f3_stage_b_planner_spec_v3_1(stage_b_spec)
    terminal_b = _self_hashed(stage_b_terminal, "receipt_sha256", "Stage-B terminal")
    qualification = finalize_f3_candidate_qualification_v3_1(
        terminal_a, spec_a, terminal_b, spec_b
    )
    if qualification["planner_qualified_for_physical_probe"] is not True:
        raise ValueError("F3 shared-V physical spec requires passing Stage A and B")
    recipe = spec_a["recipe"]
    tuple_contract = build_f3_asset_grasp_qualification_v2()
    candidates = [
        item
        for item in tuple_contract["grasp_tuples"]
        if item["asset"] == recipe["asset"] and item["arm"] == recipe["arm"]
    ]
    if len(candidates) != 1:
        raise ValueError("F3 recipe does not resolve to one runtime asset tuple")
    stage_a_goals = terminal_a["final_pose_freeze"]["final_goal_poses"]
    stage_b_targets = build_f3_stage_b_targets_v3_1(spec_b)
    legacy_scene_spec = build_f3_runtime_spec_v1(
        candidates[0]["tuple_id"], purpose="f3_level2_physical"
    )
    targets = [
        {"segment_id": "f3_shared_v_pregrasp", "pose": stage_a_goals["pregrasp"]},
        {"segment_id": "f3_shared_v_grasp", "pose": stage_a_goals["grasp"]},
        {"segment_id": "f3_shared_v_lift", "pose": stage_a_goals["lift"]},
        {
            "segment_id": "f3_shared_v_central_before_v",
            "pose": stage_b_targets[0]["pose"],
        },
        {"segment_id": "f3_shared_v_v_plus", "pose": stage_b_targets[1]["pose"]},
        {"segment_id": "f3_shared_v_v_minus", "pose": stage_b_targets[2]["pose"]},
        {
            "segment_id": "f3_shared_v_return_central",
            "pose": stage_b_targets[3]["pose"],
        },
    ]
    value = {
        "schema_version": "cmf_f3_shared_v_physical_spec_v1",
        "purpose": PURPOSE,
        "family": "F3",
        "slot_id": str(slot_id),
        "arm": recipe["arm"],
        "recipe": deepcopy(recipe),
        "recipe_sha256": recipe["recipe_sha256"],
        "f3_asset_grasp_tuple_v2": deepcopy(candidates[0]),
        "f3_asset_grasp_tuple_sha256": candidates[0]["tuple_sha256"],
        "scene_binding": deepcopy(spec_a["scene_binding"]),
        "source_stage_a_spec_sha256": spec_a["spec_sha256"],
        "source_stage_a_terminal_receipt_sha256": terminal_a["receipt_sha256"],
        "source_stage_b_spec_sha256": spec_b["spec_sha256"],
        "source_stage_b_terminal_receipt_sha256": terminal_b["receipt_sha256"],
        "planner_qualification_receipt_sha256": qualification["receipt_sha256"],
        "legacy_scene_spec": legacy_scene_spec,
        "legacy_scene_spec_sha256": legacy_scene_spec[
            "planned_scope_spec_sha256"
        ],
        "ordered_targets": targets,
        "ordered_targets_sha256": canonical_hash_json(targets),
        "ordered_event_contract": [
            "pregrasp",
            "grasp",
            "close",
            "post_close_settle",
            "lift",
            "central",
            "hold_before_shared_v",
            "V_plus",
            "V_minus",
            "return_central",
            "hold_after_shared_v",
        ],
        "planner_query_limit": PLANNER_QUERY_LIMIT,
        "planner_reset_nonce": int(planner_reset_nonce),
        "suffix_allowed": False,
        "physical_execution_count_limit": 1,
        "physical_execution_authorized": False,
        "three_scene_confirmation_authorized": False,
        "stage1_authorized": False,
        "formal_data": False,
    }
    value["spec_sha256"] = canonical_hash_json(value)
    return value


def validate_f3_shared_v_physical_spec_v1(
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    value = _self_hashed(spec, "spec_sha256", "physical spec")
    if (
        value.get("purpose") != PURPOSE
        or value.get("planner_query_limit") != PLANNER_QUERY_LIMIT
        or len(value.get("ordered_targets", [])) != PLANNER_QUERY_LIMIT
        or canonical_hash_json(value.get("ordered_targets"))
        != value.get("ordered_targets_sha256")
        or value.get("suffix_allowed") is not False
        or value.get("physical_execution_count_limit") != 1
        or value.get("physical_execution_authorized") is not False
        or value.get("stage1_authorized") is not False
        or value.get("formal_data") is not False
    ):
        raise ValueError("F3 shared-V physical spec semantics changed")
    return value


def run_f3_shared_v_physical_v1(scene, spec: Mapping[str, Any]) -> dict[str, Any]:
    value = validate_f3_shared_v_physical_spec_v1(spec)
    result = execute_f3_level2_physical_v1(scene, value)
    passed = result.get("sequence_complete") is True
    terminal = {
        "schema_version": "cmf_f3_shared_v_physical_terminal_v1",
        "purpose": PURPOSE,
        "slot_id": value["slot_id"],
        "spec_sha256": value["spec_sha256"],
        "recipe_sha256": value["recipe_sha256"],
        "physical_result": canonical_jsonable(result),
        "planner_query_count": int(getattr(scene, "planner_query_count", 0)),
        "physical_execution_count": 1,
        "shared_v_physically_qualified": passed,
        "three_scene_confirmation_ready": passed,
        "candidate_ready": False,
        "stage1_ready": False,
        "formal_data": False,
    }
    terminal["receipt_sha256"] = canonical_hash_json(terminal)
    return terminal


__all__ = [
    "PLANNER_QUERY_LIMIT",
    "PURPOSE",
    "build_f3_shared_v_physical_spec_v1",
    "run_f3_shared_v_physical_v1",
    "validate_f3_shared_v_physical_spec_v1",
]
