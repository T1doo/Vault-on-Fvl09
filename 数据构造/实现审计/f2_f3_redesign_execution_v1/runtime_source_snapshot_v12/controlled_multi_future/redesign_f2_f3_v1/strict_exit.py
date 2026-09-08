"""Fail-closed nested whitelist for observable model input."""

from __future__ import annotations

import math
from typing import Any, Mapping


class StrictExitError(ValueError):
    """Raised when an observable payload can carry hidden execution truth."""


TOP_LEVEL = {"rgb", "state", "future", "candidate_set", "target"}
FORBIDDEN = ("path", "file", "local", "branch", "instance", "planner", "phase", "verifier", "truth", "contact", "pose", "success")


def _finite_array(value: Any, name: str) -> None:
    if not isinstance(value, list):
        raise StrictExitError(f"{name} must be a list")
    for item in value:
        if isinstance(item, list):
            _finite_array(item, name)
        elif isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)):
            raise StrictExitError(f"{name} contains a non-finite scalar")


def _reject_nested(value: Any, location: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise StrictExitError(f"non-string key at {location}")
            lowered = key.lower()
            if any(token in lowered for token in FORBIDDEN):
                raise StrictExitError(f"forbidden field {location}.{key}")
            _reject_nested(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_nested(item, f"{location}[{index}]")


def validate_observable_input(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise StrictExitError("observable input must be a mapping")
    unknown = set(payload) - TOP_LEVEL
    if unknown:
        raise StrictExitError(f"unknown top-level fields: {sorted(unknown)}")
    if set(payload) != TOP_LEVEL:
        raise StrictExitError("observable input requires exactly the five top-level fields")
    _reject_nested(payload, "$")
    _finite_array(payload["rgb"], "rgb")
    _finite_array(payload["state"], "state")
    _finite_array(payload["future"], "future")
    if not isinstance(payload["candidate_set"], list) or not payload["candidate_set"]:
        raise StrictExitError("candidate_set must be a non-empty list")
    for candidate in payload["candidate_set"]:
        if not isinstance(candidate, Mapping) or set(candidate) != {"family", "relation", "object_ref"}:
            raise StrictExitError("candidate schema is not strict")
        if not all(isinstance(candidate[key], str) and candidate[key] for key in candidate):
            raise StrictExitError("candidate values must be non-empty strings")
    if not isinstance(payload["target"], Mapping) or set(payload["target"]) != {"family", "relation", "object_ref"}:
        raise StrictExitError("target schema is not strict")
    if not all(isinstance(payload["target"][key], str) and payload["target"][key] for key in payload["target"]):
        raise StrictExitError("target values must be non-empty strings")
    return dict(payload)
