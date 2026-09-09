"""Pure validation for effective scale and staged physical readback."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


class AssetReadbackError(ValueError):
    """Raised when visual/collision/semantic or physical attributes diverge."""


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise AssetReadbackError(f"{name} must be finite numeric")
    return float(value)


def validate_scale(scale: Sequence[Any]) -> tuple[float, float, float]:
    if len(scale) != 3:
        raise AssetReadbackError("effective_scale must have three axes")
    result = tuple(_finite(item, "effective_scale") for item in scale)
    if any(item <= 0 for item in result):
        raise AssetReadbackError("effective_scale must be positive")
    return result


def scaled_point(point: Sequence[Any], scale: Sequence[Any]) -> list[float]:
    if len(point) != 3:
        raise AssetReadbackError("semantic point must have three coordinates")
    factors = validate_scale(scale)
    return [_finite(value, "semantic_point") * factors[i] for i, value in enumerate(point)]


def principal_to_actor_tensor(principal: Sequence[Any], rotation: Sequence[Sequence[Any]]) -> list[list[float]]:
    if len(principal) != 3 or len(rotation) != 3 or any(len(row) != 3 for row in rotation):
        raise AssetReadbackError("inertia dimensions are invalid")
    diagonal = [_finite(value, "principal_inertia") for value in principal]
    if any(value <= 0 for value in diagonal):
        raise AssetReadbackError("principal inertia must be positive")
    matrix = [[_finite(value, "mass_frame_rotation") for value in row] for row in rotation]
    return [
        [sum(matrix[i][k] * diagonal[k] * matrix[j][k] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]


def validate_inertia(mass: Any, tensor: Sequence[Sequence[Any]], radius_m: Any) -> None:
    m = _finite(mass, "mass")
    radius = _finite(radius_m, "radius_m")
    if m <= 0 or radius <= 0 or len(tensor) != 3 or any(len(row) != 3 for row in tensor):
        raise AssetReadbackError("mass, radius, or inertia dimensions are invalid")
    values = [[_finite(value, "inertia_tensor") for value in row] for row in tensor]
    for i in range(3):
        for j in range(3):
            if abs(values[i][j] - values[j][i]) > 1e-9:
                raise AssetReadbackError("inertia tensor is not symmetric")
    upper = m * radius * radius
    if any(values[i][i] <= 0 or values[i][i] > upper * (1 + 1e-6) for i in range(3)):
        raise AssetReadbackError("inertia violates positive or mR^2 bound")
    if values[0][0] + values[1][1] < values[2][2] or values[0][0] + values[2][2] < values[1][1] or values[1][1] + values[2][2] < values[0][0]:
        raise AssetReadbackError("principal inertia triangle inequality failed")


def build_readback_receipt(*, asset_id: str, effective_scale: Sequence[Any], semantic_points: Mapping[str, Sequence[Any]], stages: Mapping[str, Mapping[str, Any]], radius_m: Any) -> dict[str, Any]:
    scale = validate_scale(effective_scale)
    required_stages = ("native_before_wrapper", "after_wrapper", "after_revision", "after_settle")
    if tuple(stages) != required_stages and set(stages) != set(required_stages):
        raise AssetReadbackError("four required physical readback stages are missing")
    normalized_stages = {}
    for name in required_stages:
        stage = dict(stages[name])
        tensor = stage.get("inertia_tensor")
        validate_inertia(stage.get("mass"), tensor, radius_m)
        if stage.get("frame") != "actor" or stage.get("units") != {"mass": "kg", "inertia": "kg*m^2"}:
            raise AssetReadbackError("mass properties must use actor frame and SI units")
        normalized_stages[name] = stage
    points = {name: scaled_point(point, scale) for name, point in semantic_points.items()}
    return {
        "schema_version": "cmf_f2_f3_asset_readback_v1",
        "asset_id": asset_id,
        "effective_scale": list(scale),
        "visual_scale": list(scale),
        "collision_scale": list(scale),
        "metadata_scale": list(scale),
        "functional_semantic_points": points,
        "stages": normalized_stages,
        "settle_is_dynamic": bool(normalized_stages["after_settle"].get("dynamic", False)),
    }
