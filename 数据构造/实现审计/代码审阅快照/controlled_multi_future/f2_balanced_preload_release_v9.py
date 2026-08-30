"""F2 revision-9 single-hypothesis balanced-preload release contract.

Revision 8 proved that the XY target, pre-release stability and rim clearance
were adequate, but full opening accelerated the can while it remained between
the selected fingers.  This module defines one deterministic controller-only
hypothesis: command both fingers to the mean *realized* aperture to remove the
asymmetric preload, then require physical finger disengagement, true-inside,
stable motion and physical box support before the ordinary full-open command.

There is no candidate search, fallback, asset/layout/arm change, or verifier
relaxation.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .f3_physical_contact_signal_v8 import (
    classify_contact_pair_physical_hit_v8,
)


SCHEMA_VERSION = "cmf_f2_balanced_preload_release_v9"
GATE_SCHEMA_VERSION = "cmf_f2_balanced_preload_release_gate_v9"
RELEASE_VERSION = "f2_inside_two_stage_balanced_preload_release_v9"
GRIPPER_SCALE_M = (-0.01, 0.045)
POST_COMMAND_HOLD_STEPS = 50
STABLE_WINDOW_FRAMES = 50
DISENGAGEMENT_CONFIRM_FRAMES = 10
STABLE_LINEAR_SPEED_MPS = 0.02
STABLE_ANGULAR_SPEED_RPS = 0.05

R8_FAILURE_EVIDENCE = {
    "namespace": "nonformal_runtime_v3_3_f2_root_seed20260829_revision8_run1_anygpu",
    "implementation_source_sha256": "4b5ac619c0d765024bc7cdc01ea02e2a30e7a9bc195274961c626aa48f0c2d21",
    "evidence_manifest_file_sha256": "a160724ddd422a1f63f0ccd3f6a00e1835e46f3eaafc6fe78a349808f7b50a6c",
    "evidence_tree_sha256": "767ded27e13a3e691220c5d1ce0b34ba1f98faae75e7978d9187703aba4a0ccb",
    "impact_review_file_sha256": "53fc945923bcc6f828f0b3e4dda023b5d224ad56e15d5590d7c0e52140e92389",
    "top_receipt_file_sha256": "048cd1991711247cb24733d217c2febbe10e98eeac04e370cc087bddc577fe7e",
    "guard_file_sha256": "f00084f0000567fa4570faf4335762f014162dfcaeb9cf3163a6bd4cb64a8cb0",
    "inside_open_start_trace_index": 1994,
    "inside_first_finger_disconnect_trace_index": 2151,
    "inside_contact_frames_after_open": 157,
    "inside_linear_speed_mps_before_disconnect": 1.1418868359450025,
    "inside_angular_speed_rps_before_disconnect": 5.159692730899969,
    "inside_maximum_linear_speed_mps_after_open": 1.489688381871149,
    "inside_maximum_angular_speed_rps_after_open": 14.775461109133428,
    "inside_final_true_cavity_obb": False,
    "on_status": "accepted",
    "beside_status": "accepted",
}


def canonical_json_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _finite_vector(value: Any, *, label: str, length: int = 2) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(-1)
    if result.shape != (length,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be one finite {length}-D vector")
    return result


def build_f2_balanced_preload_release_spec_v9(
    *,
    actual_finger_qpos: Sequence[float],
    current_drive_target: Sequence[float],
    applied_finger_qf: Sequence[float],
    estimated_drive_effort: Sequence[float],
    drive_stiffness: Sequence[float],
    drive_damping: Sequence[float],
    drive_force_limit: Sequence[float],
    drive_mode: Sequence[str],
) -> dict[str, Any]:
    qpos = _finite_vector(actual_finger_qpos, label="actual finger qpos")
    target = _finite_vector(current_drive_target, label="current drive target")
    qf = _finite_vector(applied_finger_qf, label="applied finger qf")
    drive_effort = _finite_vector(
        estimated_drive_effort, label="estimated drive effort"
    )
    stiffness = _finite_vector(drive_stiffness, label="drive stiffness")
    damping = _finite_vector(drive_damping, label="drive damping")
    force_limit = _finite_vector(drive_force_limit, label="drive force limit")
    modes = tuple(str(value) for value in drive_mode)
    if modes != ("force", "force"):
        raise ValueError("F2 staged release requires both gripper drives in force mode")
    lower, upper = GRIPPER_SCALE_M
    balanced_drive_target = float(np.mean(qpos))
    normalized = (balanced_drive_target - lower) / (upper - lower)
    if not 0.0 < normalized < 1.0:
        raise ValueError("balanced preload target must remain strictly in (0,1)")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "release_version": RELEASE_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "arm": "left",
        "main_object": "071_can/base1",
        "relation": "inside",
        "source_evidence": dict(R8_FAILURE_EVIDENCE),
        "actual_finger_qpos_m": qpos.tolist(),
        "current_drive_target_m": target.tolist(),
        "applied_finger_qf": qf.tolist(),
        "estimated_drive_effort_audit_only": drive_effort.tolist(),
        "drive_effort_is_measured_force": False,
        "drive_stiffness": stiffness.tolist(),
        "drive_damping": damping.tolist(),
        "drive_force_limit": force_limit.tolist(),
        "drive_mode": list(modes),
        "gripper_scale_m": list(GRIPPER_SCALE_M),
        "balanced_drive_target_m": balanced_drive_target,
        "partial_open_normalized_target": float(normalized),
        "expected_balanced_joint_targets_m": [
            balanced_drive_target,
            balanced_drive_target,
        ],
        "formula": "mean(actual selected-finger qpos), then normalize by (-0.01,0.045)",
        "post_command_hold_steps": POST_COMMAND_HOLD_STEPS,
        "stable_window_frames": STABLE_WINDOW_FRAMES,
        "disengagement_confirm_frames": DISENGAGEMENT_CONFIRM_FRAMES,
        "candidate_search": False,
        "fallback": False,
        "online_parameter_search": False,
        "scene_layout_changed": False,
        "asset_changed": False,
        "executing_arm_changed": False,
        "desired_actor_target_changed": False,
        "final_verifier_changed": False,
        "final_verifier_threshold_changed": False,
    }
    payload["receipt_sha256"] = canonical_json_sha256(payload)
    return validate_f2_balanced_preload_release_spec_v9(payload)


def validate_f2_balanced_preload_release_spec_v9(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    value = json.loads(
        json.dumps(receipt, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )
    digest = value.pop("receipt_sha256", None)
    if not isinstance(digest, str) or canonical_json_sha256(value) != digest:
        raise ValueError("F2 balanced-preload receipt hash mismatch")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("F2 balanced-preload schema mismatch")
    if value.get("source_evidence") != R8_FAILURE_EVIDENCE:
        raise ValueError("F2 revision-8 evidence binding changed")
    invariants = (
        value.get("arm") == "left",
        value.get("main_object") == "071_can/base1",
        value.get("relation") == "inside",
        value.get("candidate_search") is False,
        value.get("fallback") is False,
        value.get("online_parameter_search") is False,
        value.get("scene_layout_changed") is False,
        value.get("asset_changed") is False,
        value.get("executing_arm_changed") is False,
        value.get("desired_actor_target_changed") is False,
        value.get("final_verifier_changed") is False,
        value.get("final_verifier_threshold_changed") is False,
        value.get("drive_mode") == ["force", "force"],
        value.get("drive_effort_is_measured_force") is False,
    )
    if not all(invariants):
        raise ValueError("F2 balanced-preload frozen invariants changed")
    # Formula is recomputed directly to avoid recursive validation.
    qpos = _finite_vector(
        value["actual_finger_qpos_m"], label="recorded actual finger qpos"
    )
    balanced = float(np.mean(qpos))
    normalized = (balanced - GRIPPER_SCALE_M[0]) / (
        GRIPPER_SCALE_M[1] - GRIPPER_SCALE_M[0]
    )
    if (
        value.get("balanced_drive_target_m") != balanced
        or value.get("partial_open_normalized_target") != normalized
        or value.get("expected_balanced_joint_targets_m")
        != [balanced, balanced]
    ):
        raise ValueError("F2 balanced-preload formula mismatch")
    value["receipt_sha256"] = digest
    return value


def _physical_pair_summary(
    pairs: Sequence[Mapping[str, Any]],
    *,
    first_names: set[str],
    second_names: set[str],
) -> dict[str, Any]:
    relevant = []
    for pair in pairs:
        bodies = {str(pair.get("body_a")), str(pair.get("body_b"))}
        if bodies & first_names and bodies & second_names:
            relevant.append(classify_contact_pair_physical_hit_v8(pair))
    return {
        "pair_presence_count": len(relevant),
        "evidence_complete": all(
            item["evidence_complete"] is True for item in relevant
        ),
        "physical_hit": any(
            item["physical_hit_for_gate"] is True for item in relevant
        ),
        "pair_receipt_sha256": [
            item["receipt_sha256"] for item in relevant
        ],
    }


def audit_f2_balanced_preload_release_gate_v9(
    rows: Sequence[Mapping[str, Any]],
    *,
    can_actor_name: str,
    selected_finger_link_names: Sequence[str],
    box_actor_name: str,
    true_cavity_obb_pass: bool,
) -> dict[str, Any]:
    values = list(rows)
    if len(values) < STABLE_WINDOW_FRAMES:
        raise ValueError("F2 balanced-preload gate lacks stable-window rows")
    fingers = {str(value) for value in selected_finger_link_names}
    if not fingers or not can_actor_name or not box_actor_name:
        raise ValueError("F2 balanced-preload gate lacks actor/link identity")
    stable_rows = values[-STABLE_WINDOW_FRAMES:]
    confirm_rows = values[-DISENGAGEMENT_CONFIRM_FRAMES:]
    linear = [
        float(np.linalg.norm(np.asarray(row["actor_linear_velocity"])))
        for row in stable_rows
    ]
    angular = [
        float(np.linalg.norm(np.asarray(row["actor_angular_velocity"])))
        for row in stable_rows
    ]
    finger_contact = [
        _physical_pair_summary(
            row["contact_pairs"],
            first_names={can_actor_name},
            second_names=fingers,
        )
        for row in confirm_rows
    ]
    box_contact = [
        _physical_pair_summary(
            row["contact_pairs"],
            first_names={can_actor_name},
            second_names={box_actor_name},
        )
        for row in confirm_rows
    ]
    checks = {
        "true_cavity_obb": true_cavity_obb_pass is True,
        "stable_linear_window": max(linear) <= STABLE_LINEAR_SPEED_MPS,
        "stable_angular_window": max(angular) <= STABLE_ANGULAR_SPEED_RPS,
        "selected_fingers_physically_disengaged": all(
            item["evidence_complete"] is True
            and item["physical_hit"] is False
            for item in finger_contact
        ),
        "physical_box_support_continuous": all(
            item["evidence_complete"] is True
            and item["physical_hit"] is True
            for item in box_contact
        ),
    }
    last = values[-1]
    receipt = {
        "schema_version": GATE_SCHEMA_VERSION,
        "release_version": RELEASE_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "row_count": len(values),
        "stable_window_frames": STABLE_WINDOW_FRAMES,
        "disengagement_confirm_frames": DISENGAGEMENT_CONFIRM_FRAMES,
        "maximum_linear_speed_mps": max(linear),
        "maximum_angular_speed_rps": max(angular),
        "final_actual_finger_qpos_m": _finite_vector(
            last["realized_left_gripper_joint_qpos"],
            label="final actual finger qpos",
        ).tolist(),
        "final_applied_finger_qf": _finite_vector(
            last["realized_left_gripper_joint_qf"],
            label="final applied finger qf",
        ).tolist(),
        "final_estimated_drive_effort_audit_only": _finite_vector(
            last["estimated_left_gripper_joint_drive_effort"],
            label="final estimated drive effort",
        ).tolist(),
        "final_drive_target_error_m": _finite_vector(
            last["left_gripper_joint_drive_target_error"],
            label="final drive target error",
        ).tolist(),
        "finger_contact_confirm_window": finger_contact,
        "box_contact_confirm_window": box_contact,
        "checks": checks,
        "pass": all(checks.values()),
        "full_open_allowed": all(checks.values()),
        "missing_signal_policy": "fail_closed_before_full_open",
    }
    receipt["receipt_sha256"] = canonical_json_sha256(receipt)
    return receipt


__all__ = [
    "DISENGAGEMENT_CONFIRM_FRAMES",
    "POST_COMMAND_HOLD_STEPS",
    "R8_FAILURE_EVIDENCE",
    "RELEASE_VERSION",
    "STABLE_WINDOW_FRAMES",
    "audit_f2_balanced_preload_release_gate_v9",
    "build_f2_balanced_preload_release_spec_v9",
    "validate_f2_balanced_preload_release_spec_v9",
]
