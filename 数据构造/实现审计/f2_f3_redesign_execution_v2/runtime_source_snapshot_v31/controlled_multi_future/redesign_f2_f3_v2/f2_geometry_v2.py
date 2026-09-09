"""Independent F2 geometry predicates for the v2 scene contract."""

from __future__ import annotations

from typing import Any

import numpy as np


def _rotation(quaternion: Any) -> np.ndarray:
    w, x, y, z = np.asarray(quaternion, dtype=float)
    norm = np.linalg.norm([w, x, y, z])
    if norm <= 0:
        raise ValueError("asset pose quaternion is zero")
    w, x, y, z = np.asarray([w, x, y, z]) / norm
    return np.asarray([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]], dtype=float)


def _world_geometry(pose: Any, f2: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = np.asarray(pose, dtype=float)
    quaternion = values[3:7] if values.size >= 7 else np.asarray([1.0, 0.0, 0.0, 0.0])
    binding = f2["asset_binding"]
    scale = np.asarray(binding["effective_scale"], dtype=float)
    local_center = np.asarray(binding["center"], dtype=float) * scale
    local_half = np.asarray(binding["scaled_extents"], dtype=float) / 2.0
    rotation = _rotation(quaternion)
    world_center = values[:3] + rotation @ local_center
    world_half = np.abs(rotation) @ local_half
    support_point = values[:3] + rotation @ np.asarray(f2["support_point_local_xyz"], dtype=float)
    return support_point, world_center, world_half


def classify_relation(*, pose: Any, spec: dict[str, Any], contact: dict[str, bool] | None = None) -> dict[str, Any]:
    """Compute each predicate independently, then report exclusivity.

    ``pose[:3]`` is the actor-origin base pose and the support point is
    transformed from the pre-registered local support point in the asset
    contract.  It is intentionally distinct from a stand-top placement.
    """
    f2 = spec["f2"]
    point, world_center, world_half = _world_geometry(pose, f2)
    box_lo = np.asarray(f2["box_inner_lower_xyz"], dtype=float)
    box_hi = np.asarray(f2["box_inner_upper_xyz"], dtype=float)
    margin = np.asarray(f2["inside_horizontal_margin"], dtype=float)
    footprint_lo, footprint_hi = world_center[:2] - world_half[:2], world_center[:2] + world_half[:2]
    inside = bool(
        np.all(footprint_lo >= box_lo[:2] + margin)
        and np.all(footprint_hi <= box_hi[:2] - margin)
        and abs(point[2] - float(f2["box_support_z"])) <= float(f2["inside_support_z_tolerance"])
    )
    scale = np.asarray(f2["scale_center_xyz"], dtype=float)
    scale_half = np.asarray(f2["scale_half_xy"], dtype=float)
    on = bool(
        np.all(np.abs(world_center[:2] - scale[:2]) + world_half[:2] <= scale_half)
        and abs(point[2] - float(f2["scale_top_z"])) <= float(f2["beside_z_tolerance"])
    )
    stand = np.asarray(f2["stand_center_xyz"], dtype=float)
    target = np.asarray(f2["beside_target_xy"], dtype=float)
    radial = float(np.linalg.norm(point[:2] - stand[:2]))
    axis_gap = np.abs(world_center[:2] - stand[:2]) - (np.asarray(f2["stand_half_xy"], dtype=float) + world_half[:2])
    separated_from_stand = bool(np.any(axis_gap >= float(f2["beside_min_axis_clearance_m"])))
    beside_region = bool(
        float(f2["beside_annulus_radius"][0]) <= radial <= float(f2["beside_annulus_radius"][1])
        and abs(point[2] - float(f2["beside_table_z"])) <= float(f2["beside_z_tolerance"])
        and np.linalg.norm(point[:2] - target) <= 0.060
        and separated_from_stand
    )
    reference_top_contact = bool((contact or {}).get("stand_top_contact", False))
    beside = bool(beside_region and not reference_top_contact)
    predicates = {"inside": inside, "on": on, "beside": beside}
    return {
        "support_point_xyz": point.tolist(),
        "beside_target_xy": target.tolist(),
        "radial_distance_to_stand_m": radial,
        "axis_gap_to_stand_m": axis_gap.tolist(),
        "separated_from_stand": separated_from_stand,
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


def build_beside_route_waypoints(
    carry_pose: Any,
    target_pose: Any,
    *,
    route_offset_m: float = 0.12,
    lateral_axis: int = 1,
) -> dict[str, list[float]]:
    """Build the three-segment beside transport route.

    The first waypoint is at the *current* transport X, the second is at the
    target X while retaining the lateral clearance, and the final waypoint
    returns to the target lateral coordinate.  The old collector constructed
    both of the first two points from ``high`` and therefore tested the same
    remote target twice.  This pure helper keeps the route semantics CPU
    testable and independent of the simulator.
    """
    carry = np.asarray(carry_pose, dtype=np.float64).reshape(-1)
    target = np.asarray(target_pose, dtype=np.float64).reshape(-1)
    if carry.shape != (7,) or target.shape != (7,):
        raise ValueError("beside route poses must be seven-dimensional")
    if lateral_axis not in (0, 1):
        raise ValueError("beside route lateral_axis must be 0 or 1")
    if not np.isfinite(carry).all() or not np.isfinite(target).all():
        raise ValueError("beside route poses must be finite")
    if isinstance(route_offset_m, bool) or not np.isfinite(float(route_offset_m)) or float(route_offset_m) <= 0:
        raise ValueError("beside route offset must be a positive finite number")

    # Transport at the proven carry height while preserving the measured
    # grasp orientation.  The first side step changes only the lateral axis.
    high = target.copy()
    high[2] = carry[2]
    route_y = float(carry[lateral_axis] + float(route_offset_m))
    side_at_current = carry.copy()
    side_at_current[lateral_axis] = route_y
    side_at_target = high.copy()
    side_at_target[lateral_axis] = route_y

    # These invariants are part of the route contract, not an assertion about
    # physical reachability.  A later planner diagnostic decides reachability.
    if np.array_equal(side_at_current, side_at_target):
        raise ValueError("beside route collapsed its current and target side waypoints")
    if not np.array_equal(side_at_current[np.arange(7) != lateral_axis], carry[np.arange(7) != lateral_axis]):
        raise ValueError("beside route first waypoint changed non-lateral coordinates")
    # The second leg may rotate into the target grasp orientation, but its
    # Cartesian position must change only along the transport axis.
    changed = np.flatnonzero(~np.isclose(side_at_target[:3], side_at_current[:3], rtol=0.0, atol=1e-12))
    expected_transport_axis = 0 if lateral_axis == 1 else 1
    if set(changed.tolist()) != {expected_transport_axis}:
        raise ValueError("beside route second waypoint must change only the transport axis")
    final_changed = np.flatnonzero(~np.isclose(high[:3], side_at_target[:3], rtol=0.0, atol=1e-12))
    if set(final_changed.tolist()) != {lateral_axis}:
        raise ValueError("beside route final waypoint must return only the lateral coordinate")
    return {
        "side_at_current": side_at_current.tolist(),
        "side_at_target": side_at_target.tolist(),
        "target": high.tolist(),
        "route_lateral_coordinate": route_y,
        "route_offset_m": float(route_offset_m),
        "lateral_axis": int(lateral_axis),
    }


def synthetic_boundary_checks() -> dict[str, bool]:
    spec = {"f2": {**_SPEC_FIXTURE}}
    high = verify_expected_relation(program_id="inside", pose=[-0.18, -0.18, 1.50], spec=spec)
    top = verify_expected_relation(program_id="beside", pose=[0.08, -0.18, 0.825], spec=spec, contact={"stand_top_contact": True})
    overlap_spec = {"f2": {**_SPEC_FIXTURE, "scale_center_xyz": [-0.18, -0.18, 0.760], "scale_half_xy": [0.20, 0.20]}}
    overlap = classify_relation(pose=[-0.18, -0.18, 0.760], spec=overlap_spec)
    return {
        "high_above_box_rejected": not high["pass"],
        "stand_top_rejected_as_beside": not top["pass"],
        "overlap_is_not_accepted_as_exclusive": not overlap["exclusive"],
    }


_SPEC_FIXTURE = {
    "box_center_xyz": [-0.18, -0.18, 0.755], "scale_center_xyz": [-0.02, -0.18, 0.755], "stand_center_xyz": [0.08, -0.18, 0.79], "stand_half_xy": [0.05, 0.05],
    "table_support_z": 0.740, "box_support_z": 0.760, "box_inner_lower_xyz": [-0.29, -0.29, 0.760], "box_inner_upper_xyz": [-0.07, -0.07, 0.855],
    "scale_half_xy": [0.04, 0.06], "scale_top_z": 0.760, "beside_annulus_radius": [0.105, 0.205], "beside_table_z": 0.740, "beside_min_axis_clearance_m": 0.005,
    "beside_z_tolerance": 0.012, "inside_support_z_tolerance": 0.012, "inside_horizontal_margin": [0.0, 0.0], "can_support_half_xy": [0.038, 0.049],
    "beside_target_xy": [0.20, -0.18],
    "support_point_local_xyz": [0.0, 0.0, 0.0],
    "asset_binding": {"effective_scale": [1.0, 1.0, 1.0], "center": [0.0, 0.0, 0.0], "scaled_extents": [0.01, 0.01, 0.01]},
}
