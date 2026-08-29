"""Pure F4 helper for a uniform one-midpoint block carry route.

This module intentionally has no simulator or planner dependency.  It expands
the historical six-target A/B/C block groups to seven targets by inserting one
deterministic midpoint between ``lift`` and ``preplace``.  The frozen F4
layout, common-X prefix, right-arm assignment, program order, and verifier are
outside this helper and are explicitly reported as unchanged.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

import numpy as np

from .geometry import segment_intersects_aabb


F4_UNIFORM_BLOCK_CARRY_VERSION = "f4_uniform_per_block_carry_midpoint_v3"
F4_BLOCK_ROLES = ("A", "B", "C")
F4_ALLOWED_OBJECT_ORDERS = (
    ("A", "B", "C"),
    ("A", "C", "B"),
    ("B", "A", "C"),
)
F4_COMMON_SEGMENT_IDS = (
    "common_pregrasp",
    "common_grasp",
    "common_lift",
    "common_safe_vertical",
    "common_center_high",
    "common_above_tray",
    "common_preplace",
    "common_release",
    "common_neutral",
)
F4_LEGACY_BLOCK_SUFFIXES = (
    "pregrasp",
    "grasp",
    "lift",
    "preplace",
    "release",
    "neutral",
)
F4_SEGMENTED_BLOCK_SUFFIXES = (
    "pregrasp",
    "grasp",
    "lift",
    "carry_mid",
    "preplace",
    "release",
    "neutral",
)
MIDPOINT_XY_FRACTION = 0.5
QUATERNION_EQUIVALENCE_ATOL_RAD = 1e-10


def _pose(value: Any, *, label: str) -> np.ndarray:
    pose = np.asarray(value, dtype=np.float64).reshape(-1)
    if pose.shape != (7,) or not np.all(np.isfinite(pose)):
        raise ValueError(f"{label} must be one finite 7-D pose")
    norm = float(np.linalg.norm(pose[3:]))
    if not np.isfinite(norm) or norm <= 0.0:
        raise ValueError(f"{label} has an invalid quaternion")
    return pose.copy()


def _quaternion_angular_error(left: np.ndarray, right: np.ndarray) -> float:
    left = np.asarray(left, dtype=np.float64).reshape(4)
    right = np.asarray(right, dtype=np.float64).reshape(4)
    left = left / np.linalg.norm(left)
    right = right / np.linalg.norm(right)
    cosine = float(np.clip(abs(np.dot(left, right)), 0.0, 1.0))
    return float(2.0 * np.arccos(cosine))


def build_uniform_carry_midpoint(
    lift_pose: Sequence[float],
    preplace_pose: Sequence[float],
) -> tuple[np.ndarray, dict]:
    """Return the frozen midpoint and a JSON-compatible construction audit."""

    lift = _pose(lift_pose, label="F4 lift pose")
    preplace = _pose(preplace_pose, label="F4 preplace pose")
    orientation_error = _quaternion_angular_error(lift[3:], preplace[3:])
    if orientation_error > QUATERNION_EQUIVALENCE_ATOL_RAD:
        raise ValueError("F4 lift/preplace orientations differ before midpoint repair")

    midpoint = preplace.copy()
    midpoint[:2] = (1.0 - MIDPOINT_XY_FRACTION) * lift[:2] + (
        MIDPOINT_XY_FRACTION * preplace[:2]
    )
    midpoint[2] = max(float(lift[2]), float(preplace[2]))
    direct_distance = float(np.linalg.norm(preplace[:3] - lift[:3]))
    first_distance = float(np.linalg.norm(midpoint[:3] - lift[:3]))
    second_distance = float(np.linalg.norm(preplace[:3] - midpoint[:3]))
    return midpoint, {
        "midpoint_xy_fraction": MIDPOINT_XY_FRACTION,
        "z_policy": "max(lift_z,preplace_z)",
        "orientation_policy": "copy_preplace_quaternion_after_sign_invariant_equivalence_check",
        "lift_preplace_orientation_error_rad": orientation_error,
        "direct_lift_to_preplace_distance_m": direct_distance,
        "lift_to_carry_mid_distance_m": first_distance,
        "carry_mid_to_preplace_distance_m": second_distance,
        "carry_mid_pose": midpoint.tolist(),
    }


def _expected_ids(role: str, suffixes: Sequence[str]) -> tuple[str, ...]:
    return tuple(f"{role}_{suffix}" for suffix in suffixes)


def _validate_common_and_order(
    all_targets: Sequence[Mapping[str, Any]],
    extra: Mapping[str, Any],
) -> tuple[list[Mapping[str, Any]], tuple[str, ...], list[Mapping[str, Any]]]:
    targets = list(all_targets)
    if len(targets) < len(F4_COMMON_SEGMENT_IDS):
        raise ValueError("F4 targets do not contain the complete common prefix")
    common_ids = tuple(
        item.get("segment_id") for item in targets[: len(F4_COMMON_SEGMENT_IDS)]
    )
    if common_ids != F4_COMMON_SEGMENT_IDS:
        raise ValueError("F4 common target segment structure changed")
    order = tuple(extra.get("object_order", ()))
    if order not in F4_ALLOWED_OBJECT_ORDERS:
        raise ValueError("F4 object order is outside ABC/ACB/BAC")
    groups = extra.get("object_target_groups")
    if not isinstance(groups, list) or len(groups) != 3:
        raise ValueError("F4 requires exactly three object target groups")
    if tuple(group.get("role") for group in groups) != order:
        raise ValueError("F4 object target groups differ from program order")
    if extra.get("execution_arm") != "right":
        raise ValueError("F4 uniform block carry requires the frozen right arm")
    if extra.get("tray_pose_changed") not in (None, False):
        raise ValueError("F4 uniform block carry may not change the tray pose")
    return targets, order, groups


def expand_uniform_f4_block_carry_targets(
    all_targets: Sequence[Mapping[str, Any]],
    extra: Mapping[str, Any],
) -> tuple[list[dict], dict]:
    """Expand three legacy six-segment groups to uniform seven-segment groups.

    ``all_targets`` must contain the unchanged nine-segment common prefix and
    three legacy object groups in the program's frozen order.  The returned
    mappings are deep copies; inputs are never mutated.
    """

    targets, order, groups = _validate_common_and_order(all_targets, extra)
    common = deepcopy(targets[: len(F4_COMMON_SEGMENT_IDS)])
    flattened_legacy = targets[len(F4_COMMON_SEGMENT_IDS) :]
    expected_flattened_ids: list[str] = []
    revised_groups: list[dict] = []
    revised_flattened: list[dict] = []
    role_audits: dict[str, dict] = {}

    for role, group in zip(order, groups):
        group_targets = group.get("targets")
        if not isinstance(group_targets, list) or len(group_targets) != len(
            F4_LEGACY_BLOCK_SUFFIXES
        ):
            raise ValueError(f"F4 {role} legacy group must contain six targets")
        ids = tuple(item.get("segment_id") for item in group_targets)
        expected = _expected_ids(role, F4_LEGACY_BLOCK_SUFFIXES)
        if ids != expected:
            raise ValueError(f"F4 {role} legacy target order changed")
        expected_flattened_ids.extend(expected)
        copied = deepcopy(group_targets)
        for index, item in enumerate(copied):
            item["pose"] = _pose(
                item.get("pose"), label=f"F4 {role} {ids[index]} pose"
            ).tolist()
        midpoint, midpoint_audit = build_uniform_carry_midpoint(
            copied[2]["pose"], copied[3]["pose"]
        )
        midpoint_target = {
            "segment_id": f"{role}_carry_mid",
            "pose": midpoint.tolist(),
        }
        revised_targets = copied[:3] + [midpoint_target] + copied[3:]
        if tuple(item["segment_id"] for item in revised_targets) != _expected_ids(
            role, F4_SEGMENTED_BLOCK_SUFFIXES
        ):
            raise AssertionError("F4 segmented block target construction failed")
        revised_group = deepcopy(group)
        revised_group["targets"] = revised_targets
        revised_group["target_start_index"] = len(revised_flattened)
        revised_groups.append(revised_group)
        revised_flattened.extend(deepcopy(revised_targets))
        role_audits[role] = {
            "role": role,
            **midpoint_audit,
        }

    actual_flattened_ids = tuple(item.get("segment_id") for item in flattened_legacy)
    if actual_flattened_ids != tuple(expected_flattened_ids):
        raise ValueError("F4 flattened legacy targets differ from object groups")

    audit = {
        "schema_version": "cmf_f4_uniform_block_carry_midpoint_v3",
        "route_version": F4_UNIFORM_BLOCK_CARRY_VERSION,
        "uniform_roles": list(F4_BLOCK_ROLES),
        "program_object_order": list(order),
        "legacy_group_width": len(F4_LEGACY_BLOCK_SUFFIXES),
        "segmented_group_width": len(F4_SEGMENTED_BLOCK_SUFFIXES),
        "common_target_count": len(F4_COMMON_SEGMENT_IDS),
        "midpoint_xy_fraction": MIDPOINT_XY_FRACTION,
        "z_policy": "max(lift_z,preplace_z)",
        "orientation_policy": "copy_preplace_quaternion_after_sign_invariant_equivalence_check",
        "per_role": role_audits,
        "scene_layout_changed": False,
        "tray_pose_changed": False,
        "executing_arm_changed": False,
        "common_prefix_changed": False,
        "program_changed": False,
        "verifier_changed": False,
        "branch_specific_condition": False,
    }
    revised_extra = deepcopy(dict(extra))
    revised_extra["object_target_groups"] = revised_groups
    revised_extra["block_carry_route_version"] = F4_UNIFORM_BLOCK_CARRY_VERSION
    revised_extra["block_carry_route_audit"] = audit
    revised_all = common + revised_flattened
    validate_uniform_f4_block_carry_targets(revised_all, revised_extra)
    return revised_all, revised_extra


def validate_uniform_f4_block_carry_targets(
    all_targets: Sequence[Mapping[str, Any]],
    extra: Mapping[str, Any],
) -> dict:
    """Fail closed unless a target set exactly follows the uniform v3 route."""

    targets, order, groups = _validate_common_and_order(all_targets, extra)
    if extra.get("block_carry_route_version") != F4_UNIFORM_BLOCK_CARRY_VERSION:
        raise ValueError("F4 block carry route version is missing or stale")
    flattened = targets[len(F4_COMMON_SEGMENT_IDS) :]
    expected_flattened_ids: list[str] = []
    role_audits: dict[str, dict] = {}
    cursor = 0
    for role, group in zip(order, groups):
        group_targets = group.get("targets")
        if not isinstance(group_targets, list) or len(group_targets) != len(
            F4_SEGMENTED_BLOCK_SUFFIXES
        ):
            raise ValueError(f"F4 {role} segmented group must contain seven targets")
        expected = _expected_ids(role, F4_SEGMENTED_BLOCK_SUFFIXES)
        ids = tuple(item.get("segment_id") for item in group_targets)
        if ids != expected:
            raise ValueError(f"F4 {role} segmented target order changed")
        if group.get("target_start_index") != cursor:
            raise ValueError(f"F4 {role} target_start_index is inconsistent")
        poses = [
            _pose(item.get("pose"), label=f"F4 {segment_id} pose")
            for item, segment_id in zip(group_targets, ids)
        ]
        expected_midpoint, midpoint_audit = build_uniform_carry_midpoint(
            poses[2], poses[4]
        )
        if not np.array_equal(poses[3], expected_midpoint):
            raise ValueError(f"F4 {role} carry midpoint differs from frozen formula")
        expected_flattened_ids.extend(expected)
        role_audits[role] = {"role": role, **midpoint_audit}
        cursor += len(F4_SEGMENTED_BLOCK_SUFFIXES)
    if tuple(item.get("segment_id") for item in flattened) != tuple(
        expected_flattened_ids
    ):
        raise ValueError("F4 flattened segmented targets differ from object groups")
    return {
        "schema_version": "cmf_f4_uniform_block_carry_validation_v3",
        "route_version": F4_UNIFORM_BLOCK_CARRY_VERSION,
        "common_segment_ids": list(F4_COMMON_SEGMENT_IDS),
        "program_object_order": list(order),
        "uniform_roles": list(F4_BLOCK_ROLES),
        "per_role": role_audits,
        "scene_layout_changed": False,
        "tray_pose_changed": False,
        "executing_arm_changed": False,
        "common_prefix_changed": False,
        "program_changed": False,
        "verifier_changed": False,
        "branch_specific_condition": False,
        "pass": True,
    }


def audit_nominal_uniform_block_carry_geometry(
    *,
    object_poses: Mapping[str, Sequence[float]],
    slot_poses: Mapping[str, Sequence[float]],
    block_half_extents_m: Sequence[float] = (0.022, 0.022, 0.022),
    lift_distance_m: float = 0.10,
    preplace_distance_m: float = 0.10,
    table_bounds_xy: Mapping[str, Sequence[float]] | None = None,
) -> dict:
    """Conservative nominal carried-block sweep audit for the three roles.

    The calculation is intentionally limited to project-block geometry.  It
    does not replace official CuRobo whole-robot collision checking.
    """

    half = np.asarray(block_half_extents_m, dtype=np.float64).reshape(-1)
    if half.shape != (3,) or not np.all(np.isfinite(half)) or not np.all(half > 0):
        raise ValueError("F4 block half extents must be three positive values")
    if lift_distance_m <= 0 or preplace_distance_m <= 0:
        raise ValueError("F4 lift and preplace distances must be positive")
    if set(object_poses) != set(F4_BLOCK_ROLES) or set(slot_poses) != set(
        F4_BLOCK_ROLES
    ):
        raise ValueError("F4 nominal geometry requires exactly A/B/C objects and slots")
    objects = {
        role: _pose(object_poses[role], label=f"F4 nominal object {role} pose")
        for role in F4_BLOCK_ROLES
    }
    slots = {
        role: _pose(slot_poses[role], label=f"F4 nominal slot {role} pose")
        for role in F4_BLOCK_ROLES
    }
    bounds = table_bounds_xy or {"x": (-0.45, 0.45), "y": (-0.35, 0.20)}
    x_bounds = np.asarray(bounds["x"], dtype=np.float64).reshape(2)
    y_bounds = np.asarray(bounds["y"], dtype=np.float64).reshape(2)
    if not (x_bounds[0] < x_bounds[1] and y_bounds[0] < y_bounds[1]):
        raise ValueError("F4 table bounds are invalid")

    role_receipts: dict[str, dict] = {}
    global_clearances: list[float] = []
    for role in F4_BLOCK_ROLES:
        lift = objects[role].copy()
        lift[2] += float(lift_distance_m)
        target = slots[role].copy()
        target[:3] = slots[role][:3] + np.asarray([0.0, 0.0, half[2]])
        preplace = target.copy()
        preplace[2] += float(preplace_distance_m)
        midpoint, midpoint_audit = build_uniform_carry_midpoint(lift, preplace)
        collisions: dict[str, list[str]] = {
            "lift_to_carry_mid": [],
            "carry_mid_to_preplace": [],
        }
        clearances: dict[str, dict[str, float]] = {
            "lift_to_carry_mid": {},
            "carry_mid_to_preplace": {},
        }
        for segment_id, start, end in (
            ("lift_to_carry_mid", lift, midpoint),
            ("carry_mid_to_preplace", midpoint, preplace),
        ):
            carried_bottom = min(float(start[2]), float(end[2])) - half[2]
            for other_role in F4_BLOCK_ROLES:
                if other_role == role:
                    continue
                lower = objects[other_role][:3] - half
                upper = objects[other_role][:3] + half
                if segment_intersects_aabb(
                    start[:3],
                    end[:3],
                    lower,
                    upper,
                    swept_half_extents=half,
                ):
                    collisions[segment_id].append(other_role)
                clearance = float(carried_bottom - upper[2])
                clearances[segment_id][other_role] = clearance
                global_clearances.append(clearance)
        waypoints = (lift, midpoint, preplace)
        inside_table = all(
            x_bounds[0] + half[0] <= point[0] <= x_bounds[1] - half[0]
            and y_bounds[0] + half[1] <= point[1] <= y_bounds[1] - half[1]
            for point in waypoints
        )
        role_pass = (
            inside_table
            and all(not values for values in collisions.values())
            and all(
                value > 0.0
                for segment in clearances.values()
                for value in segment.values()
            )
        )
        role_receipts[role] = {
            "lift_actor_pose": lift.tolist(),
            "carry_mid_actor_pose": midpoint.tolist(),
            "preplace_actor_pose": preplace.tolist(),
            **midpoint_audit,
            "swept_non_target_collisions": collisions,
            "vertical_surface_clearance_m": clearances,
            "all_waypoints_inside_table": bool(inside_table),
            "pass": bool(role_pass),
        }
    passed = all(item["pass"] for item in role_receipts.values())
    return {
        "schema_version": "cmf_f4_uniform_block_carry_nominal_geometry_v3",
        "route_version": F4_UNIFORM_BLOCK_CARRY_VERSION,
        "geometry_scope": "nominal carried block AABB versus non-target A/B/C AABBs",
        "official_planner_authority": "whole-robot path collision remains an official CuRobo runtime Gate",
        "roles": role_receipts,
        "minimum_vertical_surface_clearance_m": min(global_clearances),
        "scene_layout_changed": False,
        "tray_pose_changed": False,
        "executing_arm_changed": False,
        "common_prefix_changed": False,
        "program_changed": False,
        "verifier_changed": False,
        "pass": bool(passed),
    }
