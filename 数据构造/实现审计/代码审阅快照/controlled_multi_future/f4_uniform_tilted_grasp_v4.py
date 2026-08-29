"""Pure F4 contract for one uniform inward-tilted block grasp route.

The revision-3 F4 probe showed that splitting the original top-down carry did
not make its first midpoint planner endpoint feasible.  This module encodes a
single, role-independent revision-4 hypothesis without importing SAPIEN or a
planner: tilt the ordered-block tool axis 60 degrees from table ``-z`` toward
table ``+y``.  The EEF therefore sits toward table ``-y`` (the robot side) of
the cube while preserving the requested actor pose.

Only the A/B/C block grasp/place geometry is constructed here.  The common-X
prefix, scene layout, tray, right-arm assignment, ABC/ACB/BAC programs,
branch-neutral pose, actor final targets, and semantic verifier remain inputs
or explicitly out of scope.  Runtime CuRobo and real contact checks remain
authoritative; the planner-frame norm and table-clearance calculations below
are an auditable CPU hypothesis, not an IK or collision proof.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .f4_uniform_block_carry_midpoint_v3 import build_uniform_carry_midpoint
from .geometry import (
    actor_target_to_eef_pose,
    compose_pose,
    matrix_quaternion,
    quaternion_matrix,
    relative_pose,
    world_axis_offset_pose,
)


SCHEMA_VERSION = "cmf_f4_uniform_tilted_grasp_v4"
ROUTE_VERSION = "f4_uniform_inward_tilted_block_grasp_v4"
SUPPORTED_ARM = "right"
F4_BLOCK_ROLES = ("A", "B", "C")
F4_ALLOWED_OBJECT_ORDERS = (
    ("A", "B", "C"),
    ("A", "C", "B"),
    ("B", "A", "C"),
)
F4_BLOCK_SEGMENT_SUFFIXES = (
    "pregrasp",
    "grasp",
    "lift",
    "carry_mid",
    "preplace",
    "release",
    "neutral",
)

TILT_FROM_TABLE_NEGATIVE_Z_DEGREES = 60.0
TOOL_REACH_FROM_EEF_TO_ACTOR_M = 0.12
FROZEN_CUBE_HALF_EXTENTS_M = np.asarray([0.022, 0.022, 0.022], dtype=np.float64)
DEFAULT_PREGRASP_DISTANCE_M = 0.09
DEFAULT_LIFT_DISTANCE_M = 0.10
DEFAULT_PREPLACE_DISTANCE_M = 0.10
DEFAULT_TABLE_TOP_Z_M = 0.74
DEFAULT_TRANSPORT_BOTTOM_CLEARANCE_M = 0.03
TARGET_RECONSTRUCTION_POSITION_ATOL_M = 1e-9
TARGET_RECONSTRUCTION_ORIENTATION_ATOL_RAD = 1e-7
DEFAULT_TABLE_BOUNDS_XY = {
    "x": (-0.45, 0.45),
    "y": (-0.35, 0.20),
}

# The Aloha root pose and right-arm CuRobo position transform are copied from
# the fixed RoboTwin embodiment/config sources.  The root quaternion is the
# normalized form of config.yml's [0.707, 0, 0, 0.707].
RIGHT_ROBOT_WORLD_ORIGIN_XYZ = np.asarray([0.0, -0.65, 0.0], dtype=np.float64)
RIGHT_ROBOT_WORLD_ORIGIN_WXYZ = np.asarray(
    [np.sqrt(0.5), 0.0, 0.0, np.sqrt(0.5)], dtype=np.float64
)
RIGHT_CUROBO_FRAME_BIAS_XYZ = np.asarray(
    [-0.2315, 0.3063, -0.781], dtype=np.float64
)
RIGHT_CUROBO_PATCH_YAW_RADIANS = -0.01
RIGHT_GRIPPER_BIAS_M = 0.12
RIGHT_GRIPPER_TO_ENDLINK_OFFSET_M = 0.12 - RIGHT_GRIPPER_BIAS_M

R3_FAILED_A_CARRY_MID_WORLD_XYZ = np.asarray(
    [0.15499947389631477, 0.07802601537640955, 0.9834013175523649],
    dtype=np.float64,
)


def _json_hash(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _pose(value: Any, *, label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(-1)
    if result.shape != (7,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be one finite 7-D pose")
    norm = float(np.linalg.norm(result[3:]))
    if not np.isfinite(norm) or norm <= 1e-12:
        raise ValueError(f"{label} has an invalid quaternion")
    return result.copy()


def _half_extents(value: Any) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(-1)
    if result.shape != (3,) or not np.all(np.isfinite(result)):
        raise ValueError("F4 cube half extents must be three finite values")
    if not np.allclose(
        result, FROZEN_CUBE_HALF_EXTENTS_M, rtol=0.0, atol=1e-12
    ):
        raise ValueError("F4 cube half extents differ from the frozen contract")
    return result.copy()


def _positive_distance(value: Any, *, label: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise ValueError(f"{label} must be finite and positive")
    return result


def _quaternion_angular_error(left: Sequence[float], right: Sequence[float]) -> float:
    first = np.asarray(left, dtype=np.float64).reshape(4)
    second = np.asarray(right, dtype=np.float64).reshape(4)
    first /= np.linalg.norm(first)
    second /= np.linalg.norm(second)
    cosine = float(np.clip(abs(np.dot(first, second)), 0.0, 1.0))
    return float(2.0 * np.arccos(cosine))


_TILT_RADIANS = np.deg2rad(TILT_FROM_TABLE_NEGATIVE_Z_DEGREES)
TILTED_TOOL_X_TABLE = np.asarray(
    [0.0, np.sin(_TILT_RADIANS), -np.cos(_TILT_RADIANS)], dtype=np.float64
)
TILTED_TOOL_Y_TABLE = np.asarray([-1.0, 0.0, 0.0], dtype=np.float64)
TILTED_TOOL_Z_TABLE = np.cross(TILTED_TOOL_X_TABLE, TILTED_TOOL_Y_TABLE)
TILTED_TOOL_ROTATION_TABLE = np.column_stack(
    (TILTED_TOOL_X_TABLE, TILTED_TOOL_Y_TABLE, TILTED_TOOL_Z_TABLE)
)
TILTED_GRASP_QUATERNION_WXYZ = matrix_quaternion(TILTED_TOOL_ROTATION_TABLE)
TILTED_ACTOR_TO_EEF_TRANSLATION_M = (
    -TOOL_REACH_FROM_EEF_TO_ACTOR_M * TILTED_TOOL_X_TABLE
)
TILTED_LOCAL_ACTOR_TO_EEF_POSE_WXYZ = np.concatenate(
    (TILTED_ACTOR_TO_EEF_TRANSLATION_M, TILTED_GRASP_QUATERNION_WXYZ)
)


def uniform_tilted_grasp_contract() -> dict:
    """Return the JSON-compatible, global A/B/C grasp contract."""

    contract = {
        "schema_version": SCHEMA_VERSION,
        "route_version": ROUTE_VERSION,
        "arm": SUPPORTED_ARM,
        "uniform_roles": list(F4_BLOCK_ROLES),
        "tilt_from_table_negative_z_degrees": TILT_FROM_TABLE_NEGATIVE_Z_DEGREES,
        "tilt_direction": "tool_x_toward_table_plus_y; EEF inward toward table_minus_y",
        "tool_x_table": TILTED_TOOL_X_TABLE.tolist(),
        "tool_y_table": TILTED_TOOL_Y_TABLE.tolist(),
        "tool_z_table": TILTED_TOOL_Z_TABLE.tolist(),
        "tool_rotation_table": TILTED_TOOL_ROTATION_TABLE.tolist(),
        "grasp_quaternion_wxyz": TILTED_GRASP_QUATERNION_WXYZ.tolist(),
        "actor_to_eef_translation_m": TILTED_ACTOR_TO_EEF_TRANSLATION_M.tolist(),
        "local_actor_to_eef_pose_wxyz": TILTED_LOCAL_ACTOR_TO_EEF_POSE_WXYZ.tolist(),
        "tool_reach_from_eef_to_actor_m": TOOL_REACH_FROM_EEF_TO_ACTOR_M,
        "cube_half_extents_m": FROZEN_CUBE_HALF_EXTENTS_M.tolist(),
        "common_prefix_policy": "not_read_or_modified",
        "final_actor_target_policy": "preserve_exact_caller_supplied_actor_pose",
        "role_specific_condition": False,
        "scene_layout_changed": False,
        "tray_pose_changed": False,
        "executing_arm_changed": False,
        "common_prefix_changed": False,
        "program_changed": False,
        "verifier_changed": False,
    }
    contract["grasp_contract_sha256"] = _json_hash(contract)
    return contract


def right_curobo_planner_position(world_xyz: Sequence[float]) -> np.ndarray:
    """Apply RoboTwin's fixed world-to-right-CuRobo position transform.

    The official right gripper-to-endlink position offset is zero for this
    embodiment (``0.12 - gripper_bias``), so no additional translation is
    required here.  This function deliberately audits only target position;
    orientation feasibility remains a real CuRobo Gate.
    """

    point = np.asarray(world_xyz, dtype=np.float64).reshape(-1)
    if point.shape != (3,) or not np.all(np.isfinite(point)):
        raise ValueError("right CuRobo target must be one finite 3-D point")
    if abs(RIGHT_GRIPPER_TO_ENDLINK_OFFSET_M) > 1e-12:
        raise RuntimeError("right gripper-to-endlink position offset changed")
    world_from_base = quaternion_matrix(RIGHT_ROBOT_WORLD_ORIGIN_WXYZ)
    base_point = world_from_base.T @ (point - RIGHT_ROBOT_WORLD_ORIGIN_XYZ)
    biased = base_point + RIGHT_CUROBO_FRAME_BIAS_XYZ
    yaw = RIGHT_CUROBO_PATCH_YAW_RADIANS
    patch = np.asarray(
        [
            [np.cos(yaw), -np.sin(yaw), 0.0],
            [np.sin(yaw), np.cos(yaw), 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    return patch @ biased


def build_uniform_tilted_block_group(
    *,
    role: str,
    actor_pose: Sequence[float],
    target_actor_pose: Sequence[float],
    neutral_pose: Sequence[float],
    arm: str = SUPPORTED_ARM,
    cube_half_extents_m: Sequence[float] = FROZEN_CUBE_HALF_EXTENTS_M,
    pregrasp_distance_m: float = DEFAULT_PREGRASP_DISTANCE_M,
    lift_distance_m: float = DEFAULT_LIFT_DISTANCE_M,
    preplace_distance_m: float = DEFAULT_PREPLACE_DISTANCE_M,
) -> dict:
    """Build one seven-target block group from the global tilted transform."""

    if role not in F4_BLOCK_ROLES:
        raise ValueError("F4 tilted grasp role must be A, B, or C")
    if arm != SUPPORTED_ARM:
        raise ValueError("F4 tilted grasp is frozen for the right arm")
    _half_extents(cube_half_extents_m)
    source = _pose(actor_pose, label=f"F4 {role} source actor pose")
    target = _pose(target_actor_pose, label=f"F4 {role} target actor pose")
    neutral = _pose(neutral_pose, label="F4 branch-neutral pose")
    pregrasp_distance = _positive_distance(
        pregrasp_distance_m, label="F4 pregrasp distance"
    )
    lift_distance = _positive_distance(lift_distance_m, label="F4 lift distance")
    preplace_distance = _positive_distance(
        preplace_distance_m, label="F4 preplace distance"
    )

    local_grasp = TILTED_LOCAL_ACTOR_TO_EEF_POSE_WXYZ.copy()
    local_pregrasp = local_grasp.copy()
    local_pregrasp[:3] -= pregrasp_distance * TILTED_TOOL_X_TABLE
    grasp = compose_pose(source, local_grasp)
    pregrasp = compose_pose(source, local_pregrasp)
    lift = world_axis_offset_pose(grasp, lift_distance)
    release = actor_target_to_eef_pose(grasp, source, target)
    preplace = world_axis_offset_pose(release, preplace_distance)
    carry_mid, midpoint_audit = build_uniform_carry_midpoint(lift, preplace)

    poses = {
        "pregrasp": pregrasp,
        "grasp": grasp,
        "lift": lift,
        "carry_mid": carry_mid,
        "preplace": preplace,
        "release": release,
        "neutral": neutral,
    }
    targets = [
        {"segment_id": f"{role}_{suffix}", "pose": poses[suffix].tolist()}
        for suffix in F4_BLOCK_SEGMENT_SUFFIXES
    ]
    eef_to_actor = relative_pose(grasp, source)
    reconstructed_target = compose_pose(release, eef_to_actor)
    final_position_error = float(np.linalg.norm(reconstructed_target[:3] - target[:3]))
    final_orientation_error = _quaternion_angular_error(
        reconstructed_target[3:], target[3:]
    )
    target_preserved = (
        final_position_error <= TARGET_RECONSTRUCTION_POSITION_ATOL_M
        and final_orientation_error
        <= TARGET_RECONSTRUCTION_ORIENTATION_ATOL_RAD
    )
    if not target_preserved:
        raise RuntimeError("F4 tilted grasp failed to preserve the actor target pose")

    contract = uniform_tilted_grasp_contract()
    return {
        "role": role,
        "targets": targets,
        "grasp_contract": contract,
        "target_actor_pose": target.tolist(),
        "route_audit": {
            "schema_version": "cmf_f4_uniform_tilted_block_group_v4",
            "route_version": ROUTE_VERSION,
            "role": role,
            "arm": arm,
            "source_actor_pose": source.tolist(),
            "target_actor_pose": target.tolist(),
            "reconstructed_release_actor_pose": reconstructed_target.tolist(),
            "final_actor_target_position_error_m": final_position_error,
            "final_actor_target_orientation_error_rad": final_orientation_error,
            "target_reconstruction_position_atol_m": (
                TARGET_RECONSTRUCTION_POSITION_ATOL_M
            ),
            "target_reconstruction_orientation_atol_rad": (
                TARGET_RECONSTRUCTION_ORIENTATION_ATOL_RAD
            ),
            "final_actor_target_preserved": target_preserved,
            "pregrasp_distance_m": pregrasp_distance,
            "lift_distance_m": lift_distance,
            "preplace_distance_m": preplace_distance,
            "midpoint_audit": midpoint_audit,
            "common_prefix_changed": False,
            "scene_layout_changed": False,
            "tray_pose_changed": False,
            "executing_arm_changed": False,
            "program_changed": False,
            "verifier_changed": False,
            "role_specific_condition": False,
        },
    }


def build_uniform_tilted_f4_block_groups(
    *,
    object_poses: Mapping[str, Sequence[float]],
    target_actor_poses: Mapping[str, Sequence[float]],
    neutral_pose: Sequence[float],
    object_order: Sequence[str] = F4_BLOCK_ROLES,
    arm: str = SUPPORTED_ARM,
) -> dict:
    """Build all A/B/C groups while preserving a frozen program order."""

    if set(object_poses) != set(F4_BLOCK_ROLES):
        raise ValueError("F4 tilted grasp requires exactly A/B/C source poses")
    if set(target_actor_poses) != set(F4_BLOCK_ROLES):
        raise ValueError("F4 tilted grasp requires exactly A/B/C actor targets")
    order = tuple(object_order)
    if order not in F4_ALLOWED_OBJECT_ORDERS:
        raise ValueError("F4 tilted grasp order must be ABC, ACB, or BAC")
    original_objects = deepcopy(dict(object_poses))
    original_targets = deepcopy(dict(target_actor_poses))
    original_neutral = deepcopy(neutral_pose)
    groups = []
    flattened = []
    for role in order:
        group = build_uniform_tilted_block_group(
            role=role,
            actor_pose=object_poses[role],
            target_actor_pose=target_actor_poses[role],
            neutral_pose=neutral_pose,
            arm=arm,
        )
        group["target_start_index"] = len(flattened)
        groups.append(group)
        flattened.extend(deepcopy(group["targets"]))
    if any(
        not np.array_equal(
            np.asarray(object_poses[role]), np.asarray(original_objects[role])
        )
        for role in F4_BLOCK_ROLES
    ):
        raise RuntimeError("F4 tilted grasp mutated source object poses")
    if any(
        not np.array_equal(
            np.asarray(target_actor_poses[role]),
            np.asarray(original_targets[role]),
        )
        for role in F4_BLOCK_ROLES
    ):
        raise RuntimeError("F4 tilted grasp mutated target actor poses")
    if not np.array_equal(
        np.asarray(neutral_pose), np.asarray(original_neutral)
    ):
        raise RuntimeError("F4 tilted grasp mutated the branch-neutral pose")
    hashes = {group["grasp_contract"]["grasp_contract_sha256"] for group in groups}
    if len(hashes) != 1:
        raise RuntimeError("F4 A/B/C tilted grasp contracts are not uniform")
    audit = {
        "schema_version": "cmf_f4_uniform_tilted_group_set_v4",
        "route_version": ROUTE_VERSION,
        "object_order": list(order),
        "uniform_roles": list(F4_BLOCK_ROLES),
        "group_width": len(F4_BLOCK_SEGMENT_SUFFIXES),
        "single_grasp_contract_sha256": next(iter(hashes)),
        "common_prefix_policy": "not_read_or_modified",
        "actor_final_targets_preserved": all(
            group["route_audit"]["final_actor_target_preserved"] for group in groups
        ),
        "scene_layout_changed": False,
        "tray_pose_changed": False,
        "executing_arm_changed": False,
        "common_prefix_changed": False,
        "program_changed": False,
        "verifier_changed": False,
        "role_specific_condition": False,
    }
    return {
        "object_target_groups": groups,
        "flattened_targets": flattened,
        "grasp_contract": uniform_tilted_grasp_contract(),
        "audit": audit,
    }


def audit_uniform_tilted_f4_geometry(
    *,
    object_poses: Mapping[str, Sequence[float]],
    target_actor_poses: Mapping[str, Sequence[float]],
    neutral_pose: Sequence[float],
    object_order: Sequence[str] = F4_BLOCK_ROLES,
    table_top_z_m: float = DEFAULT_TABLE_TOP_Z_M,
    table_bounds_xy: Mapping[str, Sequence[float]] = DEFAULT_TABLE_BOUNDS_XY,
    required_transport_bottom_clearance_m: float = DEFAULT_TRANSPORT_BOTTOM_CLEARANCE_M,
) -> dict:
    """Audit target preservation, planner norms, and table clearances.

    ``pass`` means that this pure geometric hypothesis is internally
    consistent and improves the recorded r3 positional norm.  It never means
    that CuRobo IK, whole-robot collision, grasp contact, or rollout semantics
    have passed.
    """

    table_top = float(table_top_z_m)
    clearance_required = _positive_distance(
        required_transport_bottom_clearance_m,
        label="F4 transport bottom clearance",
    )
    if not np.isfinite(table_top):
        raise ValueError("F4 table top must be finite")
    x_bounds = np.asarray(table_bounds_xy["x"], dtype=np.float64).reshape(2)
    y_bounds = np.asarray(table_bounds_xy["y"], dtype=np.float64).reshape(2)
    if not (
        np.all(np.isfinite(x_bounds))
        and np.all(np.isfinite(y_bounds))
        and x_bounds[0] < x_bounds[1]
        and y_bounds[0] < y_bounds[1]
    ):
        raise ValueError("F4 table bounds are invalid")

    built = build_uniform_tilted_f4_block_groups(
        object_poses=object_poses,
        target_actor_poses=target_actor_poses,
        neutral_pose=neutral_pose,
        object_order=object_order,
    )
    failed_r3_planner_position = right_curobo_planner_position(
        R3_FAILED_A_CARRY_MID_WORLD_XYZ
    )
    failed_r3_norm = float(np.linalg.norm(failed_r3_planner_position))
    role_receipts = {}
    all_planner_norms = []
    all_transport_clearances = []
    for group in built["object_target_groups"]:
        role = group["role"]
        source = _pose(object_poses[role], label=f"F4 {role} source actor pose")
        target_actor = _pose(
            target_actor_poses[role], label=f"F4 {role} target actor pose"
        )
        poses = {
            item["segment_id"].removeprefix(f"{role}_"): _pose(
                item["pose"], label=f"F4 {item['segment_id']} pose"
            )
            for item in group["targets"]
        }
        eef_to_actor = relative_pose(poses["grasp"], source)
        held_actor_poses = {
            suffix: compose_pose(poses[suffix], eef_to_actor)
            for suffix in ("grasp", "lift", "carry_mid", "preplace", "release")
        }
        planner_positions = {
            suffix: right_curobo_planner_position(poses[suffix][:3])
            for suffix in F4_BLOCK_SEGMENT_SUFFIXES
        }
        planner_norms = {
            suffix: float(np.linalg.norm(position))
            for suffix, position in planner_positions.items()
        }
        all_planner_norms.extend(planner_norms.values())
        transport_clearances = {
            suffix: float(
                held_actor_poses[suffix][2]
                - FROZEN_CUBE_HALF_EXTENTS_M[2]
                - table_top
            )
            for suffix in ("lift", "carry_mid", "preplace")
        }
        all_transport_clearances.extend(transport_clearances.values())
        support_gaps = {
            "source_grasp_actor_bottom_gap_m": float(
                held_actor_poses["grasp"][2]
                - FROZEN_CUBE_HALF_EXTENTS_M[2]
                - table_top
            ),
            "target_release_actor_bottom_gap_m": float(
                held_actor_poses["release"][2]
                - FROZEN_CUBE_HALF_EXTENTS_M[2]
                - table_top
            ),
        }
        source_inside = bool(
            x_bounds[0] + FROZEN_CUBE_HALF_EXTENTS_M[0]
            <= source[0]
            <= x_bounds[1] - FROZEN_CUBE_HALF_EXTENTS_M[0]
            and y_bounds[0] + FROZEN_CUBE_HALF_EXTENTS_M[1]
            <= source[1]
            <= y_bounds[1] - FROZEN_CUBE_HALF_EXTENTS_M[1]
        )
        target_inside = bool(
            x_bounds[0] + FROZEN_CUBE_HALF_EXTENTS_M[0]
            <= target_actor[0]
            <= x_bounds[1] - FROZEN_CUBE_HALF_EXTENTS_M[0]
            and y_bounds[0] + FROZEN_CUBE_HALF_EXTENTS_M[1]
            <= target_actor[1]
            <= y_bounds[1] - FROZEN_CUBE_HALF_EXTENTS_M[1]
        )
        final_position_error = float(
            np.linalg.norm(held_actor_poses["release"][:3] - target_actor[:3])
        )
        final_orientation_error = _quaternion_angular_error(
            held_actor_poses["release"][3:], target_actor[3:]
        )
        checks = {
            "source_actor_inside_table": source_inside,
            "target_actor_inside_table": target_inside,
            "final_actor_position_preserved": final_position_error
            <= TARGET_RECONSTRUCTION_POSITION_ATOL_M,
            "final_actor_orientation_preserved": final_orientation_error
            <= TARGET_RECONSTRUCTION_ORIENTATION_ATOL_RAD,
            "transport_actor_bottom_clearance": min(transport_clearances.values())
            >= clearance_required,
            "source_not_below_table": support_gaps[
                "source_grasp_actor_bottom_gap_m"
            ]
            >= -1e-9,
            "target_not_below_table": support_gaps[
                "target_release_actor_bottom_gap_m"
            ]
            >= -1e-9,
        }
        role_receipts[role] = {
            "role": role,
            "planner_frame_positions": {
                key: value.tolist() for key, value in planner_positions.items()
            },
            "planner_frame_position_norms_m": planner_norms,
            "maximum_planner_frame_position_norm_m": max(planner_norms.values()),
            "transport_actor_bottom_clearance_m": transport_clearances,
            **support_gaps,
            "final_actor_target_position_error_m": final_position_error,
            "final_actor_target_orientation_error_rad": final_orientation_error,
            "checks": checks,
            "pass": all(checks.values()),
        }

    maximum_norm = max(all_planner_norms)
    minimum_clearance = min(all_transport_clearances)
    checks = {
        "all_roles_geometry_pass": all(item["pass"] for item in role_receipts.values()),
        "one_uniform_contract": len(
            {
                group["grasp_contract"]["grasp_contract_sha256"]
                for group in built["object_target_groups"]
            }
        )
        == 1,
        "all_actor_final_targets_preserved": built["audit"][
            "actor_final_targets_preserved"
        ],
        "maximum_planner_position_norm_below_r3_failed_midpoint": maximum_norm
        < failed_r3_norm,
        "minimum_transport_bottom_clearance": minimum_clearance
        >= clearance_required,
    }
    return {
        "schema_version": "cmf_f4_uniform_tilted_geometry_audit_v4",
        "route_version": ROUTE_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "runtime_ik_still_required": True,
        "planner_norm_is_not_reachability_proof": True,
        "whole_robot_collision_authority": "official CuRobo runtime success/failure",
        "gripper_mesh_table_clearance_available": False,
        "carried_cube_and_eef_geometry_scope_only": True,
        "r3_failed_a_midpoint_world_xyz": R3_FAILED_A_CARRY_MID_WORLD_XYZ.tolist(),
        "r3_failed_a_midpoint_planner_position": failed_r3_planner_position.tolist(),
        "r3_failed_a_midpoint_planner_position_norm_m": failed_r3_norm,
        "maximum_proposed_planner_frame_position_norm_m": maximum_norm,
        "required_transport_bottom_clearance_m": clearance_required,
        "minimum_transport_actor_bottom_clearance_m": minimum_clearance,
        "roles": role_receipts,
        "build_audit": built["audit"],
        "checks": checks,
        "scene_layout_changed": False,
        "tray_pose_changed": False,
        "executing_arm_changed": False,
        "common_prefix_changed": False,
        "program_changed": False,
        "verifier_changed": False,
        "role_specific_condition": False,
        "pass": all(checks.values()),
    }


__all__ = [
    "DEFAULT_LIFT_DISTANCE_M",
    "DEFAULT_PREGRASP_DISTANCE_M",
    "DEFAULT_PREPLACE_DISTANCE_M",
    "F4_ALLOWED_OBJECT_ORDERS",
    "F4_BLOCK_ROLES",
    "F4_BLOCK_SEGMENT_SUFFIXES",
    "FROZEN_CUBE_HALF_EXTENTS_M",
    "R3_FAILED_A_CARRY_MID_WORLD_XYZ",
    "ROUTE_VERSION",
    "SCHEMA_VERSION",
    "SUPPORTED_ARM",
    "TILTED_ACTOR_TO_EEF_TRANSLATION_M",
    "TILTED_GRASP_QUATERNION_WXYZ",
    "TILTED_LOCAL_ACTOR_TO_EEF_POSE_WXYZ",
    "TILTED_TOOL_ROTATION_TABLE",
    "TILTED_TOOL_X_TABLE",
    "TILTED_TOOL_Y_TABLE",
    "TILTED_TOOL_Z_TABLE",
    "TILT_FROM_TABLE_NEGATIVE_Z_DEGREES",
    "audit_uniform_tilted_f4_geometry",
    "build_uniform_tilted_block_group",
    "build_uniform_tilted_f4_block_groups",
    "right_curobo_planner_position",
    "uniform_tilted_grasp_contract",
]
