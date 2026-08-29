"""Offline diagnosis of the runtime-v3_2 F2 inside failure."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .geometry import obb_corners, quaternion_orientation_error
from .runtime_v3_2_contracts import F2_PLASTICBOX_BASE2_CAVITY
from .verifiers import verify_true_cavity_obb


VAULT_ROOT = Path("/nfs_share/lijunhui/Vault-on-Fvl09")
BRANCH_ROOT = (
    VAULT_ROOT
    / "数据构造/实现审计/probe_outputs"
    / "nonformal_F2_asset_mapping_root_runtime_v3_2_seed20260829_gpu0_run2_raw_timing_repair"
    / "root/branches/F2-inside"
)
CAN_HALF_EXTENTS_M = np.asarray(
    [0.06508397222247786, 0.09657016642050303, 0.06527871934324424],
    dtype=np.float64,
) / 2.0
TABLE_BOUNDS_XY = np.asarray([[-0.45, -0.35], [0.45, 0.20]], dtype=np.float64)
SAMPLE_OFFSETS = (1, 5, 10, 25, 50, 125, 250)


def _contact_summary(raw: np.lib.npyio.NpzFile, index: int) -> dict:
    pairs = json.loads(str(raw["audit__contact_pairs_json"][index]))
    selected = []
    for item in pairs:
        names = (item.get("body_a"), item.get("body_b"))
        if "f2_main_can" in names and "f2_plasticbox" in names:
            selected.append(item)
    return {
        "can_box_contact_pair_count": len(selected),
        "can_box_contact_impulse": float(
            sum(float(item.get("impulse_norm_sum", 0.0)) for item in selected)
        ),
        "can_box_contact_normals": [
            normal for item in selected for normal in item.get("point_normals", [])
        ],
    }


def _sample(raw: np.lib.npyio.NpzFile, index: int, release_eef_pose) -> dict:
    can_pose = np.asarray(raw["audit__role_object_pose__main_can"][index], dtype=np.float64)
    box_pose = np.asarray(raw["audit__role_object_pose__box"][index], dtype=np.float64)
    fit = verify_true_cavity_obb(
        can_pose,
        CAN_HALF_EXTENTS_M,
        box_pose,
        F2_PLASTICBOX_BASE2_CAVITY,
    )
    corners = obb_corners(can_pose, CAN_HALF_EXTENTS_M)
    lower = corners[:, :2].min(axis=0)
    upper = corners[:, :2].max(axis=0)
    table_edge_clearance = float(
        np.min(
            np.concatenate(
                (
                    lower - TABLE_BOUNDS_XY[0],
                    TABLE_BOUNDS_XY[1] - upper,
                )
            )
        )
    )
    eef = np.asarray(raw["stream__realized_eef"][index, :7], dtype=np.float64)
    contact = _contact_summary(raw, index)
    return {
        "state_index": int(index),
        "can_pose": can_pose.tolist(),
        "can_linear_velocity_mps": np.asarray(
            raw["audit__object_linear_velocity"][index], dtype=np.float64
        ).tolist(),
        "can_angular_velocity_rps": np.asarray(
            raw["audit__object_angular_velocity"][index], dtype=np.float64
        ).tolist(),
        "can_speed_mps": float(
            np.linalg.norm(raw["audit__object_linear_velocity"][index])
        ),
        "can_obb_inside_true_cavity": bool(fit["pass_true_cavity_obb"]),
        "can_obb_relative_cavity": fit,
        "eef_pose": eef.tolist(),
        "eef_release_target_position_error_m": float(
            np.linalg.norm(eef[:3] - release_eef_pose[:3])
        ),
        "eef_release_target_orientation_error_rad": quaternion_orientation_error(
            eef[3:], release_eef_pose[3:]
        ),
        "actual_left_gripper_joint_qpos": np.asarray(
            raw["audit__realized_left_gripper_joint_qpos"][index],
            dtype=np.float64,
        ).tolist(),
        "selected_gripper_contact": bool(
            raw["audit__selected_gripper_contact"][index]
        ),
        "selected_gripper_contact_impulse": float(
            raw["audit__selected_gripper_contact_impulse"][index]
        ),
        "table_edge_clearance_m": table_edge_clearance,
        **contact,
    }


def build_inside_diagnosis(branch_root: Path = BRANCH_ROOT) -> dict:
    branch_root = Path(branch_root)
    receipt = json.loads((branch_root / "receipt.json").read_text(encoding="utf-8"))
    execution_spec = receipt["raw_manifest"]["provenance"]["realization_spec"][
        "planner_execution_spec"
    ]
    targets = {item["segment_id"]: item["pose"] for item in execution_spec["targets"]}
    release_eef_pose = np.asarray(targets["release"], dtype=np.float64)
    with np.load(branch_root / "raw/raw_streams.npz", allow_pickle=False) as raw:
        gripper = np.asarray(raw["stream__gripper_command"][:, 0], dtype=np.float64)
        release_start_action = int(
            np.where((np.arange(len(gripper)) > 2300) & (gripper > 0.0))[0][0]
        )
        release_complete_action = int(
            np.where(
                (np.arange(len(gripper)) >= release_start_action)
                & (gripper >= 1.0 - 1e-9)
            )[0][0]
        )
        planner_queries = receipt["raw_manifest"]["provenance"]["planner_queries"]
        # Query IDs 4/5 are preplace/release in the frozen execution table.
        preplace_end = int(planner_queries[3]["end_step"])
        release_descent_end = int(planner_queries[4]["end_step"])
        retreat_end = int(planner_queries[5]["end_step"])
        rest_end = int(planner_queries[6]["end_step"])
        sample_indices = {
            "preplace_end": preplace_end,
            "before_release": release_start_action,
            **{
                f"after_release_{offset}": release_complete_action + offset
                for offset in SAMPLE_OFFSETS
            },
            "after_retreat": retreat_end,
            "after_rest": rest_end,
        }
        samples = {
            name: _sample(raw, index, release_eef_pose)
            for name, index in sample_indices.items()
        }
        selected_contact = np.asarray(
            raw["audit__selected_gripper_contact"], dtype=bool
        )
        first_contact_loss = next(
            (
                index
                for index in range(preplace_end, release_descent_end + 1)
                if not selected_contact[index]
            ),
            None,
        )
        can_pose = np.asarray(raw["audit__role_object_pose__main_can"], dtype=np.float64)
        first_outside_table = next(
            (
                index
                for index in range(preplace_end, release_descent_end + 1)
                if not (
                    TABLE_BOUNDS_XY[0, 0] <= can_pose[index, 0] <= TABLE_BOUNDS_XY[1, 0]
                    and TABLE_BOUNDS_XY[0, 1] <= can_pose[index, 1] <= TABLE_BOUNDS_XY[1, 1]
                )
            ),
            None,
        )
    classification = "box_wall_collision_and_ejection_before_gripper_release"
    checks = {
        "preplace_still_grasped": samples["preplace_end"]["selected_gripper_contact"],
        "before_release_not_inside": not samples["before_release"][
            "can_obb_inside_true_cavity"
        ],
        "before_release_high_speed": samples["before_release"]["can_speed_mps"] > 0.1,
        "before_release_outside_table": samples["before_release"][
            "table_edge_clearance_m"
        ]
        < 0.0,
        "contact_lost_during_release_descent": first_contact_loss is not None,
        "left_table_during_release_descent": first_outside_table is not None,
    }
    return {
        "schema_version": "cmf_f2_inside_release_diagnosis_v3_3_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_3",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "source_branch": str(branch_root),
        "release_event": {
            "open_start_action": release_start_action,
            "open_complete_action": release_complete_action,
            "preplace_end_state": preplace_end,
            "release_descent_end_state": release_descent_end,
            "retreat_end_state": retreat_end,
            "rest_end_state": rest_end,
        },
        "samples": samples,
        "first_selected_gripper_contact_loss_state": first_contact_loss,
        "first_can_center_outside_table_state": first_outside_table,
        "classification": classification,
        "classification_checks": checks,
        "selected_global_repair": {
            "rule": "inside suffix uses frozen actor-to-EEF target with staged world-z descent and intermediate OBB/contact Gates",
            "descent_offsets_m_above_release": [0.10, 0.06, 0.03, 0.0],
            "retreat": "world-z reverse through the same staged poses",
            "layout_version": "f2_box2_mutually_exclusive_facilities_v2",
            "full_obb_inside_verifier_relaxed": False,
            "branch_specific_retry": False,
        },
        "pass_diagnosis": all(checks.values()),
    }


def write_diagnosis(path: Path) -> dict:
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    value = build_inside_diagnosis()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value
