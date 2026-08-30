"""Pure-CPU F2 revision-6 pre-release settling-window contract.

The gravity-drop inside route remains unchanged.  This contract separates a
short deterministic settling warmup from the existing 50-frame velocity Gate:

* frames 0..9 are warmup and are excluded only from velocity stationarity;
* frames 10..59 are the unchanged 50-frame stationarity window;
* selected-finger contact, actor identity, and unintended body contact are
  checked over all 60 frames;
* opening projection and rim clearance are checked at the final frame.

The module is dependency-light and does not create a scene, query a planner,
execute an action, authorize a GPU probe, or authorize Stage 0.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .runtime_v2_contracts import PROVISIONAL_RUNTIME_THRESHOLDS


SCHEMA_VERSION = "cmf_f2_inside_pre_release_settle_window_v6"
DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_3"
IMPLEMENTATION_PROPOSAL = "f2_inside_10_warmup_plus_final_50_stability_v6"

WARMUP_STEPS = 10
EVALUATED_STABILITY_FRAMES = 50
TOTAL_SETTLE_STEPS = WARMUP_STEPS + EVALUATED_STABILITY_FRAMES
MINIMUM_RIM_CLEARANCE_M = 0.020
STABLE_LINEAR_SPEED_MPS = float(
    PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"]
)
STABLE_ANGULAR_SPEED_RPS = float(
    PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"]
)


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _name_set(values: Sequence[str], *, label: str) -> set[str]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"{label} must be a sequence")
    names = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} contains an invalid name")
        names.append(value)
    if len(names) != len(set(names)):
        raise ValueError(f"{label} contains duplicate names")
    return set(names)


def _velocity(row: Mapping[str, Any], field: str, *, frame_index: int) -> np.ndarray:
    if not isinstance(row, Mapping):
        raise ValueError(f"F2 settle frame {frame_index} is not a mapping")
    value = np.asarray(row.get(field), dtype=np.float64)
    if value.shape != (3,) or not np.all(np.isfinite(value)):
        raise ValueError(
            f"F2 settle frame {frame_index} has invalid {field}"
        )
    return value


def _final_geometry(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("F2 final inside geometry Gate must be a mapping")
    required = {
        "opening_projection_inside",
        "rim_clearance_m",
        "rim_clearance_pass",
        "can_geometry_center_pose",
    }
    if not required.issubset(value):
        raise ValueError(
            "F2 final inside geometry Gate is missing "
            + str(sorted(required - set(value)))
        )
    clearance = float(value["rim_clearance_m"])
    geometry_pose = np.asarray(
        value["can_geometry_center_pose"], dtype=np.float64
    )
    if not np.isfinite(clearance):
        raise ValueError("F2 final rim clearance must be finite")
    if geometry_pose.shape != (7,) or not np.all(np.isfinite(geometry_pose)):
        raise ValueError("F2 final geometry-center pose must be finite shape (7,)")
    return {
        "opening_projection_inside": value["opening_projection_inside"] is True,
        "rim_clearance_m": clearance,
        "rim_clearance_pass_reported": value["rim_clearance_pass"] is True,
        "can_geometry_center_pose": geometry_pose.tolist(),
    }


def audit_f2_inside_pre_release_settle_window_v6(
    rows: Sequence[Mapping[str, Any]],
    *,
    can_actor_name: str,
    selected_contact_signal_link_names: Sequence[str],
    allowed_gripper_assembly_body_names: Sequence[str],
    final_geometry_gate: Mapping[str, Any],
) -> dict[str, Any]:
    """Audit the exact 10-warmup + final-50 F2 inside settle window."""

    frames = list(rows)
    if len(frames) != TOTAL_SETTLE_STEPS:
        raise ValueError(
            f"F2 inside settle Gate requires exactly {TOTAL_SETTLE_STEPS} frames"
        )
    if not isinstance(can_actor_name, str) or not can_actor_name:
        raise ValueError("F2 inside settle Gate requires a can actor name")
    selected_links = _name_set(
        selected_contact_signal_link_names,
        label="selected_contact_signal_link_names",
    )
    assembly_links = _name_set(
        allowed_gripper_assembly_body_names,
        label="allowed_gripper_assembly_body_names",
    )
    if not selected_links or not selected_links.issubset(assembly_links):
        raise ValueError(
            "F2 allowed gripper assembly must contain the selected-contact links"
        )
    if can_actor_name in assembly_links:
        raise ValueError("F2 can actor cannot be an allowed gripper body")

    linear_speeds = []
    angular_speeds = []
    contact_flags = []
    actor_identities = []
    unintended_contacts = []
    for frame_index, row in enumerate(frames):
        linear_speeds.append(
            float(
                np.linalg.norm(
                    _velocity(
                        row,
                        "actor_linear_velocity",
                        frame_index=frame_index,
                    )
                )
            )
        )
        angular_speeds.append(
            float(
                np.linalg.norm(
                    _velocity(
                        row,
                        "actor_angular_velocity",
                        frame_index=frame_index,
                    )
                )
            )
        )
        contact_flags.append(bool(row.get("selected_gripper_contact")))
        actor_identities.append(str(row.get("selected_contact_actor_name")))
        pairs = row.get("contact_pairs")
        if not isinstance(pairs, list):
            raise ValueError(f"F2 settle frame {frame_index} lacks contact_pairs")
        for pair in pairs:
            if not isinstance(pair, Mapping):
                raise ValueError(
                    f"F2 settle frame {frame_index} contains invalid contact evidence"
                )
            bodies = {str(pair.get("body_a")), str(pair.get("body_b"))}
            if can_actor_name not in bodies:
                continue
            collided = sorted(bodies - {can_actor_name} - assembly_links)
            if collided:
                unintended_contacts.append(
                    {
                        "frame_index": frame_index,
                        "window_phase": (
                            "warmup"
                            if frame_index < WARMUP_STEPS
                            else "evaluated_stability"
                        ),
                        "body_a": pair.get("body_a"),
                        "body_b": pair.get("body_b"),
                        "unintended_body_names": collided,
                        "point_count": int(pair.get("point_count", 0)),
                        "impulse_norm_sum": float(
                            pair.get("impulse_norm_sum", 0.0)
                        ),
                    }
                )

    geometry = _final_geometry(final_geometry_gate)
    evaluated_linear = linear_speeds[WARMUP_STEPS:]
    evaluated_angular = angular_speeds[WARMUP_STEPS:]
    warmup_linear = linear_speeds[:WARMUP_STEPS]
    warmup_angular = angular_speeds[:WARMUP_STEPS]
    checks = {
        "exact_10_plus_50_window": len(warmup_linear) == WARMUP_STEPS
        and len(evaluated_linear) == EVALUATED_STABILITY_FRAMES,
        "evaluated_linear_stationary": max(evaluated_linear)
        <= STABLE_LINEAR_SPEED_MPS,
        "evaluated_angular_stationary": max(evaluated_angular)
        <= STABLE_ANGULAR_SPEED_RPS,
        "selected_finger_contact_continuous_all_60": all(contact_flags),
        "selected_actor_identity_all_60": all(
            value == can_actor_name for value in actor_identities
        ),
        "no_unintended_body_contact_all_60": not unintended_contacts,
        "final_opening_projection_inside": geometry[
            "opening_projection_inside"
        ],
        "final_rim_clearance_reported_pass": geometry[
            "rim_clearance_pass_reported"
        ],
        "final_rim_clearance_at_least_20mm": geometry["rim_clearance_m"]
        >= MINIMUM_RIM_CLEARANCE_M,
    }
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_proposal": IMPLEMENTATION_PROPOSAL,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "family": "F2",
        "relation": "inside",
        "can_actor_name": can_actor_name,
        "warmup_steps": WARMUP_STEPS,
        "evaluated_stability_frames": EVALUATED_STABILITY_FRAMES,
        "total_settle_steps": TOTAL_SETTLE_STEPS,
        "warmup_exclusion_scope": "velocity stationarity only",
        "selected_contact_signal_link_names": sorted(selected_links),
        "allowed_gripper_assembly_body_names": sorted(assembly_links),
        "thresholds": {
            "stable_linear_speed_mps": STABLE_LINEAR_SPEED_MPS,
            "stable_angular_speed_rps": STABLE_ANGULAR_SPEED_RPS,
            "minimum_rim_clearance_m": MINIMUM_RIM_CLEARANCE_M,
        },
        "warmup_metrics": {
            "maximum_linear_speed_mps": max(warmup_linear),
            "maximum_angular_speed_rps": max(warmup_angular),
        },
        "evaluated_stability_metrics": {
            "maximum_linear_speed_mps": max(evaluated_linear),
            "maximum_angular_speed_rps": max(evaluated_angular),
        },
        "all_60_contact_identity_evidence": {
            "selected_contact_fraction": float(np.mean(contact_flags)),
            "selected_contact_actor_names": actor_identities,
            "unintended_contacts": unintended_contacts,
        },
        "final_geometry_gate": geometry,
        "checks": checks,
        "pass": all(checks.values()),
    }
    receipt["receipt_sha256"] = _canonical_sha256(receipt)
    return json.loads(
        json.dumps(
            receipt,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
        )
    )


def validate_f2_inside_pre_release_settle_receipt_v6(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate receipt integrity and the frozen 10+50 contract."""

    if not isinstance(receipt, Mapping):
        raise ValueError("F2 settle receipt must be a mapping")
    value = json.loads(
        json.dumps(
            receipt,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
        )
    )
    digest = value.pop("receipt_sha256", None)
    if not isinstance(digest, str) or _canonical_sha256(value) != digest:
        raise ValueError("F2 settle receipt hash mismatch")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("F2 settle receipt schema mismatch")
    if (
        value.get("warmup_steps") != WARMUP_STEPS
        or value.get("evaluated_stability_frames")
        != EVALUATED_STABILITY_FRAMES
        or value.get("total_settle_steps") != TOTAL_SETTLE_STEPS
        or value.get("warmup_exclusion_scope") != "velocity stationarity only"
    ):
        raise ValueError("F2 settle receipt window contract changed")
    if (
        value.get("formal_data") is not False
        or value.get("stage0_data") is not False
        or value.get("stage0_authorized") is not False
    ):
        raise ValueError("F2 settle receipt cannot authorize collection")
    thresholds = value.get("thresholds", {})
    if thresholds != {
        "stable_linear_speed_mps": STABLE_LINEAR_SPEED_MPS,
        "stable_angular_speed_rps": STABLE_ANGULAR_SPEED_RPS,
        "minimum_rim_clearance_m": MINIMUM_RIM_CLEARANCE_M,
    }:
        raise ValueError("F2 settle receipt thresholds changed")
    validated = dict(value)
    validated["receipt_sha256"] = digest
    return validated
