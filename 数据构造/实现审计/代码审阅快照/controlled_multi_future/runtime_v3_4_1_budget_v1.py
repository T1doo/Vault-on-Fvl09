"""Single-freeze finite budgets for runtime-v3_4_1."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


BUDGET_SCHEMA_VERSION = "cmf_runtime_v3_4_1_scope_budget_v1"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_4_1"
ALLOWED_PHYSICAL_GPU_INDICES = (0,)
SUPPORTED_SCOPES = (
    "F1_shared_regression_v3_4_1",
    "F2_inside_targeted_v11",
    "F2_full_root_v3_4_1",
    "F3_three_context_targeted_v11",
    "F3_full_root_v3_4_1",
    "F4_exact_corridor_A_v11",
    "F4_BC_preflight_v11",
    "F4_full_root_v3_4_1",
)
SCOPE_FAMILIES = {
    "F1_shared_regression_v3_4_1": "F1",
    "F2_inside_targeted_v11": "F2",
    "F2_full_root_v3_4_1": "F2",
    "F3_three_context_targeted_v11": "F3",
    "F3_full_root_v3_4_1": "F3",
    "F4_exact_corridor_A_v11": "F4",
    "F4_BC_preflight_v11": "F4",
    "F4_full_root_v3_4_1": "F4",
}
FULL_ROOT_SCOPES = frozenset(
    {
        "F1_shared_regression_v3_4_1",
        "F2_full_root_v3_4_1",
        "F3_full_root_v3_4_1",
        "F4_full_root_v3_4_1",
    }
)
SCOPE_BUDGETS = {
    "F1_shared_regression_v3_4_1": {
        "planner_query_limit": 64,
        "execution_limit": 3,
        "timeout_seconds": 7200,
    },
    "F2_inside_targeted_v11": {
        "planner_query_limit": 32,
        "execution_limit": 1,
        "timeout_seconds": 7200,
    },
    "F2_full_root_v3_4_1": {
        "planner_query_limit": 32,
        "execution_limit": 3,
        "timeout_seconds": 7200,
    },
    "F3_three_context_targeted_v11": {
        "planner_query_limit": 48,
        "execution_limit": 3,
        "timeout_seconds": 10800,
    },
    "F3_full_root_v3_4_1": {
        "planner_query_limit": 96,
        "execution_limit": 3,
        "timeout_seconds": 10800,
    },
    "F4_exact_corridor_A_v11": {
        "planner_query_limit": 64,
        "execution_limit": 1,
        "timeout_seconds": 14400,
    },
    "F4_BC_preflight_v11": {
        "planner_query_limit": 32,
        "execution_limit": 0,
        "timeout_seconds": 10800,
    },
    "F4_full_root_v3_4_1": {
        "planner_query_limit": 96,
        "execution_limit": 3,
        "timeout_seconds": 20400,
    },
}
STATIC_SCOPE_ACTIVITY_ENVELOPES = {
    "F1_shared_regression_v3_4_1": {
        "planner_query_count": 46,
        "execution_attempt_count": 3,
    },
    "F2_inside_targeted_v11": {
        "planner_query_count": 22,
        "execution_attempt_count": 1,
    },
    "F2_full_root_v3_4_1": {
        "planner_query_count": 32,
        "execution_attempt_count": 3,
    },
    "F3_three_context_targeted_v11": {
        "planner_query_count": 42,
        "execution_attempt_count": 3,
    },
    "F3_full_root_v3_4_1": {
        "planner_query_count": 96,
        "execution_attempt_count": 3,
    },
    "F4_exact_corridor_A_v11": {
        "planner_query_count": 58,
        "execution_attempt_count": 1,
    },
    "F4_BC_preflight_v11": {
        "planner_query_count": 26,
        "execution_attempt_count": 0,
    },
    "F4_full_root_v3_4_1": {
        "planner_query_count": 82,
        "execution_attempt_count": 3,
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
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_strategy": "one_shot_postmortem_hardening",
        "status": "user_authorized_nonformal_runtime_v3_4_1",
        "approved": True,
        "frozen": True,
        "single_source_freeze": True,
        "second_freeze_forbidden": True,
        "stage0_authorized": False,
        "formal_data": False,
        "stage0_data": False,
        "allowed_physical_gpu_indices": list(ALLOWED_PHYSICAL_GPU_INDICES),
        "automatic_retry": False,
        "recovery_attempts": 0,
        "maximum_scope_invocations": 1,
        "maximum_full_root_execution_per_family": 1,
        "scopes": SCOPE_BUDGETS,
    }
    result["budget_receipt_sha256"] = _sha(result)
    return result


def budget_receipt_sha256() -> str:
    return budget_artifact()["budget_receipt_sha256"]


def scope_budget(scope: str) -> dict[str, Any]:
    if scope not in SCOPE_BUDGETS:
        raise ValueError(f"unsupported v3_4_1 scope {scope}")
    result = json.loads(json.dumps(SCOPE_BUDGETS[scope], sort_keys=True))
    result.update(
        {
            "scope": scope,
            "family": SCOPE_FAMILIES[scope],
            "allowed_physical_gpu_indices": list(ALLOWED_PHYSICAL_GPU_INDICES),
            "automatic_retry": False,
            "recovery_attempts": 0,
        }
    )
    result["scope_budget_sha256"] = _sha(
        {"scope": scope, "budget": SCOPE_BUDGETS[scope]}
    )
    return result


def validate_static_scope_activity_envelope(scope: str) -> dict[str, Any]:
    budget = scope_budget(scope)
    envelope = STATIC_SCOPE_ACTIVITY_ENVELOPES[scope]
    checks = {
        "planner_within_budget": envelope["planner_query_count"]
        <= budget["planner_query_limit"],
        "execution_within_budget": envelope["execution_attempt_count"]
        <= budget["execution_limit"],
    }
    result = {
        "scope": scope,
        "source_bound_static_envelope": dict(envelope),
        "scope_budget_sha256": budget["scope_budget_sha256"],
        "checks": checks,
        "pass": all(checks.values()),
    }
    if not result["pass"]:
        raise ValueError("v3_4_1 static envelope exceeds budget")
    return result


def validate_runtime_receipt_against_budget(
    scope: str, receipt: Mapping[str, Any]
) -> dict[str, Any]:
    budget = scope_budget(scope)
    counts = receipt.get("budget_counts")
    if not isinstance(counts, Mapping):
        raise ValueError("v3_4_1 receipt lacks budget_counts")
    planner = int(counts.get("planner_query_count", -1))
    execution = int(counts.get("execution_attempt_count", -1))
    recovery = int(counts.get("recovery_attempt_count", -1))
    envelope = STATIC_SCOPE_ACTIVITY_ENVELOPES[scope]
    checks = {
        "planner_nonnegative_within_budget": 0 <= planner <= budget[
            "planner_query_limit"
        ],
        "execution_nonnegative_within_budget": 0 <= execution <= budget[
            "execution_limit"
        ],
        "recovery_zero": recovery == 0,
        "planner_within_source_envelope": planner
        <= envelope["planner_query_count"],
        "execution_within_source_envelope": execution
        <= envelope["execution_attempt_count"],
    }
    result = {
        "scope": scope,
        "checks": checks,
        "pass": all(checks.values()),
        "budget": budget,
        "source_bound_static_envelope": envelope,
    }
    if not result["pass"]:
        raise ValueError(f"v3_4_1 receipt exceeded budget: {checks}")
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
