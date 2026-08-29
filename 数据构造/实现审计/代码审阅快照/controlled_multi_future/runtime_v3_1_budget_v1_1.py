"""Machine-enforced finite nonformal probe budgets for runtime-v3_1 v5.

The values remain proposed and unapproved.  This module makes the proposal
machine-checkable; it does not authorize any scope.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


BUDGET_SCHEMA_VERSION = "cmf_runtime_v3_1_scope_budget_v1_1"
SUPPORTED_SCOPES = (
    "A0_current_anchor_smoke",
    "F1_three_branch_nonformal_probe",
    "F2_beside_nonformal_probe",
    "F3_release_diagnosis_nonformal_probe",
    "F4_common_carry_nonformal_probe",
    "real_sapien_root_integration_nonformal_probe",
)


SCOPE_BUDGETS_V5 = {
    "A0_current_anchor_smoke": {
        "family": "F1",
        "scene_count": 4,
        "scene_pattern": ["A0_pristine", "A0_fresh_1", "A0_fresh_2", "A0_fresh_3"],
        "planner_query_limit": 0,
        "controlled_action_limit": 0,
        "execution_limit": 0,
        "timeout_seconds": 600,
        "max_invocations": 1,
        "automatic_retry": False,
        "currently_requestable": True,
    },
    "F1_three_branch_nonformal_probe": {
        "family": "F1",
        "branch_order": ["red", "green", "blue"],
        "execution_limit_per_branch": 1,
        "planner_query_limit_per_branch": 12,
        "timeout_seconds_per_branch": 1200,
        "recovery_attempt_limit": 0,
        "automatic_retry": False,
        "currently_requestable": False,
    },
    "F2_beside_nonformal_probe": {
        "family": "F2",
        "pose_candidate_limit": 6,
        "planner_query_limit_total": 16,
        "execution_limit": 1,
        "timeout_seconds": 1200,
        "recovery_attempt_limit": 0,
        "automatic_retry": False,
        "currently_requestable": False,
    },
    "F3_release_diagnosis_nonformal_probe": {
        "family": "F3",
        "diagnosis_execution_limit": 1,
        "conditional_correction_execution_limit": 1,
        "planner_query_limit_per_run": 16,
        "timeout_seconds_per_run": 1800,
        "recovery_attempt_limit": 0,
        "automatic_retry": False,
        "currently_requestable": False,
    },
    "F4_common_carry_nonformal_probe": {
        "family": "F4",
        "route_order": ["route1_minimum_height_segmented", "route2_carry_neutral_fallback"],
        "route_limit": 2,
        "planner_query_limit_per_route": 16,
        "execution_limit_per_route": 1,
        "timeout_seconds_per_route": 1800,
        "recovery_attempt_limit": 0,
        "automatic_retry": False,
        "currently_requestable": False,
    },
    "real_sapien_root_integration_nonformal_probe": {
        "family": "F1",
        "branch_count": 3,
        "execution_limit_per_branch": 1,
        "planner_query_limit_per_branch": 12,
        "timeout_seconds_per_branch": 1200,
        "recovery_attempt_limit": 0,
        "automatic_retry": False,
        "currently_requestable": False,
    },
}


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def budget_artifact() -> dict:
    payload = {
        "schema_version": BUDGET_SCHEMA_VERSION,
        "implementation_revision": "runtime_v3_1_cpu_hardening_v5",
        "status": "proposed_for_user_review",
        "approved": False,
        "frozen": False,
        "gpu_probe_authorized": False,
        "stage0_authorized": False,
        "scopes": SCOPE_BUDGETS_V5,
    }
    payload["budget_receipt_sha256"] = _sha256(payload)
    return payload


def budget_receipt_sha256() -> str:
    return budget_artifact()["budget_receipt_sha256"]


def scope_budget(scope: str) -> dict:
    if scope not in SCOPE_BUDGETS_V5:
        raise ValueError(f"unsupported runtime-v3_1 scope {scope}")
    value = json.loads(json.dumps(SCOPE_BUDGETS_V5[scope], sort_keys=True))
    value["scope"] = scope
    value["scope_budget_sha256"] = _sha256({"scope": scope, "budget": SCOPE_BUDGETS_V5[scope]})
    return value


def validate_scope_budget(scope: str, value: Mapping[str, Any]) -> dict:
    expected = scope_budget(scope)
    if not isinstance(value, Mapping) or dict(value) != expected:
        raise ValueError(f"scope budget mismatch for {scope}")
    return expected


def validate_runtime_receipt_against_budget(scope: str, receipt: Mapping[str, Any]) -> dict:
    """Fail closed if a completed launcher/orchestrator exceeded its envelope."""

    budget = scope_budget(scope)
    checks: dict[str, bool] = {}
    if scope == "A0_current_anchor_smoke":
        checks = {
            "scene_count": len(receipt.get("scenes", [])) <= budget["scene_count"],
            "planner_queries": int(receipt.get("post_setup_planner_query_count", 0))
            <= budget["planner_query_limit"],
            "controlled_actions": int(receipt.get("post_setup_controlled_action_count", 0))
            <= budget["controlled_action_limit"],
        }
    elif scope in ("F1_three_branch_nonformal_probe", "real_sapien_root_integration_nonformal_probe"):
        branches = list(receipt.get("branch_receipts", []))
        checks = {
            "branch_count": len(branches) <= 3,
            "planner_per_branch": all(
                int(item.get("rollout_planner_query_count", 0)) <= budget["planner_query_limit_per_branch"]
                for item in branches
            ),
            "no_recovery": int(receipt.get("recovery_attempt_count", 0)) == 0,
        }
    elif scope == "F2_beside_nonformal_probe":
        checks = {
            "pose_candidates": len(receipt.get("planner_variant_receipts", [])) <= budget["pose_candidate_limit"],
            "planner_total": int(receipt.get("planner_solvability_query_count_total", 0))
            + int(receipt.get("rollout_planner_query_count") or 0)
            <= budget["planner_query_limit_total"],
            "execution": int(receipt.get("execution_attempt_count", 1 if receipt.get("rollout_attempted") else 0))
            <= budget["execution_limit"],
        }
    elif scope == "F3_release_diagnosis_nonformal_probe":
        attempts = list(receipt.get("attempts", []))
        diagnosis = sum(item.get("attempt_kind") == "diagnosis" for item in attempts)
        correction = sum(item.get("attempt_kind") == "correction" for item in attempts)
        checks = {
            "diagnosis_execution": diagnosis <= budget["diagnosis_execution_limit"],
            "conditional_correction": correction <= budget["conditional_correction_execution_limit"],
            "planner_per_run": all(
                int(item.get("planner_solvability_query_count", 0))
                + int(item.get("rollout_planner_query_count", 0))
                <= budget["planner_query_limit_per_run"]
                for item in receipt.get("planner_query_count_by_run", attempts)
            ),
        }
    elif scope == "F4_common_carry_nonformal_probe":
        routes = list(receipt.get("planner_variant_receipts", []))
        checks = {
            "route_count": len(routes) <= budget["route_limit"],
            "planner_per_route": all(
                int(item.get("planner_query_count", 0)) <= budget["planner_query_limit_per_route"]
                for item in routes
            ),
            "execution_per_route": int(receipt.get("execution_attempt_count", 0)) <= budget["route_limit"],
        }
    else:
        raise ValueError(f"unsupported receipt budget validator scope {scope}")
    result = {"scope": scope, "budget": budget, "checks": checks, "pass": all(checks.values())}
    if not result["pass"]:
        raise ValueError(f"runtime receipt exceeded {scope} budget: {checks}")
    return result
