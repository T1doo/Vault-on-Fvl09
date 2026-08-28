"""Fail-closed authorization receipts for runtime-v3_1 GPU children."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def load_runtime_v3_1_authorization(path: Path, *, requested_scope: str) -> dict:
    if not path.is_file():
        raise PermissionError("runtime-v3_1 GPU execution requires an explicit authorization receipt")
    value = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version": "cmf_runtime_v3_1_gpu_authorization_v1",
        "implementation_version": "controlled_multi_future_runtime_v3_1",
        "approved": True,
        "stage0_authorized": False,
        "formal_data": False,
        "stage0_data": False,
    }
    for key, expected in required.items():
        if value.get(key) != expected:
            raise PermissionError(f"authorization receipt rejected field {key}")
    scopes = value.get("approved_scopes")
    if not isinstance(scopes, list) or requested_scope not in scopes:
        raise PermissionError(f"authorization receipt does not approve {requested_scope}")
    if not isinstance(value.get("receipt_sha256"), str) or len(value["receipt_sha256"]) != 64:
        raise PermissionError("authorization receipt requires a sealed receipt_sha256")
    sealed = dict(value)
    expected_sha256 = sealed.pop("receipt_sha256")
    actual_sha256 = hashlib.sha256(
        json.dumps(sealed, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    if actual_sha256 != expected_sha256:
        raise PermissionError("authorization receipt SHA-256 does not match its canonical payload")
    return value


def authorization_summary(value: Mapping[str, Any]) -> dict:
    return {
        "authorization_receipt_sha256": value["receipt_sha256"],
        "approved_scopes": list(value["approved_scopes"]),
        "stage0_authorized": False,
        "formal_data": False,
        "stage0_data": False,
    }


def require_atomic_gpu_guard(*, expected_uuid: str, physical_index: int) -> dict:
    path_value = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    index_value = os.environ.get("CMF_GPU_GUARD_PHYSICAL_INDEX")
    if not path_value or index_value != str(physical_index):
        raise PermissionError("runtime-v3_1 child must be launched by the atomic GPU guard")
    path = Path(path_value)
    if not path.is_file():
        raise PermissionError("atomic GPU guard precheck receipt is missing")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    precheck = receipt.get("precheck")
    try:
        captured_at = datetime.fromisoformat(precheck.get("captured_at")) if isinstance(precheck, Mapping) else None
        if captured_at is None or captured_at.tzinfo is None:
            raise ValueError
        age_seconds = (datetime.now(timezone.utc) - captured_at.astimezone(timezone.utc)).total_seconds()
    except (TypeError, ValueError):
        age_seconds = float("inf")
    if (
        receipt.get("schema_version") != "cmf_gpu_guard_v2"
        or receipt.get("status") != "precheck_passed"
        or receipt.get("physical_gpu_index") != physical_index
        or receipt.get("expected_gpu_uuid") != expected_uuid
        or receipt.get("guard_pid") != os.getppid()
        or not isinstance(precheck, Mapping)
        or precheck.get("uuid") != expected_uuid
        or precheck.get("memory_used_mib", 10**9) > 100
        or precheck.get("utilization_percent", 100) > 1
        or precheck.get("pstate") != "P8"
        or precheck.get("compute_processes")
        or not (0.0 <= age_seconds <= 60.0)
    ):
        raise PermissionError("atomic GPU guard receipt does not prove a fresh-idle matching device")
    return {"path": str(path), "guard_pid": receipt["guard_pid"], "precheck_age_seconds": age_seconds, "precheck": dict(precheck)}
