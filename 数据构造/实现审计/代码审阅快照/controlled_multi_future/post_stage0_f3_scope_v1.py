"""Frozen scope, budget, and paths for one post-Stage-0 F3 diagnostic."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .current_hasher import hash_json
from .f3_contact_preserving_prefix_v11 import (
    IMPLEMENTATION_VERSION,
    PROGRAM_IDS,
    build_f3_contact_preserving_prefix_contract_v11,
)


WORKSPACE_ROOT = Path("/nfs_share/lijunhui")
AUDIT_ROOT = WORKSPACE_ROOT / "Vault-on-Fvl09/数据构造/实现审计"
GROUP = "controlled_multi_future_post_stage0_f3_v1"
SCOPE = "F3_shared_prefix_no_suffix_diagnostic_v1"
SCENE_SEED = 20260829
NAMESPACE = "post_stage0_f3_shared_prefix_no_suffix_seed20260829_run1"
AUTHORIZATION_ID = "post-stage0-f3-shared-prefix-no-suffix-run1"
OUTPUT_NAMESPACE = (
    WORKSPACE_ROOT / "Robotwin2/datasets" / GROUP / NAMESPACE
)
PARENT_AUTHORIZATION = (
    AUDIT_ROOT / "USER_AUTHORIZATION_POST_STAGE0_F3_SHARED_PREFIX_DIAGNOSTIC_V1_20260831.json"
)
BUDGET_PUBLICATION = (
    AUDIT_ROOT / "POST_STAGE0_F3_SHARED_PREFIX_DIAGNOSTIC_BUDGET_V1.json"
)
SCOPE_PUBLICATION = (
    AUDIT_ROOT / "POST_STAGE0_F3_SHARED_PREFIX_DIAGNOSTIC_SCOPE_V1.json"
)
IMPACT_REVIEW = AUDIT_ROOT / "F3_SHARED_PREFIX_PHYSICAL_IMPACT_REVIEW_V1.json"
REQUEST_PATH = AUDIT_ROOT / "scope_requests" / GROUP / f"{NAMESPACE}.request.json"
SOURCE_LOCK_PATH = AUDIT_ROOT / "source_locks" / GROUP / f"{NAMESPACE}.source_lock.json"
AUTHORIZATION_PATH = AUDIT_ROOT / "authorizations" / GROUP / f"{NAMESPACE}.authorization.json"
GUARD_PATH = AUDIT_ROOT / "gpu_guards" / GROUP / f"{NAMESPACE}.guard.json"


def _sha(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def post_stage0_f3_budget_v1() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_post_stage0_f3_scope_budget_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "family": "F3",
        "planner_query_limit": 16,
        "execution_limit": 3,
        "physics_step_limit": -1,
        "timeout_seconds": 7200,
        "fresh_scene_limit": 3,
        "suffix_planner_query_limit": 0,
        "suffix_execution_limit": 0,
        "release_execution_limit": 0,
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


def post_stage0_f3_planned_spec_v1() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_post_stage0_f3_planned_scope_spec_v1",
        "slot_id": "post-stage0-F3-shared-prefix-diagnostic-A-v1",
        "scope": SCOPE,
        "family": "F3",
        "arm": "left",
        "seed": SCENE_SEED,
        "generator": "controlled_multi_future_post_stage0_f3_adapter_v1",
        "origin": "post_stage0_development_impact_review",
        "bottle": "001_bottle/base13",
        "canonical_program_ids": list(PROGRAM_IDS),
        "repair_contract": build_f3_contact_preserving_prefix_contract_v11(),
        "diagnostic_contract": {
            "fresh_scene_count": 3,
            "execution_modes": [
                "reference_generation",
                "exact_replay",
                "exact_replay"
            ],
            "same_immutable_prefix_action_bytes_required": True,
            "shared_first_v_included": True,
            "suffix_planner_query_count": 0,
            "suffix_execution_count": 0,
            "release_execution_count": 0,
            "diagnostic_nonroot": True,
            "accepted_root_increment": 0
        },
        "budget_receipt_sha256": post_stage0_f3_budget_v1()[
            "budget_receipt_sha256"
        ],
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage0_reopened": False,
        "stage1_authorized": False,
        "stop_condition": "first terminal receipt or any cleanup/source/GPU uncertainty",
    }
    value["planned_scope_spec_sha256"] = _sha(value)
    return value


def post_stage0_f3_scope_publication_v1() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_post_stage0_f3_scope_publication_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "planned_scope_spec": post_stage0_f3_planned_spec_v1(),
        "budget": post_stage0_f3_budget_v1(),
        "impact_review_payload_sha256": (
            "07882b05fe0cbc1932aab24a9b7a4b669f79e53c10504faacd20078947d93325"
        ),
        "stage0_seal_unchanged": True,
        "stage0_result_sha256": (
            "394093a2571269eaa659cc90df654c449ffd1fb3a9ab041bbcfc321231c21df7"
        ),
        "stage0_terminal_seal_sha256": (
            "08ef2c20e6508b32a026fcd168ce5b69bb8686cec0071e5a243d7e211e810783"
        ),
    }
    value["scope_publication_sha256"] = _sha(value)
    return value


def post_stage0_f3_parent_authorization_v1() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_post_stage0_f3_parent_user_authorization_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "approved": True,
        "authorized_scope": SCOPE,
        "maximum_scope_invocations": 1,
        "fresh_scene_count": 3,
        "same_prefix": True,
        "no_suffix": True,
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
        "user_direction_source": "current_2026-08-31_continuation_message_and_sealed_handoff",
    }
    value["parent_user_authorization_sha256"] = hash_json(value)
    return value


__all__ = [
    "AUTHORIZATION_ID",
    "AUTHORIZATION_PATH",
    "BUDGET_PUBLICATION",
    "GROUP",
    "GUARD_PATH",
    "IMPACT_REVIEW",
    "NAMESPACE",
    "OUTPUT_NAMESPACE",
    "PARENT_AUTHORIZATION",
    "REQUEST_PATH",
    "SCENE_SEED",
    "SCOPE",
    "SCOPE_PUBLICATION",
    "SOURCE_LOCK_PATH",
    "post_stage0_f3_budget_v1",
    "post_stage0_f3_parent_authorization_v1",
    "post_stage0_f3_planned_spec_v1",
    "post_stage0_f3_scope_publication_v1",
]
