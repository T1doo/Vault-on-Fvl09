"""CPU geometry contract for the new F2 relation targets and exits."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from .canonical import atomic_write_json, canonical_sha256


RELATIONS = ("inside", "on", "beside")
BOX_LOWER_XY = np.asarray([-0.19, -0.29], dtype=np.float64)
BOX_UPPER_XY = np.asarray([0.03, -0.07], dtype=np.float64)
SCALE_CENTER_XY = np.asarray([0.08, -0.18], dtype=np.float64)
STAND_CENTER_XY = np.asarray([0.23, -0.18], dtype=np.float64)
CAN_HALF_XY = np.asarray([0.0355745611100579, 0.048233944091278,], dtype=np.float64)
EXIT_VECTOR_X = {"inside": 0.10, "on": -0.15, "beside": 0.10}
SUPPORT_IDENTITY = {"inside": "f2_redesign_box_bottom", "on": "f2_redesign_scale", "beside": "f2_redesign_stand"}


class F2GeometryError(ValueError):
    pass


def classify_relation(xy: Sequence[float]) -> dict[str, bool]:
    point = np.asarray(xy, dtype=np.float64).reshape(2)
    inside = bool(np.all(point >= BOX_LOWER_XY + CAN_HALF_XY) and np.all(point <= BOX_UPPER_XY - CAN_HALF_XY))
    on = bool(np.all(np.abs(point - SCALE_CENTER_XY) <= np.asarray([0.08, 0.08])) and not inside)
    beside = bool(np.all(np.abs(point - STAND_CENTER_XY) <= np.asarray([0.08, 0.08])) and not inside and not on)
    return {"inside": inside, "on": on, "beside": beside}


def build_relation_contract() -> dict[str, Any]:
    points = {"inside": (BOX_LOWER_XY + BOX_UPPER_XY) / 2, "on": SCALE_CENTER_XY, "beside": STAND_CENTER_XY}
    rows = {}
    for relation in RELATIONS:
        values = classify_relation(points[relation])
        if values[relation] is not True or sum(values.values()) != 1:
            raise F2GeometryError(f"relation point is not exclusive: {relation}: {values}")
        rows[relation] = {
            "support_identity": SUPPORT_IDENTITY[relation],
            "target_xy_m": points[relation].tolist(),
            "exclusive_classification": values,
            "empty_hand_exit_vector_x_m": EXIT_VECTOR_X[relation],
            "exit_direction_is_away_from_support": (relation != "on" or EXIT_VECTOR_X[relation] < 0) and (relation != "beside" or EXIT_VECTOR_X[relation] > 0),
        }
    result = {
        "schema_version": "cmf_f2_relation_geometry_contract_v1",
        "relations": rows,
        "can_half_xy_m": CAN_HALF_XY.tolist(),
        "box_lower_xy_m": BOX_LOWER_XY.tolist(),
        "box_upper_xy_m": BOX_UPPER_XY.tolist(),
        "source": "redesign_f2_f3_v1/f2_scene.py and V2.1 R2/R4",
    }
    result["contract_sha256"] = canonical_sha256(result)
    return result


def audit_relation_contract(output: str) -> dict[str, Any]:
    result = build_relation_contract()
    result["pass"] = all(row["exit_direction_is_away_from_support"] and sum(row["exclusive_classification"].values()) == 1 for row in result["relations"].values())
    atomic_write_json(output, result)
    return result
