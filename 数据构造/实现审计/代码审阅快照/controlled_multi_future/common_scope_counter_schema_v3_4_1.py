"""Shared counter/failure receipts for runtime-v3_4_1.

This module is CPU-only and deliberately separates planner scope totals from
the subset of planner queries that produced executable cached controls.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


SCHEMA_VERSION = "cmf_common_scope_counter_schema_runtime_v3_4_1"
FAILURE_SCHEMA_VERSION = "cmf_primary_failure_cleanup_receipt_v3_4_1"
EVIDENCE_SCHEMA_VERSION = "cmf_evidence_completeness_classification_v3_4_1"
PLANNER_FIELDS = (
    "canonical_prefix",
    "target_construction",
    "suffix_control_chain",
    "diagnostic_only",
)
EXECUTION_FIELDS = (
    "dispatch_started",
    "controller_entered",
    "terminal_receipt_written",
)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _count(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


def build_planner_query_counts(
    *,
    canonical_prefix: int = 0,
    target_construction: int = 0,
    suffix_control_chain: int = 0,
    diagnostic_only: int = 0,
) -> dict[str, Any]:
    raw = {
        "canonical_prefix": canonical_prefix,
        "target_construction": target_construction,
        "suffix_control_chain": suffix_control_chain,
        "diagnostic_only": diagnostic_only,
    }
    values = {
        name: _count(raw[name], f"planner_query_counts.{name}")
        for name in PLANNER_FIELDS
    }
    values["scope_total"] = sum(values.values())
    result = {
        "schema_version": SCHEMA_VERSION,
        **values,
        "identity": (
            "scope_total = canonical_prefix + target_construction + "
            "suffix_control_chain + diagnostic_only"
        ),
        "budget_count_field": "scope_total",
        "executable_control_cache_count_field": "suffix_control_chain",
    }
    result["receipt_sha256"] = canonical_sha256(result)
    return result


def validate_planner_query_counts(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("planner query count schema mismatch")
    result = json.loads(json.dumps(value, sort_keys=True, allow_nan=False))
    digest = result.pop("receipt_sha256", None)
    if not isinstance(digest, str) or digest != canonical_sha256(result):
        raise ValueError("planner query count receipt hash mismatch")
    counts = {name: _count(result.get(name), name) for name in PLANNER_FIELDS}
    total = _count(result.get("scope_total"), "scope_total")
    if total != sum(counts.values()):
        raise ValueError("planner scope_total identity failed")
    if result.get("budget_count_field") != "scope_total":
        raise ValueError("planner budget count field changed")
    if result.get("executable_control_cache_count_field") != "suffix_control_chain":
        raise ValueError("executable control count field changed")
    result["receipt_sha256"] = digest
    return result


def add_planner_query_counts(*values: Mapping[str, Any]) -> dict[str, Any]:
    totals = {name: 0 for name in PLANNER_FIELDS}
    for value in values:
        checked = validate_planner_query_counts(value)
        for name in PLANNER_FIELDS:
            totals[name] += int(checked[name])
    return build_planner_query_counts(**totals)


def build_execution_attempt_counts(
    *,
    dispatch_started: int,
    controller_entered: int,
    terminal_receipt_written: int,
) -> dict[str, Any]:
    raw = {
        "dispatch_started": dispatch_started,
        "controller_entered": controller_entered,
        "terminal_receipt_written": terminal_receipt_written,
    }
    values = {
        name: _count(raw[name], f"execution_attempt_counts.{name}")
        for name in EXECUTION_FIELDS
    }
    if not (
        values["terminal_receipt_written"]
        <= values["controller_entered"]
        <= values["dispatch_started"]
    ):
        raise ValueError("execution attempt lifecycle counts are not monotonic")
    result = {
        "schema_version": SCHEMA_VERSION,
        **values,
        "budget_count_field": "dispatch_started",
        "dispatch_is_counted_before_controller_call": True,
        "finally_persistence_required": True,
    }
    result["receipt_sha256"] = canonical_sha256(result)
    return result


def validate_execution_attempt_counts(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("execution count schema mismatch")
    result = json.loads(json.dumps(value, sort_keys=True, allow_nan=False))
    digest = result.pop("receipt_sha256", None)
    if not isinstance(digest, str) or digest != canonical_sha256(result):
        raise ValueError("execution count receipt hash mismatch")
    expected = build_execution_attempt_counts(
        **{name: result[name] for name in EXECUTION_FIELDS}
    )
    if any(result.get(key) != expected.get(key) for key in expected if key != "receipt_sha256"):
        raise ValueError("execution lifecycle contract changed")
    result["receipt_sha256"] = digest
    return result


def classify_evidence_field(
    *, field_name: str, present: bool, condition_pass: bool | None
) -> dict[str, Any]:
    if not isinstance(field_name, str) or not field_name:
        raise ValueError("evidence field_name is invalid")
    if not present:
        status = "infrastructure_schema_failure"
        evidence_complete = False
        normalized_condition = None
    else:
        if not isinstance(condition_pass, bool):
            raise ValueError("present evidence must carry a boolean condition")
        status = "condition_pass" if condition_pass else "physical_or_planner_failure"
        evidence_complete = True
        normalized_condition = condition_pass
    result = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "field_name": field_name,
        "field_present": bool(present),
        "evidence_complete": evidence_complete,
        "condition_pass": normalized_condition,
        "classification": status,
    }
    result["receipt_sha256"] = canonical_sha256(result)
    return result


def build_primary_failure_cleanup_receipt(
    *,
    primary_failure: Mapping[str, Any] | None,
    cleanup_status: Mapping[str, Any],
    receipt_propagation_status: str,
) -> dict[str, Any]:
    if primary_failure is not None:
        required = {"stage", "type", "message"}
        if not required.issubset(primary_failure):
            raise ValueError("primary_failure lacks stage/type/message")
    required_cleanup = {"attempted", "passed", "uncertainty"}
    if not required_cleanup.issubset(cleanup_status):
        raise ValueError("cleanup_status is incomplete")
    if cleanup_status["passed"] is True and cleanup_status["uncertainty"] is True:
        raise ValueError("cleanup cannot pass while remaining uncertain")
    result = {
        "schema_version": FAILURE_SCHEMA_VERSION,
        "primary_failure": None
        if primary_failure is None
        else {
            "stage": str(primary_failure["stage"]),
            "type": str(primary_failure["type"]),
            "message": str(primary_failure["message"]),
        },
        "cleanup_status": {
            "attempted": cleanup_status["attempted"] is True,
            "passed": cleanup_status["passed"] is True,
            "uncertainty": cleanup_status["uncertainty"] is True,
        },
        "receipt_propagation_status": str(receipt_propagation_status),
        "primary_failure_may_not_be_overwritten_by_cleanup": True,
    }
    result["receipt_sha256"] = canonical_sha256(result)
    return result


__all__ = [
    "add_planner_query_counts",
    "build_execution_attempt_counts",
    "build_planner_query_counts",
    "build_primary_failure_cleanup_receipt",
    "canonical_sha256",
    "classify_evidence_field",
    "validate_execution_attempt_counts",
    "validate_planner_query_counts",
]
