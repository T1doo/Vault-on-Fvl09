"""Uniform F1 revision-2 carry hub derived from the frozen cluster neutral pose."""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np

from .geometry import segment_intersects_aabb


F1_CARRY_HUB_VERSION = "f1_uniform_carry_hub_v2"
F1_CARRY_HUB_XY_M = (-0.11, 0.02)
F1_SAFE_TRANSPORT_EEF_Z_M = 1.02
BLOCK_HALF_EXTENTS_M = np.asarray([0.022, 0.022, 0.022], dtype=np.float64)
F1_OBJECT_XYZ_M = {
    "red": (-0.20, 0.02, 0.762),
    "green": (-0.11, 0.02, 0.762),
    "blue": (-0.02, 0.02, 0.762),
}

LEGACY_SEGMENT_ORDER = (
    "common_cluster_neutral",
    "target_pregrasp",
    "target_grasp",
    "target_lift_mid",
    "target_lift",
    "safe_vertical",
    "safe_horizontal",
    "preplace",
    "release",
    "retreat",
    "rest",
)

REVISION2_SEGMENT_ORDER = (
    "common_cluster_neutral",
    "target_pregrasp",
    "target_grasp",
    "target_lift_mid",
    "target_lift",
    "carry_hub_low",
    "carry_hub_high",
    "safe_horizontal",
    "preplace",
    "release",
    "retreat",
    "rest",
)


def build_uniform_carry_hub_targets(
    legacy_targets: Sequence[Mapping[str, object]],
) -> tuple[list[dict], dict]:
    """Replace only the role-local high raise with a common-XY two-step hub."""

    ids = tuple(item.get("segment_id") for item in legacy_targets)
    if ids != LEGACY_SEGMENT_ORDER:
        raise ValueError("F1 legacy target order changed before revision-2 hub repair")
    copied = [
        {
            "segment_id": str(item["segment_id"]),
            "pose": np.asarray(item["pose"], dtype=np.float64).reshape(7).copy(),
        }
        for item in legacy_targets
    ]
    lift = copied[4]["pose"].copy()
    hub_low = lift.copy()
    hub_low[:2] = np.asarray(F1_CARRY_HUB_XY_M, dtype=np.float64)
    hub_high = hub_low.copy()
    hub_high[2] = max(float(hub_low[2]), F1_SAFE_TRANSPORT_EEF_Z_M)
    safe_horizontal = copied[6]
    if not np.isclose(
        safe_horizontal["pose"][2],
        F1_SAFE_TRANSPORT_EEF_Z_M,
        rtol=0.0,
        atol=1e-9,
    ):
        raise ValueError("F1 frozen safe-horizontal height changed")
    revised = copied[:5] + [
        {"segment_id": "carry_hub_low", "pose": hub_low},
        {"segment_id": "carry_hub_high", "pose": hub_high},
    ] + copied[6:]
    if tuple(item["segment_id"] for item in revised) != REVISION2_SEGMENT_ORDER:
        raise AssertionError("F1 revision-2 target order construction failed")
    audit = {
        "repair_version": F1_CARRY_HUB_VERSION,
        "uniform_for_roles": ["red", "green", "blue"],
        "hub_xy_m": list(F1_CARRY_HUB_XY_M),
        "hub_xy_source": "frozen canonical cluster-neutral xy",
        "safe_transport_eef_z_m": F1_SAFE_TRANSPORT_EEF_Z_M,
        "safe_height_changed_from_revision1": False,
        "scene_layout_changed": False,
        "executing_arm_changed": False,
        "verifier_changed": False,
        "branch_specific_condition": False,
    }
    return revised, audit


def nominal_swept_clearance_audit() -> dict:
    """Conservative cube-AABB check for the low lifted-center-to-hub segment."""

    lifted_z = 0.762 + 0.08
    hub = np.asarray([*F1_CARRY_HUB_XY_M, lifted_z], dtype=np.float64)
    by_role = {}
    for role, xyz in F1_OBJECT_XYZ_M.items():
        start = np.asarray([xyz[0], xyz[1], lifted_z], dtype=np.float64)
        collisions = []
        vertical_clearances = []
        for other_role, other_xyz in F1_OBJECT_XYZ_M.items():
            if other_role == role:
                continue
            center = np.asarray(other_xyz, dtype=np.float64)
            lower = center - BLOCK_HALF_EXTENTS_M
            upper = center + BLOCK_HALF_EXTENTS_M
            intersects = segment_intersects_aabb(
                start,
                hub,
                lower,
                upper,
                swept_half_extents=BLOCK_HALF_EXTENTS_M,
            )
            if intersects:
                collisions.append(other_role)
            carried_bottom = lifted_z - BLOCK_HALF_EXTENTS_M[2]
            obstacle_top = upper[2]
            vertical_clearances.append(float(carried_bottom - obstacle_top))
        by_role[role] = {
            "collisions": collisions,
            "minimum_vertical_surface_clearance_m": min(vertical_clearances),
            "pass": not collisions and min(vertical_clearances) > 0.0,
        }
    return {
        "schema_version": "cmf_f1_uniform_carry_hub_cpu_geometry_v2",
        "repair_version": F1_CARRY_HUB_VERSION,
        "roles": by_role,
        "minimum_vertical_surface_clearance_m": min(
            item["minimum_vertical_surface_clearance_m"]
            for item in by_role.values()
        ),
        "pass": all(item["pass"] for item in by_role.values()),
    }
