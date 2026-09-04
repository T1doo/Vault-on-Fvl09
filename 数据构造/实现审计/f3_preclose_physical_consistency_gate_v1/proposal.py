"""Non-executable proposal contract for one bounded future F3 micro-Gate."""

from __future__ import annotations

from typing import Any, Mapping

from gate import canonical_hash, gate_contract


STATUS = "PROPOSAL_ONLY_AWAITING_EXTERNAL_REVIEW"
EXPECTED_BUDGET = {
    "candidate_cap": 4,
    "stage_a_queries_per_candidate": 3,
    "stage_b_queries_per_candidate": 7,
    "physical_micro_queries_per_candidate": 3,
    "qualification_planner_query_cap": 40,
    "physical_micro_planner_query_cap": 12,
    "aggregate_planner_query_cap": 52,
    "planner_scene_cap": 8,
    "physical_scene_cap": 4,
    "aggregate_scene_cap": 12,
    "physical_attempt_cap": 4,
    "shared_v_scene_cap": 0,
    "suffix_scene_cap": 0,
    "root_execution_cap": 0,
    "raw_trajectory_cap": 0,
    "formal_trajectory_cap": 0,
}


def build_proposal(source_bindings: Mapping[str, Any]) -> dict[str, Any]:
    """Build an explicitly unapproved draft without fabricating candidates."""

    value = {
        "schema_version": "cmf_f3_preclose_physical_consistency_proposal_manifest_v1",
        "status": STATUS,
        "approved": False,
        "family": "F3",
        "mode": "F3_PRECLOSE_PHYSICAL_CONSISTENCY_MICRO_GATE_V1",
        "source_bindings": dict(source_bindings),
        "gate_contract": gate_contract(),
        "candidate_slots": [
            {
                "slot_id": f"f3-preclose-candidate-{index:02d}",
                "candidate_freeze_status": "pending_cpu_collision_screen",
                "recipe": None,
                "recipe_sha256": None,
            }
            for index in range(1, 5)
        ],
        "candidate_selection": {
            "source_universe": "existing_f3_final_pose_v3_3840_recipe_universe",
            "freeze_before_gpu": True,
            "online_search": False,
            "fallback_allowed": False,
            "success_conditioned_recipe_substitution": False,
            "old_failed_candidates_retried": False,
        },
        "ordered_physical_micro": [
            "pregrasp",
            "pregrasp_physical_consistency_gate",
            "grasp",
            "grasp_physical_consistency_gate",
            "conditional_close_0_50",
            "conditional_post_close_hold_250",
            "conditional_25mm_micro_lift",
            "conditional_contact_off_support_transform_gate",
        ],
        "budget": dict(EXPECTED_BUDGET),
        "authorization": {
            "gpu_execution_authorized": False,
            "planner_execution_authorized": False,
            "scene_creation_authorized": False,
            "physical_execution_authorized": False,
            "shared_v_authorized": False,
            "suffix_authorized": False,
            "root_execution_authorized": False,
            "raw_collection_authorized": False,
            "formal_collection_authorized": False,
            "stage0_reopened": False,
            "stage1_authorized": False,
            "training_authorized": False,
            "h_reveal_authorized": False,
            "compression_authorized": False,
            "pi05_authorized": False,
        },
        "stop_rule": {
            "any_preclose_gate_failure": "stop_before_close_for_that_candidate",
            "candidate_loop": "frozen_order_until_two_pass_or_four_exhausted",
            "automatic_shared_v_continuation": False,
            "automatic_retry": False,
        },
        "requires_new_external_review": True,
        "formal_data": False,
    }
    value["manifest_sha256"] = canonical_hash(value)
    return value


def validate_proposal(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("proposal must be a mapping")
    result = dict(value)
    payload = dict(result)
    digest = payload.pop("manifest_sha256", None)
    if digest != canonical_hash(payload):
        raise ValueError("proposal self-hash mismatch")
    if result.get("status") != STATUS or result.get("approved") is not False:
        raise PermissionError("F3 pre-close proposal is not an unapproved draft")
    if result.get("budget") != EXPECTED_BUDGET:
        raise ValueError("proposal budget changed")
    slots = result.get("candidate_slots")
    if not isinstance(slots, list) or len(slots) != 4:
        raise ValueError("proposal must contain exactly four pending slots")
    for index, slot in enumerate(slots, start=1):
        if slot != {
            "slot_id": f"f3-preclose-candidate-{index:02d}",
            "candidate_freeze_status": "pending_cpu_collision_screen",
            "recipe": None,
            "recipe_sha256": None,
        }:
            raise ValueError("proposal fabricated or reordered a candidate")
    authorization = result.get("authorization")
    if not isinstance(authorization, Mapping) or any(
        item is not False for item in authorization.values()
    ):
        raise PermissionError("proposal unexpectedly authorizes execution")
    selection = result.get("candidate_selection")
    stop = result.get("stop_rule")
    if (
        selection.get("freeze_before_gpu") is not True
        or selection.get("online_search") is not False
        or selection.get("fallback_allowed") is not False
        or selection.get("old_failed_candidates_retried") is not False
        or stop.get("automatic_shared_v_continuation") is not False
        or stop.get("automatic_retry") is not False
        or result.get("requires_new_external_review") is not True
        or result.get("formal_data") is not False
    ):
        raise ValueError("proposal stop or authorization boundary changed")
    result["manifest_sha256"] = digest
    return result


def reject_execution(value: Mapping[str, Any]) -> None:
    validate_proposal(value)
    raise PermissionError(
        "proposal-only F3 pre-close Gate has no GPU/planner/scene/physical authority"
    )


__all__ = [
    "EXPECTED_BUDGET",
    "STATUS",
    "build_proposal",
    "reject_execution",
    "validate_proposal",
]
