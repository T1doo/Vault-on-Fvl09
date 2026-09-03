"""Production-bound F2 controlled-insertion physical runner.

The physical specification is derived only from one validated Stage-A planner
terminal and its exact planner spec.  It carries no external target pose,
margin, or grasp geometry, and it does not itself authorize execution.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_inside_control_search_v2 import (
    validate_f2_final_grasp_qualification_v2,
)
from .f2_hierarchical_template_search_v1 import (
    build_f2_hierarchical_template_search_v1,
)
from .f2_planner_integration_v2 import (
    validate_f2_final_grasp_stage_a_spec_v2,
    validate_f2_planner_terminal_v2,
)
from .high_level_physical_runner_v1 import (
    execute_f2_controlled_insertion_physical_v2,
)
from .high_level_runtime_specs_v1 import build_f2_runtime_spec_v1


PURPOSE = "f2_controlled_insertion_physical_v2"
PLANNER_QUERY_LIMIT = 8


def _self_hashed(value: Mapping[str, Any], key: str, label: str) -> dict[str, Any]:
    result = canonical_jsonable(value)
    payload = dict(result)
    digest = payload.pop(key, None)
    if digest != canonical_hash_json(payload):
        raise ValueError(f"F2 controlled insertion {label} hash mismatch")
    return result


def _qualification_from_stage_a(
    stage_a_spec: Mapping[str, Any], stage_a_terminal: Mapping[str, Any]
) -> dict[str, Any]:
    spec = validate_f2_final_grasp_stage_a_spec_v2(stage_a_spec)
    terminal = validate_f2_planner_terminal_v2(stage_a_terminal, spec)
    if terminal.get("planner_qualified_for_physical_probe") is not True:
        raise ValueError("F2 physical spec requires a passing Stage-A terminal")
    freeze = terminal["final_grasp_pose_freeze"]
    receipts = terminal["planner_result"]["segment_receipts"]
    status_by_id = {
        item.get("segment_id"): item.get("planner_status") for item in receipts
    }
    prefix = "f2_final_grasp_v2_"
    qualification = {
        "schema_version": "cmf_f2_final_grasp_qualification_receipt_v2",
        "recipe_sha256": spec["recipe_sha256"],
        "final_grasp_pose_freeze_sha256": freeze[
            "final_grasp_pose_freeze_sha256"
        ],
        "ordered_planner_input_sha256": freeze[
            "ordered_final_planner_input_sha256"
        ],
        "goal_pose_hashes": freeze["final_goal_pose_hashes"],
        "planner_statuses": {
            name: status_by_id.get(prefix + name)
            for name in (
                "pregrasp",
                "grasp",
                "qualification_micro_lift_25mm",
            )
        },
        "ik_collision_planner_checked": len(receipts) == 3,
        "post_qualification_pose_mutation": False,
        "stage_a_terminal_receipt_sha256": terminal["receipt_sha256"],
    }
    qualification["receipt_sha256"] = canonical_hash_json(qualification)
    validation = validate_f2_final_grasp_qualification_v2(
        spec["recipe"], freeze, qualification
    )
    if validation["pass"] is not True:
        raise ValueError("F2 Stage-A qualification cannot seed physical execution")
    return qualification


def build_f2_controlled_insertion_physical_spec_v2(
    stage_a_spec: Mapping[str, Any],
    stage_a_terminal: Mapping[str, Any],
    *,
    slot_id: str,
    planner_reset_nonce: int,
) -> dict[str, Any]:
    source_spec = validate_f2_final_grasp_stage_a_spec_v2(stage_a_spec)
    source_terminal = validate_f2_planner_terminal_v2(
        stage_a_terminal, source_spec
    )
    qualification = _qualification_from_stage_a(source_spec, source_terminal)
    recipe = source_spec["recipe"]
    search = build_f2_hierarchical_template_search_v1()
    scene_candidates = [
        item
        for item in search["inside_candidates"]
        if item["main_object_model_id"] == recipe["main_object_model_id"]
        and item["plastic_box_model_id"] == recipe["plastic_box_model_id"]
        and item["arm"] == recipe["arm"]
    ]
    if len(scene_candidates) != 1:
        raise ValueError("F2 physical recipe does not resolve to one scene binding")
    legacy_scene_spec = build_f2_runtime_spec_v1(
        scene_candidates[0]["candidate_id"], purpose="f2_inside_physical"
    )
    value = {
        "schema_version": "cmf_f2_controlled_insertion_physical_spec_v2",
        "purpose": PURPOSE,
        "family": "F2",
        "slot_id": str(slot_id),
        "arm": source_spec["recipe"]["arm"],
        "recipe": deepcopy(source_spec["recipe"]),
        "recipe_sha256": source_spec["recipe_sha256"],
        "binding": deepcopy(source_spec["binding"]),
        "binding_sha256": source_spec["binding_sha256"],
        "geometry_certificate": deepcopy(source_spec["geometry_certificate"]),
        "geometry_certificate_sha256": source_spec[
            "geometry_certificate_sha256"
        ],
        "final_grasp_pose_freeze": deepcopy(
            source_terminal["final_grasp_pose_freeze"]
        ),
        "final_grasp_qualification": qualification,
        "source_stage_a_spec_sha256": source_spec["spec_sha256"],
        "source_stage_a_terminal_receipt_sha256": source_terminal[
            "receipt_sha256"
        ],
        "legacy_scene_spec": legacy_scene_spec,
        "legacy_scene_spec_sha256": legacy_scene_spec[
            "planned_scope_spec_sha256"
        ],
        "planner_reset_nonce": int(planner_reset_nonce),
        "planner_query_limit": PLANNER_QUERY_LIMIT,
        "ordered_phases": [
            "pregrasp",
            "grasp",
            "close",
            "settle_250",
            "pre_lift_gate_table_support_allowed",
            "qualification_micro_lift_25mm",
            "post_lift_hold_50",
            "post_lift_off_table_retention_gate",
            "suffix_from_post_lift_actual_transform",
            "lift",
            "preinsert_30mm",
            "controlled_descend_to_support",
            "support_stability_gate_50",
            "slow_release",
            "post_release_settle_250",
            "retreat_neutral",
        ],
        "external_target_pose_allowed": False,
        "external_margin_allowed": False,
        "old_gravity_drop_executor_allowed": False,
        "physical_execution_count_limit": 1,
        "planner_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
        "formal_data": False,
    }
    value["spec_sha256"] = canonical_hash_json(value)
    return value


def validate_f2_controlled_insertion_physical_spec_v2(
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    value = _self_hashed(spec, "spec_sha256", "physical spec")
    if (
        value.get("purpose") != PURPOSE
        or value.get("planner_query_limit") != PLANNER_QUERY_LIMIT
        or value.get("physical_execution_count_limit") != 1
        or value.get("external_target_pose_allowed") is not False
        or value.get("external_margin_allowed") is not False
        or value.get("old_gravity_drop_executor_allowed") is not False
        or value.get("physical_execution_authorized") is not False
        or value.get("stage1_authorized") is not False
        or value.get("formal_data") is not False
    ):
        raise ValueError("F2 controlled insertion physical semantics changed")
    validation = validate_f2_final_grasp_qualification_v2(
        value["recipe"],
        value["final_grasp_pose_freeze"],
        value["final_grasp_qualification"],
    )
    if validation["pass"] is not True:
        raise ValueError("F2 physical spec contains invalid grasp qualification")
    return value


def run_f2_controlled_insertion_physical_v2(
    scene, spec: Mapping[str, Any]
) -> dict[str, Any]:
    value = validate_f2_controlled_insertion_physical_spec_v2(spec)
    result = execute_f2_controlled_insertion_physical_v2(
        scene,
        arm=value["arm"],
        binding=value["binding"],
        recipe=value["recipe"],
        final_grasp_freeze=value["final_grasp_pose_freeze"],
        final_grasp_qualification=value["final_grasp_qualification"],
        geometry_certificate=value["geometry_certificate"],
        planner_query_limit=value["planner_query_limit"],
    )
    passed = (
        result.get("sequence_complete") is True
        and result.get("strict_inside_verifier_pass") is True
    )
    terminal = {
        "schema_version": "cmf_f2_controlled_insertion_physical_terminal_v2",
        "purpose": PURPOSE,
        "slot_id": value["slot_id"],
        "spec_sha256": value["spec_sha256"],
        "recipe_sha256": value["recipe_sha256"],
        "source_stage_a_spec_sha256": value["source_stage_a_spec_sha256"],
        "source_stage_a_terminal_receipt_sha256": value[
            "source_stage_a_terminal_receipt_sha256"
        ],
        "physical_result": canonical_jsonable(result),
        "planner_query_count": int(getattr(scene, "planner_query_count", 0)),
        "physical_execution_count": 1,
        "strict_inside_verifier_pass": passed,
        "physically_qualified": passed,
        "candidate_ready": passed,
        "stage1_ready": False,
        "formal_data": False,
    }
    terminal["receipt_sha256"] = canonical_hash_json(terminal)
    return terminal


__all__ = [
    "PLANNER_QUERY_LIMIT",
    "PURPOSE",
    "build_f2_controlled_insertion_physical_spec_v2",
    "run_f2_controlled_insertion_physical_v2",
    "validate_f2_controlled_insertion_physical_spec_v2",
]
