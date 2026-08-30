"""Finalize four family receipts into a 12-attempt Stage 0 outcome."""

from __future__ import annotations

from typing import Any, Mapping

from .current_hasher import hash_json


FAMILIES = ("F1", "F2", "F3", "F4")


def finalize_stage0_smoke_v1(
    family_receipts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if set(family_receipts) != set(FAMILIES):
        raise ValueError("Stage 0 finalizer requires exactly F1-F4 receipts")
    normalized = {family: dict(family_receipts[family]) for family in FAMILIES}
    attempts = [
        dict(attempt)
        for family in FAMILIES
        for attempt in normalized[family].get("attempt_receipts", [])
    ]
    attempt_ids = [item.get("attempt_id") for item in attempts]
    family_outcomes = {
        family: normalized[family].get("outcome") for family in FAMILIES
    }
    checks = {
        "exact_four_family_receipts": len(normalized) == 4,
        "exact_twelve_attempt_receipts": len(attempts) == 12,
        "exact_three_attempts_per_family": all(
            sum(item.get("family") == family for item in attempts) == 3
            for family in FAMILIES
        ),
        "attempt_ids_unique": len(attempt_ids) == len(set(attempt_ids)) == 12,
        "all_attempts_terminal": all(
            item.get("terminal_status") in ("PASS", "FAILED_WITH_EVIDENCE")
            for item in attempts
        ),
        "all_attempts_stage0_not_formal": all(
            item.get("stage0_data") is True
            and item.get("stage0_authorized") is True
            and item.get("formal_data") is False
            for item in attempts
        ),
        "all_family_pipeline_integrity_pass": all(
            normalized[family].get("pipeline_integrity_pass") is True
            for family in FAMILIES
        ),
        "all_family_cleanup_pass": all(
            normalized[family].get("cleanup_pass") is True
            and int(normalized[family].get("orphan_process_count", 0)) == 0
            for family in FAMILIES
        ),
        "family_outcomes_valid": all(
            value in ("PASS", "FAILED_WITH_EVIDENCE")
            for value in family_outcomes.values()
        ),
    }
    pipeline_complete = all(checks.values())
    overall_outcome = (
        "PASS"
        if pipeline_complete and all(value == "PASS" for value in family_outcomes.values())
        else "FAILED_WITH_EVIDENCE"
    )
    result = {
        "schema_version": "cmf_stage0_smoke_finalizer_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_stage0_smoke_v1",
        "stage0_completed": pipeline_complete,
        "stage0_outcome": overall_outcome,
        "family_outcomes": family_outcomes,
        "planned_attempt_count": 12,
        "terminal_attempt_count": len(attempts),
        "successful_attempt_count": sum(
            item["terminal_status"] == "PASS" for item in attempts
        ),
        "failed_attempt_count": sum(
            item["terminal_status"] == "FAILED_WITH_EVIDENCE"
            for item in attempts
        ),
        "generated_trajectory_count": sum(
            item.get("trajectory_generated") is True for item in attempts
        ),
        "attempt_receipts": attempts,
        "checks": checks,
        "accepted_formal_root_count": 0,
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
    }
    result["receipt_sha256"] = hash_json(result)
    return result


__all__ = ["finalize_stage0_smoke_v1"]
