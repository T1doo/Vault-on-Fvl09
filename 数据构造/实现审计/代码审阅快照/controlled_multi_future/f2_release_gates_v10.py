"""Runtime-v3_4 F2 release-safety/final-success gate separation.

The Revision-9 gate incorrectly required final semantic success before the
ordinary full-open command.  These two fail-closed gates keep the frozen F2
inside verifier unchanged while separating controller safety from the final
250-frame semantic verdict.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .f3_physical_contact_signal_v8 import classify_contact_pair_physical_hit_v8


RELEASE_VERSION = "f2_release_safety_then_final_inside_v10"
SAFETY_SCHEMA_VERSION = "cmf_f2_release_safety_gate_v10"
FINAL_SCHEMA_VERSION = "cmf_f2_final_inside_success_gate_v10"
SAFETY_WINDOW_FRAMES = 50
CONTACT_CONFIRM_FRAMES = 10
FINAL_SETTLE_FRAMES = 250
FINAL_STABLE_WINDOW_FRAMES = 50

# Controller-safety bounds only; these are deliberately looser than the
# unchanged final semantic stability thresholds.  They prevent an r8-style
# ejection while allowing a supported object to continue settling.
SAFETY_MAX_LINEAR_SPEED_MPS = 0.05
SAFETY_MAX_ANGULAR_SPEED_RPS = 1.0
SAFETY_MAX_NEGATIVE_MARGIN_SLOPE_M_PER_FRAME = 5e-4

# Existing provisional final thresholds, unchanged from runtime-v3_3.
FINAL_MAX_LINEAR_SPEED_MPS = 0.02
FINAL_MAX_ANGULAR_SPEED_RPS = 0.05
FORENSIC_OUTPUT_SHA256 = (
    "2919e9844ae386f1a65faa58c4d975ad7e21435ee627eb190b3e9bd46306dab3"
)


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _slope(values: Sequence[float]) -> float:
    array = np.asarray(values, dtype=np.float64)
    if len(array) < 2 or not np.all(np.isfinite(array)):
        raise ValueError("F2 safety trend requires finite multi-frame evidence")
    return float(np.polyfit(np.arange(len(array), dtype=np.float64), array, 1)[0])


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
        "pair_count": len(relevant),
        "evidence_complete": bool(relevant)
        and all(item["evidence_complete"] is True for item in relevant),
        "physical_hit": any(
            item["physical_hit_for_gate"] is True for item in relevant
        ),
        "pair_receipt_sha256": [item["receipt_sha256"] for item in relevant],
    }


def _speed(row: Mapping[str, Any], field: str) -> float:
    value = np.asarray(row[field], dtype=np.float64).reshape(3)
    if not np.all(np.isfinite(value)):
        raise ValueError(f"F2 release row has non-finite {field}")
    return float(np.linalg.norm(value))


def audit_f2_release_safety_gate_v10(
    rows: Sequence[Mapping[str, Any]],
    opening_safety_records: Sequence[Mapping[str, Any]],
    *,
    can_actor_name: str,
    selected_finger_link_names: Sequence[str],
    box_actor_name: str,
) -> dict[str, Any]:
    """Decide whether it is safe to proceed to full-open.

    This gate intentionally does *not* inspect final true-cavity success or the
    final 0.05 rad/s angular-stability criterion.
    """

    values = list(rows)
    geometry = list(opening_safety_records)
    if len(values) != len(geometry) or len(values) < SAFETY_WINDOW_FRAMES:
        raise ValueError("F2 safety gate requires aligned 50-frame evidence")
    fingers = {str(name) for name in selected_finger_link_names}
    if not fingers or not can_actor_name or not box_actor_name:
        raise ValueError("F2 safety gate lacks actor/link identity")
    stable_rows = values[-SAFETY_WINDOW_FRAMES:]
    stable_geometry = geometry[-SAFETY_WINDOW_FRAMES:]
    confirm_rows = stable_rows[-CONTACT_CONFIRM_FRAMES:]
    confirm_geometry = stable_geometry[-CONTACT_CONFIRM_FRAMES:]
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
    linear = [_speed(row, "actor_linear_velocity") for row in stable_rows]
    angular = [_speed(row, "actor_angular_velocity") for row in stable_rows]
    center_margin = [
        float(item["opening_center_signed_margin_m"])
        for item in stable_geometry
    ]
    overlap_margin = [
        float(item["opening_projection_overlap_signed_m"])
        for item in stable_geometry
    ]
    center_slope = _slope(center_margin)
    overlap_slope = _slope(overlap_margin)
    checks = {
        "selected_fingers_physically_detached": all(
            item["physical_hit"] is False for item in finger_contact
        ),
        "finger_contact_evidence_complete": all(
            # A missing pair is a complete negative observation only when the
            # row-level contact signal itself was marked complete by caller.
            bool(row.get("contact_signal_complete", False))
            for row in confirm_rows
        ),
        "continuous_physical_box_support": all(
            item["evidence_complete"] is True
            and item["physical_hit"] is True
            for item in box_contact
        ),
        "opening_center_inside_confirm_window": all(
            item.get("opening_center_inside") is True
            for item in confirm_geometry
        ),
        "opening_projection_overlaps_confirm_window": all(
            item.get("opening_projection_overlaps") is True
            for item in confirm_geometry
        ),
        "no_escape_trend": (
            center_slope >= -SAFETY_MAX_NEGATIVE_MARGIN_SLOPE_M_PER_FRAME
            and overlap_slope >= -SAFETY_MAX_NEGATIVE_MARGIN_SLOPE_M_PER_FRAME
        ),
        "dynamics_non_dangerous": (
            max(linear) <= SAFETY_MAX_LINEAR_SPEED_MPS
            and max(angular) <= SAFETY_MAX_ANGULAR_SPEED_RPS
        ),
        "evidence_complete": all(
            bool(row.get("contact_signal_complete", False))
            and bool(item.get("geometry_evidence_complete", False))
            for row, item in zip(stable_rows, stable_geometry)
        ),
    }
    receipt = {
        "schema_version": SAFETY_SCHEMA_VERSION,
        "release_version": RELEASE_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "forensic_output_sha256": FORENSIC_OUTPUT_SHA256,
        "row_count": len(values),
        "safety_window_frames": SAFETY_WINDOW_FRAMES,
        "contact_confirm_frames": CONTACT_CONFIRM_FRAMES,
        "maximum_linear_speed_mps": max(linear),
        "maximum_angular_speed_rps": max(angular),
        "opening_center_margin_slope_m_per_frame": center_slope,
        "opening_overlap_margin_slope_m_per_frame": overlap_slope,
        "thresholds": {
            "safety_max_linear_speed_mps": SAFETY_MAX_LINEAR_SPEED_MPS,
            "safety_max_angular_speed_rps": SAFETY_MAX_ANGULAR_SPEED_RPS,
            "safety_max_negative_margin_slope_m_per_frame": (
                SAFETY_MAX_NEGATIVE_MARGIN_SLOPE_M_PER_FRAME
            ),
            "threshold_role": "controller safety only; not final verifier relaxation",
        },
        "checks": checks,
        "true_cavity_obb_evaluated": False,
        "final_angular_stability_evaluated": False,
        "full_open_allowed": all(checks.values()),
        "pass": all(checks.values()),
    }
    receipt["receipt_sha256"] = _canonical_sha256(receipt)
    return receipt


def audit_f2_final_inside_success_gate_v10(
    settle_rows: Sequence[Mapping[str, Any]],
    *,
    true_cavity_obb_pass: bool,
    relation_predicates: Mapping[str, bool],
    gripper_full_open: bool,
    arm_rest_pass: bool,
    can_actor_name: str,
    box_actor_name: str,
) -> dict[str, Any]:
    """Apply the unchanged final F2 inside semantics after exactly 250 frames."""

    values = list(settle_rows)
    if len(values) != FINAL_SETTLE_FRAMES:
        raise ValueError("F2 final success requires exactly 250 settle frames")
    stable_rows = values[-FINAL_STABLE_WINDOW_FRAMES:]
    contact_rows = stable_rows[-CONTACT_CONFIRM_FRAMES:]
    linear = [_speed(row, "actor_linear_velocity") for row in stable_rows]
    angular = [_speed(row, "actor_angular_velocity") for row in stable_rows]
    box_contact = [
        _physical_pair_summary(
            row["contact_pairs"],
            first_names={can_actor_name},
            second_names={box_actor_name},
        )
        for row in contact_rows
    ]
    relation = {name: bool(relation_predicates.get(name, False)) for name in (
        "inside",
        "on",
        "beside",
    )}
    checks = {
        "exact_250_settle_frames": len(values) == FINAL_SETTLE_FRAMES,
        "true_cavity_obb": true_cavity_obb_pass is True,
        "stable_linear_window": max(linear) <= FINAL_MAX_LINEAR_SPEED_MPS,
        "stable_angular_window": max(angular) <= FINAL_MAX_ANGULAR_SPEED_RPS,
        "continuous_physical_box_support": all(
            item["evidence_complete"] is True
            and item["physical_hit"] is True
            for item in box_contact
        ),
        "exclusive_inside_relation": (
            relation == {"inside": True, "on": False, "beside": False}
        ),
        "gripper_full_open": gripper_full_open is True,
        "arm_rest": arm_rest_pass is True,
        "contact_signal_complete": all(
            bool(row.get("contact_signal_complete", False))
            for row in contact_rows
        ),
    }
    receipt = {
        "schema_version": FINAL_SCHEMA_VERSION,
        "release_version": RELEASE_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "forensic_output_sha256": FORENSIC_OUTPUT_SHA256,
        "settle_frames": len(values),
        "stable_window_frames": FINAL_STABLE_WINDOW_FRAMES,
        "contact_confirm_frames": CONTACT_CONFIRM_FRAMES,
        "maximum_final_linear_speed_mps": max(linear),
        "maximum_final_angular_speed_rps": max(angular),
        "relation_predicates": relation,
        "thresholds": {
            "final_max_linear_speed_mps": FINAL_MAX_LINEAR_SPEED_MPS,
            "final_max_angular_speed_rps": FINAL_MAX_ANGULAR_SPEED_RPS,
            "verifier_thresholds_changed": False,
        },
        "checks": checks,
        "pass": all(checks.values()),
    }
    receipt["receipt_sha256"] = _canonical_sha256(receipt)
    return receipt


class F2ReleaseSafetyGateV10:
    audit = staticmethod(audit_f2_release_safety_gate_v10)


class F2FinalInsideSuccessGateV10:
    audit = staticmethod(audit_f2_final_inside_success_gate_v10)


__all__ = [
    "F2FinalInsideSuccessGateV10",
    "F2ReleaseSafetyGateV10",
    "FINAL_SETTLE_FRAMES",
    "RELEASE_VERSION",
    "audit_f2_final_inside_success_gate_v10",
    "audit_f2_release_safety_gate_v10",
]
