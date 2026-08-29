"""Finite user-authorized nonformal budgets for runtime-v3_3."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


BUDGET_SCHEMA_VERSION = "cmf_runtime_v3_3_scope_budget_v1"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_3"
SUPPORTED_SCOPES = (
    "canonical_prefix_real_smoke",
    "F4_cube_grasp_no_action_ik",
    "F1_planner_root_per_revision",
    "F2_diagnosis_root_per_revision",
    "F3_prefix_root_per_revision",
    "F4_block_root_per_revision",
)

SCOPE_FAMILIES = {
    "canonical_prefix_real_smoke": "F1",
    "F4_cube_grasp_no_action_ik": "F4",
    "F1_planner_root_per_revision": "F1",
    "F2_diagnosis_root_per_revision": "F2",
    "F3_prefix_root_per_revision": "F3",
    "F4_block_root_per_revision": "F4",
}
ROOT_SCOPES = frozenset(
    {
        "F1_planner_root_per_revision",
        "F2_diagnosis_root_per_revision",
        "F3_prefix_root_per_revision",
        "F4_block_root_per_revision",
    }
)


SCOPE_BUDGETS = {
    "canonical_prefix_real_smoke": {
        "planner_query_limit": 16,
        "execution_limit": 1,
        "timeout_seconds": 1800,
    },
    "F4_cube_grasp_no_action_ik": {
        "planner_query_limit": 24,
        "execution_limit": 0,
        "timeout_seconds": 1800,
    },
    "F1_planner_root_per_revision": {
        "planner_query_limit": 64,
        "execution_limit": 3,
        "timeout_seconds": 5400,
    },
    "F2_diagnosis_root_per_revision": {
        "planner_query_limit": 96,
        "execution_limit": 4,
        "timeout_seconds": 7200,
    },
    "F3_prefix_root_per_revision": {
        "planner_query_limit": 160,
        "execution_limit": 4,
        "timeout_seconds": 10800,
    },
    "F4_block_root_per_revision": {
        "planner_query_limit": 256,
        "execution_limit": 10,
        "timeout_seconds": 20400,
    },
}


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def budget_artifact() -> dict:
    payload = {
        "schema_version": BUDGET_SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "status": "user_authorized_pre_stage0_nonformal_v3_3",
        "approved": True,
        "frozen": True,
        "stage0_authorized": False,
        "formal_data": False,
        "stage0_data": False,
        "allowed_physical_gpu_indices": [0],
        "automatic_retry": False,
        "recovery_attempts": 0,
        "maximum_new_implementation_revisions_per_family": 2,
        "maximum_full_root_execution_per_revision": 1,
        "scopes": SCOPE_BUDGETS,
    }
    payload["budget_receipt_sha256"] = _sha256(payload)
    return payload


def budget_receipt_sha256() -> str:
    return budget_artifact()["budget_receipt_sha256"]


def scope_budget(scope: str) -> dict:
    if scope not in SCOPE_BUDGETS:
        raise ValueError(f"unsupported runtime-v3_3 scope {scope}")
    value = json.loads(json.dumps(SCOPE_BUDGETS[scope], sort_keys=True))
    value.update(
        {
            "scope": scope,
            "family": SCOPE_FAMILIES[scope],
            "automatic_retry": False,
            "recovery_attempts": 0,
        }
    )
    value["scope_budget_sha256"] = _sha256(
        {"scope": scope, "budget": SCOPE_BUDGETS[scope]}
    )
    return value


def validate_scope_budget(scope: str, value: Mapping[str, Any]) -> dict:
    expected = scope_budget(scope)
    if not isinstance(value, Mapping) or dict(value) != expected:
        raise ValueError(f"runtime-v3_3 budget mismatch for {scope}")
    return expected


def authorization_common_limits(scope: str) -> tuple[int, int, int, int]:
    budget = scope_budget(scope)
    return (
        int(budget["planner_query_limit"]),
        int(budget["execution_limit"]),
        -1,
        int(budget["timeout_seconds"]),
    )


def validate_runtime_receipt_against_budget(
    scope: str, receipt: Mapping[str, Any]
) -> dict:
    planner_limit, execution_limit, _, _ = authorization_common_limits(scope)
    counts = receipt.get("budget_counts")
    if not isinstance(counts, Mapping):
        raise ValueError("runtime-v3_3 receipt lacks budget_counts")
    required_counts = {
        "planner_query_count",
        "execution_attempt_count",
        "recovery_attempt_count",
    }
    if not required_counts.issubset(counts):
        raise ValueError("runtime-v3_3 receipt has incomplete budget counts")
    normalized_counts = {}
    for key in required_counts:
        raw = counts[key]
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
            raise ValueError(f"runtime-v3_3 budget count {key} must be a nonnegative integer")
        normalized_counts[key] = raw
    checks = {
        "planner_queries": normalized_counts["planner_query_count"]
        <= planner_limit,
        "controlled_executions": normalized_counts[
            "execution_attempt_count"
        ]
        <= execution_limit,
        "no_recovery": normalized_counts["recovery_attempt_count"] == 0,
    }
    result = {
        "scope": scope,
        "budget": scope_budget(scope),
        "checks": checks,
        "pass": all(checks.values()),
    }
    if not result["pass"]:
        raise ValueError(f"runtime-v3_3 receipt exceeded budget: {checks}")
    return result
