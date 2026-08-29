"""CPU evidence audit for fair F1 red/green/blue reachability."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


VAULT_ROOT = Path("/nfs_share/lijunhui/Vault-on-Fvl09")
V3_2_FINAL_ROOT = (
    VAULT_ROOT
    / "数据构造/实现审计/probe_outputs"
    / "nonformal_F1_three_branch_root_runtime_v3_2_seed20260829_gpu0_run2_segmented_lift"
    / "root/root_receipt.json"
)
BLOCK_HALF_EXTENTS_M = np.asarray([0.022, 0.022, 0.022], dtype=np.float64)
EEF_WORKSPACE_BOX_V1 = {
    "lower_m": [-0.45, -0.35, 0.78],
    "upper_m": [0.45, 0.20, 1.02],
    "status": "provisional_CPU_comparison_only_not_a_reachability_proof",
}


def _workspace_margin(point) -> float:
    point = np.asarray(point, dtype=np.float64)
    lower = np.asarray(EEF_WORKSPACE_BOX_V1["lower_m"], dtype=np.float64)
    upper = np.asarray(EEF_WORKSPACE_BOX_V1["upper_m"], dtype=np.float64)
    return float(np.min(np.concatenate((point - lower, upper - point))))


def build_reachability_review(root_receipt_path: Path = V3_2_FINAL_ROOT) -> dict:
    root = json.loads(Path(root_receipt_path).read_text(encoding="utf-8"))
    reference_anchor_path = Path(root_receipt_path).with_name("reference_anchor.json")
    reference_anchor = json.loads(reference_anchor_path.read_text(encoding="utf-8"))
    actor_states = reference_anchor["actor_states"]
    planner = {
        item["program_id"].removeprefix("F1-"): item
        for item in root["planner_solvability_receipts"]
    }
    records = []
    roles = ("red", "green", "blue")
    for role in roles:
        item = planner[role]
        segments = item["evidence"]["segment_receipts"]
        by_id = {segment["segment_id"]: segment for segment in segments}
        actor_pose = actor_states[role]["pose"]
        other_clearances = []
        for other in roles:
            if other == role:
                continue
            distance = float(
                np.linalg.norm(
                    np.asarray(actor_pose[:3], dtype=np.float64)
                    - np.asarray(actor_states[other]["pose"][:3], dtype=np.float64)
                )
            )
            other_clearances.append(
                distance - 2.0 * float(np.max(BLOCK_HALF_EXTENTS_M))
            )
        records.append(
            {
                "role": role,
                "object_pose": actor_pose,
                "pregrasp_pose": by_id["target_pregrasp"]["goal_eef_pose"],
                "grasp_pose": by_id["target_grasp"]["goal_eef_pose"],
                "grasp_quaternion_wxyz": by_id["target_grasp"]["goal_eef_pose"][3:],
                "lift_mid_target": by_id["target_lift_mid"]["goal_eef_pose"],
                "lift_target": by_id.get("target_lift", {}).get("goal_eef_pose"),
                "planner_status": item["status"],
                "planner_query_count": item["planner_query_count"],
                "terminal_qpos_sha256_by_segment": {
                    segment["segment_id"]: segment["end_qpos_sha256"]
                    for segment in segments
                },
                "terminal_qpos_values_available": False,
                "joint_limit_margin": None,
                "joint_limit_margin_status": "pending_fixed_gpu0_planner_only_gate",
                "eef_workspace_margin_m": {
                    "grasp": _workspace_margin(
                        by_id["target_grasp"]["goal_eef_pose"][:3]
                    ),
                    "lift_mid": _workspace_margin(
                        by_id["target_lift_mid"]["goal_eef_pose"][:3]
                    ),
                    "lift": None
                    if "target_lift" not in by_id
                    else _workspace_margin(
                        by_id["target_lift"]["goal_eef_pose"][:3]
                    ),
                },
                "minimum_pairwise_block_surface_clearance_m": min(
                    other_clearances
                ),
                "failure_segment": next(
                    (
                        segment["segment_id"]
                        for segment in segments
                        if segment["planner_status"] != "Success"
                    ),
                    None,
                ),
            }
        )
    return {
        "schema_version": "cmf_f1_three_object_reachability_impact_review_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_3",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "source_runtime": "controlled_multi_future_runtime_v3_2",
        "source_root_receipt": str(Path(root_receipt_path)),
        "source_reference_anchor": str(reference_anchor_path),
        "eef_workspace_box": EEF_WORKSPACE_BOX_V1,
        "records": records,
        "comparative_finding": {
            "red_green_full_12cm_lift_planner_passed": all(
                next(record for record in records if record["role"] == role)[
                    "planner_status"
                ]
                == "passed"
                for role in ("red", "green")
            ),
            "blue_first_6cm_passed_second_6cm_failed": (
                next(record for record in records if record["role"] == "blue")
                ["failure_segment"]
                == "target_lift"
            ),
            "role_specific_repair_allowed": False,
            "terminal_qpos_values_missing_from_v3_2_receipt": True,
        },
        "selected_uniform_repair": {
            "rule": "all red/green/blue use two 4cm world-z lift segments; total 8cm",
            "layout_changed": False,
            "grasp_orientation_changed": False,
            "target_role_specific_parameters": False,
            "planner_only_gate_required_before_execution": True,
        },
        "status": "cpu_comparison_complete_joint_margin_pending_planner_only_gate",
    }


def write_review(path: Path) -> dict:
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    value = build_reachability_review()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value
