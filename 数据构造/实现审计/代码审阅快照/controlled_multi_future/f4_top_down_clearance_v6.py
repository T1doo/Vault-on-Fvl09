"""Pure F4 r6 contract for a uniform table-clear top-down grasp height.

The r5 A diagnostic reached a stationary collision equilibrium with both open
fingers on the table before close.  This dependency-free module freezes that
machine evidence and applies one source-distinct repair: raise the existing
project top-down pregrasp and grasp targets by exactly 16 mm in world z for
all A/B/C roles, while retaining the exact 20 mm diagnostic micro-lift.

This is a geometric hypothesis only.  It does not relax collision/contact or
realized-boundary Gates, move the scene, authorize collection, or claim real
IK/grasp success.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .geometry import world_axis_offset_pose
from .project_cube_grasp_pose_v1 import (
    FROZEN_CUBE_HALF_EXTENTS_M,
    build_project_cube_grasp_poses,
)


SCHEMA_VERSION = "cmf_f4_uniform_top_down_clearance_v6"
ROUTE_VERSION = "f4_uniform_top_down_grasp_height_plus16mm_v6"
SUPPORTED_ARM = "right"
F4_BLOCK_ROLES = ("A", "B", "C")
PREGRASP_DISTANCE_M = 0.09
GRASP_HEIGHT_OFFSET_M = 0.016
MICRO_LIFT_DISTANCE_M = 0.020

# Immutable r5 evidence from the A grasp boundary and partial trace.
R5_SOURCE_NAMESPACE = (
    "nonformal_runtime_v3_3_f4_common_boundary_A_micro_lift_"
    "seed20260829_revision5_run1_anygpu"
)
R5_A_ACTOR_CENTER_Z_M = 0.7620004415512085
R5_A_CUBE_TOP_Z_M = R5_A_ACTOR_CENTER_Z_M + float(
    FROZEN_CUBE_HALF_EXTENTS_M[2]
)
R5_TOP_DOWN_GRASP_TARGET_Z_M = 0.8814017753160367
R5_REALIZED_COLLISION_EQUILIBRIUM_EEF_Z_M = 0.8950384259223938
R5_LOWEST_FINGER_TABLE_CONTACT_Z_M = 0.7399989366531372
R5_TABLE_TOP_Z_M = 0.740
REQUIRED_FINGER_TABLE_CLEARANCE_M = 0.002

R5_COLLISION_EQUILIBRIUM_TARGET_GAP_M = (
    R5_REALIZED_COLLISION_EQUILIBRIUM_EEF_Z_M
    - R5_TOP_DOWN_GRASP_TARGET_Z_M
)
R5_ADDITIONAL_CLEARANCE_DELTA_M = (
    R5_TABLE_TOP_Z_M
    + REQUIRED_FINGER_TABLE_CLEARANCE_M
    - R5_LOWEST_FINGER_TABLE_CONTACT_Z_M
)
R5_DERIVED_MINIMUM_GRASP_OFFSET_M = (
    R5_COLLISION_EQUILIBRIUM_TARGET_GAP_M
    + R5_ADDITIONAL_CLEARANCE_DELTA_M
)
FROZEN_OFFSET_MARGIN_OVER_DERIVED_M = (
    GRASP_HEIGHT_OFFSET_M - R5_DERIVED_MINIMUM_GRASP_OFFSET_M
)


def _json_safe(value: Any, *, path: str = "value") -> Any:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise ValueError(f"{path} must be finite")
        return result
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist(), path=path)
    if isinstance(value, Mapping):
        output = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} mapping keys must be strings")
            output[key] = _json_safe(item, path=f"{path}.{key}")
        return output
    if isinstance(value, (list, tuple)):
        return [
            _json_safe(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    raise TypeError(f"{path} contains unsupported type {type(value).__name__}")


def canonical_json_sha256(value: Any) -> str:
    normalized = _json_safe(value)
    return hashlib.sha256(
        json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _pose(value: Any, *, label: str) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if result.shape != (7,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be finite shape (7,)")
    if float(np.linalg.norm(result[3:])) <= 1e-12:
        raise ValueError(f"{label} quaternion must be nonzero")
    return np.ascontiguousarray(result)


def r5_clearance_derivation_receipt() -> dict:
    receipt = {
        "schema_version": "cmf_f4_r5_grasp_height_derivation_v6",
        "source_namespace": R5_SOURCE_NAMESPACE,
        "cube_half_extents_m": FROZEN_CUBE_HALF_EXTENTS_M.tolist(),
        "cube_full_size_m": (2.0 * FROZEN_CUBE_HALF_EXTENTS_M).tolist(),
        "r5_actor_center_z_m": R5_A_ACTOR_CENTER_Z_M,
        "r5_cube_top_z_m": R5_A_CUBE_TOP_Z_M,
        "r5_top_down_grasp_target_z_m": R5_TOP_DOWN_GRASP_TARGET_Z_M,
        "r5_realized_collision_equilibrium_eef_z_m": (
            R5_REALIZED_COLLISION_EQUILIBRIUM_EEF_Z_M
        ),
        "r5_lowest_finger_table_contact_z_m": (
            R5_LOWEST_FINGER_TABLE_CONTACT_Z_M
        ),
        "table_top_z_m": R5_TABLE_TOP_Z_M,
        "required_finger_table_clearance_m": REQUIRED_FINGER_TABLE_CLEARANCE_M,
        "collision_equilibrium_target_gap_m": (
            R5_COLLISION_EQUILIBRIUM_TARGET_GAP_M
        ),
        "additional_clearance_delta_m": R5_ADDITIONAL_CLEARANCE_DELTA_M,
        "derived_minimum_grasp_offset_m": R5_DERIVED_MINIMUM_GRASP_OFFSET_M,
        "frozen_grasp_height_offset_m": GRASP_HEIGHT_OFFSET_M,
        "frozen_margin_over_derived_m": FROZEN_OFFSET_MARGIN_OVER_DERIVED_M,
        "checks": {
            "frozen_offset_covers_derived_minimum": (
                GRASP_HEIGHT_OFFSET_M >= R5_DERIVED_MINIMUM_GRASP_OFFSET_M
            ),
            "frozen_offset_is_single_bounded_repair": (
                0.0 <= FROZEN_OFFSET_MARGIN_OVER_DERIVED_M < 0.001
            ),
            "cube_is_44mm": bool(
                np.allclose(
                    2.0 * FROZEN_CUBE_HALF_EXTENTS_M,
                    [0.044, 0.044, 0.044],
                    rtol=0.0,
                    atol=1e-12,
                )
            ),
        },
    }
    receipt["pass"] = all(receipt["checks"].values())
    receipt = _json_safe(receipt)
    receipt["receipt_sha256"] = canonical_json_sha256(receipt)
    return receipt


def _build_role_targets(role: str, actor_pose: Sequence[float]) -> dict:
    if role not in F4_BLOCK_ROLES:
        raise ValueError("F4 r6 role must be A, B, or C")
    actor = _pose(actor_pose, label=f"F4 {role} actor pose")
    legacy_pregrasp, legacy_grasp, grasp_contract = build_project_cube_grasp_poses(
        actor,
        cube_half_extents_m=FROZEN_CUBE_HALF_EXTENTS_M,
        arm=SUPPORTED_ARM,
        pregrasp_distance_m=PREGRASP_DISTANCE_M,
    )
    shifted_pregrasp = world_axis_offset_pose(
        legacy_pregrasp, GRASP_HEIGHT_OFFSET_M
    )
    shifted_grasp = world_axis_offset_pose(legacy_grasp, GRASP_HEIGHT_OFFSET_M)
    micro_lift = world_axis_offset_pose(shifted_grasp, MICRO_LIFT_DISTANCE_M)
    targets = [
        {"segment_id": f"{role}_pregrasp", "pose": shifted_pregrasp.tolist()},
        {"segment_id": f"{role}_grasp", "pose": shifted_grasp.tolist()},
        {"segment_id": f"{role}_micro_lift", "pose": micro_lift.tolist()},
    ]

    predicted_lowest_finger_z = R5_LOWEST_FINGER_TABLE_CONTACT_Z_M + (
        shifted_grasp[2] - R5_REALIZED_COLLISION_EQUILIBRIUM_EEF_Z_M
    )
    predicted_table_clearance = predicted_lowest_finger_z - R5_TABLE_TOP_Z_M
    actor_top_z = float(actor[2] + FROZEN_CUBE_HALF_EXTENTS_M[2])
    predicted_cube_vertical_overlap = actor_top_z - predicted_lowest_finger_z
    checks = {
        "pregrasp_xy_preserved": bool(
            np.array_equal(shifted_pregrasp[:2], legacy_pregrasp[:2])
        ),
        "grasp_xy_preserved": bool(
            np.array_equal(shifted_grasp[:2], legacy_grasp[:2])
        ),
        "pregrasp_quaternion_preserved": bool(
            np.array_equal(shifted_pregrasp[3:], legacy_pregrasp[3:])
        ),
        "grasp_quaternion_preserved": bool(
            np.array_equal(shifted_grasp[3:], legacy_grasp[3:])
        ),
        "pregrasp_to_grasp_vector_preserved": bool(
            np.allclose(
                shifted_pregrasp[:3] - shifted_grasp[:3],
                legacy_pregrasp[:3] - legacy_grasp[:3],
                rtol=0.0,
                atol=1e-12,
            )
        ),
        "uniform_16mm_world_z_offset": bool(
            np.allclose(
                shifted_pregrasp[:3] - legacy_pregrasp[:3],
                [0.0, 0.0, GRASP_HEIGHT_OFFSET_M],
                rtol=0.0,
                atol=1e-12,
            )
            and np.allclose(
                shifted_grasp[:3] - legacy_grasp[:3],
                [0.0, 0.0, GRASP_HEIGHT_OFFSET_M],
                rtol=0.0,
                atol=1e-12,
            )
        ),
        "exact_20mm_micro_lift": bool(
            np.allclose(
                micro_lift[:3] - shifted_grasp[:3],
                [0.0, 0.0, MICRO_LIFT_DISTANCE_M],
                rtol=0.0,
                atol=1e-12,
            )
        ),
        "predicted_finger_clears_table": (
            predicted_table_clearance >= REQUIRED_FINGER_TABLE_CLEARANCE_M
        ),
        "predicted_finger_still_overlaps_cube_height": (
            predicted_cube_vertical_overlap > 0.0
        ),
    }
    return {
        "role": role,
        "actor_pose": actor.tolist(),
        "legacy_targets": [
            {"segment_id": f"{role}_pregrasp", "pose": legacy_pregrasp.tolist()},
            {"segment_id": f"{role}_grasp", "pose": legacy_grasp.tolist()},
        ],
        "targets": targets,
        "grasp_contract": grasp_contract,
        "predicted_geometry": {
            "predicted_lowest_finger_z_m": predicted_lowest_finger_z,
            "predicted_table_clearance_m": predicted_table_clearance,
            "actor_top_z_m": actor_top_z,
            "predicted_cube_vertical_overlap_m": predicted_cube_vertical_overlap,
            "prediction_source": (
                "r5 realized finger-table contact translated by the proposed "
                "EEF world-z target delta"
            ),
            "runtime_collision_authority_required": True,
        },
        "checks": checks,
        "pass": all(checks.values()),
    }


def build_uniform_f4_top_down_clearance_contract_v6(
    *, object_poses: Mapping[str, Sequence[float]], arm: str = SUPPORTED_ARM
) -> dict:
    if arm != SUPPORTED_ARM:
        raise ValueError("F4 r6 top-down clearance contract requires the right arm")
    if not isinstance(object_poses, Mapping) or set(object_poses) != set(
        F4_BLOCK_ROLES
    ):
        raise ValueError("F4 r6 requires exactly A/B/C object poses")
    original = _json_safe(object_poses, path="object_poses")
    groups = [_build_role_targets(role, object_poses[role]) for role in F4_BLOCK_ROLES]
    if _json_safe(object_poses, path="object_poses") != original:
        raise RuntimeError("F4 r6 target construction mutated object poses")
    contract_hashes = {
        group["grasp_contract"]["grasp_contract_sha256"] for group in groups
    }
    checks = {
        "all_roles_pass": all(group["pass"] for group in groups),
        "one_uniform_project_grasp_contract": len(contract_hashes) == 1,
        "all_roles_share_target_suffixes": all(
            [item["segment_id"].removeprefix(f"{group['role']}_") for item in group["targets"]]
            == ["pregrasp", "grasp", "micro_lift"]
            for group in groups
        ),
        "r5_derivation_pass": r5_clearance_derivation_receipt()["pass"],
    }
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "route_version": ROUTE_VERSION,
        "implementation_version": "controlled_multi_future_runtime_v3_3",
        "formal_data": False,
        "stage0_data": False,
        "arm": arm,
        "uniform_roles": list(F4_BLOCK_ROLES),
        "grasp_height_offset_m": GRASP_HEIGHT_OFFSET_M,
        "micro_lift_distance_m": MICRO_LIFT_DISTANCE_M,
        "derivation": r5_clearance_derivation_receipt(),
        "groups": groups,
        "single_project_grasp_contract_sha256": next(iter(contract_hashes)),
        "scene_layout_changed": False,
        "common_prefix_changed": False,
        "program_changed": False,
        "collision_gate_relaxed": False,
        "verifier_threshold_changed": False,
        "diagnostic_only": True,
        "runtime_ik_collision_contact_required": True,
        "checks": checks,
        "pass": all(checks.values()),
    }
    receipt = _json_safe(receipt)
    receipt["receipt_sha256"] = canonical_json_sha256(receipt)
    return receipt


def validate_uniform_f4_top_down_clearance_contract_v6(
    receipt: Mapping[str, Any]
) -> dict:
    if not isinstance(receipt, Mapping):
        raise TypeError("F4 r6 clearance receipt must be a mapping")
    value = _json_safe(receipt)
    digest = value.pop("receipt_sha256", None)
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("F4 r6 clearance receipt schema mismatch")
    if not isinstance(digest, str) or canonical_json_sha256(value) != digest:
        raise ValueError("F4 r6 clearance receipt hash mismatch")
    if value.get("uniform_roles") != list(F4_BLOCK_ROLES):
        raise ValueError("F4 r6 clearance receipt role mismatch")
    groups = value.get("groups")
    if not isinstance(groups, list) or len(groups) != len(F4_BLOCK_ROLES):
        raise ValueError("F4 r6 clearance receipt groups are invalid")
    recomputed = build_uniform_f4_top_down_clearance_contract_v6(
        object_poses={group["role"]: group["actor_pose"] for group in groups},
        arm=value.get("arm"),
    )
    if recomputed != _json_safe(receipt):
        raise ValueError("F4 r6 clearance receipt content mismatch")
    return _json_safe(receipt)


__all__ = [
    "F4_BLOCK_ROLES",
    "FROZEN_OFFSET_MARGIN_OVER_DERIVED_M",
    "GRASP_HEIGHT_OFFSET_M",
    "MICRO_LIFT_DISTANCE_M",
    "R5_ADDITIONAL_CLEARANCE_DELTA_M",
    "R5_COLLISION_EQUILIBRIUM_TARGET_GAP_M",
    "R5_DERIVED_MINIMUM_GRASP_OFFSET_M",
    "R5_LOWEST_FINGER_TABLE_CONTACT_Z_M",
    "R5_REALIZED_COLLISION_EQUILIBRIUM_EEF_Z_M",
    "R5_SOURCE_NAMESPACE",
    "R5_TABLE_TOP_Z_M",
    "R5_TOP_DOWN_GRASP_TARGET_Z_M",
    "REQUIRED_FINGER_TABLE_CLEARANCE_M",
    "ROUTE_VERSION",
    "SCHEMA_VERSION",
    "build_uniform_f4_top_down_clearance_contract_v6",
    "canonical_json_sha256",
    "r5_clearance_derivation_receipt",
    "validate_uniform_f4_top_down_clearance_contract_v6",
]
