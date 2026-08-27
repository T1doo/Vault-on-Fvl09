"""Fail-closed pilot finalization checks."""

from __future__ import annotations

from typing import Any, Mapping


REQUIRED_ACCEPTANCE = (
    "same_current_pass",
    "anchor_equivalence_pass",
    "candidate_freeze_pass",
    "prefix_freeze_pass",
    "raw_contract_pass",
    "family_verifier_pass",
    "cleanup_pass",
    "orphan_audit_pass",
)


def finalize_nonformal_integration(checks: Mapping[str, Any]) -> dict:
    missing = [key for key in REQUIRED_ACCEPTANCE if key not in checks]
    failed = [key for key in REQUIRED_ACCEPTANCE if key in checks and checks[key] is not True]
    return {
        "accepted": not missing and not failed,
        "missing_checks": missing,
        "failed_checks": failed,
        "formal_data": False,
        "stage0_data": False,
    }
