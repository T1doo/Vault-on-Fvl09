"""Frozen scope and budget for the F4 new-layout planner-only audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .current_hasher import hash_json
from .f4_post_stage0_layout_v1 import (
    LAYOUT,
    SELECTED_EXISTING_CORRIDOR_ID,
    audit_f4_post_stage0_layout_v1,
)
from .real_sapien_adapter_post_stage0_f4_v1 import IMPLEMENTATION_VERSION


WORKSPACE_ROOT = Path("/nfs_share/lijunhui")
AUDIT_ROOT = WORKSPACE_ROOT / "Vault-on-Fvl09/数据构造/实现审计"
GROUP = "controlled_multi_future_post_stage0_f4_v1"
SCOPE = "F4_new_layout_endpoint_IK_and_three_program_planner_only_v1"
SCENE_SEED = 20260829
NAMESPACE = "post_stage0_f4_new_layout_planner_only_seed20260829_run1"
AUTHORIZATION_ID = "post-stage0-f4-new-layout-planner-only-run1"
OUTPUT_NAMESPACE = WORKSPACE_ROOT / "Robotwin2/datasets" / GROUP / NAMESPACE
PARENT_AUTHORIZATION = AUDIT_ROOT / "USER_AUTHORIZATION_POST_STAGE0_F4_PLANNER_ONLY_V1_20260831.json"
BUDGET_PUBLICATION = AUDIT_ROOT / "POST_STAGE0_F4_PLANNER_ONLY_BUDGET_V1.json"
SCOPE_PUBLICATION = AUDIT_ROOT / "POST_STAGE0_F4_PLANNER_ONLY_SCOPE_V1.json"
IMPACT_REVIEW = AUDIT_ROOT / "F4_POST_STAGE0_LAYOUT_IMPACT_REVIEW_V1.json"
REQUEST_PATH = AUDIT_ROOT / "scope_requests" / GROUP / f"{NAMESPACE}.request.json"
SOURCE_LOCK_PATH = AUDIT_ROOT / "source_locks" / GROUP / f"{NAMESPACE}.source_lock.json"
AUTHORIZATION_PATH = AUDIT_ROOT / "authorizations" / GROUP / f"{NAMESPACE}.authorization.json"
GUARD_PATH = AUDIT_ROOT / "gpu_guards" / GROUP / f"{NAMESPACE}.guard.json"


def _sha(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def post_stage0_f4_budget_v1() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_post_stage0_f4_scope_budget_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "family": "F4",
        "planner_query_limit": 96,
        "canonical_prefix_reference_execution_limit": 1,
        "suffix_execution_limit": 0,
        "release_execution_limit": 0,
        "physics_step_limit": -1,
        "timeout_seconds": 14400,
        "fresh_scene_limit": 4,
        "allowed_physical_gpu_indices": list(range(8)),
        "one_root_one_gpu": True,
        "root_sharding_authorized": False,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "maximum_scope_invocations": 1,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage1_authorized": False,
    }
    value["budget_receipt_sha256"] = _sha(value)
    return value


def post_stage0_f4_planned_spec_v1() -> dict[str, Any]:
    audit = audit_f4_post_stage0_layout_v1()
    if audit["pass"] is not True:
        raise ValueError("F4 post-Stage-0 layout CPU audit no longer passes")
    value = {
        "schema_version": "cmf_post_stage0_f4_planned_scope_spec_v1",
        "slot_id": "post-stage0-F4-layout-planner-audit-A-v1",
        "scope": SCOPE,
        "family": "F4",
        "arm": "right",
        "seed": SCENE_SEED,
        "generator": "controlled_multi_future_post_stage0_f4_adapter_v1",
        "origin": "post_stage0_layout_impact_review",
        "scene_layout": json.loads(json.dumps(LAYOUT, sort_keys=True)),
        "scene_layout_sha256": audit["layout_sha256"],
        "post_stage0_selected_f4_corridor_id": SELECTED_EXISTING_CORRIDOR_ID,
        "canonical_program_ids": ["F4-ABC", "F4-ACB", "F4-BAC"],
        "diagnostic_contract": {
            "canonical_prefix_reference_execution_count": 1,
            "fresh_program_scene_count": 3,
            "exact_prefix_replay_required": True,
            "complete_program_planner_chains_required": True,
            "suffix_execution_count": 0,
            "release_execution_count": 0,
            "diagnostic_nonroot": True,
            "accepted_root_increment": 0,
        },
        "budget_receipt_sha256": post_stage0_f4_budget_v1()["budget_receipt_sha256"],
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage0_reopened": False,
        "stage1_authorized": False,
        "stop_condition": "terminal receipt or first cleanup/source/GPU uncertainty",
    }
    value["planned_scope_spec_sha256"] = _sha(value)
    return value


def post_stage0_f4_scope_publication_v1() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_post_stage0_f4_scope_publication_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "planned_scope_spec": post_stage0_f4_planned_spec_v1(),
        "budget": post_stage0_f4_budget_v1(),
        "impact_review_payload_sha256": "ca9c3c1419a4513c849311eed904246c4784da3b36f306bcee8e9021f133e043",
        "stage0_seal_unchanged": True,
        "stage0_result_sha256": "394093a2571269eaa659cc90df654c449ffd1fb3a9ab041bbcfc321231c21df7",
    }
    value["scope_publication_sha256"] = _sha(value)
    return value


def post_stage0_f4_parent_authorization_v1() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_post_stage0_f4_parent_user_authorization_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "approved": True,
        "authorized_scope": SCOPE,
        "maximum_scope_invocations": 1,
        "allowed_physical_gpu_indices": list(range(8)),
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
        "root_sharding_authorized": False,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "stage0_reopened": False,
        "stage0_authorized": False,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
        "h_reveal_authorized": False,
        "compression_authorized": False,
        "pi05_authorized": False,
        "maximum_conditional_f4_development_roots_after_pass": 1,
        "user_direction_source": "current_2026-08-31_continuation_message_and_sealed_handoff",
    }
    value["parent_user_authorization_sha256"] = hash_json(value)
    return value


__all__ = [name for name in globals() if name.startswith("post_stage0_f4_") or name in {
    "AUTHORIZATION_ID", "AUTHORIZATION_PATH", "BUDGET_PUBLICATION", "GROUP", "GUARD_PATH",
    "IMPACT_REVIEW", "NAMESPACE", "OUTPUT_NAMESPACE", "PARENT_AUTHORIZATION", "REQUEST_PATH",
    "SCENE_SEED", "SCOPE", "SCOPE_PUBLICATION", "SOURCE_LOCK_PATH"
}]
