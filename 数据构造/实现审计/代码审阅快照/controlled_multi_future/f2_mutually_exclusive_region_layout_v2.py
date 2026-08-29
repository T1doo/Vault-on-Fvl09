"""CPU geometry proof for mutually exclusive F2 relation regions."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np


LAYOUT_VERSION = "f2_box2_mutually_exclusive_facilities_v2"
LAYOUT = {
    "layout_version": LAYOUT_VERSION,
    "can_xyz": [-0.28, 0.04, 0.79],
    "box_xyz": [-0.29, -0.20, 0.78],
    "scale_xyz": [-0.10, -0.20, 0.77],
    "stand_xyz": [0.20, -0.03, 0.77],
    "stand_q_wxyz": [0.70710678, 0.70710678, 0.0, 0.0],
}
BOX_INSIDE_CENTER_OFFSET_WORLD_M = np.asarray(
    [-0.00023097908496848, -0.00024613654613485, 0.0632653667032719]
)
BOX_INSIDE_HALF_XY_M = np.asarray([0.078, 0.078])
SCALE_TOP_CENTER_OFFSET_WORLD_M = np.asarray(
    [-0.015994399785995483, -0.00017600178718567, 0.0404071807861328]
)
SCALE_TOP_HALF_XY_M = np.asarray([0.07, 0.07])
BESIDE_INNER_M = 0.12
BESIDE_OUTER_M = 0.23
BESIDE_SECTORS_RELATIVE_XY_M = (
    (0.00, 0.15),
    (-0.08, 0.13),
    (-0.12, 0.10),
)
TABLE_BOUNDS_XY = np.asarray([[-0.45, -0.35], [0.45, 0.20]], dtype=np.float64)


def _inside_xy(point: np.ndarray) -> bool:
    center = np.asarray(LAYOUT["box_xyz"][:2]) + BOX_INSIDE_CENTER_OFFSET_WORLD_M[:2]
    return bool(np.all(np.abs(point - center) <= BOX_INSIDE_HALF_XY_M))


def _on_xy(point: np.ndarray) -> bool:
    center = np.asarray(LAYOUT["scale_xyz"][:2]) + SCALE_TOP_CENTER_OFFSET_WORLD_M[:2]
    return bool(np.all(np.abs(point - center) <= SCALE_TOP_HALF_XY_M))


def _beside_xy(point: np.ndarray) -> bool:
    stand = np.asarray(LAYOUT["stand_xyz"][:2])
    radial = float(np.linalg.norm(point - stand))
    return bool(
        BESIDE_INNER_M <= radial <= BESIDE_OUTER_M
        and not _inside_xy(point)
        and not _on_xy(point)
    )


def build_region_layout_review(grid_step_m: float = 0.005) -> dict:
    xs = np.arange(TABLE_BOUNDS_XY[0, 0], TABLE_BOUNDS_XY[1, 0] + 1e-9, grid_step_m)
    ys = np.arange(TABLE_BOUNDS_XY[0, 1], TABLE_BOUNDS_XY[1, 1] + 1e-9, grid_step_m)
    counts = {"inside": 0, "on": 0, "beside": 0}
    overlaps = []
    for x, y in itertools.product(xs, ys):
        point = np.asarray([x, y], dtype=np.float64)
        values = {
            "inside": _inside_xy(point),
            "on": _on_xy(point),
            "beside": _beside_xy(point),
        }
        for key, active in values.items():
            counts[key] += int(active)
        active = [key for key, value in values.items() if value]
        if len(active) > 1:
            overlaps.append({"point_xy": point.tolist(), "regions": active})
    candidate_points = [
        (np.asarray(LAYOUT["stand_xyz"][:2]) + np.asarray(offset)).tolist()
        for offset in BESIDE_SECTORS_RELATIVE_XY_M
    ]
    facility_distances = {
        "box_scale_center_m": float(
            np.linalg.norm(
                np.asarray(LAYOUT["box_xyz"][:2])
                - np.asarray(LAYOUT["scale_xyz"][:2])
            )
        ),
        "scale_stand_center_m": float(
            np.linalg.norm(
                np.asarray(LAYOUT["scale_xyz"][:2])
                - np.asarray(LAYOUT["stand_xyz"][:2])
            )
        ),
        "box_stand_center_m": float(
            np.linalg.norm(
                np.asarray(LAYOUT["box_xyz"][:2])
                - np.asarray(LAYOUT["stand_xyz"][:2])
            )
        ),
    }
    checks = {
        "grid_has_inside_points": counts["inside"] > 0,
        "grid_has_on_points": counts["on"] > 0,
        "grid_has_beside_points": counts["beside"] > 0,
        "grid_overlap_count_zero": len(overlaps) == 0,
        "all_beside_candidates_inside_table": all(
            TABLE_BOUNDS_XY[0, 0] <= point[0] <= TABLE_BOUNDS_XY[1, 0]
            and TABLE_BOUNDS_XY[0, 1] <= point[1] <= TABLE_BOUNDS_XY[1, 1]
            for point in candidate_points
        ),
        "all_beside_candidates_exclude_inside_on": all(
            _beside_xy(np.asarray(point))
            and not _inside_xy(np.asarray(point))
            and not _on_xy(np.asarray(point))
            for point in candidate_points
        ),
        "scale_top_outside_raw_stand_annulus": facility_distances[
            "scale_stand_center_m"
        ]
        - float(np.linalg.norm(SCALE_TOP_HALF_XY_M))
        > BESIDE_OUTER_M,
    }
    return {
        "schema_version": "cmf_f2_mutually_exclusive_region_layout_v2",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_3",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "layout": LAYOUT,
        "predicate_version": "f2_facility_local_mutually_exclusive_predicates_v2",
        "inside_region": {
            "center_offset_world_m": BOX_INSIDE_CENTER_OFFSET_WORLD_M.tolist(),
            "half_xy_m": BOX_INSIDE_HALF_XY_M.tolist(),
        },
        "on_region": {
            "center_offset_world_m": SCALE_TOP_CENTER_OFFSET_WORLD_M.tolist(),
            "half_xy_m": SCALE_TOP_HALF_XY_M.tolist(),
        },
        "beside_region": {
            "inner_radius_m": BESIDE_INNER_M,
            "outer_radius_m": BESIDE_OUTER_M,
            "explicitly_excludes": ["inside_region", "on_region"],
            "candidate_relative_xy_m": [list(item) for item in BESIDE_SECTORS_RELATIVE_XY_M],
            "candidate_world_xy_m": candidate_points,
        },
        "grid_proof": {
            "step_m": grid_step_m,
            "point_count": int(len(xs) * len(ys)),
            "region_point_counts": counts,
            "overlap_count": len(overlaps),
            "overlap_examples": overlaps[:10],
        },
        "facility_center_distances_m": facility_distances,
        "checks": checks,
        "pass": all(checks.values()),
        "status": "cpu_geometry_pass_gpu_suffix_gate_pending"
        if all(checks.values())
        else "cpu_geometry_failed",
    }


def write_review(path: Path) -> dict:
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    value = build_region_layout_review()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value
