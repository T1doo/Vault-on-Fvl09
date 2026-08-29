"""Offline shared-first-V and grasp-drift diagnosis for F3 runtime-v3_3."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .signals import closed_loop_event_metrics


VAULT_ROOT = Path("/nfs_share/lijunhui/Vault-on-Fvl09")
FINAL_BRANCH_ROOT = (
    VAULT_ROOT
    / "数据构造/实现审计/probe_outputs"
    / "nonformal_F3_grasp_lift_full_root_runtime_v3_2_seed20260829_gpu0_run3_shared_8cm"
    / "root/branches"
)
SHARED_V_NOMINAL_AMPLITUDE_M_V3_3 = 0.055
H_NOMINAL_AMPLITUDE_M_V3_3 = 0.05
GRASP_BOUNDARIES = (
    "post_close",
    "post_lift",
    "post_central",
    "post_shared_V",
    "before_release",
)


def build_shared_prefix_diagnosis(branch_root: Path = FINAL_BRANCH_ROOT) -> dict:
    branch_root = Path(branch_root)
    records = []
    for branch in sorted(branch_root.iterdir()):
        if not branch.is_dir():
            continue
        receipt = json.loads((branch / "receipt.json").read_text(encoding="utf-8"))
        with np.load(branch / "trace_source.npz", allow_pickle=False) as trace:
            markers = json.loads(str(trace["event_markers_json"].item()))
            start = int(markers["event_0_V_start"])
            end = int(markers["event_0_V_end"])
            eef = np.asarray(trace["eef_pose"][start : end + 1, :3], dtype=np.float64)
            bottle = np.asarray(
                trace["object_pose"][start : end + 1, :3], dtype=np.float64
            )
            eef_metrics = closed_loop_event_metrics(eef, eef[0], 2)
            bottle_metrics = closed_loop_event_metrics(bottle, bottle[0], 2)
            contact_fraction = float(
                np.mean(trace["selected_gripper_contact"][start : end + 1])
            )
            end_linear_speed = float(
                np.linalg.norm(trace["object_linear_velocity"][end])
            )
            end_angular_speed = float(
                np.linalg.norm(trace["object_angular_velocity"][end])
            )
        semantic = receipt["verifier"]["family_semantic_verifier"]
        records.append(
            {
                "program_id": receipt["program_id"],
                "shared_first_v_step_count": end - start + 1,
                "eef_metrics": eef_metrics,
                "bottle_metrics": bottle_metrics,
                "selected_gripper_contact_fraction": contact_fraction,
                "bottle_end_linear_speed_mps": end_linear_speed,
                "bottle_end_angular_speed_rps": end_angular_speed,
                "grasp_transform": semantic["grasp_transform"],
                "diagnosis": semantic["diagnosis"],
                "shared_v_eef_negative_gate_pass": semantic["realized_motion"]
                ["event_checks"]["event_0_V"]["eef_negative_amplitude"],
            }
        )
    negative = [record["eef_metrics"]["negative_amplitude"] for record in records]
    checks = {
        "three_program_records": len(records) == 3,
        "all_selected_gripper_contact_fraction_one": all(
            record["selected_gripper_contact_fraction"] == 1.0 for record in records
        ),
        "all_old_shared_v_negative_amplitude_below_40mm": all(
            value < 0.04 for value in negative
        ),
        "all_old_shared_v_negative_amplitude_within_1mm_of_gate": all(
            0.039 <= value < 0.04 for value in negative
        ),
        "v_h_v_h_grasp_transform_unstable": any(
            record["program_id"] == "F3-VHVH"
            and not record["grasp_transform"]["grasp_transform_stable"]
            for record in records
        ),
    }
    return {
        "schema_version": "cmf_f3_shared_prefix_diagnosis_v3_3_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_3",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "source_branch_root": str(branch_root),
        "records": records,
        "checks": checks,
        "pass_diagnosis": all(checks.values()),
        "selected_uniform_repair": {
            "canonical_prefix": [
                "pregrasp",
                "grasp",
                "close",
                "two_segment_lift",
                "central",
                "shared_first_V",
            ],
            "shared_v_nominal_amplitude_m": SHARED_V_NOMINAL_AMPLITUDE_M_V3_3,
            "h_nominal_amplitude_m": H_NOMINAL_AMPLITUDE_M_V3_3,
            "verifier_threshold_relaxed": False,
            "exact_action_bytes_replayed": True,
            "grasp_boundary_measurements": list(GRASP_BOUNDARIES),
            "settling_excluded_from_semantic_P": True,
            "program_specific_correction_allowed": False,
        },
        "status": "cpu_diagnosis_pass_exact_prefix_gpu_gate_pending"
        if all(checks.values())
        else "cpu_diagnosis_failed",
    }


def write_diagnosis(path: Path) -> dict:
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    value = build_shared_prefix_diagnosis()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value
