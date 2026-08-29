"""Shared planner/geometry dtype boundary for runtime-v3_2."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np


PLANNER_DTYPE = np.dtype(np.float32)
GEOMETRY_DTYPE = np.dtype(np.float64)


def planner_array(value: Any, *, shape=None, label: str = "planner value") -> np.ndarray:
    result = np.ascontiguousarray(np.asarray(value, dtype=PLANNER_DTYPE))
    if shape is not None:
        try:
            result = result.reshape(shape)
        except ValueError as exc:
            raise ValueError(f"{label} has invalid shape {result.shape}, expected {shape}") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{label} contains non-finite values")
    return result


def geometry_array(value: Any, *, shape=None, label: str = "geometry value") -> np.ndarray:
    result = np.ascontiguousarray(np.asarray(value, dtype=GEOMETRY_DTYPE))
    if shape is not None:
        try:
            result = result.reshape(shape)
        except ValueError as exc:
            raise ValueError(f"{label} has invalid shape {result.shape}, expected {shape}") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{label} contains non-finite values")
    return result


def normalize_planner_control(control: Mapping[str, Any]) -> dict:
    if not isinstance(control, Mapping):
        raise TypeError("planner control must be a mapping")
    result = dict(control)
    for key in ("position", "velocity", "acceleration", "jerk"):
        if key in result and result[key] is not None:
            result[key] = planner_array(result[key], label=f"planner control {key}")
    return result


def planner_dtype_receipt(*, qpos=None, goal_pose=None, control=None) -> dict:
    receipt = {
        "schema_version": "cmf_planner_dtype_contract_v3_2",
        "planner_dtype": str(PLANNER_DTYPE),
        "geometry_dtype": str(GEOMETRY_DTYPE),
    }
    if qpos is not None:
        value = planner_array(qpos, label="qpos")
        receipt["qpos"] = {"dtype": str(value.dtype), "shape": list(value.shape)}
    if goal_pose is not None:
        value = planner_array(goal_pose, shape=(7,), label="goal pose")
        receipt["goal_pose"] = {"dtype": str(value.dtype), "shape": list(value.shape)}
    if control is not None:
        value = normalize_planner_control(control)
        receipt["control"] = {
            key: {"dtype": str(item.dtype), "shape": list(item.shape)}
            for key, item in value.items()
            if isinstance(item, np.ndarray)
        }
    return receipt
