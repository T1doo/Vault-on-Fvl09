"""F4 common right-arm workspace layout after the three-role IK failure."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .current_hasher import hash_json
from .f4_arm_asset_layout_v3_2 import (
    RIGHT_ARM_COMMON_GRASP_ORIENTATION_WXYZ,
    TABLE_BOUNDS,
    audit_layout,
)


LAYOUT_VERSION = "f4_right_arm_workspace_base0_v3"
LAYOUT = {
    "layout_version": LAYOUT_VERSION,
    "branch_neutral_pose": [
        0.15,
        -0.02,
        0.95,
        *RIGHT_ARM_COMMON_GRASP_ORIENTATION_WXYZ,
    ],
    # Keep the already successful common-X and official tray mapping fixed.
    "common_x_pose": [0.28, 0.10, 0.762, 1.0, 0.0, 0.0, 0.0],
    "object_poses": {
        "A": [0.18, 0.175, 0.762, 1.0, 0.0, 0.0, 0.0],
        "B": [0.29, 0.175, 0.762, 1.0, 0.0, 0.0, 0.0],
        "C": [0.40, 0.175, 0.762, 1.0, 0.0, 0.0, 0.0],
    },
    "slot_poses": {
        "A": [0.15, 0.032, 0.742, 1.0, 0.0, 0.0, 0.0],
        "B": [0.30, 0.032, 0.742, 1.0, 0.0, 0.0, 0.0],
        "C": [0.41, 0.032, 0.742, 1.0, 0.0, 0.0, 0.0],
    },
    "tray": {
        "model_id": 0,
        "modelname": "008_tray",
        "pose": [
            0.28,
            -0.12,
            0.76,
            0.706527,
            0.706483,
            -0.0291356,
            -0.0291767,
        ],
    },
}


def _pairwise_minimum(points) -> float:
    values = [np.asarray(item[:2], dtype=np.float64) for item in points]
    return min(
        float(np.linalg.norm(values[left] - values[right]))
        for left in range(len(values))
        for right in range(left + 1, len(values))
    )


def build_impact_review() -> dict:
    full = {
        **json.loads(json.dumps(LAYOUT, sort_keys=True)),
        "arm": "right",
        "branch_neutral_orientation_policy": "fixed_same_as_realized_right_arm_common_grasp_orientation",
    }
    base = audit_layout(full)
    common = np.asarray(LAYOUT["common_x_pose"][:2], dtype=np.float64)
    objects = [np.asarray(item[:2], dtype=np.float64) for item in LAYOUT["object_poses"].values()]
    slots = [np.asarray(item[:2], dtype=np.float64) for item in LAYOUT["slot_poses"].values()]
    all_dynamic = [common, *objects]
    checks = {
        **base["checks"],
        "all_dynamic_centers_inside_table_with_cube_margin": all(
            TABLE_BOUNDS["x"][0] + 0.022 <= item[0] <= TABLE_BOUNDS["x"][1] - 0.022
            and TABLE_BOUNDS["y"][0] + 0.022 <= item[1] <= TABLE_BOUNDS["y"][1] - 0.022
            for item in all_dynamic
        ),
        "all_slots_inside_table_with_visual_margin": all(
            TABLE_BOUNDS["x"][0] + 0.035 <= item[0] <= TABLE_BOUNDS["x"][1] - 0.035
            and TABLE_BOUNDS["y"][0] + 0.035 <= item[1] <= TABLE_BOUNDS["y"][1] - 0.035
            for item in slots
        ),
        "common_clear_of_initial_objects": all(
            float(np.linalg.norm(common - item)) >= 0.075 for item in objects
        ),
        "common_clear_of_visible_slots": all(
            float(np.linalg.norm(common - item)) >= 0.062 for item in slots
        ),
        "all_object_x_in_right_workspace_candidate_band": all(
            0.18 <= item[0] <= 0.40 for item in objects
        ),
        "common_x_pose_unchanged_from_successful_v3_2": LAYOUT["common_x_pose"]
        == [0.28, 0.10, 0.762, 1.0, 0.0, 0.0, 0.0],
        "tray_pose_unchanged_from_successful_v3_2": LAYOUT["tray"]["pose"]
        == [0.28, -0.12, 0.76, 0.706527, 0.706483, -0.0291356, -0.0291767],
    }
    return {
        "schema_version": "cmf_f4_right_workspace_layout_impact_review_v7",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_3",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "layout": LAYOUT,
        "layout_sha256": hash_json(LAYOUT),
        "source_failure_namespace": "nonformal_runtime_v3_3_f4_cube_grasp_no_action_ik_seed20260829_run2_v1_2",
        "source_failure": "A/B/C all failed their first pregrasp at x=0.07/-0.08/-0.23",
        "uniform_repair": "move all A/B/C and their visible slots into one common right-workspace band; grasp transform remains identical",
        "object_pairwise_minimum_m": _pairwise_minimum(objects),
        "slot_pairwise_minimum_m": _pairwise_minimum(slots),
        "tray_world_aabb_xy": base["tray_world_aabb_xy"],
        "checks": checks,
        "pass": all(checks.values()),
        "status": "cpu_geometry_pass_real_three_role_ik_pending"
        if all(checks.values())
        else "cpu_geometry_failed",
    }


def write_review(path: Path) -> dict:
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    value = build_impact_review()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value
