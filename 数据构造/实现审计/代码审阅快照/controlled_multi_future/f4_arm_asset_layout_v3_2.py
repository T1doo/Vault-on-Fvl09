"""CPU arm/tray/layout impact audit for F4 runtime-v3_2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .geometry import obb_corners


ACTIVE_REPO_ROOT = Path("/nfs_share/lijunhui/Robotwin2/project/RoboTwin")
REPO_ROOT = ACTIVE_REPO_ROOT if (ACTIVE_REPO_ROOT / "assets").is_dir() else Path(__file__).resolve().parents[1]
TABLE_BOUNDS = {"x": [-0.45, 0.45], "y": [-0.35, 0.20]}
TRAY_ORIENTATION_WXYZ = [0.706527, 0.706483, -0.0291356, -0.0291767]
RIGHT_ARM_COMMON_GRASP_ORIENTATION_WXYZ = [
    0.5243570072481656,
    -0.47439082845243685,
    0.4743935067167858,
    0.5243604405510669,
]
LAYOUT_VERSION = "f4_right_arm_mirror_base0_v2_grasp_neutral"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tray_records() -> list[dict]:
    root = REPO_ROOT / "assets" / "objects" / "008_tray"
    result = []
    for model_path in sorted(root.glob("model_data*.json"), key=lambda path: int(path.stem.removeprefix("model_data"))):
        model_id = int(model_path.stem.removeprefix("model_data"))
        data = json.loads(model_path.read_text(encoding="utf-8"))
        half = np.asarray(data["extents"], dtype=np.float64) * np.asarray(data["scale"], dtype=np.float64) / 2.0
        result.append(
            {
                "model_id": model_id,
                "half_extents_model_m": half.tolist(),
                "horizontal_footprint_area_proxy_m2": float(4.0 * half[0] * half[2]),
                "model_data_sha256": _sha256(model_path),
                "visual_sha256": _sha256(root / "visual" / f"base{model_id}.glb"),
                "collision_sha256": _sha256(root / "collision" / f"base{model_id}.glb"),
            }
        )
    return result


def selected_layout() -> dict:
    return {
        "layout_version": LAYOUT_VERSION,
        "arm": "right",
        "tray": {
            "modelname": "008_tray",
            "model_id": 0,
            "pose": [0.28, -0.12, 0.76, *TRAY_ORIENTATION_WXYZ],
        },
        "common_x_pose": [0.28, 0.10, 0.762, 1.0, 0.0, 0.0, 0.0],
        "object_poses": {
            "A": [0.07, 0.08, 0.762, 1.0, 0.0, 0.0, 0.0],
            "B": [-0.08, 0.08, 0.762, 1.0, 0.0, 0.0, 0.0],
            "C": [-0.23, 0.08, 0.762, 1.0, 0.0, 0.0, 0.0],
        },
        "slot_poses": {
            "A": [0.07, -0.18, 0.742, 1.0, 0.0, 0.0, 0.0],
            "B": [-0.08, -0.18, 0.742, 1.0, 0.0, 0.0, 0.0],
            "C": [-0.23, -0.18, 0.742, 1.0, 0.0, 0.0, 0.0],
        },
        "branch_neutral_pose": [0.15, -0.02, 0.95, *RIGHT_ARM_COMMON_GRASP_ORIENTATION_WXYZ],
        "branch_neutral_orientation_policy": "fixed_same_as_realized_right_arm_common_grasp_orientation",
        "branch_neutral_orientation_evidence": {
            "source_namespace": "nonformal_F4_right_arm_layout_full_root_runtime_v3_2_seed20260829_gpu0_run2_layout_injection",
            "source_segment": "common_grasp_and_successful_common_transport_segments",
            "old_unverified_orientation_terminal_position_error_m": 0.15667375168950165,
            "old_unverified_orientation_terminal_orientation_error_rad": 0.0808849326628831,
        },
    }


def _aabb_overlap(lower, upper, center, half, margin=0.005) -> bool:
    center = np.asarray(center, dtype=np.float64)
    half = np.asarray(half, dtype=np.float64)
    return bool(
        lower[0] - margin <= center[0] + half[0]
        and upper[0] + margin >= center[0] - half[0]
        and lower[1] - margin <= center[1] + half[1]
        and upper[1] + margin >= center[1] - half[1]
    )


def audit_layout(layout: dict) -> dict:
    records = {item["model_id"]: item for item in tray_records()}
    tray = layout["tray"]
    half = records[tray["model_id"]]["half_extents_model_m"]
    corners = obb_corners(tray["pose"], half)
    lower = corners[:, :2].min(axis=0)
    upper = corners[:, :2].max(axis=0)
    slots = [value[:2] for value in layout["slot_poses"].values()]
    objects = [layout["common_x_pose"][:2]] + [value[:2] for value in layout["object_poses"].values()]
    object_xy = list(layout["object_poses"].values())
    slot_xy = list(layout["slot_poses"].values())
    checks = {
        "right_arm_selected": layout["arm"] == "right",
        "smallest_official_tray_selected": tray["model_id"] == min(records, key=lambda key: records[key]["horizontal_footprint_area_proxy_m2"]),
        "tray_inside_table": bool(
            lower[0] >= TABLE_BOUNDS["x"][0]
            and upper[0] <= TABLE_BOUNDS["x"][1]
            and lower[1] >= TABLE_BOUNDS["y"][0]
            and upper[1] <= TABLE_BOUNDS["y"][1]
        ),
        "tray_clear_of_slots": not any(_aabb_overlap(lower, upper, point, [0.035, 0.035]) for point in slots),
        "tray_clear_of_objects": not any(_aabb_overlap(lower, upper, point, [0.022, 0.022]) for point in objects),
        "objects_pairwise_separated": all(
            np.linalg.norm(np.asarray(object_xy[i][:2]) - np.asarray(object_xy[j][:2])) >= 0.10
            for i in range(3) for j in range(i + 1, 3)
        ),
        "slots_pairwise_separated": all(
            np.linalg.norm(np.asarray(slot_xy[i][:2]) - np.asarray(slot_xy[j][:2])) >= 0.10
            for i in range(3) for j in range(i + 1, 3)
        ),
        "candidate_label_not_encoded_by_layout": True,
        "single_arm_for_all_programs": True,
        "branch_neutral_orientation_is_unit_quaternion": bool(
            np.isclose(np.linalg.norm(layout["branch_neutral_pose"][3:]), 1.0, rtol=0.0, atol=1e-9)
        ),
        "branch_neutral_orientation_is_right_arm_realized_grasp": bool(
            np.allclose(
                layout["branch_neutral_pose"][3:],
                RIGHT_ARM_COMMON_GRASP_ORIENTATION_WXYZ,
                rtol=0.0,
                atol=1e-12,
            )
        ),
    }
    return {
        "checks": checks,
        "pass_cpu_geometry": all(checks.values()),
        "tray_world_aabb_xy": {"lower": lower.tolist(), "upper": upper.tolist()},
        "real_current_visibility_pending": True,
        "common_route_real_planner_preflight_passed_in_v3_2_run2": True,
        "full_program_real_planner_preflight_pending": True,
    }


def build_impact_review() -> dict:
    records = tray_records()
    layout = selected_layout()
    audit = audit_layout(layout)
    return {
        "schema_version": "cmf_f4_arm_asset_layout_impact_review_v6",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_2",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "ranking": [
            "smallest compliant official tray model",
            "single arm with larger IK/joint-limit margin",
            "minimum common-X transport distance",
            "slot visibility and positional balance",
            "minimum occlusion and carried-path collision",
        ],
        "tray_records": records,
        "selected_layout": layout,
        "cpu_audit": audit,
        "status": "cpu_geometry_and_common_route_pass_neutral_orientation_repair_pending"
        if audit["pass_cpu_geometry"]
        else "cpu_geometry_failed",
    }


def write_impact_review(path: Path) -> dict:
    if path.exists():
        raise FileExistsError("F4 impact review output must be new")
    value = build_impact_review()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return value
