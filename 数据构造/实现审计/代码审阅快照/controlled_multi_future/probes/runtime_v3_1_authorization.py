"""Fail-closed authorization receipts for runtime-v3_1 GPU children."""

from __future__ import annotations

import hashlib
import json
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
