"""Canonical, finite JSON and hash helpers for immutable execution evidence."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


class CanonicalizationError(ValueError):
    """Raised when evidence cannot be represented deterministically."""


def _check(value: Any, path: str = "$ ") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise CanonicalizationError(f"non-finite number at {path}")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError(f"non-string key at {path}")
            _check(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _check(item, f"{path}[{index}]")


def canonical_json(value: Any) -> bytes:
    _check(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CanonicalizationError(str(exc)) from exc


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: str | Path, value: Any) -> None:
    """Write a JSON receipt without exposing a partial file on interruption."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(payload)
        stream.flush()
        import os

        os.fsync(stream.fileno())
    temporary.replace(target)
