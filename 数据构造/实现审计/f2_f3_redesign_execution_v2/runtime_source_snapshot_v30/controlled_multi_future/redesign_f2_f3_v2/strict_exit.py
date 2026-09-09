"""Strict model-input boundary for v2.

The answer belongs to supervision.  ``inputs`` deliberately has no target,
path, instance, planner or verifier fields.
"""

from __future__ import annotations

import math
from typing import Any, Mapping


class StrictExitError(ValueError):
    pass


TOP_LEVEL = {"rgb", "state", "future", "candidate_set"}
FORBIDDEN = ("path", "file", "local", "branch", "instance", "planner", "phase", "verifier", "truth", "contact", "pose", "success", "target", "answer")


def _shape(value: Any, name: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise StrictExitError(f"{name} must be a non-empty JSON list")
    children = [_shape(item, name) if isinstance(item, list) else () for item in value]
    if len(set(children)) != 1:
        raise StrictExitError(f"{name} must be rectangular")
    for item in value:
        if not isinstance(item, list) and (isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item))):
            raise StrictExitError(f"{name} has invalid scalar")
    return (len(value),) + children[0]


def _walk(value: Any, location: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = key.lower() if isinstance(key, str) else ""
            if not isinstance(key, str) or lowered == "target" or any(token in lowered for token in FORBIDDEN if token != "target"):
                raise StrictExitError(f"forbidden field at {location}")
            _walk(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _walk(item, f"{location}[{index}]")


def validate_observable_inputs(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != TOP_LEVEL:
        raise StrictExitError("inputs must contain exactly rgb/state/future/candidate_set")
    _walk(payload, "$")
    rgb = payload["rgb"]; state = payload["state"]; future = payload["future"]
    rgb_shape = _shape(rgb, "rgb"); state_shape = _shape(state, "state"); future_shape = _shape(future, "future")
    if len(rgb_shape) not in {3, 4} or rgb_shape[-1] != 3:
        raise StrictExitError("rgb must be HxWx3 or VxHxWx3")
    def scalars(value):
        for item in value:
            yield from scalars(item) if isinstance(item, list) else [item]
    if any(isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 255 for value in scalars(rgb)):
        raise StrictExitError("rgb must use uint8-compatible integer values")
    if state_shape != (76,):
        raise StrictExitError("state must be exactly 38 qpos+38qvel")
    if len(future_shape) != 2 or future_shape[1] != 26:
        raise StrictExitError("future must be [N,26]")
    candidates = payload["candidate_set"]
    if not isinstance(candidates, list) or len(candidates) != 3:
        raise StrictExitError("candidate_set must contain three candidates")
    families = {item.get("family") if isinstance(item, Mapping) else None for item in candidates}
    if len(families) != 1 or families not in ({"F2"}, {"F3"}):
        raise StrictExitError("candidate families must be one coherent F2 or F3 set")
    expected = {"family", "object_ref", "target_ref", "relation", "program_id"} if families == {"F2"} else {"family", "object_ref", "program_id", "event_sequence"}
    identities = []
    for item in candidates:
        if not isinstance(item, Mapping) or set(item) != expected or any(not isinstance(v, str) or not v for v in item.values()):
            raise StrictExitError("candidate schema/value invalid")
        identities.append(tuple(sorted(item.items())))
    if len(set(identities)) != 3:
        raise StrictExitError("candidate identities must be unique")
    return dict(payload)


def validate_numpy_observable_inputs(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the producer's native fixed-array interface without JSONifying RGB."""
    import numpy as np

    if not isinstance(payload, Mapping) or set(payload) != TOP_LEVEL:
        raise StrictExitError("numpy inputs must contain exactly rgb/state/future/candidate_set")
    rgb = payload["rgb"]
    if not isinstance(rgb, Mapping) or not rgb:
        raise StrictExitError("rgb must be an ordered camera mapping")
    names = tuple(rgb)
    if names != tuple(sorted(names)):
        raise StrictExitError("camera order must be canonical and explicit")
    if any(not isinstance(value, np.ndarray) or value.ndim != 3 or value.shape[-1] != 3 or value.dtype != np.uint8 or not np.isfinite(value).all() for value in rgb.values()):
        raise StrictExitError("rgb camera arrays must be finite native uint8 HxWx3")
    state = payload["state"]; future = payload["future"]
    if not isinstance(state, np.ndarray) or state.shape != (76,) or state.dtype.kind not in "fc" or not np.isfinite(state).all():
        raise StrictExitError("state must be finite native [76]")
    if not isinstance(future, np.ndarray) or future.ndim != 2 or future.shape[1] != 26 or future.shape[0] < 1 or future.dtype.kind not in "fc" or not np.isfinite(future).all():
        raise StrictExitError("future must be finite native [N,26]")
    candidates = payload["candidate_set"]
    if not isinstance(candidates, list) or len(candidates) != 3:
        raise StrictExitError("candidate_set must contain three candidates")
    families = {item.get("family") if isinstance(item, Mapping) else None for item in candidates}
    if len(families) != 1 or families not in ({"F2"}, {"F3"}):
        raise StrictExitError("candidate families must be one coherent F2 or F3 set")
    expected = {"family", "object_ref", "target_ref", "relation", "program_id"} if families == {"F2"} else {"family", "object_ref", "program_id", "event_sequence"}
    identities = []
    for item in candidates:
        if not isinstance(item, Mapping) or set(item) != expected or any(not isinstance(value, str) or not value for value in item.values()):
            raise StrictExitError("candidate schema/value invalid")
        identities.append(tuple(sorted(item.items())))
    if len(set(identities)) != 3:
        raise StrictExitError("candidate identities must be unique")
    return dict(payload)


def validate_inputs_supervision_audit(*, inputs: Mapping[str, Any], supervision: Mapping[str, Any], audit: Mapping[str, Any]) -> dict[str, Any]:
    import numpy as np
    if isinstance(inputs.get("state") if isinstance(inputs, Mapping) else None, np.ndarray):
        validate_numpy_observable_inputs(inputs)
    else:
        validate_observable_inputs(inputs)
    if not isinstance(supervision, Mapping) or "target" not in supervision:
        raise StrictExitError("supervision must carry target outside inputs")
    if not isinstance(audit, Mapping):
        raise StrictExitError("audit envelope missing")
    return {"inputs": dict(inputs), "supervision": dict(supervision), "audit": dict(audit)}


def strict_negative_tests() -> dict[str, bool]:
    candidates = [{"family": "F2", "object_ref": "main_can", "target_ref": x, "relation": x, "program_id": x} for x in ("inside", "on", "beside")]
    valid = {"rgb": [[[0, 1, 2]]], "state": [0.0] * 76, "future": [[0.0] * 26], "candidate_set": candidates}
    validate_observable_inputs(valid)
    checks = {"valid": True}
    for name, bad in (("target", {**valid, "target": candidates[0]}), ("planner", {**valid, "state": {"planner_phase": 1}}), ("wrong_rgb", {**valid, "rgb": [[[0, 1]]]}), ("wrong_state", {**valid, "state": [0.0] * 75}), ("wrong_candidate", {**valid, "candidate_set": [{"family": "F2", "relation": "inside", "object_ref": "main_can"}] * 3})):
        try:
            validate_observable_inputs(bad); checks[name] = False
        except StrictExitError:
            checks[name] = True
    return checks | {"pass": all(checks.values())}
