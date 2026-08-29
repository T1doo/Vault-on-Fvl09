"""User-authorized finite budgets for complete nonformal pre-Stage-0 work.

These envelopes authorize only the named one-shot nonformal scopes derived
from the 2026-08-29 parent user authorization.  They never authorize Stage 0
or formal data.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


BUDGET_SCHEMA_VERSION = "cmf_runtime_v3_1_scope_budget_v1_2"
IMPLEMENTATION_REVISION = "runtime_v3_1_cpu_hardening_v5_1"
SUPPORTED_SCOPES = (
    "A0_current_anchor_smoke",
    "F1_three_branch_nonformal_probe",
    "F2_workspace_and_three_branch_nonformal_probe",
    "F3_release_and_full_program_nonformal_probe",
    "F4_common_carry_and_full_program_nonformal_probe",
    "real_sapien_root_integration_nonformal_probe",
)


SCOPE_BUDGETS_V5_1 = {
    "A0_current_anchor_smoke": {
        "family": "F1",
        "scene_count": 4,
        "scene_pattern": ["A0_pristine", "A0_fresh_1", "A0_fresh_2", "A0_fresh_3"],
        "post_setup_planner_query_limit": 0,
        "post_setup_controlled_action_limit": 0,
        "post_setup_physics_step_limit": 0,
        "execution_limit": 0,
        "timeout_seconds": 600,
        "max_invocations": 1,
        "automatic_retry": False,
        "maximum_implementation_repair_revisions": 1,
        "user_authorized": True,
    },
    "F1_three_branch_nonformal_probe": {
        "family": "F1",
        "branch_order": ["red", "green", "blue"],
        "execution_limit_per_branch": 1,
        "planner_query_limit_per_branch": 12,
        "timeout_seconds_per_branch": 1200,
        "recovery_attempt_limit": 0,
        "automatic_retry": False,
        "maximum_implementation_repair_revisions": 2,
        "user_authorized": True,
    },
    "F2_workspace_and_three_branch_nonformal_probe": {
        "family": "F2",
        "pose_candidate_limit": 6,
        "workspace_preflight_planner_query_limit_total": 16,
        "workspace_repair_execution_limit": 1,
        "root_branch_order": ["inside", "on", "beside"],
        "root_execution_limit_per_branch": 1,
        "root_planner_query_limit_per_branch": 12,
        "timeout_seconds_workspace": 1200,
        "timeout_seconds_per_root_branch": 1200,
        "recovery_attempt_limit": 0,
        "automatic_retry": False,
        "maximum_implementation_repair_revisions": 2,
        "user_authorized": True,
    },
    "F3_release_and_full_program_nonformal_probe": {
        "family": "F3",
        "diagnosis_execution_limit": 1,
        "conditional_repair_execution_limit": 1,
        "full_program_order": ["VVHH", "VHVH", "VHHV"],
        "full_program_execution_limit_per_program": 1,
        "repair_planner_query_limit_per_run": 16,
        "full_program_planner_query_limit_per_program": 32,
        "timeout_seconds_per_run": 1800,
        "recovery_attempt_limit": 0,
        "automatic_retry": False,
        "maximum_implementation_repair_revisions": 2,
        "user_authorized": True,
    },
    "F4_common_carry_and_full_program_nonformal_probe": {
        "family": "F4",
        "route_order": ["route1_minimum_height_segmented", "route2_carry_neutral_fallback"],
        "route_limit": 2,
        "planner_query_limit_per_route": 16,
        "execution_limit_per_route": 1,
        "timeout_seconds_per_route": 1800,
        "post_common_gate_order": [
            "A_only",
            "B_only",
            "C_only",
            "common_X_A_B_noninterference",
            "common_X_ABC",
            "common_X_ACB",
            "common_X_BAC",
        ],
        "post_common_execution_limit_per_item": 1,
        "post_common_planner_query_limit_per_item": 32,
        "post_common_timeout_seconds_per_item": 2400,
        "recovery_attempt_limit": 0,
        "automatic_retry": False,
        "maximum_implementation_repair_revisions": 2,
        "user_authorized": True,
    },
    "real_sapien_root_integration_nonformal_probe": {
        "family": "F1",
        "branch_count": 3,
        "execution_limit_per_branch": 1,
        "planner_query_limit_per_branch": 12,
        "timeout_seconds_per_branch": 1200,
        "recovery_attempt_limit": 0,
        "automatic_retry": False,
        "maximum_implementation_repair_revisions": 1,
        "user_authorized": True,
    },
}


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def budget_artifact() -> dict:
    payload = {
        "schema_version": BUDGET_SCHEMA_VERSION,
        "implementation_revision": IMPLEMENTATION_REVISION,
        "status": "user_authorized_pre_stage0_nonformal",
        "approved": True,
        "frozen": True,
        "gpu_probe_authorized": True,
        "stage0_authorized": False,
        "formal_data": False,
        "stage0_data": False,
        "scopes": SCOPE_BUDGETS_V5_1,
    }
    payload["budget_receipt_sha256"] = _sha256(payload)
    return payload


def budget_receipt_sha256() -> str:
    return budget_artifact()["budget_receipt_sha256"]


def scope_budget(scope: str) -> dict:
    if scope not in SCOPE_BUDGETS_V5_1:
        raise ValueError(f"unsupported runtime-v3_1 scope {scope}")
    value = json.loads(json.dumps(SCOPE_BUDGETS_V5_1[scope], sort_keys=True))
    value["scope"] = scope
    value["scope_budget_sha256"] = _sha256({"scope": scope, "budget": SCOPE_BUDGETS_V5_1[scope]})
    return value


def validate_scope_budget(scope: str, value: Mapping[str, Any]) -> dict:
    expected = scope_budget(scope)
    if not isinstance(value, Mapping) or dict(value) != expected:
        raise ValueError(f"scope budget mismatch for {scope}")
    return expected


def authorization_common_limits(scope: str) -> tuple[int, int, int, int]:
    """Return planner, controlled execution, physics, and timeout envelopes."""

    budget = scope_budget(scope)
    if scope == "A0_current_anchor_smoke":
        return (
            budget["post_setup_planner_query_limit"],
            budget["post_setup_controlled_action_limit"],
            budget["post_setup_physics_step_limit"],
            budget["timeout_seconds"],
        )
    if scope in ("F1_three_branch_nonformal_probe", "real_sapien_root_integration_nonformal_probe"):
        return (
            3 * budget["planner_query_limit_per_branch"],
            3,
            -1,
            3 * budget["timeout_seconds_per_branch"],
        )
    if scope == "F2_workspace_and_three_branch_nonformal_probe":
        return (
            budget["workspace_preflight_planner_query_limit_total"]
            + 3 * budget["root_planner_query_limit_per_branch"],
            budget["workspace_repair_execution_limit"] + 3,
            -1,
            budget["timeout_seconds_workspace"] + 3 * budget["timeout_seconds_per_root_branch"],
        )
    if scope == "F3_release_and_full_program_nonformal_probe":
        return (
            2 * budget["repair_planner_query_limit_per_run"]
            + 3 * budget["full_program_planner_query_limit_per_program"],
            budget["diagnosis_execution_limit"]
            + budget["conditional_repair_execution_limit"]
            + 3 * budget["full_program_execution_limit_per_program"],
            -1,
            5 * budget["timeout_seconds_per_run"],
        )
    if scope == "F4_common_carry_and_full_program_nonformal_probe":
        return (
            budget["route_limit"] * budget["planner_query_limit_per_route"]
            + len(budget["post_common_gate_order"]) * budget["post_common_planner_query_limit_per_item"],
            budget["route_limit"] * budget["execution_limit_per_route"]
            + len(budget["post_common_gate_order"]) * budget["post_common_execution_limit_per_item"],
            -1,
            budget["route_limit"] * budget["timeout_seconds_per_route"]
            + len(budget["post_common_gate_order"]) * budget["post_common_timeout_seconds_per_item"],
        )
    raise ValueError(f"unsupported scope {scope}")


def validate_runtime_receipt_against_budget(scope: str, receipt: Mapping[str, Any]) -> dict:
    budget = scope_budget(scope)
    planner_limit, controlled_limit, physics_limit, _ = authorization_common_limits(scope)
    actual = receipt.get("budget_counts", {}) if isinstance(receipt.get("budget_counts"), Mapping) else {}
    branch_receipts = list(receipt.get("branch_receipts", []))
    observed_planner = int(
        actual.get(
            "planner_query_count",
            int(receipt.get("planner_solvability_query_count_total", 0))
            + int(receipt.get("rollout_planner_query_count") or 0)
            + sum(int(item.get("rollout_planner_query_count") or 0) for item in branch_receipts),
        )
    )
    observed_executions = int(
        actual.get(
            "execution_attempt_count",
            receipt.get("execution_attempt_count", len(branch_receipts)),
        )
    )
    checks = {
        "planner_queries": observed_planner <= planner_limit,
        "controlled_executions": observed_executions <= controlled_limit,
        "no_recovery": int(actual.get("recovery_attempt_count", receipt.get("recovery_attempt_count", 0))) == 0,
    }
    if scope == "A0_current_anchor_smoke":
        checks.update(
            {
                "scene_count": len(receipt.get("scenes", [])) <= budget["scene_count"],
                "planner_queries": int(receipt.get("post_setup_planner_query_count", -1)) == planner_limit,
                "controlled_executions": int(receipt.get("post_setup_controlled_action_count", -1))
                == controlled_limit,
                "post_setup_physics_steps": int(receipt.get("post_setup_physics_step_count", -1)) == physics_limit,
            }
        )
    elif branch_receipts:
        checks["three_branch_limit"] = len(branch_receipts) <= 3
        if scope in ("F1_three_branch_nonformal_probe", "real_sapien_root_integration_nonformal_probe"):
            per_branch_limit = budget["planner_query_limit_per_branch"]
        elif scope == "F2_workspace_and_three_branch_nonformal_probe":
            per_branch_limit = budget["root_planner_query_limit_per_branch"]
        elif scope == "F3_release_and_full_program_nonformal_probe":
            per_branch_limit = budget["full_program_planner_query_limit_per_program"]
        elif scope == "F4_common_carry_and_full_program_nonformal_probe":
            per_branch_limit = budget["post_common_planner_query_limit_per_item"]
        else:
            per_branch_limit = planner_limit
        checks["planner_per_branch"] = all(
            int(item.get("rollout_planner_query_count") or 0) <= per_branch_limit for item in branch_receipts
        )
    result = {"scope": scope, "budget": budget, "checks": checks, "pass": all(checks.values())}
    if not result["pass"]:
        raise ValueError(f"runtime receipt exceeded {scope} budget: {checks}")
    return result
