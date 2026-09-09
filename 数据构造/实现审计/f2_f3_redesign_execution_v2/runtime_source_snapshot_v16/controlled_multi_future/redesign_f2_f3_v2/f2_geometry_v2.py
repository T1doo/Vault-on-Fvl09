"""Independent F2 geometry predicates for the v2 scene contract."""

from __future__ import annotations

from typing import Any

import numpy as np


def _aabb_xy(pose: Any, half_xy: Any) -> tuple[np.ndarray, np.ndarray]:
    center = np.asarray(pose[:2], dtype=float)
    half = np.asarray(half_xy, dtype=float)
    return center - half, center + half


def classify_relation(*, pose: Any, spec: dict[str, Any], contact: dict[str, bool] | None = None) -> dict[str, Any]:
    """Compute each predicate independently, then report exclusivity.

    ``pose[:3]`` is the pre-registered can support-point frame produced by the
    asset contract.  It is intentionally distinct from a stand-top placement.
    """
    f2 = spec["f2"]
    point = np.asarray(pose[:3], dtype=float)
    box_lo = np.asarray(f2["box_inner_lower_xyz"], dtype=float)
    box_hi = np.asarray(f2["box_inner_upper_xyz"], dtype=float)
    margin = np.asarray(f2["inside_horizontal_margin"], dtype=float)
    footprint_lo, footprint_hi = _aabb_xy(point, f2["can_support_half_xy"])
    inside = bool(
        np.all(footprint_lo >= box_lo[:2] + margin)
        and np.all(footprint_hi <= box_hi[:2] - margin)
        and abs(point[2] - float(f2["box_support_z"])) <= float(f2["inside_support_z_tolerance"])
    )
    scale = np.asarray(f2["scale_center_xyz"], dtype=float)
    scale_half = np.asarray(f2["scale_half_xy"], dtype=float)
    on = bool(
        np.all(np.abs(point[:2] - scale[:2]) <= scale_half - np.asarray(f2["can_support_half_xy"]))
        and abs(point[2] - float(f2["scale_top_z"])) <= float(f2["beside_z_tolerance"])
    )
    stand = np.asarray(f2["stand_center_xyz"], dtype=float)
    target = np.asarray(f2["beside_target_xy"], dtype=float)
    radial = float(np.linalg.norm(point[:2] - stand[:2]))
    beside_region = bool(
        float(f2["beside_annulus_radius"][0]) <= radial <= float(f2["beside_annulus_radius"][1])
        and abs(point[2] - float(f2["beside_table_z"])) <= float(f2["beside_z_tolerance"])
        and np.linalg.norm(point[:2] - target) <= 0.060
    )
    reference_top_contact = bool((contact or {}).get("stand_top_contact", False))
    beside = bool(beside_region and not reference_top_contact)
    predicates = {"inside": inside, "on": on, "beside": beside}
    return {
        "support_point_xyz": point.tolist(),
        "beside_target_xy": target.tolist(),
        "radial_distance_to_stand_m": radial,
        "stand_top_contact": reference_top_contact,
        "independent_predicates": predicates,
        "predicate_count": int(sum(predicates.values())),
        "exclusive": int(sum(predicates.values())) == 1,
    }


def verify_expected_relation(*, program_id: str, pose: Any, spec: dict[str, Any], contact: dict[str, bool] | None = None) -> dict[str, Any]:
    result = classify_relation(pose=pose, spec=spec, contact=contact)
    result["expected"] = program_id
    result["pass"] = bool(result["exclusive"] and result["independent_predicates"].get(program_id) is True)
    return result


def synthetic_boundary_checks() -> dict[str, bool]:
    spec = {"f2": {**_SPEC_FIXTURE}}
    high = verify_expected_relation(program_id="inside", pose=[-0.18, -0.18, 1.50], spec=spec)
    top = verify_expected_relation(program_id="beside", pose=[0.08, -0.18, 0.825], spec=spec, contact={"stand_top_contact": True})
    overlap = classify_relation(pose=[-0.05, -0.18, 0.760], spec=spec)
    return {
        "high_above_box_rejected": not high["pass"],
        "stand_top_rejected_as_beside": not top["pass"],
        "overlap_is_not_accepted_as_exclusive": not overlap["exclusive"],
    }


_SPEC_FIXTURE = {
    "box_center_xyz": [-0.18, -0.18, 0.755], "scale_center_xyz": [-0.02, -0.18, 0.755], "stand_center_xyz": [0.08, -0.18, 0.79],
    "table_support_z": 0.740, "box_support_z": 0.760, "box_inner_lower_xyz": [-0.29, -0.29, 0.760], "box_inner_upper_xyz": [-0.07, -0.07, 0.855],
    "scale_half_xy": [0.04, 0.06], "scale_top_z": 0.760, "beside_annulus_radius": [0.105, 0.205], "beside_table_z": 0.760,
    "beside_z_tolerance": 0.012, "inside_support_z_tolerance": 0.012, "inside_horizontal_margin": [0.0, 0.0], "can_support_half_xy": [0.038, 0.049],
    "beside_target_xy": [0.20, -0.18],
}
