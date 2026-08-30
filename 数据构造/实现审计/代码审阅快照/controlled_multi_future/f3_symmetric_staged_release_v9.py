"""F3 revision-9 controller-only symmetric staged-release hypothesis.

Revision 8 proved every V/H event and the physical contact signal, but two of
three bottles rolled beyond the frozen final orientation tolerance after the
single 0->1 gripper ramp.  This module freezes one hypothesis derived from the
observed release aperture: first neutralize asymmetric preload at the mean
realized finger position, then open only another 0.16 normalized units at the
same 300-step RoboTwin interpolation.  Full-open is allowed only after physical
assembly disengagement, pad support, stable motion, footprint and frozen final
return-equivalence all pass.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .f3_physical_contact_signal_v8 import (
    classify_contact_pair_physical_hit_v8,
)


SCHEMA_VERSION = "cmf_f3_symmetric_staged_release_v9"
GATE_SCHEMA_VERSION = "cmf_f3_symmetric_staged_release_gate_v9"
RELEASE_VERSION = "f3_post_release_roll_symmetric_staged_release_v9"
GRIPPER_SCALE_M = (-0.01, 0.045)
DISENGAGEMENT_DELTA_NORMALIZED = 0.16
MAXIMUM_DISENGAGEMENT_TARGET_NORMALIZED = 0.98
STAGE_HOLD_STEPS = 50
STABLE_WINDOW_FRAMES = 50
DISENGAGEMENT_CONFIRM_FRAMES = 10
STABLE_LINEAR_SPEED_MPS = 0.02
STABLE_ANGULAR_SPEED_RPS = 0.05
POSITION_ERROR_M = 0.03
ORIENTATION_ERROR_RAD = 0.02

R8_FAILURE_EVIDENCE = {
    "namespace": "nonformal_runtime_v3_3_f3_root_seed20260829_revision8_run1_anygpu",
    "implementation_source_sha256": "4b5ac619c0d765024bc7cdc01ea02e2a30e7a9bc195274961c626aa48f0c2d21",
    "evidence_manifest_file_sha256": "f6eb29862115c252ae7be46f3d3d356de444de4294199c72d923f162187d522e",
    "evidence_tree_sha256": "e4e88965529e1678ac4aba47fd33bcb693f456c77ab64c10e5b5e5c56fb67455",
    "impact_review_file_sha256": "53fc945923bcc6f828f0b3e4dda023b5d224ad56e15d5590d7c0e52140e92389",
    "top_receipt_file_sha256": "0ef8c12c204f28a646dad1a289549500aecbcee1cf27857b412933fb5d8eb398",
    "guard_file_sha256": "4d885b659417a9743f986b14e995a37362ea8fcda57af19fd222517d8d201171",
    "program_status": {
        "VVHH": "failed_verifier",
        "VHVH": "accepted",
        "VHHV": "failed_verifier",
    },
    "physical_release_mean_qpos_m": {
        "VVHH": 0.04018566943705082,
    },
    "post_release_roll_is_primary_hypothesis": True,
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


def _vector(value: Any, *, label: str, length: int = 2) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(-1)
    if result.shape != (length,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be one finite {length}-D vector")
    return result


def build_f3_symmetric_staged_release_spec_v9(
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
    qpos = _vector(actual_finger_qpos, label="F3 actual finger qpos")
    target = _vector(current_drive_target, label="F3 current drive target")
    qf = _vector(applied_finger_qf, label="F3 applied finger qf")
    drive_effort = _vector(
        estimated_drive_effort, label="F3 estimated drive effort"
    )
    stiffness = _vector(drive_stiffness, label="F3 drive stiffness")
    damping = _vector(drive_damping, label="F3 drive damping")
    force_limit = _vector(drive_force_limit, label="F3 drive force limit")
    modes = tuple(str(value) for value in drive_mode)
    if modes != ("force", "force"):
        raise ValueError("F3 staged release requires both gripper drives in force mode")
    lower, upper = GRIPPER_SCALE_M
    balanced_drive_target = float(np.mean(qpos))
    balanced_normalized = (balanced_drive_target - lower) / (upper - lower)
    disengagement_normalized = min(
        balanced_normalized + DISENGAGEMENT_DELTA_NORMALIZED,
        MAXIMUM_DISENGAGEMENT_TARGET_NORMALIZED,
    )
    if not 0.0 < balanced_normalized < disengagement_normalized < 1.0:
        raise ValueError("F3 staged-release targets must be strictly ordered")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "release_version": RELEASE_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "arm": "left",
        "main_object": "001_bottle/base13",
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
        "balanced_normalized_target": float(balanced_normalized),
        "disengagement_delta_normalized": DISENGAGEMENT_DELTA_NORMALIZED,
        "disengagement_normalized_target": float(disengagement_normalized),
        "maximum_disengagement_target_normalized": MAXIMUM_DISENGAGEMENT_TARGET_NORMALIZED,
        "stage_hold_steps": STAGE_HOLD_STEPS,
        "stable_window_frames": STABLE_WINDOW_FRAMES,
        "disengagement_confirm_frames": DISENGAGEMENT_CONFIRM_FRAMES,
        "candidate_search": False,
        "fallback": False,
        "online_parameter_search": False,
        "bottle_changed": False,
        "pad_changed": False,
        "physics_changed": False,
        "executing_arm_changed": False,
        "VH_axis_or_program_changed": False,
        "release_actor_target_changed": False,
        "final_verifier_changed": False,
        "final_verifier_threshold_changed": False,
    }
    payload["receipt_sha256"] = canonical_json_sha256(payload)
    return validate_f3_symmetric_staged_release_spec_v9(payload)


def validate_f3_symmetric_staged_release_spec_v9(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    value = json.loads(
        json.dumps(receipt, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )
    digest = value.pop("receipt_sha256", None)
    if not isinstance(digest, str) or canonical_json_sha256(value) != digest:
        raise ValueError("F3 staged-release receipt hash mismatch")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("F3 staged-release schema mismatch")
    if value.get("source_evidence") != R8_FAILURE_EVIDENCE:
        raise ValueError("F3 revision-8 evidence binding changed")
    invariants = (
        value.get("arm") == "left",
        value.get("main_object") == "001_bottle/base13",
        value.get("candidate_search") is False,
        value.get("fallback") is False,
        value.get("online_parameter_search") is False,
        value.get("bottle_changed") is False,
        value.get("pad_changed") is False,
        value.get("physics_changed") is False,
        value.get("executing_arm_changed") is False,
        value.get("VH_axis_or_program_changed") is False,
        value.get("release_actor_target_changed") is False,
        value.get("final_verifier_changed") is False,
        value.get("final_verifier_threshold_changed") is False,
        value.get("drive_mode") == ["force", "force"],
        value.get("drive_effort_is_measured_force") is False,
    )
    if not all(invariants):
        raise ValueError("F3 staged-release frozen invariants changed")
    qpos = _vector(
        value["actual_finger_qpos_m"], label="recorded F3 finger qpos"
    )
    balanced = float(np.mean(qpos))
    normalized = (balanced - GRIPPER_SCALE_M[0]) / (
        GRIPPER_SCALE_M[1] - GRIPPER_SCALE_M[0]
    )
    disengagement = min(
        normalized + DISENGAGEMENT_DELTA_NORMALIZED,
        MAXIMUM_DISENGAGEMENT_TARGET_NORMALIZED,
    )
    if (
        value.get("balanced_drive_target_m") != balanced
        or value.get("balanced_normalized_target") != normalized
        or value.get("disengagement_normalized_target") != disengagement
    ):
        raise ValueError("F3 staged-release formula mismatch")
    value["receipt_sha256"] = digest
    return value


def _pair_summary(
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
        "pair_receipt_sha256": [item["receipt_sha256"] for item in relevant],
    }


def audit_f3_symmetric_staged_release_gate_v9(
    rows: Sequence[Mapping[str, Any]],
    *,
    bottle_actor_name: str,
    gripper_assembly_link_names: Sequence[str],
    pad_actor_name: str,
    bottle_position_error_m: float,
    bottle_orientation_error_rad: float,
    footprint_inside_pad: bool,
) -> dict[str, Any]:
    values = list(rows)
    if len(values) < STABLE_WINDOW_FRAMES:
        raise ValueError("F3 staged-release gate lacks stable-window rows")
    assembly = {str(value) for value in gripper_assembly_link_names}
    if not assembly or not bottle_actor_name or not pad_actor_name:
        raise ValueError("F3 staged-release gate lacks actor/link identity")
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
    assembly_contact = [
        _pair_summary(
            row["contact_pairs"],
            first_names={bottle_actor_name},
            second_names=assembly,
        )
        for row in confirm_rows
    ]
    pad_contact = [
        _pair_summary(
            row["contact_pairs"],
            first_names={bottle_actor_name},
            second_names={pad_actor_name},
        )
        for row in confirm_rows
    ]
    checks = {
        "position_return_equivalence": float(bottle_position_error_m)
        <= POSITION_ERROR_M,
        "orientation_return_equivalence": float(bottle_orientation_error_rad)
        <= ORIENTATION_ERROR_RAD,
        "bottle_footprint_inside_pad": footprint_inside_pad is True,
        "stable_linear_window": max(linear) <= STABLE_LINEAR_SPEED_MPS,
        "stable_angular_window": max(angular) <= STABLE_ANGULAR_SPEED_RPS,
        "gripper_assembly_physically_disengaged": all(
            item["evidence_complete"] is True
            and item["physical_hit"] is False
            for item in assembly_contact
        ),
        "physical_pad_support_continuous": all(
            item["evidence_complete"] is True
            and item["physical_hit"] is True
            for item in pad_contact
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
        "bottle_position_error_m": float(bottle_position_error_m),
        "bottle_orientation_error_rad": float(bottle_orientation_error_rad),
        "maximum_linear_speed_mps": max(linear),
        "maximum_angular_speed_rps": max(angular),
        "final_actual_finger_qpos_m": _vector(
            last["realized_left_gripper_joint_qpos"],
            label="F3 final actual finger qpos",
        ).tolist(),
        "final_applied_finger_qf": _vector(
            last["realized_left_gripper_joint_qf"],
            label="F3 final applied finger qf",
        ).tolist(),
        "final_estimated_drive_effort_audit_only": _vector(
            last["estimated_left_gripper_joint_drive_effort"],
            label="F3 final estimated drive effort",
        ).tolist(),
        "final_drive_target_error_m": _vector(
            last["left_gripper_joint_drive_target_error"],
            label="F3 final drive target error",
        ).tolist(),
        "assembly_contact_confirm_window": assembly_contact,
        "pad_contact_confirm_window": pad_contact,
        "checks": checks,
        "pass": all(checks.values()),
        "full_open_allowed": all(checks.values()),
        "missing_signal_policy": "fail_closed_before_full_open",
    }
    receipt["receipt_sha256"] = canonical_json_sha256(receipt)
    return receipt


__all__ = [
    "DISENGAGEMENT_DELTA_NORMALIZED",
    "R8_FAILURE_EVIDENCE",
    "RELEASE_VERSION",
    "STAGE_HOLD_STEPS",
    "audit_f3_symmetric_staged_release_gate_v9",
    "build_f3_symmetric_staged_release_spec_v9",
    "validate_f3_symmetric_staged_release_spec_v9",
]
