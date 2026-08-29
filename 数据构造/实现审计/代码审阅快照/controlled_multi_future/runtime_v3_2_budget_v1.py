"""Finite user-authorized nonformal budgets for runtime-v3_2."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


BUDGET_SCHEMA_VERSION = "cmf_runtime_v3_2_scope_budget_v1"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_2"
IMPLEMENTATION_REVISION = "runtime_v3_2_common_hardening_v1"
SUPPORTED_SCOPES = (
    "F1_three_branch_nonformal_probe_v3_2",
    "F2_asset_mapping_and_three_branch_nonformal_probe_v3_2",
    "F3_grasp_lift_and_full_program_nonformal_probe_v3_2",
    "F4_arm_asset_layout_and_full_program_nonformal_probe_v3_2",
    "real_sapien_root_integration_nonformal_probe_v3_2",
)


SCOPE_BUDGETS = {
    "F1_three_branch_nonformal_probe_v3_2": {
        "family": "F1",
        "branch_order": ["red", "green", "blue"],
        "execution_limit_per_branch": 1,
        "planner_query_limit_per_branch": 12,
        "timeout_seconds_per_branch": 1200,
        "maximum_new_repair_revisions": 1,
        "recovery_attempt_limit": 0,
        "automatic_retry": False,
    },
    "F2_asset_mapping_and_three_branch_nonformal_probe_v3_2": {
        "family": "F2",
        "asset_combination_execution_limit": 1,
        "root_execution_limit_per_branch": 1,
        "planner_query_limit_per_branch": 12,
        "timeout_seconds_per_branch": 1200,
        "maximum_new_repair_revisions": 1,
        "recovery_attempt_limit": 0,
        "automatic_retry": False,
    },
    "F3_grasp_lift_and_full_program_nonformal_probe_v3_2": {
        "family": "F3",
        "diagnostic_execution_limit": 1,
        "repair_execution_limit": 1,
        "full_program_execution_limit_per_program": 1,
        "program_order": ["VVHH", "VHVH", "VHHV"],
        "planner_query_limit_per_diagnostic_run": 16,
        "planner_query_limit_per_full_program": 32,
        "timeout_seconds_per_run": 1800,
        "maximum_new_repair_revisions": 2,
        "recovery_attempt_limit": 0,
        "automatic_retry": False,
    },
    "F4_arm_asset_layout_and_full_program_nonformal_probe_v3_2": {
        "family": "F4",
        "layout_preflight_execution_limit": 1,
        "common_route_execution_limit": 2,
        "post_common_execution_limit": 7,
        "planner_query_limit_total": 256,
        "timeout_seconds_total": 20400,
        "maximum_new_repair_revisions": 2,
        "recovery_attempt_limit": 0,
        "automatic_retry": False,
    },
    "real_sapien_root_integration_nonformal_probe_v3_2": {
        "family": "F1",
        "branch_count": 3,
        "execution_limit_per_branch": 1,
        "planner_query_limit_per_branch": 12,
        "timeout_seconds_per_branch": 1200,
        "maximum_new_repair_revisions": 1,
        "recovery_attempt_limit": 0,
        "automatic_retry": False,
    },
}


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def budget_artifact() -> dict:
    payload = {
        "schema_version": BUDGET_SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_revision": IMPLEMENTATION_REVISION,
        "status": "user_authorized_pre_stage0_nonformal_v3_2",
        "approved": True,
        "frozen": True,
        "gpu_probe_authorized": True,
        "stage0_authorized": False,
        "formal_data": False,
        "stage0_data": False,
        "scopes": SCOPE_BUDGETS,
    }
    payload["budget_receipt_sha256"] = _sha256(payload)
    return payload


def budget_receipt_sha256() -> str:
    return budget_artifact()["budget_receipt_sha256"]


def scope_budget(scope: str) -> dict:
    if scope not in SCOPE_BUDGETS:
        raise ValueError(f"unsupported runtime-v3_2 scope {scope}")
    value = json.loads(json.dumps(SCOPE_BUDGETS[scope], sort_keys=True))
    value["scope"] = scope
    value["scope_budget_sha256"] = _sha256({"scope": scope, "budget": SCOPE_BUDGETS[scope]})
    return value


def validate_scope_budget(scope: str, value: Mapping[str, Any]) -> dict:
    expected = scope_budget(scope)
    if not isinstance(value, Mapping) or dict(value) != expected:
        raise ValueError(f"scope budget mismatch for {scope}")
    return expected


def authorization_common_limits(scope: str) -> tuple[int, int, int, int]:
    budget = scope_budget(scope)
    if scope in ("F1_three_branch_nonformal_probe_v3_2", "real_sapien_root_integration_nonformal_probe_v3_2"):
        return 3 * budget["planner_query_limit_per_branch"], 3, -1, 3 * budget["timeout_seconds_per_branch"]
    if scope == "F2_asset_mapping_and_three_branch_nonformal_probe_v3_2":
        return 4 * budget["planner_query_limit_per_branch"], 4, -1, 4 * budget["timeout_seconds_per_branch"]
    if scope == "F3_grasp_lift_and_full_program_nonformal_probe_v3_2":
        planner = 2 * budget["planner_query_limit_per_diagnostic_run"] + 3 * budget["planner_query_limit_per_full_program"]
        return planner, 5, -1, 5 * budget["timeout_seconds_per_run"]
    if scope == "F4_arm_asset_layout_and_full_program_nonformal_probe_v3_2":
        return budget["planner_query_limit_total"], 10, -1, budget["timeout_seconds_total"]
    raise ValueError(f"unsupported runtime-v3_2 scope {scope}")


def validate_runtime_receipt_against_budget(scope: str, receipt: Mapping[str, Any]) -> dict:
    budget = scope_budget(scope)
    planner_limit, execution_limit, _, _ = authorization_common_limits(scope)
    counts = receipt.get("budget_counts", {}) if isinstance(receipt.get("budget_counts"), Mapping) else {}
    checks = {
        "planner_queries": int(counts.get("planner_query_count", 0)) <= planner_limit,
        "controlled_executions": int(counts.get("execution_attempt_count", 0)) <= execution_limit,
        "no_recovery": int(counts.get("recovery_attempt_count", 0)) == 0,
    }
    result = {"scope": scope, "budget": budget, "checks": checks, "pass": all(checks.values())}
    if not result["pass"]:
        raise ValueError(f"runtime-v3_2 receipt exceeded budget: {checks}")
    return result
