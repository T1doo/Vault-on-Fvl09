"""F2 preload-entry evidence Gate for runtime-v3_4_1.

The old v6 final-like 0.02 m/s and 0.05 rad/s values remain diagnostic, while
the hard pre-partial-open dynamics use the already-approved v10 controller
safety envelope (0.05 m/s, 1.0 rad/s).  Final success thresholds are unchanged.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .f2_inside_pre_release_settle_v6 import (
    EVALUATED_STABILITY_FRAMES,
    MINIMUM_RIM_CLEARANCE_M,
    STABLE_ANGULAR_SPEED_RPS,
    STABLE_LINEAR_SPEED_MPS,
    TOTAL_SETTLE_STEPS,
    WARMUP_STEPS,
)
from .f2_release_gates_v10 import (
    SAFETY_MAX_ANGULAR_SPEED_RPS,
    SAFETY_MAX_LINEAR_SPEED_MPS,
)


SCHEMA_VERSION = "cmf_f2_preload_entry_evidence_gate_v11"
GATE_VERSION = "f2_preload_entry_evidence_then_v10_release_v11"
F2_V10_SOURCE_SHA256 = (
    "6a4910f6da4e6f90fb78083ff675b4ec5a3cfaf0b52fe29495958a7a449310c9"
)


def _sha(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _names(values: Sequence[str], label: str) -> set[str]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{label} must be a sequence")
    result = {str(value) for value in values}
    if not result or len(result) != len(values) or any(not value for value in result):
        raise ValueError(f"{label} is invalid")
    return result


def _speed(row: Mapping[str, Any], field: str, index: int) -> float:
    vector = np.asarray(row.get(field), dtype=np.float64)
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"F2 preload frame {index} has invalid {field}")
    return float(np.linalg.norm(vector))


def audit_f2_preload_entry_evidence_gate_v11(
    rows: Sequence[Mapping[str, Any]],
    *,
    can_actor_name: str,
    selected_contact_signal_link_names: Sequence[str],
    allowed_gripper_assembly_body_names: Sequence[str],
    final_geometry_gate: Mapping[str, Any],
) -> dict[str, Any]:
    frames = list(rows)
    if len(frames) != TOTAL_SETTLE_STEPS:
        raise ValueError("F2 preload entry requires exact 10+50 rows")
    selected = _names(
        selected_contact_signal_link_names,
        "selected_contact_signal_link_names",
    )
    assembly = _names(
        allowed_gripper_assembly_body_names,
        "allowed_gripper_assembly_body_names",
    )
    if not selected.issubset(assembly) or can_actor_name in assembly:
        raise ValueError("F2 preload gripper topology is invalid")
    geometry_required = {
        "opening_projection_inside",
        "rim_clearance_m",
        "rim_clearance_pass",
        "can_geometry_center_pose",
        "geometry_evidence_complete",
    }
    if not isinstance(final_geometry_gate, Mapping) or not geometry_required.issubset(
        final_geometry_gate
    ):
        raise ValueError("F2 preload final geometry evidence is incomplete")
    linear = []
    angular = []
    contact = []
    identities = []
    signal_complete = []
    unintended = []
    for index, row in enumerate(frames):
        linear.append(_speed(row, "actor_linear_velocity", index))
        angular.append(_speed(row, "actor_angular_velocity", index))
        contact.append(row.get("selected_gripper_contact") is True)
        identities.append(str(row.get("selected_contact_actor_name")))
        signal_complete.append(row.get("contact_signal_complete") is True)
        pairs = row.get("contact_pairs")
        if not isinstance(pairs, list):
            raise ValueError("F2 preload row lacks contact_pairs")
        for pair in pairs:
            if not isinstance(pair, Mapping):
                raise ValueError("F2 preload contact pair is invalid")
            bodies = {str(pair.get("body_a")), str(pair.get("body_b"))}
            if can_actor_name not in bodies:
                continue
            collided = sorted(bodies - {can_actor_name} - assembly)
            if collided:
                unintended.append(
                    {
                        "frame_index": index,
                        "body_a": pair.get("body_a"),
                        "body_b": pair.get("body_b"),
                        "unintended_body_names": collided,
                    }
                )
    evaluated_linear = linear[WARMUP_STEPS:]
    evaluated_angular = angular[WARMUP_STEPS:]
    legacy_diagnostic = {
        "linear_at_or_below_final_like_v6_threshold": max(evaluated_linear)
        <= STABLE_LINEAR_SPEED_MPS,
        "angular_at_or_below_final_like_v6_threshold": max(evaluated_angular)
        <= STABLE_ANGULAR_SPEED_RPS,
        "hard_gate": False,
    }
    hard_checks = {
        "exact_10_plus_50_evidence_window": (
            len(linear[:WARMUP_STEPS]) == WARMUP_STEPS
            and len(evaluated_linear) == EVALUATED_STABILITY_FRAMES
        ),
        "contact_signal_complete_all_60": all(signal_complete),
        "selected_finger_contact_continuous_all_60": all(contact),
        "selected_actor_identity_all_60": all(
            value == can_actor_name for value in identities
        ),
        "no_unintended_contact_all_60": not unintended,
        "opening_projection_inside": final_geometry_gate[
            "opening_projection_inside"
        ]
        is True,
        "rim_clearance_reported_pass": final_geometry_gate[
            "rim_clearance_pass"
        ]
        is True,
        "rim_clearance_at_least_20mm": float(
            final_geometry_gate["rim_clearance_m"]
        )
        >= MINIMUM_RIM_CLEARANCE_M,
        "geometry_evidence_complete": final_geometry_gate[
            "geometry_evidence_complete"
        ]
        is True,
        "controller_safety_linear": max(evaluated_linear)
        <= SAFETY_MAX_LINEAR_SPEED_MPS,
        "controller_safety_angular": max(evaluated_angular)
        <= SAFETY_MAX_ANGULAR_SPEED_RPS,
    }
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "gate_version": GATE_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_4_1",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "f2_v10_release_gates_source_sha256": F2_V10_SOURCE_SHA256,
        "v10_release_gate_changed": False,
        "v10_final_gate_changed": False,
        "warmup_steps": WARMUP_STEPS,
        "evaluated_frames": EVALUATED_STABILITY_FRAMES,
        "evaluated_metrics": {
            "maximum_linear_speed_mps": max(evaluated_linear),
            "maximum_angular_speed_rps": max(evaluated_angular),
        },
        "controller_safety_thresholds": {
            "maximum_linear_speed_mps": SAFETY_MAX_LINEAR_SPEED_MPS,
            "maximum_angular_speed_rps": SAFETY_MAX_ANGULAR_SPEED_RPS,
            "source": "approved F2ReleaseSafetyGateV10 envelope",
        },
        "legacy_final_like_diagnostics": {
            **legacy_diagnostic,
            "linear_threshold_mps": STABLE_LINEAR_SPEED_MPS,
            "angular_threshold_rps": STABLE_ANGULAR_SPEED_RPS,
        },
        "unintended_contacts": unintended,
        "final_geometry_gate": dict(final_geometry_gate),
        "checks": hard_checks,
        "pass": all(hard_checks.values()),
    }
    receipt["receipt_sha256"] = _sha(receipt)
    return receipt


__all__ = ["audit_f2_preload_entry_evidence_gate_v11"]
