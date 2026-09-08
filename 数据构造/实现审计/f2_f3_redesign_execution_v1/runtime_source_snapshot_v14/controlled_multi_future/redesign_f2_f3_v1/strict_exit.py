"""Fail-closed nested whitelist for observable model input."""

from __future__ import annotations

import math
from typing import Any, Mapping


class StrictExitError(ValueError):
    """Raised when an observable payload can carry hidden execution truth."""


TOP_LEVEL = {"rgb", "state", "future", "candidate_set", "target"}
FORBIDDEN = ("path", "file", "local", "branch", "instance", "planner", "phase", "verifier", "truth", "contact", "pose", "success")


def _finite_array(value: Any, name: str) -> tuple[int, ...]:
    if not isinstance(value, list):
        raise StrictExitError(f"{name} must be a list")
    if not value:
        raise StrictExitError(f"{name} must be non-empty")
    child_shapes = []
    for item in value:
        if isinstance(item, list):
            child_shapes.append(_finite_array(item, name))
        elif isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)):
            raise StrictExitError(f"{name} contains a non-finite scalar")
        else:
            child_shapes.append(())
    if len(set(child_shapes)) != 1:
        raise StrictExitError(f"{name} must be rectangular")
    return (len(value),) + child_shapes[0]


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
    rgb_shape = _finite_array(payload["rgb"], "rgb")
    state_shape = _finite_array(payload["state"], "state")
    future_shape = _finite_array(payload["future"], "future")
    if len(rgb_shape) not in {3, 4} or rgb_shape[-1] != 3:
        raise StrictExitError("rgb must be rectangular HxWx3 or VxHxWx3")
    def rgb_scalars(value):
        for item in value:
            if isinstance(item, list):
                yield from rgb_scalars(item)
            else:
                yield item
    if any(not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 255 for value in rgb_scalars(payload["rgb"])):
        raise StrictExitError("rgb must contain uint8-compatible integer values")
    if state_shape != (76,):
        raise StrictExitError("state must be exactly 38 qpos plus 38 qvel values")
    if len(future_shape) != 2 or future_shape[1] != 26:
        raise StrictExitError("future must be a non-empty sequence of 26-D effective setpoints")
    if not isinstance(payload["candidate_set"], list) or len(payload["candidate_set"]) != 3:
        raise StrictExitError("candidate_set must contain exactly three candidates")
    for candidate in payload["candidate_set"]:
        if not isinstance(candidate, Mapping) or set(candidate) != {"family", "relation", "object_ref"}:
            raise StrictExitError("candidate schema is not strict")
        if not all(isinstance(candidate[key], str) and candidate[key] for key in candidate):
            raise StrictExitError("candidate values must be non-empty strings")
    if not isinstance(payload["target"], Mapping) or set(payload["target"]) != {"family", "relation", "object_ref"}:
        raise StrictExitError("target schema is not strict")
    if not all(isinstance(payload["target"][key], str) and payload["target"][key] for key in payload["target"]):
        raise StrictExitError("target values must be non-empty strings")
    candidate_identities = {(item["family"], item["relation"], item["object_ref"]) for item in payload["candidate_set"]}
    if len(candidate_identities) != 3:
        raise StrictExitError("candidate_set identities must be unique")
    target_identity = tuple(payload["target"][key] for key in ("family", "relation", "object_ref"))
    if target_identity not in candidate_identities:
        raise StrictExitError("target must match one candidate identity")
    return dict(payload)
