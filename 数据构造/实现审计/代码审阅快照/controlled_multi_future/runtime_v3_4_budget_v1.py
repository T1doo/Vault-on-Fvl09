"""Finite diagnosis-first nonformal budgets authorized for runtime-v3_4."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


BUDGET_SCHEMA_VERSION = "cmf_runtime_v3_4_scope_budget_v1"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_4"
ALLOWED_PHYSICAL_GPU_INDICES = tuple(range(8))
SUPPORTED_SCOPES = (
    "F1_shared_regression_v3_4",
    "F2_inside_targeted_v10",
    "F2_full_root_v10",
    "F3_grasp_three_context_v10",
    "F3_full_root_v10",
    "F4_corridor_A_v10",
    "F4_BC_AB_v10",
    "F4_full_root_v10",
)
SCOPE_FAMILIES = {
    "F1_shared_regression_v3_4": "F1",
    "F2_inside_targeted_v10": "F2",
    "F2_full_root_v10": "F2",
    "F3_grasp_three_context_v10": "F3",
    "F3_full_root_v10": "F3",
    "F4_corridor_A_v10": "F4",
    "F4_BC_AB_v10": "F4",
    "F4_full_root_v10": "F4",
}
FULL_ROOT_SCOPES = frozenset(
    {
        "F1_shared_regression_v3_4",
        "F2_full_root_v10",
        "F3_full_root_v10",
        "F4_full_root_v10",
    }
)

SCOPE_BUDGETS = {
    "F1_shared_regression_v3_4": {
        "planner_query_limit": 64,
        "execution_limit": 3,
        "timeout_seconds": 7200,
    },
    "F2_inside_targeted_v10": {
        "planner_query_limit": 32,
        "execution_limit": 1,
        "timeout_seconds": 7200,
    },
    "F2_full_root_v10": {
        "planner_query_limit": 32,
        "execution_limit": 3,
        "timeout_seconds": 7200,
    },
    "F3_grasp_three_context_v10": {
        "planner_query_limit": 96,
        "execution_limit": 3,
        "timeout_seconds": 10800,
    },
    "F3_full_root_v10": {
        "planner_query_limit": 96,
        "execution_limit": 3,
        "timeout_seconds": 10800,
    },
    "F4_corridor_A_v10": {
        "planner_query_limit": 64,
        "execution_limit": 1,
        "timeout_seconds": 10800,
    },
    "F4_BC_AB_v10": {
        "planner_query_limit": 64,
        "execution_limit": 3,
        "timeout_seconds": 14400,
    },
    "F4_full_root_v10": {
        "planner_query_limit": 96,
        "execution_limit": 3,
        "timeout_seconds": 20400,
    },
}

STATIC_SCOPE_ACTIVITY_ENVELOPES = {
    "F1_shared_regression_v3_4": {"planner_query_count": 46, "execution_attempt_count": 3},
    "F2_inside_targeted_v10": {"planner_query_count": 16, "execution_attempt_count": 1},
    "F2_full_root_v10": {"planner_query_count": 32, "execution_attempt_count": 3},
    "F3_grasp_three_context_v10": {"planner_query_count": 96, "execution_attempt_count": 3},
    "F3_full_root_v10": {"planner_query_count": 96, "execution_attempt_count": 3},
    "F4_corridor_A_v10": {"planner_query_count": 64, "execution_attempt_count": 1},
    "F4_BC_AB_v10": {"planner_query_count": 64, "execution_attempt_count": 3},
    "F4_full_root_v10": {"planner_query_count": 96, "execution_attempt_count": 3},
}


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def budget_artifact() -> dict[str, Any]:
    payload = {
        "schema_version": BUDGET_SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_strategy": "diagnosis_first_multi_gpu_convergence",
        "status": "user_authorized_nonformal_runtime_v3_4",
        "approved": True,
        "frozen": True,
        "stage0_authorized": False,
        "formal_data": False,
        "stage0_data": False,
        "allowed_physical_gpu_indices": list(ALLOWED_PHYSICAL_GPU_INDICES),
        "maximum_concurrency": "min(ready_scopes, independently_fresh_idle_gpus)",
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "maximum_new_implementation_revisions_per_family": 1,
        "maximum_full_root_execution_per_family": 1,
        "scopes": SCOPE_BUDGETS,
    }
    payload["budget_receipt_sha256"] = _sha256(payload)
    return payload


def budget_receipt_sha256() -> str:
    return budget_artifact()["budget_receipt_sha256"]


def scope_budget(scope: str) -> dict[str, Any]:
    if scope not in SCOPE_BUDGETS:
        raise ValueError(f"unsupported runtime-v3_4 scope {scope}")
    result = json.loads(json.dumps(SCOPE_BUDGETS[scope], sort_keys=True))
    result.update(
        {
            "scope": scope,
            "family": SCOPE_FAMILIES[scope],
            "automatic_retry": False,
            "recovery_attempts": 0,
            "allowed_physical_gpu_indices": list(ALLOWED_PHYSICAL_GPU_INDICES),
        }
    )
    result["scope_budget_sha256"] = _sha256(
        {"scope": scope, "budget": SCOPE_BUDGETS[scope]}
    )
    return result


def validate_static_scope_activity_envelope(scope: str) -> dict[str, Any]:
    budget = scope_budget(scope)
    envelope = STATIC_SCOPE_ACTIVITY_ENVELOPES[scope]
    checks = {
        "planner_within_budget": 0
        <= envelope["planner_query_count"]
        <= budget["planner_query_limit"],
        "execution_within_budget": 0
        <= envelope["execution_attempt_count"]
        <= budget["execution_limit"],
    }
    result = {
        "scope": scope,
        "scope_budget_sha256": budget["scope_budget_sha256"],
        "source_bound_static_envelope": dict(envelope),
        "checks": checks,
        "pass": all(checks.values()),
    }
    if not result["pass"]:
        raise ValueError("runtime-v3_4 static envelope exceeds budget")
    return result


def validate_runtime_receipt_against_budget(
    scope: str, receipt: Mapping[str, Any]
) -> dict[str, Any]:
    budget = scope_budget(scope)
    counts = receipt.get("budget_counts")
    if not isinstance(counts, Mapping):
        raise ValueError("runtime-v3_4 receipt lacks budget_counts")
    normalized = {}
    for key in (
        "planner_query_count",
        "execution_attempt_count",
        "recovery_attempt_count",
    ):
        value = counts.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"invalid runtime-v3_4 budget count {key}")
        normalized[key] = value
    envelope = validate_static_scope_activity_envelope(scope)[
        "source_bound_static_envelope"
    ]
    checks = {
        "planner_within_budget": normalized["planner_query_count"]
        <= budget["planner_query_limit"],
        "execution_within_budget": normalized["execution_attempt_count"]
        <= budget["execution_limit"],
        "no_recovery": normalized["recovery_attempt_count"] == 0,
        "planner_within_source_envelope": normalized["planner_query_count"]
        <= envelope["planner_query_count"],
        "execution_within_source_envelope": normalized[
            "execution_attempt_count"
        ]
        <= envelope["execution_attempt_count"],
    }
    result = {
        "scope": scope,
        "budget": budget,
        "source_bound_static_envelope": envelope,
        "checks": checks,
        "pass": all(checks.values()),
    }
    if not result["pass"]:
        raise ValueError(f"runtime-v3_4 receipt exceeded budget: {checks}")
    return result


__all__ = [
    "ALLOWED_PHYSICAL_GPU_INDICES",
    "FULL_ROOT_SCOPES",
    "SCOPE_FAMILIES",
    "SUPPORTED_SCOPES",
    "budget_artifact",
    "budget_receipt_sha256",
    "scope_budget",
    "validate_runtime_receipt_against_budget",
    "validate_static_scope_activity_envelope",
]
