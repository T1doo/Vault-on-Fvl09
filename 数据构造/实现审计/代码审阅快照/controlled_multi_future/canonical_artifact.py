"""One fail-closed canonical JSON, hashing and receipt implementation."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping

import numpy as np


class CanonicalArtifactError(ValueError):
    """A value is outside the frozen canonical JSON algebra."""


def canonical_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, np.ndarray):
        return canonical_jsonable(value.tolist())
    if isinstance(value, np.generic):
        return canonical_jsonable(value.item())
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        result = float(value)
        if not math.isfinite(result):
            raise CanonicalArtifactError("canonical JSON rejects NaN/Inf")
        return result
    if isinstance(value, Mapping):
        normalized = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalArtifactError(
                    "canonical JSON mapping keys must be strings"
                )
            normalized[key] = canonical_jsonable(item)
        return normalized
    if isinstance(value, (list, tuple)):
        return [canonical_jsonable(item) for item in value]
    raise CanonicalArtifactError(
        f"unsupported canonical JSON value: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        canonical_jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_hash_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def canonical_write_json(
    path: Path,
    value: Any,
    *,
    exclusive: bool = False,
    mode: int = 0o644,
) -> dict[str, Any]:
    path = Path(path)
    normalized = canonical_jsonable(value)
    data = (
        json.dumps(
            normalized,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    if exclusive:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    else:
        temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        descriptor = os.open(
            temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode
        )
    try:
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise OSError("short canonical JSON write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if temporary is not None:
        os.replace(temporary, path)
    return {
        "path": str(path.resolve()),
        "bytes": len(data),
        "file_sha256": hashlib.sha256(data).hexdigest(),
        "canonical_payload_sha256": canonical_hash_json(normalized),
    }


def build_self_hashed_receipt(
    value: Mapping[str, Any], *, hash_field: str = "receipt_sha256"
) -> dict[str, Any]:
    if not isinstance(hash_field, str) or not hash_field:
        raise CanonicalArtifactError("self-hash field must be non-empty")
    receipt = canonical_jsonable(value)
    if not isinstance(receipt, dict):
        raise CanonicalArtifactError("self-hashed receipt must be a mapping")
    if hash_field in receipt:
        raise CanonicalArtifactError(f"self-hash field already exists: {hash_field}")
    receipt[hash_field] = canonical_hash_json(receipt)
    return receipt


def validate_self_hashed_receipt(
    value: Mapping[str, Any], *, hash_field: str = "receipt_sha256"
) -> dict[str, Any]:
    receipt = canonical_jsonable(value)
    if not isinstance(receipt, dict):
        raise CanonicalArtifactError("self-hashed receipt must be a mapping")
    claimed = receipt.pop(hash_field, None)
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise CanonicalArtifactError(f"missing canonical self-hash: {hash_field}")
    if canonical_hash_json(receipt) != claimed:
        raise CanonicalArtifactError(f"canonical self-hash mismatch: {hash_field}")
    receipt[hash_field] = claimed
    return receipt


__all__ = [
    "CanonicalArtifactError",
    "build_self_hashed_receipt",
    "canonical_hash_json",
    "canonical_json_bytes",
    "canonical_jsonable",
    "canonical_write_json",
    "validate_self_hashed_receipt",
]
