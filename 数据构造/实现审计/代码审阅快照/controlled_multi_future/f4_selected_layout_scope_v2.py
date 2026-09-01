"""Frozen future one-shot scope for the CPU-selected F4 V2 layout."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .current_hasher import hash_json
from .f4_layout_candidate_search_v2 import (
    IMPLEMENTATION_VERSION,
    SELECTED_EXISTING_CORRIDOR_ID,
    SELECTED_LAYOUT_SCOPE,
    build_f4_layout_candidate_search_v2,
    build_single_selected_layout_dispatch_v2,
)


ROOT = Path("/nfs_share/lijunhui")
AUDIT = ROOT / "Vault-on-Fvl09/数据构造/实现审计"
GROUP = "controlled_multi_future_post_stage0_f4_selected_layout_v2"
SCOPE = SELECTED_LAYOUT_SCOPE
SEED = 20260829
NAMESPACE = "f4_selected_layout_v2_c01_planner_only_seed20260829_run4"
AUTH_ID = "f4-selected-layout-v2-c01-planner-only-run4"
OUTPUT = ROOT / "Robotwin2/datasets" / GROUP / NAMESPACE
PARENT = AUDIT / "USER_AUTHORIZATION_F4_SELECTED_LAYOUT_V2_20260831.json"
BUDGET = AUDIT / "POST_STAGE0_F4_SELECTED_LAYOUT_V2_BUDGET.json"
PUBLICATION = AUDIT / "POST_STAGE0_F4_SELECTED_LAYOUT_V2_SCOPE.json"
EVIDENCE = AUDIT / "POST_STAGE0_CLOSURE_V1_F4_RESULT.json"
REQUEST = AUDIT / "scope_requests" / GROUP / f"{NAMESPACE}.request.json"
SOURCE = AUDIT / "source_locks" / GROUP / f"{NAMESPACE}.source_lock.json"
AUTH = AUDIT / "authorizations" / GROUP / f"{NAMESPACE}.authorization.json"
GUARD = AUDIT / "gpu_guards" / GROUP / f"{NAMESPACE}.guard.json"


def _sha(value):
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def budget():
    value = {
        "schema_version": "cmf_f4_selected_layout_v2_budget",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "family": "F4",
        "planner_query_limit": 96,
        "canonical_prefix_reference_execution_limit": 1,
        "fresh_scene_limit": 4,
        "program_scene_limit": 3,
        "suffix_execution_limit": 0,
        "release_execution_limit": 0,
        "recovery_attempts": 0,
        "physics_step_limit": -1,
        "timeout_seconds": 14400,
        "allowed_physical_gpu_indices": list(range(8)),
        "one_root_one_gpu": True,
        "root_sharding_authorized": False,
        "maximum_scope_invocations": 1,
        "maximum_layout_dispatch_count": 1,
        "automatic_retry": False,
        "automatic_fallback": False,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage1_authorized": False,
    }
    value["budget_receipt_sha256"] = _sha(value)
    return value


def spec():
    search = build_f4_layout_candidate_search_v2()
    dispatch = build_single_selected_layout_dispatch_v2(search)
    selected = next(
        item
        for item in search["candidates"]
        if item["candidate_id"] == dispatch["dispatch_candidate_id"]
    )
    value = {
        "schema_version": "cmf_f4_selected_layout_v2_planned_scope_spec",
        "slot_id": "post-stage0-F4-selected-layout-v2-c01-planner-only",
        "scope": SCOPE,
        "family": "F4",
        "arm": "right",
        "seed": SEED,
        "generator": "controlled_multi_future_post_stage0_f4_selected_layout_v2_adapter",
        "origin": "post_closure_f4_finite_layout_search_v2",
        "scene_layout": selected["layout"],
        "scene_layout_sha256": selected["layout_sha256"],
        "selected_layout_candidate_id": selected["candidate_id"],
        "selected_layout_candidate_sha256": selected["candidate_sha256"],
        "f4_layout_candidate_search_v2": search,
        "f4_layout_search_contract_sha256": search["search_contract_sha256"],
        "f4_single_selected_layout_dispatch_v2": dispatch,
        "f4_layout_dispatch_contract_sha256": dispatch[
            "dispatch_contract_sha256"
        ],
        "post_stage0_selected_f4_corridor_id": SELECTED_EXISTING_CORRIDOR_ID,
        "canonical_program_ids": ["F4-ABC", "F4-ACB", "F4-BAC"],
        "canonical_prefix_reference_execution_count": 1,
        "fresh_program_scene_count": 3,
        "rendered_actor_segmentation_visibility_required": True,
        "complete_program_planner_chains_required": True,
        "suffix_execution_count": 0,
        "release_execution_count": 0,
        "recovery_attempts": 0,
        "temporary_waypoint_allowed": False,
        "automatic_retry": False,
        "automatic_fallback": False,
        "failure_requires_higher_level_redesign": True,
        "cpu_search_is_not_ik_evidence": True,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage0_reopened": False,
        "stage1_authorized": False,
        "budget_receipt_sha256": budget()["budget_receipt_sha256"],
        "stop_condition": "first terminal visibility/planner/cleanup/source/GPU failure or all three complete planner-only chains pass; never fallback",
    }
    value["planned_scope_spec_sha256"] = _sha(value)
    return value


def parent():
    value = {
        "schema_version": "cmf_f4_selected_layout_v2_parent_authorization",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "approved": True,
        "authorized_scopes": [SCOPE],
        "allowed_physical_gpu_indices": list(range(8)),
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
        "automatic_retry": False,
        "automatic_fallback": False,
        "maximum_layout_dispatch_count": 1,
        "recovery_attempts": 0,
        "stage0_reopened": False,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
        "h_reveal_authorized": False,
        "compression_authorized": False,
        "pi05_authorized": False,
        "user_direction_source": "https://chatgpt.com/s/t_6a95674546fc81918e8287f959e8e46c",
    }
    value["parent_user_authorization_sha256"] = hash_json(value)
    return value


def publication():
    search = build_f4_layout_candidate_search_v2()
    dispatch = build_single_selected_layout_dispatch_v2(search)
    value = {
        "schema_version": "cmf_f4_selected_layout_v2_scope_publication",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "planned_scope_spec": spec(),
        "budget": budget(),
        "search_contract_sha256": search["search_contract_sha256"],
        "dispatch_contract_sha256": dispatch["dispatch_contract_sha256"],
        "source_failure_result_payload_sha256": (
            "1a02903c5503a055dfc9188d19c63803544d69be8e94af22fa9501c9fa1c1d7a"
        ),
        "stage0_seal_unchanged": True,
    }
    value["scope_publication_sha256"] = _sha(value)
    return value


__all__ = [
    "AUTH",
    "AUTH_ID",
    "BUDGET",
    "EVIDENCE",
    "GROUP",
    "GUARD",
    "NAMESPACE",
    "OUTPUT",
    "PARENT",
    "PUBLICATION",
    "REQUEST",
    "SCOPE",
    "SEED",
    "SOURCE",
    "budget",
    "parent",
    "publication",
    "spec",
]
