"""Explicit right-arm grasp contract for project procedural RGB cubes."""

from __future__ import annotations

from typing import Any

import numpy as np

from .current_hasher import hash_json
from .geometry import compose_pose


SCHEMA_VERSION = "cmf_project_cube_grasp_pose_v1"
SUPPORTED_ARM = "right"
FROZEN_CUBE_HALF_EXTENTS_M = np.asarray([0.022, 0.022, 0.022], dtype=np.float64)
# Derived from runtime-v3_2 F4 common-X successful right-arm grasp/transport.
FROZEN_LOCAL_GRASP_POSE_WXYZ = np.asarray(
    [
        0.00000071628941287,
        -0.01197646825808985,
        0.1194011020263819,
        0.5243570072481656,
        -0.47439082845243685,
        0.4743935067167858,
        0.5243604405510669,
    ],
    dtype=np.float64,
)
FROZEN_LOCAL_PREGRASP_DIRECTION = np.asarray(
    [
        0.00000055274939243,
        -0.0089827456793138,
        0.0895506017833227,
    ],
    dtype=np.float64,
)
FROZEN_LOCAL_PREGRASP_DIRECTION /= np.linalg.norm(FROZEN_LOCAL_PREGRASP_DIRECTION)


def project_cube_grasp_contract() -> dict:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "arm": SUPPORTED_ARM,
        "cube_half_extents_m": FROZEN_CUBE_HALF_EXTENTS_M.tolist(),
        "local_grasp_pose_wxyz": FROZEN_LOCAL_GRASP_POSE_WXYZ.tolist(),
        "local_pregrasp_direction": FROZEN_LOCAL_PREGRASP_DIRECTION.tolist(),
        "source_namespace": "nonformal_F4_right_arm_layout_full_root_runtime_v3_2_seed20260829_gpu0_run2_layout_injection",
        "source_segment": "successful common_grasp and common transport",
        "functional_point_helper_used": False,
        "same_contract_required_for_roles": ["A", "B", "C"],
    }
    payload["grasp_contract_sha256"] = hash_json(payload)
    return payload


def build_project_cube_grasp_poses(
    actor_pose: Any,
    *,
    cube_half_extents_m: Any,
    arm: str,
    pregrasp_distance_m: float,
) -> tuple[np.ndarray, np.ndarray, dict]:
    if arm != SUPPORTED_ARM:
        raise ValueError("project cube grasp v1 is frozen for the right arm")
    actor = np.asarray(actor_pose, dtype=np.float64)
    if actor.shape != (7,) or not np.all(np.isfinite(actor)):
        raise ValueError("project cube actor pose must be finite shape-(7,)")
    half = np.asarray(cube_half_extents_m, dtype=np.float64)
    if half.shape != (3,) or not np.allclose(
        half, FROZEN_CUBE_HALF_EXTENTS_M, rtol=0.0, atol=1e-12
    ):
        raise ValueError("project cube half extents differ from frozen contract")
    distance = float(pregrasp_distance_m)
    if not np.isfinite(distance) or distance <= 0:
        raise ValueError("project cube pregrasp distance must be positive")
    local_grasp = FROZEN_LOCAL_GRASP_POSE_WXYZ.copy()
    local_pregrasp = local_grasp.copy()
    local_pregrasp[:3] += FROZEN_LOCAL_PREGRASP_DIRECTION * distance
    grasp = compose_pose(actor, local_grasp)
    pregrasp = compose_pose(actor, local_pregrasp)
    for name, value in (("pregrasp", pregrasp), ("grasp", grasp)):
        if value.shape != (7,) or not np.all(np.isfinite(value)):
            raise ValueError(f"project cube {name} pose is invalid")
    return pregrasp, grasp, project_cube_grasp_contract()
