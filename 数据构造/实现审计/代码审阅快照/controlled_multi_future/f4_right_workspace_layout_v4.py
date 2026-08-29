"""Final F4 uniform layout repair: common right-arm x and y workspace band."""

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


LAYOUT_VERSION = "f4_right_arm_workspace_base0_v4_final"
LAYOUT = {
    "layout_version": LAYOUT_VERSION,
    "branch_neutral_pose": [
        0.15,
        -0.02,
        0.95,
        *RIGHT_ARM_COMMON_GRASP_ORIENTATION_WXYZ,
    ],
    "common_x_pose": [0.28, 0.10, 0.762, 1.0, 0.0, 0.0, 0.0],
    "object_poses": {
        "A": [0.16, 0.020, 0.762, 1.0, 0.0, 0.0, 0.0],
        "B": [0.28, 0.020, 0.762, 1.0, 0.0, 0.0, 0.0],
        "C": [0.40, 0.020, 0.762, 1.0, 0.0, 0.0, 0.0],
    },
    "slot_poses": {
        "A": [0.15, 0.160, 0.742, 1.0, 0.0, 0.0, 0.0],
        "B": [0.30, 0.160, 0.742, 1.0, 0.0, 0.0, 0.0],
        "C": [0.41, 0.160, 0.742, 1.0, 0.0, 0.0, 0.0],
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


def _minimum_pairwise(points) -> float:
    values = [np.asarray(item[:2], dtype=np.float64) for item in points]
    return min(
        float(np.linalg.norm(values[i] - values[j]))
        for i in range(len(values))
        for j in range(i + 1, len(values))
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
    checks = {
        **base["checks"],
        "all_dynamic_inside_table": all(
            TABLE_BOUNDS["x"][0] + 0.022 <= point[0] <= TABLE_BOUNDS["x"][1] - 0.022
            and TABLE_BOUNDS["y"][0] + 0.022 <= point[1] <= TABLE_BOUNDS["y"][1] - 0.022
            for point in [common, *objects]
        ),
        "all_slots_inside_table": all(
            TABLE_BOUNDS["x"][0] + 0.035 <= point[0] <= TABLE_BOUNDS["x"][1] - 0.035
            and TABLE_BOUNDS["y"][0] + 0.035 <= point[1] <= TABLE_BOUNDS["y"][1] - 0.035
            for point in slots
        ),
        "common_clear_of_objects": all(
            float(np.linalg.norm(common - point)) >= 0.075 for point in objects
        ),
        "common_clear_of_slots": all(
            float(np.linalg.norm(common - point)) >= 0.062 for point in slots
        ),
        "objects_share_one_y_band": len({point[1] for point in objects}) == 1,
        "objects_share_one_right_x_band_rule": [point[0] for point in objects]
        == [0.16, 0.28, 0.40],
        "common_and_tray_unchanged": LAYOUT["common_x_pose"]
        == [0.28, 0.10, 0.762, 1.0, 0.0, 0.0, 0.0]
        and LAYOUT["tray"]["pose"]
        == [0.28, -0.12, 0.76, 0.706527, 0.706483, -0.0291356, -0.0291767],
        "final_repair_changes_layout_only": True,
    }
    return {
        "schema_version": "cmf_f4_right_workspace_layout_impact_review_v8",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_3",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "layout": LAYOUT,
        "layout_sha256": hash_json(LAYOUT),
        "source_failure_namespace": "nonformal_runtime_v3_3_f4_cube_grasp_no_action_ik_seed20260829_run3_layout_v3",
        "source_failure": "x-band repair passed CPU geometry but y=0.175 row still failed A/B/C pregrasp",
        "uniform_final_repair": "preserve x-band and move the complete object row to y=0.02; move all slots to y=0.16",
        "object_pairwise_minimum_m": _minimum_pairwise(objects),
        "slot_pairwise_minimum_m": _minimum_pairwise(slots),
        "tray_world_aabb_xy": base["tray_world_aabb_xy"],
        "checks": checks,
        "pass": all(checks.values()),
        "status": "cpu_geometry_pass_final_real_ik_pending"
        if all(checks.values())
        else "cpu_geometry_failed_terminal",
        "failure_rule": "if A/B/C no-action IK is not 3/3, mark F4 terminal and do not run staged/full programs",
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
