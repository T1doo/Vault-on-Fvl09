"""Attempt receipt construction and fail-closed lifecycle fields."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .schemas import TERMINAL_ATTEMPT_STATUSES, validate_attempt_counts


def initial_attempt_receipt(*, family: str, namespace: str, purpose: str = "nonformal_feasibility") -> dict:
    return {
        "schema_version": "cmf_attempt_receipt_v2",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "family": family,
        "namespace": namespace,
        "purpose": purpose,
        "formal_data": False,
        "stage0_data": False,
        "status": "running",
        "scene_created": False,
        "scene_cleanup_attempted": False,
        "scene_cleanup_succeeded": False,
        "cleanup_error": None,
        "partial_output_status": "none",
        "gpu_postcheck": "pending_external_postcheck",
        "orphan_process_count": None,
        "attempt_counts": {
            "feasibility_query_count": 0,
            "planner_query_count": 0,
            "execution_attempt_count": 0,
            "recovery_attempt_count": 0,
        },
    }


def finalize_attempt_receipt(receipt: dict, status: str, *, gpu_postcheck: Any, orphan_process_count: int) -> dict:
    if status not in TERMINAL_ATTEMPT_STATUSES:
        raise ValueError(f"unsupported terminal status: {status}")
    validate_attempt_counts(receipt["attempt_counts"])
    receipt["gpu_postcheck"] = gpu_postcheck
    receipt["orphan_process_count"] = int(orphan_process_count)
    if receipt.get("scene_created") and not receipt.get("scene_cleanup_succeeded"):
        status = "failed_cleanup_uncertain"
    if orphan_process_count:
        status = "failed_cleanup_uncertain"
    receipt["status"] = status
    return receipt


def write_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(receipt), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
