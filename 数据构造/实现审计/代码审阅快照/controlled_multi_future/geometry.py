"""Dependency-light geometry contracts for controlled multi-future runtime v2.

All poses use RoboTwin's ``[x, y, z, qw, qx, qy, qz]`` convention.  The
helpers in this module deliberately avoid importing SAPIEN or the official
task package so that the transform and verifier contracts can be unit-tested
before a GPU process is started.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence

import numpy as np


IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v2"


def _unit_quaternion(value: Sequence[float]) -> np.ndarray:
    quaternion = np.asarray(value, dtype=np.float64).reshape(4)
    norm = float(np.linalg.norm(quaternion))
    if norm <= 1e-12:
        raise ValueError("quaternion norm must be positive")
    return quaternion / norm


def quaternion_matrix(value: Sequence[float]) -> np.ndarray:
    """Return a 3x3 rotation matrix for a wxyz quaternion."""

    w, x, y, z = _unit_quaternion(value)
    return np.asarray(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def quaternion_multiply(first: Sequence[float], second: Sequence[float]) -> np.ndarray:
    """Hamilton product of normalized wxyz quaternions."""

    w1, x1, y1, z1 = _unit_quaternion(first)
    w2, x2, y2, z2 = _unit_quaternion(second)
    return _unit_quaternion(
        [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ]
    )


def world_z_yaw_pose(pose: Sequence[float], yaw_radians: float) -> np.ndarray:
    result = np.asarray(pose, dtype=np.float64).reshape(7).copy()
    half = float(yaw_radians) / 2.0
    result[3:] = quaternion_multiply([np.cos(half), 0.0, 0.0, np.sin(half)], result[3:])
    return result


def matrix_quaternion(value: Sequence[Sequence[float]]) -> np.ndarray:
    """Return a normalized wxyz quaternion for a 3x3 rotation matrix."""

    matrix = np.asarray(value, dtype=np.float64).reshape(3, 3)
    trace = float(np.trace(matrix))
    if trace > 0:
        scale = np.sqrt(trace + 1.0) * 2.0
        quaternion = np.asarray(
            [0.25 * scale, (matrix[2, 1] - matrix[1, 2]) / scale, (matrix[0, 2] - matrix[2, 0]) / scale, (matrix[1, 0] - matrix[0, 1]) / scale]
        )
    else:
        axis = int(np.argmax(np.diag(matrix)))
        if axis == 0:
            scale = np.sqrt(1.0 + matrix[0, 0] - matrix[1, 1] - matrix[2, 2]) * 2.0
            quaternion = np.asarray([(matrix[2, 1] - matrix[1, 2]) / scale, 0.25 * scale, (matrix[0, 1] + matrix[1, 0]) / scale, (matrix[0, 2] + matrix[2, 0]) / scale])
        elif axis == 1:
            scale = np.sqrt(1.0 + matrix[1, 1] - matrix[0, 0] - matrix[2, 2]) * 2.0
            quaternion = np.asarray([(matrix[0, 2] - matrix[2, 0]) / scale, (matrix[0, 1] + matrix[1, 0]) / scale, 0.25 * scale, (matrix[1, 2] + matrix[2, 1]) / scale])
        else:
            scale = np.sqrt(1.0 + matrix[2, 2] - matrix[0, 0] - matrix[1, 1]) * 2.0
            quaternion = np.asarray([(matrix[1, 0] - matrix[0, 1]) / scale, (matrix[0, 2] + matrix[2, 0]) / scale, (matrix[1, 2] + matrix[2, 1]) / scale, 0.25 * scale])
    quaternion = _unit_quaternion(quaternion)
    return quaternion if quaternion[0] >= 0 else -quaternion


def pose_matrix(pose: Sequence[float]) -> np.ndarray:
    pose_array = np.asarray(pose, dtype=np.float64).reshape(7)
    result = np.eye(4, dtype=np.float64)
    result[:3, :3] = quaternion_matrix(pose_array[3:])
    result[:3, 3] = pose_array[:3]
    return result


def matrix_pose(matrix: Sequence[Sequence[float]]) -> np.ndarray:
    matrix_array = np.asarray(matrix, dtype=np.float64).reshape(4, 4)
    return np.concatenate((matrix_array[:3, 3], matrix_quaternion(matrix_array[:3, :3])))


def relative_pose(parent_world_pose: Sequence[float], child_world_pose: Sequence[float]) -> np.ndarray:
    """Return ``T_parent_child`` from two world-frame poses."""

    return matrix_pose(np.linalg.inv(pose_matrix(parent_world_pose)) @ pose_matrix(child_world_pose))


def compose_pose(parent_world_pose: Sequence[float], child_parent_pose: Sequence[float]) -> np.ndarray:
    return matrix_pose(pose_matrix(parent_world_pose) @ pose_matrix(child_parent_pose))


def actor_target_to_eef_pose(
    current_eef_world_pose: Sequence[float],
    current_actor_world_pose: Sequence[float],
    target_actor_world_pose: Sequence[float],
) -> np.ndarray:
    """Map a desired actor pose to the EEF pose that preserves the grasp.

    The frozen grasp transform is ``T_eef_actor``.  The requested EEF pose is
    therefore ``T_world_actor_target @ inv(T_eef_actor)``.  This is the shared
    runtime-v2 replacement for passing an actor center or facility functional
    point directly to ``place_actor``.
    """

    eef_to_actor = np.linalg.inv(pose_matrix(current_eef_world_pose)) @ pose_matrix(current_actor_world_pose)
    return matrix_pose(pose_matrix(target_actor_world_pose) @ np.linalg.inv(eef_to_actor))


def world_axis_offset_pose(pose: Sequence[float], distance: float, axis: Sequence[float] = (0.0, 0.0, 1.0)) -> np.ndarray:
    result = np.asarray(pose, dtype=np.float64).reshape(7).copy()
    direction = np.asarray(axis, dtype=np.float64).reshape(3)
    norm = float(np.linalg.norm(direction))
    if norm <= 1e-12:
        raise ValueError("offset axis must be non-zero")
    result[:3] += float(distance) * direction / norm
    return result


def transform_local_point(parent_world_pose: Sequence[float], local_xyz: Sequence[float]) -> np.ndarray:
    point = np.ones(4, dtype=np.float64)
    point[:3] = np.asarray(local_xyz, dtype=np.float64).reshape(3)
    return (pose_matrix(parent_world_pose) @ point)[:3]


def obb_corners(world_pose: Sequence[float], half_extents: Sequence[float]) -> np.ndarray:
    half = np.asarray(half_extents, dtype=np.float64).reshape(3)
    if np.any(half <= 0):
        raise ValueError("OBB half extents must be positive")
    local = np.asarray([[x, y, z, 1.0] for x in (-half[0], half[0]) for y in (-half[1], half[1]) for z in (-half[2], half[2])])
    return (pose_matrix(world_pose) @ local.T).T[:, :3]


def obb_inside_local_cavity(
    actor_world_pose: Sequence[float],
    actor_half_extents: Sequence[float],
    container_world_pose: Sequence[float],
    cavity_lower_local: Sequence[float],
    cavity_upper_local: Sequence[float],
    margin: float = 0.0,
) -> dict:
    """Check every actor OBB corner against an explicit container cavity."""

    lower = np.asarray(cavity_lower_local, dtype=np.float64).reshape(3) + float(margin)
    upper = np.asarray(cavity_upper_local, dtype=np.float64).reshape(3) - float(margin)
    if np.any(lower >= upper):
        raise ValueError("cavity is empty after margin")
    corners_world = obb_corners(actor_world_pose, actor_half_extents)
    homogeneous = np.concatenate((corners_world, np.ones((len(corners_world), 1))), axis=1)
    corners_local = (np.linalg.inv(pose_matrix(container_world_pose)) @ homogeneous.T).T[:, :3]
    passed = bool(np.all(corners_local >= lower) and np.all(corners_local <= upper))
    return {
        "pass_true_cavity_obb": passed,
        "local_corner_min": corners_local.min(axis=0).tolist(),
        "local_corner_max": corners_local.max(axis=0).tolist(),
        "cavity_lower": lower.tolist(),
        "cavity_upper": upper.tolist(),
    }


def footprint_inside_local_region(
    actor_world_pose: Sequence[float],
    actor_half_extents: Sequence[float],
    support_world_pose: Sequence[float],
    region_lower_local: Sequence[float],
    region_upper_local: Sequence[float],
    horizontal_axes: Sequence[int] = (0, 2),
) -> dict:
    """Check the complete object footprint against a visible support region."""

    axes = tuple(int(axis) for axis in horizontal_axes)
    if len(axes) != 2 or len(set(axes)) != 2 or any(axis not in (0, 1, 2) for axis in axes):
        raise ValueError("horizontal_axes must contain two distinct local axes")
    lower = np.asarray(region_lower_local, dtype=np.float64).reshape(3)
    upper = np.asarray(region_upper_local, dtype=np.float64).reshape(3)
    corners_world = obb_corners(actor_world_pose, actor_half_extents)
    homogeneous = np.concatenate((corners_world, np.ones((len(corners_world), 1))), axis=1)
    corners_local = (np.linalg.inv(pose_matrix(support_world_pose)) @ homogeneous.T).T[:, :3]
    footprint_min = corners_local[:, axes].min(axis=0)
    footprint_max = corners_local[:, axes].max(axis=0)
    passed = bool(np.all(footprint_min >= lower[list(axes)]) and np.all(footprint_max <= upper[list(axes)]))
    return {
        "pass_support_footprint": passed,
        "horizontal_axes": list(axes),
        "footprint_min": footprint_min.tolist(),
        "footprint_max": footprint_max.tolist(),
        "region_lower": lower[list(axes)].tolist(),
        "region_upper": upper[list(axes)].tolist(),
    }


def segment_intersects_aabb(
    start_xyz: Sequence[float],
    end_xyz: Sequence[float],
    lower_xyz: Sequence[float],
    upper_xyz: Sequence[float],
    swept_half_extents: Sequence[float] = (0.0, 0.0, 0.0),
) -> bool:
    """Conservative line-segment/AABB test using a Minkowski expansion."""

    start = np.asarray(start_xyz, dtype=np.float64).reshape(3)
    end = np.asarray(end_xyz, dtype=np.float64).reshape(3)
    half = np.asarray(swept_half_extents, dtype=np.float64).reshape(3)
    lower = np.asarray(lower_xyz, dtype=np.float64).reshape(3) - half
    upper = np.asarray(upper_xyz, dtype=np.float64).reshape(3) + half
    direction = end - start
    near, far = 0.0, 1.0
    for axis in range(3):
        if abs(direction[axis]) <= 1e-12:
            if start[axis] < lower[axis] or start[axis] > upper[axis]:
                return False
            continue
        first = (lower[axis] - start[axis]) / direction[axis]
        second = (upper[axis] - start[axis]) / direction[axis]
        first, second = min(first, second), max(first, second)
        near, far = max(near, first), min(far, second)
        if near > far:
            return False
    return True


def swept_path_collisions(
    waypoint_xyz: Iterable[Sequence[float]],
    swept_half_extents: Sequence[float],
    obstacles: Mapping[str, Mapping[str, Sequence[float]]],
) -> dict:
    points = [np.asarray(point, dtype=np.float64).reshape(3) for point in waypoint_xyz]
    if len(points) < 2:
        raise ValueError("at least two path waypoints are required")
    collisions = []
    for segment_index, (start, end) in enumerate(zip(points[:-1], points[1:])):
        for name, bounds in obstacles.items():
            if segment_intersects_aabb(start, end, bounds["lower"], bounds["upper"], swept_half_extents):
                collisions.append({"segment_index": segment_index, "obstacle": name})
    return {"pass": not collisions, "collisions": collisions, "segment_count": len(points) - 1}


def quaternion_orientation_error(first: Sequence[float], second: Sequence[float]) -> float:
    return float(1.0 - abs(float(np.dot(_unit_quaternion(first), _unit_quaternion(second)))))


def quaternion_angular_velocity(previous: Sequence[float], current: Sequence[float], dt: float) -> np.ndarray:
    """Derive world-frame angular velocity from consecutive wxyz samples."""

    if dt <= 0:
        raise ValueError("dt must be positive")
    q0 = _unit_quaternion(previous)
    q1 = _unit_quaternion(current)
    if float(np.dot(q0, q1)) < 0:
        q1 = -q1
    w0, x0, y0, z0 = q0
    conjugate = np.asarray([w0, -x0, -y0, -z0])
    w1, x1, y1, z1 = q1
    wc, xc, yc, zc = conjugate
    delta = np.asarray(
        [
            w1 * wc - x1 * xc - y1 * yc - z1 * zc,
            w1 * xc + x1 * wc + y1 * zc - z1 * yc,
            w1 * yc - x1 * zc + y1 * wc + z1 * xc,
            w1 * zc + x1 * yc - y1 * xc + z1 * wc,
        ]
    )
    delta = _unit_quaternion(delta)
    if delta[0] < 0:
        delta = -delta
    vector_norm = float(np.linalg.norm(delta[1:]))
    if vector_norm <= 1e-12:
        return np.zeros(3, dtype=np.float64)
    angle = 2.0 * np.arctan2(vector_norm, float(np.clip(delta[0], -1.0, 1.0)))
    return delta[1:] / vector_norm * angle / float(dt)


def select_first_verified_pose(candidates: Sequence[Mapping[str, object]]) -> dict:
    """Select only a pose with geometric clearance and a real planner success.

    A provisional/hard-coded reachability boolean is intentionally not part of
    this contract.  GPU planner preflight must populate ``planner_status``.
    """

    evaluated = []
    selected = None
    for candidate in candidates:
        item = dict(candidate)
        item["verified"] = bool(
            item.get("workspace_pass") is True
            and item.get("swept_collision_free") is True
            and item.get("planner_status") == "Success"
        )
        evaluated.append(item)
        if selected is None and item["verified"]:
            selected = item
    return {"selected": selected, "evaluated": evaluated, "pass": selected is not None}
