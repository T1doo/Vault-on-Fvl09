"""Pure CPU planner-control retiming candidate for the P4 F3-B repair.

The factor is deliberately a candidate until a bounded qualification run.  It
changes the movement duration at 250 Hz and scales derivative fields; changing
hold frames or sleeping in the coordinator is not equivalent.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import numpy as np


def _resample(values: np.ndarray, new_count: int) -> np.ndarray:
    old_count = int(values.shape[0])
    old_t = np.arange(old_count, dtype=np.float64)
    new_t = np.linspace(0.0, float(old_count - 1), int(new_count))
    if values.ndim == 1:
        return np.interp(new_t, old_t, values).astype(values.dtype, copy=False)
    columns = [np.interp(new_t, old_t, values[:, index]) for index in range(values.shape[1])]
    return np.stack(columns, axis=1).astype(values.dtype, copy=False)


def retime_planner_control(control: Mapping[str, Any], *, factor: float = 1.5) -> dict[str, Any]:
    if not isinstance(control, Mapping) or control.get("status") != "Success":
        raise ValueError("retiming requires a successful planner control")
    if isinstance(factor, bool) or not np.isfinite(float(factor)) or float(factor) <= 1.0:
        raise ValueError("retiming factor must be finite and greater than one")
    required = ("position", "velocity")
    if any(field not in control for field in required):
        raise ValueError("planner control is missing position or velocity")
    arrays: dict[str, np.ndarray] = {}
    count: int | None = None
    for field in ("position", "velocity", "acceleration", "jerk"):
        if control.get(field) is None:
            continue
        value = np.asarray(control[field])
        if value.ndim != 2 or value.shape[0] < 2 or not np.issubdtype(value.dtype, np.floating) or not np.isfinite(value).all():
            raise ValueError(f"planner control {field} must be finite floating [N,J]")
        if count is None:
            count = int(value.shape[0])
        if value.shape[0] != count:
            raise ValueError("planner control arrays must share their step count")
        arrays[field] = np.ascontiguousarray(value)
    if count is None:
        raise ValueError("planner control has no numeric arrays")

    output_count = int(np.ceil((count - 1) * float(factor))) + 1
    derivative_order = {"position": 0, "velocity": 1, "acceleration": 2, "jerk": 3}
    transformed = deepcopy(dict(control))
    for field, value in arrays.items():
        sampled = _resample(value, output_count)
        scale = float(factor) ** derivative_order[field]
        transformed[field] = np.ascontiguousarray(sampled / scale)
    transformed["position"][0] = arrays["position"][0]
    transformed["position"][-1] = arrays["position"][-1]
    transformed["_cmf_time_dilation"] = {
        "schema_version": "cmf_f3_time_dilation_candidate_v1",
        "factor": float(factor),
        "input_step_count": count,
        "output_step_count": output_count,
        "fixed_frequency_hz": 250,
        "derivative_scales": {field: float(1.0 / (float(factor) ** derivative_order[field])) for field in arrays},
        "position_endpoints_preserved_exactly": True,
    }
    return transformed


def retiming_unit_checks() -> dict[str, bool]:
    count = 5
    position = np.stack([np.linspace(0.0, 1.0, count), np.linspace(1.0, 0.0, count)], axis=1)
    velocity = np.ones_like(position)
    result = retime_planner_control({"status": "Success", "position": position, "velocity": velocity}, factor=1.5)
    return {
        "duration_increased": int(result["position"].shape[0]) > count,
        "position_start_preserved": bool(np.array_equal(result["position"][0], position[0])),
        "position_end_preserved": bool(np.array_equal(result["position"][-1], position[-1])),
        "velocity_scaled": bool(np.allclose(result["velocity"], 1.0 / 1.5)),
        "factor_recorded": result["_cmf_time_dilation"]["factor"] == 1.5,
    }
