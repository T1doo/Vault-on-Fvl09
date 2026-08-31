"""Finite budgets for the v13 infrastructure check and v1.1 Stage 0 smoke."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


IMPLEMENTATION_VERSION = "controlled_multi_future_stage0_smoke_v1_1"
BUDGET_SCHEMA_VERSION = "cmf_stage0_smoke_budget_v1_1"
ALLOWED_PHYSICAL_GPU_INDICES = tuple(range(8))
F4_INFRA_SCOPE = "F4_candidate_hash_infra_v13"
STAGE0_SCOPES = (
    "Stage0_v1_1_F1_root_A",
    "Stage0_v1_1_F2_root_A",
    "Stage0_v1_1_F3_root_A",
    "Stage0_v1_1_F4_root_A",
)
SUPPORTED_SCOPES = (F4_INFRA_SCOPE, *STAGE0_SCOPES)
SCOPE_FAMILIES = {
    F4_INFRA_SCOPE: "F4",
    "Stage0_v1_1_F1_root_A": "F1",
    "Stage0_v1_1_F2_root_A": "F2",
    "Stage0_v1_1_F3_root_A": "F3",
    "Stage0_v1_1_F4_root_A": "F4",
}
SCOPE_BUDGETS = {
    F4_INFRA_SCOPE: {
        "planner_query_limit": 48,
        "execution_limit": 0,
        "timeout_seconds": 7200,
        "stage0_data": False,
    },
    "Stage0_v1_1_F1_root_A": {
        "planner_query_limit": 64,
        "execution_limit": 3,
        "timeout_seconds": 7200,
        "stage0_data": True,
    },
    "Stage0_v1_1_F2_root_A": {
        "planner_query_limit": 64,
        "execution_limit": 3,
        "timeout_seconds": 7200,
        "stage0_data": True,
    },
    "Stage0_v1_1_F3_root_A": {
        "planner_query_limit": 96,
        "execution_limit": 3,
        "timeout_seconds": 10800,
        "stage0_data": True,
    },
    "Stage0_v1_1_F4_root_A": {
        "planner_query_limit": 96,
        "execution_limit": 3,
        "timeout_seconds": 20400,
        "stage0_data": True,
    },
}


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def budget_artifact() -> dict[str, Any]:
    result = {
        "schema_version": BUDGET_SCHEMA_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_revision": (
            "f4_canonical_neutral_provenance_v13_then_12_smoke_v1_1"
        ),
        "status": "user_authorized_f4_v13_then_stage0_smoke_v1_1",
        "approved": True,
        "stage0_authorized": True,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
        "h_reveal": None,
        "compression_authorized": False,
        "pi05_authorized": False,
        "stage0_planned_attempt_count": 12,
        "stage0_success_required_for_completion": False,
        "stage0_generated_trajectory_mp4_required": True,
        "stage0_video_contract": {
            "format": "mp4",
            "camera": "head_camera",
            "video_fps": 25,
            "control_frequency_hz": 250,
            "sample_stride_steps": 10,
            "initial_and_final_frames_required": True,
            "no_trajectory_status": "video_not_applicable_no_trajectory",
        },
        "allowed_family_outcomes": ["PASS", "FAILED_WITH_EVIDENCE"],
        "allowed_physical_gpu_indices": list(ALLOWED_PHYSICAL_GPU_INDICES),
        "family_level_parallelism_authorized": True,
        "one_project_job_per_gpu": True,
        "one_family_root_one_gpu": True,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "scope_max_invocations": 1,
        "scopes": SCOPE_BUDGETS,
    }
    result["budget_receipt_sha256"] = _sha(result)
    return result


def budget_receipt_sha256() -> str:
    return budget_artifact()["budget_receipt_sha256"]


def scope_budget(scope: str) -> dict[str, Any]:
    if scope not in SCOPE_BUDGETS:
        raise ValueError(f"unsupported Stage 0 v1.1 scope {scope}")
    result = json.loads(json.dumps(SCOPE_BUDGETS[scope], sort_keys=True))
    result.update(
        {
            "scope": scope,
            "family": SCOPE_FAMILIES[scope],
            "allowed_physical_gpu_indices": list(
                ALLOWED_PHYSICAL_GPU_INDICES
            ),
            "automatic_retry": False,
            "recovery_attempts": 0,
        }
    )
    result["scope_budget_sha256"] = _sha(
        {"scope": scope, "budget": SCOPE_BUDGETS[scope]}
    )
    return result


def validate_runtime_counts(
    scope: str, counts: Mapping[str, Any]
) -> dict[str, Any]:
    budget = scope_budget(scope)
    planner = int(counts.get("planner_query_count", -1))
    execution = int(counts.get("execution_attempt_count", -1))
    recovery = int(counts.get("recovery_attempt_count", -1))
    checks = {
        "planner_nonnegative_within_budget": 0
        <= planner
        <= budget["planner_query_limit"],
        "execution_nonnegative_within_budget": 0
        <= execution
        <= budget["execution_limit"],
        "recovery_zero": recovery == 0,
    }
    result = {"scope": scope, "checks": checks, "pass": all(checks.values())}
    if not result["pass"]:
        raise ValueError(f"Stage 0 v1.1 scope exceeded budget: {checks}")
    return result


__all__ = [
    "ALLOWED_PHYSICAL_GPU_INDICES",
    "F4_INFRA_SCOPE",
    "SCOPE_FAMILIES",
    "STAGE0_SCOPES",
    "SUPPORTED_SCOPES",
    "budget_artifact",
    "budget_receipt_sha256",
    "scope_budget",
    "validate_runtime_counts",
]
