"""Pure-CPU contract for the F2 revision-4 beside route.

The revision-3 six-route probe exhausted its frozen candidates before a
stand-adjacent target was queried.  This helper therefore does not move the
stand and does not perform another candidate search.  It freezes the single
stand-relative sector that already has an immutable accepted runtime-v3_2
rollout, fixes the actor support height from the table plane and the scaled
local OBB, and exposes one reciprocal carry hub.

Importing this module does not create a SAPIEN scene, query a planner, execute
an action, authorize a GPU probe, or authorize Stage 0.  The exact-OBB path
audit covers only the declared straight waypoint segments; official CuRobo
collision checking and the runtime actual-contact Gate remain mandatory.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from .f2_mutually_exclusive_region_layout_v2 import (
    BESIDE_INNER_M,
    BESIDE_OUTER_M,
    BOX_INSIDE_CENTER_OFFSET_WORLD_M,
    BOX_INSIDE_HALF_XY_M,
    LAYOUT,
    SCALE_TOP_CENTER_OFFSET_WORLD_M,
    SCALE_TOP_HALF_XY_M,
    TABLE_BOUNDS_XY,
)
from .geometry import (
    actor_target_to_eef_pose,
    compose_pose,
    obb_corners,
    quaternion_matrix,
    relative_pose,
    world_axis_offset_pose,
)


SCHEMA_VERSION = "cmf_f2_beside_historical_safe_route_v4"
DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_3"
IMPLEMENTATION_PROPOSAL = "f2_historical_safe_sector_support_route_v4"

F2_MAIN_OBJECT = "071_can/base1"
F2_EXECUTION_ARM = "left"
F2_BOX = "062_plasticbox/base2"
F2_SCALE = "072_electronicscale/base0"
F2_STAND = "074_displaystand/base3"

HISTORICAL_VARIANT_ID = "f2_pose_4"
HISTORICAL_SAFE_STAND_RELATIVE_XY_M = (-0.15, -0.04)
FROZEN_CAN_UPRIGHT_QUATERNION_WXYZ = (0.5, 0.5, 0.5, 0.5)
FROZEN_STAND_POSE = (
    *LAYOUT["stand_xyz"],
    *LAYOUT["stand_q_wxyz"],
)
TABLE_SUPPORT_PLANE_Z_M = 0.74
PREPLACE_OFFSET_M = 0.08
FACILITY_CLEARANCE_MARGIN_M = 0.005
ENVELOPE_SAMPLES_PER_SEGMENT = 41
EXPECTED_FACILITY_ROLES = ("box", "scale", "stand")

SEGMENT_IDS = (
    "beside_historical_carry_hub",
    "beside_historical_preplace",
    "beside_historical_release",
    "beside_historical_retreat",
    "beside_historical_carry_hub_return",
    "f2_rest",
)
RELEASE_TARGET_INDEX = 2


def _pose(value: Sequence[float], *, label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(7)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be finite")
    norm = float(np.linalg.norm(result[3:]))
    if norm <= 1e-12:
        raise ValueError(f"{label} quaternion norm must be positive")
    result = result.copy()
    result[3:] /= norm
    return result


def _vector3(value: Sequence[float], *, label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(3)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be finite")
    return result.copy()


def _half_extents(value: Sequence[float]) -> np.ndarray:
    result = _vector3(value, label="can_half_extents_m")
    if np.any(result <= 0.0):
        raise ValueError("can_half_extents_m must be positive")
    return result


def _quaternion_angular_error(first: Sequence[float], second: Sequence[float]) -> float:
    first_value = np.asarray(first, dtype=np.float64).reshape(4)
    second_value = np.asarray(second, dtype=np.float64).reshape(4)
    first_value /= np.linalg.norm(first_value)
    second_value /= np.linalg.norm(second_value)
    cosine = float(np.clip(abs(np.dot(first_value, second_value)), -1.0, 1.0))
    return float(2.0 * np.arccos(cosine))


def _nlerp_pose(first: Sequence[float], second: Sequence[float], alpha: float) -> np.ndarray:
    first_value = _pose(first, label="interpolation first pose")
    second_value = _pose(second, label="interpolation second pose")
    amount = float(alpha)
    if not 0.0 <= amount <= 1.0:
        raise ValueError("pose interpolation alpha must be in [0, 1]")
    second_quaternion = second_value[3:].copy()
    if float(np.dot(first_value[3:], second_quaternion)) < 0.0:
        second_quaternion *= -1.0
    quaternion = (1.0 - amount) * first_value[3:] + amount * second_quaternion
    quaternion /= np.linalg.norm(quaternion)
    return np.concatenate(
        ((1.0 - amount) * first_value[:3] + amount * second_value[:3], quaternion)
    )


def _facility_aabbs(
    value: Mapping[str, Mapping[str, Sequence[float]]],
) -> dict[str, dict[str, np.ndarray]]:
    if not isinstance(value, Mapping):
        raise ValueError("facility_aabbs must be a mapping")
    if set(value) != set(EXPECTED_FACILITY_ROLES):
        raise ValueError("facility_aabbs must contain exactly box, scale, and stand")
    result: dict[str, dict[str, np.ndarray]] = {}
    for role in EXPECTED_FACILITY_ROLES:
        bounds = value[role]
        if not isinstance(bounds, Mapping):
            raise ValueError(f"facility AABB {role} must be a mapping")
        lower = _vector3(bounds.get("lower", ()), label=f"{role} lower")
        upper = _vector3(bounds.get("upper", ()), label=f"{role} upper")
        if np.any(lower >= upper):
            raise ValueError(f"facility AABB {role} is empty")
        result[role] = {"lower": lower, "upper": upper}
    return result


def _serializable_facility_aabbs(
    value: Mapping[str, Mapping[str, Sequence[float]]],
) -> dict[str, dict[str, list[float]]]:
    parsed = _facility_aabbs(value)
    return {
        role: {
            "lower": bounds["lower"].tolist(),
            "upper": bounds["upper"].tolist(),
        }
        for role, bounds in parsed.items()
    }


def _geometry_center_pose(
    actor_pose: Sequence[float], local_geometry_center_m: Sequence[float]
) -> np.ndarray:
    center = _vector3(local_geometry_center_m, label="can_local_geometry_center_m")
    return compose_pose(actor_pose, [*center, 1.0, 0.0, 0.0, 0.0])


def actor_origin_z_for_table_support(
    *,
    table_plane_z_m: float,
    actor_quaternion_wxyz: Sequence[float],
    can_local_geometry_center_m: Sequence[float],
    can_half_extents_m: Sequence[float],
) -> float:
    """Return the actor-origin z whose scaled local OBB rests on the table."""

    table_z = float(table_plane_z_m)
    if not np.isfinite(table_z):
        raise ValueError("table_plane_z_m must be finite")
    center = _vector3(can_local_geometry_center_m, label="can_local_geometry_center_m")
    half = _half_extents(can_half_extents_m)
    rotation = quaternion_matrix(actor_quaternion_wxyz)
    local_corners = np.asarray(
        [
            center + np.asarray([x, y, z], dtype=np.float64)
            for x in (-half[0], half[0])
            for y in (-half[1], half[1])
            for z in (-half[2], half[2])
        ],
        dtype=np.float64,
    )
    relative_bottom = float(np.min((rotation @ local_corners.T).T[:, 2]))
    return float(table_z - relative_bottom)


def _region_predicate_audit(target_xy: np.ndarray, stand_xy: np.ndarray) -> dict[str, Any]:
    inside_center = (
        np.asarray(LAYOUT["box_xyz"][:2], dtype=np.float64)
        + BOX_INSIDE_CENTER_OFFSET_WORLD_M[:2]
    )
    scale_center = (
        np.asarray(LAYOUT["scale_xyz"][:2], dtype=np.float64)
        + SCALE_TOP_CENTER_OFFSET_WORLD_M[:2]
    )
    inside = bool(np.all(np.abs(target_xy - inside_center) <= BOX_INSIDE_HALF_XY_M))
    on = bool(np.all(np.abs(target_xy - scale_center) <= SCALE_TOP_HALF_XY_M))
    radial = float(np.linalg.norm(target_xy - stand_xy))
    within_table = bool(
        TABLE_BOUNDS_XY[0, 0] <= target_xy[0] <= TABLE_BOUNDS_XY[1, 0]
        and TABLE_BOUNDS_XY[0, 1] <= target_xy[1] <= TABLE_BOUNDS_XY[1, 1]
    )
    beside = bool(BESIDE_INNER_M <= radial <= BESIDE_OUTER_M and not inside and not on)
    return {
        "radial_distance_m": radial,
        "inside": inside,
        "on": on,
        "beside": beside,
        "within_table": within_table,
        "exclusive_beside": beside and not inside and not on,
    }


def _aabb_clearance(
    object_lower: np.ndarray,
    object_upper: np.ndarray,
    facility_lower: np.ndarray,
    facility_upper: np.ndarray,
) -> tuple[float, list[float]]:
    axis_separation = np.maximum(
        facility_lower - object_upper, object_lower - facility_upper
    )
    return float(np.max(axis_separation)), axis_separation.tolist()


def target_facility_clearance_audit(
    *,
    target_actor_pose: Sequence[float],
    can_local_geometry_center_m: Sequence[float],
    can_half_extents_m: Sequence[float],
    facility_aabbs: Mapping[str, Mapping[str, Sequence[float]]],
    margin_m: float = FACILITY_CLEARANCE_MARGIN_M,
) -> dict[str, Any]:
    """Conservatively compare the target OBB AABB with every facility AABB."""

    margin = float(margin_m)
    if not np.isfinite(margin) or margin < 0.0:
        raise ValueError("margin_m must be finite and non-negative")
    target = _pose(target_actor_pose, label="target_actor_pose")
    half = _half_extents(can_half_extents_m)
    geometry_center = _geometry_center_pose(target, can_local_geometry_center_m)
    corners = obb_corners(geometry_center, half)
    lower = corners.min(axis=0)
    upper = corners.max(axis=0)
    facilities = _facility_aabbs(facility_aabbs)
    clearances = {}
    pass_by_role = {}
    for role, bounds in facilities.items():
        clearance, axis_separation = _aabb_clearance(
            lower, upper, bounds["lower"], bounds["upper"]
        )
        clearances[role] = {
            "separating_clearance_m": clearance,
            "axis_separation_m": axis_separation,
        }
        pass_by_role[role] = clearance >= margin
    return {
        "schema_version": "cmf_f2_target_exact_obb_aabb_clearance_v1",
        "method": "exact target OBB corners, conservative facility world AABBs",
        "margin_m": margin,
        "target_obb_aabb_lower": lower.tolist(),
        "target_obb_aabb_upper": upper.tolist(),
        "facility_clearances": clearances,
        "checks": pass_by_role,
        "pass": all(pass_by_role.values()),
    }


def exact_obb_held_waypoint_envelope_audit(
    *,
    source_eef_pose: Sequence[float],
    source_actor_pose: Sequence[float],
    held_target_eef_poses: Sequence[Sequence[float]],
    can_local_geometry_center_m: Sequence[float],
    can_half_extents_m: Sequence[float],
    facility_aabbs: Mapping[str, Mapping[str, Sequence[float]]],
    margin_m: float = FACILITY_CLEARANCE_MARGIN_M,
    samples_per_segment: int = ENVELOPE_SAMPLES_PER_SEGMENT,
) -> dict[str, Any]:
    """Audit straight declared held segments with sampled exact OBB corners."""

    source_eef = _pose(source_eef_pose, label="source_eef_pose")
    source_actor = _pose(source_actor_pose, label="source_actor_pose")
    targets = [
        _pose(value, label=f"held target {index}")
        for index, value in enumerate(held_target_eef_poses)
    ]
    if not targets:
        raise ValueError("at least one held target EEF pose is required")
    sample_count = int(samples_per_segment)
    if sample_count < 2:
        raise ValueError("samples_per_segment must be at least two")
    margin = float(margin_m)
    if not np.isfinite(margin) or margin < 0.0:
        raise ValueError("margin_m must be finite and non-negative")
    center = _vector3(can_local_geometry_center_m, label="can_local_geometry_center_m")
    half = _half_extents(can_half_extents_m)
    facilities = _facility_aabbs(facility_aabbs)
    eef_to_actor = relative_pose(source_eef, source_actor)
    points = [source_eef, *targets]
    segments = []
    collisions = []
    minimum_clearance = {role: float("inf") for role in facilities}
    for segment_index, (start, end) in enumerate(zip(points[:-1], points[1:])):
        segment_collisions = set()
        for sample_index, alpha in enumerate(np.linspace(0.0, 1.0, sample_count)):
            eef_pose = _nlerp_pose(start, end, float(alpha))
            actor_pose = compose_pose(eef_pose, eef_to_actor)
            geometry_center = _geometry_center_pose(actor_pose, center)
            corners = obb_corners(geometry_center, half)
            lower = corners.min(axis=0)
            upper = corners.max(axis=0)
            for role, bounds in facilities.items():
                clearance, _ = _aabb_clearance(
                    lower, upper, bounds["lower"], bounds["upper"]
                )
                minimum_clearance[role] = min(minimum_clearance[role], clearance)
                if clearance < margin:
                    segment_collisions.add(role)
                    collisions.append(
                        {
                            "segment_index": segment_index,
                            "sample_index": sample_index,
                            "facility_role": role,
                            "separating_clearance_m": clearance,
                        }
                    )
        segments.append(
            {
                "segment_index": segment_index,
                "facility_collisions": sorted(segment_collisions),
            }
        )
    return {
        "schema_version": "cmf_f2_sampled_exact_obb_held_waypoint_envelope_v1",
        "method": (
            "normalized-linear EEF interpolation on declared straight waypoint "
            "segments; fixed grasp transform; exact can OBB corners; "
            "conservative facility world AABBs"
        ),
        "margin_m": margin,
        "samples_per_segment": sample_count,
        "segment_count": len(points) - 1,
        "segments": segments,
        "minimum_separating_clearance_m": minimum_clearance,
        "collisions": collisions,
        "curved_planned_path_covered": False,
        "official_curobo_whole_robot_collision_still_required": True,
        "actual_execution_contact_gate_required": True,
        "pass": not collisions,
    }


def _expected_route_values(
    *,
    current_eef_pose: Sequence[float],
    current_actor_pose: Sequence[float],
    stand_pose: Sequence[float],
    rest_eef_pose: Sequence[float],
    can_local_geometry_center_m: Sequence[float],
    can_half_extents_m: Sequence[float],
    table_plane_z_m: float,
) -> dict[str, Any]:
    current_eef = _pose(current_eef_pose, label="current_eef_pose")
    current_actor = _pose(current_actor_pose, label="current_actor_pose")
    stand = _pose(stand_pose, label="stand_pose")
    rest = _pose(rest_eef_pose, label="rest_eef_pose")
    center = _vector3(can_local_geometry_center_m, label="can_local_geometry_center_m")
    half = _half_extents(can_half_extents_m)
    table_z = float(table_plane_z_m)
    target_actor_z = actor_origin_z_for_table_support(
        table_plane_z_m=table_z,
        actor_quaternion_wxyz=FROZEN_CAN_UPRIGHT_QUATERNION_WXYZ,
        can_local_geometry_center_m=center,
        can_half_extents_m=half,
    )
    target_actor = np.asarray(
        [
            stand[0] + HISTORICAL_SAFE_STAND_RELATIVE_XY_M[0],
            stand[1] + HISTORICAL_SAFE_STAND_RELATIVE_XY_M[1],
            target_actor_z,
            *FROZEN_CAN_UPRIGHT_QUATERNION_WXYZ,
        ],
        dtype=np.float64,
    )
    release = actor_target_to_eef_pose(current_eef, current_actor, target_actor)
    preplace = world_axis_offset_pose(release, PREPLACE_OFFSET_M)
    hub = preplace.copy()
    hub[:2] = (current_eef[:2] + preplace[:2]) / 2.0
    targets = [
        {"segment_id": SEGMENT_IDS[0], "pose": hub.tolist()},
        {"segment_id": SEGMENT_IDS[1], "pose": preplace.tolist()},
        {"segment_id": SEGMENT_IDS[2], "pose": release.tolist()},
        {"segment_id": SEGMENT_IDS[3], "pose": preplace.tolist()},
        {"segment_id": SEGMENT_IDS[4], "pose": hub.tolist()},
        {"segment_id": SEGMENT_IDS[5], "pose": rest.tolist()},
    ]
    return {
        "current_eef_pose": current_eef,
        "current_actor_pose": current_actor,
        "stand_pose": stand,
        "rest_eef_pose": rest,
        "can_local_geometry_center_m": center,
        "can_half_extents_m": half,
        "table_plane_z_m": table_z,
        "target_actor_pose": target_actor,
        "preplace_pose": preplace,
        "release_pose": release,
        "hub_pose": hub,
        "targets": targets,
    }


def audit_historical_safe_beside_route(route: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed on identity, layout, support, predicates, and geometry."""

    if not isinstance(route, Mapping):
        raise ValueError("route must be a mapping")
    expected = _expected_route_values(
        current_eef_pose=route.get("source_eef_pose", ()),
        current_actor_pose=route.get("source_actor_pose", ()),
        stand_pose=route.get("stand_pose", ()),
        rest_eef_pose=route.get("rest_eef_pose", ()),
        can_local_geometry_center_m=route.get("can_local_geometry_center_m", ()),
        can_half_extents_m=route.get("can_half_extents_m", ()),
        table_plane_z_m=route.get("table_plane_z_m", np.nan),
    )
    facilities = _facility_aabbs(route.get("facility_aabbs", {}))
    target = _pose(route.get("target_actor_pose", ()), label="target_actor_pose")
    targets = route.get("targets")
    if not isinstance(targets, list) or len(targets) != len(SEGMENT_IDS):
        raise ValueError("route must contain exactly six frozen targets")
    target_poses = [
        _pose(item.get("pose", ()), label=f"target {index}")
        if isinstance(item, Mapping)
        else _pose((), label=f"target {index}")
        for index, item in enumerate(targets)
    ]
    target_geometry_center = _geometry_center_pose(
        target, expected["can_local_geometry_center_m"]
    )
    target_corners = obb_corners(
        target_geometry_center, expected["can_half_extents_m"]
    )
    target_bottom = float(np.min(target_corners[:, 2]))
    predicates = _region_predicate_audit(target[:2], expected["stand_pose"][:2])
    target_clearance = target_facility_clearance_audit(
        target_actor_pose=target,
        can_local_geometry_center_m=expected["can_local_geometry_center_m"],
        can_half_extents_m=expected["can_half_extents_m"],
        facility_aabbs=facilities,
    )
    held_envelope = exact_obb_held_waypoint_envelope_audit(
        source_eef_pose=expected["current_eef_pose"],
        source_actor_pose=expected["current_actor_pose"],
        held_target_eef_poses=target_poses[: RELEASE_TARGET_INDEX + 1],
        can_local_geometry_center_m=expected["can_local_geometry_center_m"],
        can_half_extents_m=expected["can_half_extents_m"],
        facility_aabbs=facilities,
    )
    segment_ids = tuple(
        item.get("segment_id") if isinstance(item, Mapping) else None
        for item in targets
    )
    frozen_stand = _pose(FROZEN_STAND_POSE, label="frozen stand pose")
    checks = {
        "identity": route.get("main_object") == F2_MAIN_OBJECT
        and route.get("arm") == F2_EXECUTION_ARM
        and route.get("reference") == F2_STAND,
        "relation_beside": route.get("relation") == "beside",
        "no_stand_move": bool(
            np.linalg.norm(expected["stand_pose"][:3] - frozen_stand[:3]) <= 1e-6
            and _quaternion_angular_error(
                expected["stand_pose"][3:], frozen_stand[3:]
            )
            <= 1e-6
        ),
        "single_historical_route_no_search": route.get("candidate_search_enabled")
        is False
        and route.get("route_count") == 1
        and route.get("historical_variant_id") == HISTORICAL_VARIANT_ID
        and tuple(route.get("stand_relative_xy_m", ()))
        == HISTORICAL_SAFE_STAND_RELATIVE_XY_M,
        "target_actor_exact": bool(
            np.allclose(target, expected["target_actor_pose"], atol=1e-12, rtol=0.0)
        ),
        "upright_orientation_exact": _quaternion_angular_error(
            target[3:], FROZEN_CAN_UPRIGHT_QUATERNION_WXYZ
        )
        <= 1e-12,
        "center_aware_table_support": bool(
            np.isclose(
                target_bottom,
                expected["table_plane_z_m"],
                atol=1e-9,
                rtol=0.0,
            )
        ),
        "exact_segment_order": segment_ids == SEGMENT_IDS,
        "exact_target_poses": all(
            np.allclose(actual, expected_item["pose"], atol=1e-12, rtol=0.0)
            for actual, expected_item in zip(target_poses, expected["targets"])
        ),
        "release_at_third_target": route.get("release_target_index")
        == RELEASE_TARGET_INDEX,
        "fixed_eight_cm_preplace": bool(
            np.allclose(
                target_poses[1][:3] - target_poses[2][:3],
                [0.0, 0.0, PREPLACE_OFFSET_M],
                atol=1e-12,
                rtol=0.0,
            )
        ),
        "reciprocal_preplace": bool(
            np.array_equal(target_poses[1], target_poses[3])
        ),
        "one_reciprocal_hub": bool(
            np.array_equal(target_poses[0], target_poses[4])
            and np.allclose(
                target_poses[0][:2],
                (
                    expected["current_eef_pose"][:2]
                    + expected["preplace_pose"][:2]
                )
                / 2.0,
                atol=1e-12,
                rtol=0.0,
            )
            and np.isclose(
                target_poses[0][2],
                expected["preplace_pose"][2],
                atol=1e-12,
                rtol=0.0,
            )
        ),
        "strict_exclusive_beside_predicate": predicates["exclusive_beside"]
        and predicates["within_table"],
        "target_facility_clearance": target_clearance["pass"],
        "sampled_exact_obb_held_envelope": held_envelope["pass"],
        "runtime_collision_gates_retained": route.get(
            "official_curobo_whole_robot_collision_required"
        )
        is True
        and route.get("actual_held_transport_contact_gate_required") is True,
        "strict_relation_verifier_retained": route.get(
            "strict_final_relation_verifier_relaxed"
        )
        is False,
    }
    return {
        "schema_version": "cmf_f2_beside_historical_safe_route_v4_audit",
        "checks": checks,
        "predicate_audit": predicates,
        "target_geometry": {
            "target_obb_bottom_z_m": target_bottom,
            "table_plane_z_m": expected["table_plane_z_m"],
            "support_error_m": target_bottom - expected["table_plane_z_m"],
        },
        "target_facility_clearance_audit": target_clearance,
        "held_waypoint_envelope_audit": held_envelope,
        "pass": all(checks.values()),
    }


def build_historical_safe_beside_route(
    *,
    current_eef_pose: Sequence[float],
    current_actor_pose: Sequence[float],
    stand_pose: Sequence[float],
    rest_eef_pose: Sequence[float],
    can_local_geometry_center_m: Sequence[float],
    can_half_extents_m: Sequence[float],
    facility_aabbs: Mapping[str, Mapping[str, Sequence[float]]],
    table_plane_z_m: float = TABLE_SUPPORT_PLANE_Z_M,
) -> dict[str, Any]:
    """Build the one frozen, reciprocal, center-aware F2 beside route."""

    values = _expected_route_values(
        current_eef_pose=current_eef_pose,
        current_actor_pose=current_actor_pose,
        stand_pose=stand_pose,
        rest_eef_pose=rest_eef_pose,
        can_local_geometry_center_m=can_local_geometry_center_m,
        can_half_extents_m=can_half_extents_m,
        table_plane_z_m=table_plane_z_m,
    )
    route = {
        "schema_version": SCHEMA_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_proposal": IMPLEMENTATION_PROPOSAL,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "relation": "beside",
        "main_object": F2_MAIN_OBJECT,
        "arm": F2_EXECUTION_ARM,
        "reference": F2_STAND,
        "frozen_other_facilities": [F2_BOX, F2_SCALE],
        "historical_variant_id": HISTORICAL_VARIANT_ID,
        "selection_basis": (
            "immutable accepted same-layout runtime-v3_2 beside rollout; "
            "not selected from revision-4 planner results"
        ),
        "candidate_search_enabled": False,
        "route_count": 1,
        "stand_relative_xy_m": list(HISTORICAL_SAFE_STAND_RELATIVE_XY_M),
        "stand_pose": values["stand_pose"].tolist(),
        "source_eef_pose": values["current_eef_pose"].tolist(),
        "source_actor_pose": values["current_actor_pose"].tolist(),
        "rest_eef_pose": values["rest_eef_pose"].tolist(),
        "can_local_geometry_center_m": values[
            "can_local_geometry_center_m"
        ].tolist(),
        "can_half_extents_m": values["can_half_extents_m"].tolist(),
        "table_plane_z_m": values["table_plane_z_m"],
        "target_actor_pose": values["target_actor_pose"].tolist(),
        "preplace_offset_m": PREPLACE_OFFSET_M,
        "release_target_index": RELEASE_TARGET_INDEX,
        "targets": values["targets"],
        "facility_aabbs": _serializable_facility_aabbs(facility_aabbs),
        "official_curobo_whole_robot_collision_required": True,
        "actual_held_transport_contact_gate_required": True,
        "strict_final_relation_verifier_relaxed": False,
    }
    route["audit"] = audit_historical_safe_beside_route(route)
    return route

