"""Pure, JSON-safe evidence contract for the F3 pre-shared-V boundary.

The runtime-v3_3 revision-3 controller computed its pre-V gate in memory and
raised before the root orchestrator could save either the gate values or a
partial trace.  This module deliberately contains no SAPIEN/RoboTwin imports.
It turns the already-realized 50-frame hold window, grasp-boundary transforms,
and planner/route metadata into one immutable diagnostic payload that can be
attached to an exception and persisted before scene cleanup.

The eight predicates in :data:`PRE_V_PREDICATE_ORDER` preserve the revision-3
gate exactly.  Free-space bottle/gripper contact is recorded separately so
historical eight-predicate results remain unambiguous; the aggregate ``pass``
requires both the eight predicates and the free-space contact audit.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .f3_clearance_route_v3 import audit_f3_free_space_event_contacts


SCHEMA_VERSION = "cmf_f3_pre_shared_v_evidence_v4"
EXCEPTION_SCHEMA_VERSION = "cmf_f3_pre_shared_v_failure_v4"
HOLD_FRAME_COUNT = 50

PRE_V_BOUNDARY_ORDER = (
    "post_close",
    "post_lift",
    "post_clearance_raise",
    "post_center_high",
    "pre_shared_V",
)

PRE_V_PREDICATE_ORDER = (
    "eef_linear_stationary",
    "eef_angular_stationary",
    "bottle_linear_stationary",
    "bottle_angular_stationary",
    "grasp_translation_stable",
    "grasp_orientation_stable",
    "selected_gripper_contact_continuous",
    "selected_contact_actor_identity",
)

THRESHOLD_KEYS = (
    "eef_linear_speed_mps",
    "eef_angular_speed_rps",
    "bottle_linear_speed_mps",
    "bottle_angular_speed_rps",
    "grasp_translation_drift_m",
    "grasp_orientation_drift_rad",
)

_ROW_VECTOR_FIELDS = (
    "eef_linear_velocity",
    "eef_angular_velocity",
    "actor_linear_velocity",
    "actor_angular_velocity",
)


def _json_safe(value: Any, *, path: str = "value") -> Any:
    """Return a deterministic JSON-compatible deep copy.

    NumPy arrays/scalars are accepted because runtime trace rows use them.
    Non-finite floats and non-string mapping keys are rejected instead of
    being silently emitted as non-standard JSON ``NaN``/``Infinity`` tokens.
    """

    if value is None or isinstance(value, str):
        return value
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise ValueError(f"{path} must be finite")
        return result
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist(), path=path)
    if isinstance(value, Mapping):
        output = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} mapping keys must be strings")
            output[key] = _json_safe(item, path=f"{path}.{key}")
        return output
    if isinstance(value, (list, tuple)):
        return [
            _json_safe(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    raise TypeError(f"{path} contains unsupported type {type(value).__name__}")


def canonical_json_sha256(value: Any) -> str:
    """Hash a value after strict JSON-safe normalization."""

    normalized = _json_safe(value)
    return hashlib.sha256(
        json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _finite_vector(value: Any, *, shape: tuple[int, ...], label: str) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must be one finite array with shape {shape}")
    return np.ascontiguousarray(array)


def _finite_nonnegative_thresholds(thresholds: Mapping[str, Any]) -> dict[str, float]:
    if not isinstance(thresholds, Mapping) or set(thresholds) != set(THRESHOLD_KEYS):
        raise ValueError(f"thresholds must contain exactly {THRESHOLD_KEYS}")
    output = {}
    for key in THRESHOLD_KEYS:
        try:
            value = float(thresholds[key])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"thresholds.{key} must be numeric") from exc
        if not np.isfinite(value) or value < 0.0:
            raise ValueError(f"thresholds.{key} must be finite and nonnegative")
        output[key] = value
    return output


def _quaternion_angular_error(left: np.ndarray, right: np.ndarray) -> float:
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    if left_norm <= 1e-12 or right_norm <= 1e-12:
        raise ValueError("boundary quaternion must be nonzero")
    dot = float(np.dot(left / left_norm, right / right_norm))
    return float(2.0 * np.arccos(np.clip(abs(dot), -1.0, 1.0)))


def _normalize_boundaries(
    boundary_transforms: Mapping[str, Sequence[float]],
    *,
    translation_limit_m: float,
    orientation_limit_rad: float,
) -> dict:
    if not isinstance(boundary_transforms, Mapping) or set(
        boundary_transforms
    ) != set(PRE_V_BOUNDARY_ORDER):
        raise ValueError(
            "boundary_transforms must contain exactly the pre-V boundaries"
        )
    transforms = {
        name: _finite_vector(
            boundary_transforms[name], shape=(7,), label=f"boundary.{name}"
        )
        for name in PRE_V_BOUNDARY_ORDER
    }
    for name, transform in transforms.items():
        if float(np.linalg.norm(transform[3:])) <= 1e-12:
            raise ValueError(f"boundary.{name} quaternion must be nonzero")

    baseline = transforms["post_close"]
    per_boundary = {}
    for name in PRE_V_BOUNDARY_ORDER:
        transform = transforms[name]
        translation = float(np.linalg.norm(transform[:3] - baseline[:3]))
        orientation = _quaternion_angular_error(transform[3:], baseline[3:])
        per_boundary[name] = {
            "transform_t_eef_actor": transform.tolist(),
            "translation_drift_m": translation,
            "orientation_drift_rad": orientation,
            "translation_pass": translation <= translation_limit_m,
            "orientation_pass": orientation <= orientation_limit_rad,
        }

    return {
        "baseline_boundary": "post_close",
        "boundary_order": list(PRE_V_BOUNDARY_ORDER),
        "translation_drift_limit_m": translation_limit_m,
        "orientation_drift_limit_rad": orientation_limit_rad,
        "per_boundary": per_boundary,
        "maximum_translation_drift_m": max(
            item["translation_drift_m"] for item in per_boundary.values()
        ),
        "maximum_orientation_drift_rad": max(
            item["orientation_drift_rad"] for item in per_boundary.values()
        ),
    }


def _normalize_hold_rows(hold_rows: Sequence[Mapping[str, Any]]) -> dict:
    if isinstance(hold_rows, (str, bytes)) or not isinstance(hold_rows, Sequence):
        raise TypeError("hold_rows must be a sequence of trace-row mappings")
    if len(hold_rows) != HOLD_FRAME_COUNT:
        raise ValueError(f"hold_rows must contain exactly {HOLD_FRAME_COUNT} frames")

    frames = []
    contact_frames = []
    for frame_index, raw_row in enumerate(hold_rows):
        if not isinstance(raw_row, Mapping):
            raise TypeError(f"hold_rows[{frame_index}] must be a mapping")
        vectors = {
            field: _finite_vector(
                raw_row.get(field),
                shape=(3,),
                label=f"hold_rows[{frame_index}].{field}",
            )
            for field in _ROW_VECTOR_FIELDS
        }
        contact_value = raw_row.get("selected_gripper_contact")
        if not isinstance(contact_value, (bool, np.bool_)):
            raise TypeError(
                f"hold_rows[{frame_index}].selected_gripper_contact must be bool"
            )
        actor_name = raw_row.get("selected_contact_actor_name")
        if not isinstance(actor_name, str):
            raise TypeError(
                f"hold_rows[{frame_index}].selected_contact_actor_name must be str"
            )
        contact_pairs = _json_safe(
            raw_row.get("contact_pairs"),
            path=f"hold_rows[{frame_index}].contact_pairs",
        )
        if not isinstance(contact_pairs, list):
            raise TypeError(
                f"hold_rows[{frame_index}].contact_pairs must be a sequence"
            )
        contact_frames.append(contact_pairs)

        frame = {
            "frame_index": frame_index,
            "step_index": _json_safe(
                raw_row.get("step_index"),
                path=f"hold_rows[{frame_index}].step_index",
            ),
            "timestamp": _json_safe(
                raw_row.get("timestamp"),
                path=f"hold_rows[{frame_index}].timestamp",
            ),
            "eef_linear_velocity_mps": vectors["eef_linear_velocity"].tolist(),
            "eef_angular_velocity_rps": vectors["eef_angular_velocity"].tolist(),
            "bottle_linear_velocity_mps": vectors["actor_linear_velocity"].tolist(),
            "bottle_angular_velocity_rps": vectors["actor_angular_velocity"].tolist(),
            "eef_linear_speed_mps": float(
                np.linalg.norm(vectors["eef_linear_velocity"])
            ),
            "eef_angular_speed_rps": float(
                np.linalg.norm(vectors["eef_angular_velocity"])
            ),
            "bottle_linear_speed_mps": float(
                np.linalg.norm(vectors["actor_linear_velocity"])
            ),
            "bottle_angular_speed_rps": float(
                np.linalg.norm(vectors["actor_angular_velocity"])
            ),
            "selected_gripper_contact": bool(contact_value),
            "selected_contact_actor_name": actor_name,
            "contact_pairs": contact_pairs,
        }
        frames.append(frame)

    maxima = {
        "maximum_eef_linear_speed_mps": max(
            frame["eef_linear_speed_mps"] for frame in frames
        ),
        "maximum_eef_angular_speed_rps": max(
            frame["eef_angular_speed_rps"] for frame in frames
        ),
        "maximum_bottle_linear_speed_mps": max(
            frame["bottle_linear_speed_mps"] for frame in frames
        ),
        "maximum_bottle_angular_speed_rps": max(
            frame["bottle_angular_speed_rps"] for frame in frames
        ),
    }
    return {
        "frame_count": len(frames),
        "frames": frames,
        "contact_frames": contact_frames,
        **maxima,
    }


def build_f3_pre_v_evidence_v4(
    *,
    hold_rows: Sequence[Mapping[str, Any]],
    boundary_transforms: Mapping[str, Sequence[float]],
    thresholds: Mapping[str, Any],
    expected_actor_name: str,
    selected_gripper_link_names: Sequence[str],
    support_actor_names: Sequence[str],
    planner_metadata: Mapping[str, Any],
    route_metadata: Mapping[str, Any],
) -> dict:
    """Build one immutable pre-V evidence payload from realized state."""

    if not isinstance(expected_actor_name, str) or not expected_actor_name:
        raise ValueError("expected_actor_name must be a nonempty string")
    gripper_names = _json_safe(
        selected_gripper_link_names, path="selected_gripper_link_names"
    )
    support_names = _json_safe(support_actor_names, path="support_actor_names")
    if (
        not isinstance(gripper_names, list)
        or not gripper_names
        or not all(isinstance(name, str) and name for name in gripper_names)
    ):
        raise ValueError("selected_gripper_link_names must be nonempty strings")
    if len(set(gripper_names)) != len(gripper_names):
        raise ValueError("selected_gripper_link_names must be unique")
    if (
        not isinstance(support_names, list)
        or not support_names
        or not all(isinstance(name, str) and name for name in support_names)
    ):
        raise ValueError("support_actor_names must be nonempty strings")
    if len(set(support_names)) != len(support_names):
        raise ValueError("support_actor_names must be unique")
    if not isinstance(planner_metadata, Mapping):
        raise TypeError("planner_metadata must be a mapping")
    if not isinstance(route_metadata, Mapping):
        raise TypeError("route_metadata must be a mapping")

    normalized_thresholds = _finite_nonnegative_thresholds(thresholds)
    hold = _normalize_hold_rows(hold_rows)
    boundaries = _normalize_boundaries(
        boundary_transforms,
        translation_limit_m=normalized_thresholds[
            "grasp_translation_drift_m"
        ],
        orientation_limit_rad=normalized_thresholds[
            "grasp_orientation_drift_rad"
        ],
    )
    contact_audit = audit_f3_free_space_event_contacts(
        hold["contact_frames"],
        bottle_actor_name=expected_actor_name,
        selected_gripper_link_names=gripper_names,
        support_actor_names=support_names,
    )
    contact_audit = _json_safe(contact_audit, path="free_space_contact_audit")

    predicates = {
        "eef_linear_stationary": hold["maximum_eef_linear_speed_mps"]
        <= normalized_thresholds["eef_linear_speed_mps"],
        "eef_angular_stationary": hold["maximum_eef_angular_speed_rps"]
        <= normalized_thresholds["eef_angular_speed_rps"],
        "bottle_linear_stationary": hold["maximum_bottle_linear_speed_mps"]
        <= normalized_thresholds["bottle_linear_speed_mps"],
        "bottle_angular_stationary": hold["maximum_bottle_angular_speed_rps"]
        <= normalized_thresholds["bottle_angular_speed_rps"],
        "grasp_translation_stable": boundaries[
            "maximum_translation_drift_m"
        ]
        <= normalized_thresholds["grasp_translation_drift_m"],
        "grasp_orientation_stable": boundaries[
            "maximum_orientation_drift_rad"
        ]
        <= normalized_thresholds["grasp_orientation_drift_rad"],
        "selected_gripper_contact_continuous": all(
            frame["selected_gripper_contact"] for frame in hold["frames"]
        ),
        "selected_contact_actor_identity": all(
            frame["selected_contact_actor_name"] == expected_actor_name
            for frame in hold["frames"]
        ),
    }
    predicates = {name: bool(predicates[name]) for name in PRE_V_PREDICATE_ORDER}
    failed_predicates = [name for name, passed in predicates.items() if not passed]
    supplemental_contact_checks = {
        "bottle_has_no_pad_or_table_contact": bool(
            contact_audit["checks"]["bottle_has_no_pad_or_table_contact"]
        ),
        "selected_gripper_has_no_pad_or_table_contact": bool(
            contact_audit["checks"][
                "selected_gripper_has_no_pad_or_table_contact"
            ]
        ),
    }
    failed_supplemental_checks = [
        name for name, passed in supplemental_contact_checks.items() if not passed
    ]

    hold_payload = dict(hold)
    hold_payload.pop("contact_frames")
    normalized_planner = _json_safe(planner_metadata, path="planner_metadata")
    normalized_route = _json_safe(route_metadata, path="route_metadata")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "hold_frame_count_required": HOLD_FRAME_COUNT,
        "expected_actor_name": expected_actor_name,
        "selected_gripper_link_names": gripper_names,
        "support_actor_names": support_names,
        "thresholds": normalized_thresholds,
        "predicate_order": list(PRE_V_PREDICATE_ORDER),
        "predicates": predicates,
        "failed_predicates": failed_predicates,
        "eight_predicate_pass": not failed_predicates,
        "supplemental_contact_checks": supplemental_contact_checks,
        "failed_supplemental_checks": failed_supplemental_checks,
        "free_space_contact_pass": bool(contact_audit["pass"]),
        "hold_window": hold_payload,
        "grasp_boundaries": boundaries,
        "free_space_contact_audit": contact_audit,
        "planner_metadata": normalized_planner,
        "planner_metadata_sha256": canonical_json_sha256(normalized_planner),
        "route_metadata": normalized_route,
        "route_metadata_sha256": canonical_json_sha256(normalized_route),
        "pass": not failed_predicates and not failed_supplemental_checks,
    }
    payload = _json_safe(payload, path="evidence")
    payload["evidence_sha256"] = canonical_json_sha256(payload)
    return validate_f3_pre_v_evidence_v4(payload)


def validate_f3_pre_v_evidence_v4(evidence: Mapping[str, Any]) -> dict:
    """Validate integrity and internal Gate bookkeeping; return a deep copy."""

    if not isinstance(evidence, Mapping):
        raise TypeError("F3 pre-V evidence must be a mapping")
    normalized = _json_safe(evidence, path="evidence")
    if normalized.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("F3 pre-V evidence schema_version mismatch")
    expected_hash = normalized.get("evidence_sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise ValueError("F3 pre-V evidence has no valid evidence_sha256")
    unhashed = dict(normalized)
    unhashed.pop("evidence_sha256")
    if canonical_json_sha256(unhashed) != expected_hash:
        raise ValueError("F3 pre-V evidence hash mismatch")
    if normalized.get("predicate_order") != list(PRE_V_PREDICATE_ORDER):
        raise ValueError("F3 pre-V predicate order mismatch")
    predicates = normalized.get("predicates")
    if not isinstance(predicates, Mapping) or set(predicates) != set(
        PRE_V_PREDICATE_ORDER
    ):
        raise ValueError("F3 pre-V evidence must contain exactly eight predicates")
    if any(not isinstance(predicates[name], bool) for name in PRE_V_PREDICATE_ORDER):
        raise TypeError("F3 pre-V predicates must be bool")
    failed = [name for name in PRE_V_PREDICATE_ORDER if not predicates[name]]
    if normalized.get("failed_predicates") != failed:
        raise ValueError("F3 pre-V failed_predicates is inconsistent")
    if normalized.get("eight_predicate_pass") is not (not failed):
        raise ValueError("F3 pre-V eight_predicate_pass is inconsistent")
    hold = normalized.get("hold_window")
    if (
        not isinstance(hold, Mapping)
        or hold.get("frame_count") != HOLD_FRAME_COUNT
        or not isinstance(hold.get("frames"), list)
        or len(hold["frames"]) != HOLD_FRAME_COUNT
    ):
        raise ValueError("F3 pre-V evidence does not contain exactly 50 hold frames")
    boundaries = normalized.get("grasp_boundaries")
    if (
        not isinstance(boundaries, Mapping)
        or boundaries.get("boundary_order") != list(PRE_V_BOUNDARY_ORDER)
        or not isinstance(boundaries.get("per_boundary"), Mapping)
        or set(boundaries["per_boundary"]) != set(PRE_V_BOUNDARY_ORDER)
    ):
        raise ValueError("F3 pre-V boundary evidence is incomplete")
    supplemental = normalized.get("supplemental_contact_checks")
    if not isinstance(supplemental, Mapping) or set(supplemental) != {
        "bottle_has_no_pad_or_table_contact",
        "selected_gripper_has_no_pad_or_table_contact",
    }:
        raise ValueError("F3 pre-V supplemental contact checks are incomplete")
    if any(not isinstance(value, bool) for value in supplemental.values()):
        raise TypeError("F3 pre-V supplemental contact checks must be bool")
    supplemental_failed = [
        name for name, passed in supplemental.items() if not passed
    ]
    if normalized.get("failed_supplemental_checks") != supplemental_failed:
        raise ValueError("F3 pre-V failed_supplemental_checks is inconsistent")
    expected_pass = not failed and not supplemental_failed
    if normalized.get("pass") is not expected_pass:
        raise ValueError("F3 pre-V aggregate pass is inconsistent")
    if normalized.get("free_space_contact_pass") is not (
        not supplemental_failed
    ):
        raise ValueError("F3 pre-V free_space_contact_pass is inconsistent")
    # Prove that the validated value remains strict standard JSON.
    json.dumps(normalized, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return deepcopy(normalized)


class F3PreVBoundaryGateFailure(RuntimeError):
    """Failure carrying immutable evidence for persistence before cleanup."""

    def __init__(self, evidence: Mapping[str, Any]):
        validated = validate_f3_pre_v_evidence_v4(evidence)
        if validated["pass"] is True:
            raise ValueError("cannot raise F3 pre-V failure for passing evidence")
        # A strict JSON round trip prevents callers from mutating NumPy-backed
        # or shared nested objects after the exception is constructed.
        self.evidence = json.loads(
            json.dumps(validated, ensure_ascii=False, allow_nan=False)
        )
        self.failed_predicates = tuple(self.evidence["failed_predicates"])
        self.failed_supplemental_checks = tuple(
            self.evidence["failed_supplemental_checks"]
        )
        failed = [*self.failed_predicates, *self.failed_supplemental_checks]
        super().__init__(
            "F3 pre-shared-V stationary/grasp boundary Gate failed: "
            + ", ".join(failed)
        )

    def to_receipt(self) -> dict:
        payload = {
            "schema_version": EXCEPTION_SCHEMA_VERSION,
            "error_type": type(self).__name__,
            "message": str(self),
            "failed_predicates": list(self.failed_predicates),
            "failed_supplemental_checks": list(
                self.failed_supplemental_checks
            ),
            "evidence": deepcopy(self.evidence),
        }
        payload["failure_receipt_sha256"] = canonical_json_sha256(payload)
        return payload


def require_f3_pre_v_gate(evidence: Mapping[str, Any]) -> dict:
    """Return validated passing evidence or raise its structured failure."""

    validated = validate_f3_pre_v_evidence_v4(evidence)
    if validated["pass"] is not True:
        raise F3PreVBoundaryGateFailure(validated)
    return validated


__all__ = [
    "EXCEPTION_SCHEMA_VERSION",
    "F3PreVBoundaryGateFailure",
    "HOLD_FRAME_COUNT",
    "PRE_V_BOUNDARY_ORDER",
    "PRE_V_PREDICATE_ORDER",
    "SCHEMA_VERSION",
    "THRESHOLD_KEYS",
    "build_f3_pre_v_evidence_v4",
    "canonical_json_sha256",
    "require_f3_pre_v_gate",
    "validate_f3_pre_v_evidence_v4",
]
