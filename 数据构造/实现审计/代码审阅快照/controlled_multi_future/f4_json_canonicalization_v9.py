"""JSON-safe canonicalization for the F4 revision-9 staged callback boundary.

The real revision-8 staged preflight passed SAPIEN actor poses as NumPy
arrays.  The route builder's historical JSON round-trip accepted only plain
lists and failed before any block execution.  This additive helper changes no
numeric value or route semantics; it only converts NumPy containers/scalars to
the same JSON primitives produced by the list-valued CPU contract.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np


SCHEMA_VERSION = "cmf_f4_numpy_json_canonicalization_v9"
CANONICALIZATION_VERSION = "f4_numpy_json_safe_canonicalization_v9"


def _numpy_json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(
        f"Object of type {value.__class__.__name__} is not JSON serializable"
    )


def json_safe_clone_v9(value: Any) -> Any:
    """Return a detached, finite JSON tree while preserving numeric values."""

    return json.loads(
        json.dumps(
            value,
            default=_numpy_json_default,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
        )
    )


__all__ = [
    "CANONICALIZATION_VERSION",
    "SCHEMA_VERSION",
    "json_safe_clone_v9",
]
