"""Pure-CPU construction validity for F4 Stage-B layouts.

This module rejects a layout before planner or simulator work when a role's
target overlaps an object that is still present, or when the carried block's
translation sweep enters another block plus the frozen safety clearance.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

import numpy as np

from .canonical_artifact import canonical_hash_json
from .geometry import pose_matrix


SCHEMA_VERSION = "cmf_f4_stage_b_geometry_contract_v2"
IMPLEMENTATION_VERSION = "controlled_multi_future_high_level_generation_repair_v2_0"
ROLES = ("A", "B", "C")
PROGRAM_ORDERS = (("A", "B", "C"), ("A", "C", "B"), ("B", "A", "C"))
BLOCK_HALF_EXTENTS_M = np.asarray([0.022, 0.022, 0.022], dtype=np.float64)
EXTRA_SAFETY_CLEARANCE_M = 0.010
TABLE_BOUNDS_XY = {"x": (-0.45, 0.45), "y": (-0.35, 0.20)}
TABLE_TOP_Z_M = 0.740

LEGACY_SOURCE_LAYOUT_R01 = {
    "A": [-0.200, 0.020, 0.762, 1.0, 0.0, 0.0, 0.0],
    "B": [-0.110, 0.020, 0.762, 1.0, 0.0, 0.0, 0.0],
    "C": [-0.020, 0.020, 0.762, 1.0, 0.0, 0.0, 0.0],
}
LEGACY_SLOT_LAYOUT_R01 = {
    "A": [-0.100, 0.040, 0.742, 1.0, 0.0, 0.0, 0.0],
    "B": [-0.205, 0.040, 0.742, 1.0, 0.0, 0.0, 0.0],
    "C": [-0.355, 0.040, 0.742, 1.0, 0.0, 0.0, 0.0],
}
SAFE_SLOT_ROWS_V2 = (
    ((-0.20, -0.12), (-0.11, -0.12), (-0.02, -0.12)),
    ((-0.22, -0.14), (-0.13, -0.14), (-0.04, -0.14)),
    ((-0.18, -0.16), (-0.09, -0.16), (0.00, -0.16)),
    ((-0.24, -0.18), (-0.14, -0.18), (-0.04, -0.18)),
)


def _pose7(value: Sequence[float], label: str) -> np.ndarray:
    pose = np.asarray(value, dtype=np.float64).reshape(-1)
    if pose.shape != (7,) or not np.all(np.isfinite(pose)):
        raise ValueError(f"{label} must be one finite pose7")
    norm = float(np.linalg.norm(pose[3:]))
    if norm <= 1e-12:
        raise ValueError(f"{label} quaternion norm must be positive")
    pose = pose.copy()
    pose[3:] /= norm
    return pose


def _obb_projection_gaps(
    left_pose: Sequence[float],
    right_pose: Sequence[float],
    *,
    left_half_extents: Sequence[float] = BLOCK_HALF_EXTENTS_M,
    right_half_extents: Sequence[float] = BLOCK_HALF_EXTENTS_M,
) -> list[float]:
    left = _pose7(left_pose, "left OBB")
    right = _pose7(right_pose, "right OBB")
    left_axes = pose_matrix(left)[:3, :3]
    right_axes = pose_matrix(right)[:3, :3]
    delta = right[:3] - left[:3]
    left_half = np.asarray(left_half_extents, dtype=np.float64).reshape(3)
    right_half = np.asarray(right_half_extents, dtype=np.float64).reshape(3)
    axes = [left_axes[:, index] for index in range(3)]
    axes += [right_axes[:, index] for index in range(3)]
    axes += [
        np.cross(left_axes[:, left_index], right_axes[:, right_index])
        for left_index in range(3)
        for right_index in range(3)
    ]
    gaps = []
    for axis in axes:
        norm = float(np.linalg.norm(axis))
        if norm <= 1e-10:
            continue
        unit = axis / norm
        left_radius = float(np.sum(np.abs(left_axes.T @ unit) * left_half))
        right_radius = float(np.sum(np.abs(right_axes.T @ unit) * right_half))
        gaps.append(abs(float(np.dot(delta, unit))) - left_radius - right_radius)
    if not gaps:
        raise ValueError("OBB SAT produced no usable axes")
    return gaps


def audit_obb_clearance_v2(
    left_pose: Sequence[float],
    right_pose: Sequence[float],
    *,
    required_clearance_m: float = EXTRA_SAFETY_CLEARANCE_M,
) -> dict[str, Any]:
    required = float(required_clearance_m)
    if not np.isfinite(required) or required < 0.0:
        raise ValueError("required OBB clearance must be finite and nonnegative")
    gaps = _obb_projection_gaps(left_pose, right_pose)
    separating_clearance = max(gaps)
    value = {
        "schema_version": "cmf_f4_obb_clearance_v2",
        "required_clearance_m": required,
        "maximum_separating_axis_gap_m": separating_clearance,
        "obb_intersects_without_margin": separating_clearance < 0.0,
        "pass": separating_clearance + 1e-12 >= required,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def _segment_intersects_aabb(
    start: np.ndarray, end: np.ndarray, lower: np.ndarray, upper: np.ndarray
) -> bool:
    direction = end - start
    low_t = 0.0
    high_t = 1.0
    for axis in range(3):
        if abs(float(direction[axis])) <= 1e-12:
            if start[axis] < lower[axis] or start[axis] > upper[axis]:
                return False
            continue
        first = float((lower[axis] - start[axis]) / direction[axis])
        second = float((upper[axis] - start[axis]) / direction[axis])
        enter, leave = min(first, second), max(first, second)
        low_t = max(low_t, enter)
        high_t = min(high_t, leave)
        if low_t > high_t:
            return False
    return True


def audit_translation_sweep_v2(
    start_pose: Sequence[float],
    end_pose: Sequence[float],
    obstacle_pose: Sequence[float],
    *,
    required_clearance_m: float = EXTRA_SAFETY_CLEARANCE_M,
) -> dict[str, Any]:
    start = _pose7(start_pose, "sweep start")
    end = _pose7(end_pose, "sweep end")
    obstacle = _pose7(obstacle_pose, "sweep obstacle")
    obstacle_matrix = pose_matrix(obstacle)
    obstacle_rotation = obstacle_matrix[:3, :3]
    held_rotation = pose_matrix(start)[:3, :3]
    held_extent_in_obstacle = (
        np.abs(obstacle_rotation.T @ held_rotation) @ BLOCK_HALF_EXTENTS_M
    )
    base_expansion = held_extent_in_obstacle + BLOCK_HALF_EXTENTS_M
    expansion = base_expansion + float(required_clearance_m)
    start_local = obstacle_rotation.T @ (start[:3] - obstacle[:3])
    end_local = obstacle_rotation.T @ (end[:3] - obstacle[:3])
    intersects = _segment_intersects_aabb(
        start_local, end_local, -expansion, expansion
    )

    def clearance_at(fraction: float) -> float:
        point = start_local + fraction * (end_local - start_local)
        return float(np.max(np.abs(point) - base_expansion))

    lower_t, upper_t = 0.0, 1.0
    for _ in range(96):
        first = lower_t + (upper_t - lower_t) / 3.0
        second = upper_t - (upper_t - lower_t) / 3.0
        if clearance_at(first) <= clearance_at(second):
            upper_t = second
        else:
            lower_t = first
    fractions = (0.0, 1.0, lower_t, upper_t, 0.5 * (lower_t + upper_t))
    minimum_clearance = min(clearance_at(value) for value in fractions)
    value = {
        "schema_version": "cmf_f4_translation_sweep_clearance_v2",
        "required_clearance_m": float(required_clearance_m),
        "conservative_minkowski_half_extents_m": expansion.tolist(),
        "minimum_linf_surface_clearance_m": minimum_clearance,
        "intersects_expanded_obstacle": intersects,
        "pass": not intersects
        and minimum_clearance + 1e-12 >= float(required_clearance_m),
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def _target_actor_pose(slot_pose: Sequence[float]) -> np.ndarray:
    slot = _pose7(slot_pose, "F4 slot")
    target = slot.copy()
    target[2] += BLOCK_HALF_EXTENTS_M[2]
    return target


def _nominal_actor_path(
    source: np.ndarray,
    target: np.ndarray,
    *,
    corridor_policy: str,
    arm: str,
) -> dict[str, np.ndarray]:
    lift = source.copy()
    lift[2] += 0.08
    preplace = target.copy()
    preplace[2] += 0.10
    carry = lift.copy()
    if corridor_policy == "lower_carry_height":
        carry[:2] = 0.5 * (lift[:2] + preplace[:2])
        carry[2] = max(float(lift[2]), float(preplace[2]))
    elif corridor_policy == "f1_uniform_cluster_center_carry_hub":
        carry[:2] = [-0.11 if arm == "left" else 0.11, 0.02]
        carry[2] = max(float(lift[2]), float(preplace[2]), 0.95)
    else:
        raise ValueError("unknown F4 corridor policy")
    return {"lift": lift, "carry_mid": carry, "preplace": preplace, "release": target}


def audit_f4_stage_b_candidate_geometry_v2(
    *,
    source_layout: Mapping[str, Sequence[float]],
    slot_poses: Mapping[str, Sequence[float]],
    corridor_policy: str,
    arm: str,
    program_orders: Sequence[Sequence[str]] = PROGRAM_ORDERS,
    required_clearance_m: float = EXTRA_SAFETY_CLEARANCE_M,
) -> dict[str, Any]:
    if set(source_layout) != set(ROLES) or set(slot_poses) != set(ROLES):
        raise ValueError("F4 geometry audit requires exactly A/B/C sources and slots")
    sources = {role: _pose7(source_layout[role], f"F4 {role} source") for role in ROLES}
    targets = {role: _target_actor_pose(slot_poses[role]) for role in ROLES}
    programs = {}
    failure_codes = []
    for raw_order in program_orders:
        order = tuple(raw_order)
        if order not in PROGRAM_ORDERS:
            raise ValueError("F4 geometry audit received unsupported program order")
        states = {role: pose.copy() for role, pose in sources.items()}
        role_audits = []
        for role in order:
            others = [other for other in ROLES if other != role]
            target_checks = {
                other: audit_obb_clearance_v2(
                    targets[role], states[other], required_clearance_m=required_clearance_m
                )
                for other in others
            }
            path = _nominal_actor_path(
                states[role], targets[role], corridor_policy=corridor_policy, arm=arm
            )
            sweeps = {}
            for segment, start_name, end_name in (
                ("lift_to_carry_mid", "lift", "carry_mid"),
                ("carry_mid_to_preplace", "carry_mid", "preplace"),
                ("preplace_to_release", "preplace", "release"),
            ):
                sweeps[segment] = {
                    other: audit_translation_sweep_v2(
                        path[start_name],
                        path[end_name],
                        states[other],
                        required_clearance_m=required_clearance_m,
                    )
                    for other in others
                }
            terminal_pass = all(item["pass"] for item in target_checks.values())
            sweep_pass = all(
                item["pass"]
                for segment in sweeps.values()
                for item in segment.values()
            )
            if not terminal_pass:
                failure_codes.append(
                    f"{''.join(order)}:{role}:TARGET_OVERLAPS_CURRENT_OTHER_OBJECT"
                )
            if not sweep_pass:
                failure_codes.append(
                    f"{''.join(order)}:{role}:CARRIED_BLOCK_SWEEP_INTERSECTS_CURRENT_OTHER_OBJECT"
                )
            role_audits.append(
                {
                    "role": role,
                    "state_of_other_blocks_before_role": {
                        other: states[other].tolist() for other in others
                    },
                    "target_actor_pose": targets[role].tolist(),
                    "target_clearance": target_checks,
                    "nominal_actor_path": {
                        key: value.tolist() for key, value in path.items()
                    },
                    "sweep_clearance": sweeps,
                    "target_terminal_pass": terminal_pass,
                    "all_three_translation_sweeps_pass": sweep_pass,
                    "pass": terminal_pass and sweep_pass,
                }
            )
            states[role] = targets[role].copy()
        final_mapping = {
            role: states[role].tolist() for role in ROLES
        }
        programs["".join(order)] = {
            "order": list(order),
            "role_audits": role_audits,
            "final_mapping": final_mapping,
            "final_mapping_sha256": canonical_hash_json(final_mapping),
            "pass": all(item["pass"] for item in role_audits),
        }
    final_hashes = {value["final_mapping_sha256"] for value in programs.values()}
    terminal_clearances = [
        check["maximum_separating_axis_gap_m"]
        for program in programs.values()
        for role in program["role_audits"]
        for check in role["target_clearance"].values()
    ]
    swept_clearances = [
        check["minimum_linf_surface_clearance_m"]
        for program in programs.values()
        for role in program["role_audits"]
        for segment in role["sweep_clearance"].values()
        for check in segment.values()
    ]
    construction_valid = all(value["pass"] for value in programs.values()) and len(final_hashes) == 1
    value = {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "required_extra_safety_clearance_m": float(required_clearance_m),
        "source_layout": {key: value.tolist() for key, value in sources.items()},
        "slot_poses": {key: _pose7(slot_poses[key], f"F4 {key} slot").tolist() for key in ROLES},
        "target_actor_poses": {key: value.tolist() for key, value in targets.items()},
        "corridor_policy": corridor_policy,
        "arm": arm,
        "program_state_transition_audits": programs,
        "equal_final_world_state": len(final_hashes) == 1,
        "minimum_terminal_clearance_m": min(terminal_clearances),
        "minimum_swept_clearance_m": min(swept_clearances),
        "construction_failure_codes": sorted(set(failure_codes)),
        "construction_valid": construction_valid,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["geometry_contract_sha256"] = canonical_hash_json(value)
    return value


def legacy_r01_invalidation_v2() -> dict[str, Any]:
    audit = audit_f4_stage_b_candidate_geometry_v2(
        source_layout=LEGACY_SOURCE_LAYOUT_R01,
        slot_poses=LEGACY_SLOT_LAYOUT_R01,
        corridor_policy="lower_carry_height",
        arm="left",
    )
    value = {
        "schema_version": "cmf_f4_legacy_r01_invalidation_v2",
        "legacy_candidate_id": "f4-slot-corridor-hv1-r01",
        "status": "INVALID_BY_CONSTRUCTION_TARGET_OVERLAPS_UNMOVED_OBJECT",
        "geometry_audit": audit,
        "reexecution_required": False,
        "old_receipts_remain_factual": True,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


__all__ = [
    "EXTRA_SAFETY_CLEARANCE_M",
    "LEGACY_SLOT_LAYOUT_R01",
    "LEGACY_SOURCE_LAYOUT_R01",
    "PROGRAM_ORDERS",
    "SAFE_SLOT_ROWS_V2",
    "audit_f4_stage_b_candidate_geometry_v2",
    "audit_obb_clearance_v2",
    "audit_translation_sweep_v2",
    "legacy_r01_invalidation_v2",
]
