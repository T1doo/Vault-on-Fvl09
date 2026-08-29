"""Pure contracts for the proposed F3 clearance-carry revision.

This module deliberately has no SAPIEN or RoboTwin task imports.  It freezes
the geometry, grasp-selection, time-dilation, and verifier-side predicates
needed by a future runner integration without authorizing or launching that
integration.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np


SCHEMA_VERSION = "cmf_f3_clearance_route_v3"
CLEARANCE_AUDIT_SCHEMA_VERSION = "cmf_f3_clearance_height_audit_v1"
GRASP_CONTRACT_VERSION = "f3_frozen_official_contact3_candidate0_v1"
CARRY_ROUTE_VERSION = "f3_clearance_segmented_slow_carry_v3"
TIME_DILATION_VERSION = "f3_carry_control_linear_time_dilation_2x_v1"
CONTACT_AUDIT_VERSION = "f3_free_space_event_contact_audit_v1"
GRASP_BOUNDARY_AUDIT_VERSION = "f3_grasp_boundary_stability_audit_v1"

FROZEN_ARM = "left"
FROZEN_BOTTLE = {"modelname": "001_bottle", "model_id": 13}
FROZEN_CONTACT_POINT_ID = 3
FROZEN_ROTATION_CANDIDATE_INDEX = 0
FROZEN_PREGRASP_DISTANCE_M = 0.09
FROZEN_TARGET_DISTANCE_M = 0.0

F3_V_NOMINAL_AMPLITUDE_M = 0.055
F3_H_NOMINAL_AMPLITUDE_M = 0.050
F3_PROGRAMS = ("VVHH", "VHVH", "VHHV")
F3_SHARED_FIRST_EVENT = "V"

F3_CENTRAL_XY_M = (-0.08, -0.05)
F3_PAD_HALF_EXTENTS_M = (0.11, 0.145, 0.005)
F3_FROZEN_CLEARANCE_M = 0.030
F3_CENTRAL_HOLD_STEPS = 50
F3_CARRY_TIME_DILATION_FACTOR = 2

F3_GRASP_TRANSLATION_DRIFT_LIMIT_M = 0.005
F3_GRASP_ORIENTATION_DRIFT_LIMIT_RAD = 0.050
F3_GRASP_BOUNDARIES = (
    "post_close",
    "post_lift",
    "post_clearance_raise",
    "post_center_high",
    "pre_shared_V",
    "post_shared_V",
    "acceptance_end",
)

F3_SUPPORT_ACTOR_NAMES = ("table", "f3_original_pad")
F3_SELECTED_GRIPPER_LINK_NAMES = ("fl_link7", "fl_link8")
F3_BOTTLE_ACTOR_NAME = "f3_main_bottle"


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _finite_scalar(value: Any, *, label: str) -> float:
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def frozen_f3_grasp_contract() -> dict:
    """Return the immutable, no-fallback official grasp-selection contract."""

    payload = {
        "schema_version": "cmf_f3_frozen_grasp_contract_v1",
        "contract_version": GRASP_CONTRACT_VERSION,
        "arm": FROZEN_ARM,
        "asset": dict(FROZEN_BOTTLE),
        "contact_point_id": FROZEN_CONTACT_POINT_ID,
        "rotation_candidate_index": FROZEN_ROTATION_CANDIDATE_INDEX,
        "pregrasp_distance_m": FROZEN_PREGRASP_DISTANCE_M,
        "target_distance_m": FROZEN_TARGET_DISTANCE_M,
        "official_source": "Base_Task.get_grasp_pose + Robot.create_target_pose_list",
        "selection_rule": (
            "use exactly official contact point 3 and rotation candidate 0; "
            "require that candidate to be planner-successful; fail without fallback"
        ),
        "fallback_allowed": False,
        "automatic_retry": False,
    }
    payload["contract_sha256"] = _canonical_sha256(payload)
    return payload


def build_f3_clearance_height_audit(
    *,
    table_top_z_m: float,
    pad_top_z_m: float,
    post_lift_eef_z_m: float,
    bottle_below_eef_m: float,
    gripper_below_eef_m: float,
) -> dict:
    """Compute the minimum central EEF height for a collision-free -V endpoint.

    The compound held envelope is the larger downward extent of the bottle and
    the selected gripper.  The selected height is never allowed below the
    already-realized post-lift EEF height.
    """

    table_top = _finite_scalar(table_top_z_m, label="table_top_z_m")
    pad_top = _finite_scalar(pad_top_z_m, label="pad_top_z_m")
    post_lift = _finite_scalar(post_lift_eef_z_m, label="post_lift_eef_z_m")
    bottle_below = _finite_scalar(
        bottle_below_eef_m, label="bottle_below_eef_m"
    )
    gripper_below = _finite_scalar(
        gripper_below_eef_m, label="gripper_below_eef_m"
    )
    if bottle_below < 0 or gripper_below < 0:
        raise ValueError("held-envelope distances must be nonnegative")

    support_top = max(table_top, pad_top)
    compound_below = max(bottle_below, gripper_below)
    geometry_required = (
        support_top
        + F3_V_NOMINAL_AMPLITUDE_M
        + compound_below
        + F3_FROZEN_CLEARANCE_M
    )
    selected = max(post_lift, geometry_required)
    negative_endpoint = selected - F3_V_NOMINAL_AMPLITUDE_M
    predicted_lowest = negative_endpoint - compound_below
    achieved_clearance = predicted_lowest - support_top
    checks = {
        "selected_height_not_below_post_lift": selected >= post_lift,
        "negative_v_compound_envelope_clear": achieved_clearance
        >= F3_FROZEN_CLEARANCE_M - 1e-12,
        "v_amplitude_unchanged": F3_V_NOMINAL_AMPLITUDE_M == 0.055,
        "clearance_positive": F3_FROZEN_CLEARANCE_M > 0,
    }
    return {
        "schema_version": CLEARANCE_AUDIT_SCHEMA_VERSION,
        "route_version": CARRY_ROUTE_VERSION,
        "table_top_z_m": table_top,
        "pad_top_z_m": pad_top,
        "support_top_z_m": support_top,
        "post_lift_eef_z_m": post_lift,
        "bottle_below_eef_m": bottle_below,
        "gripper_below_eef_m": gripper_below,
        "compound_below_eef_m": compound_below,
        "v_nominal_amplitude_m": F3_V_NOMINAL_AMPLITUDE_M,
        "frozen_clearance_m": F3_FROZEN_CLEARANCE_M,
        "geometry_required_central_eef_z_m": geometry_required,
        "selected_central_eef_z_m": selected,
        "negative_v_endpoint_eef_z_m": negative_endpoint,
        "predicted_compound_lowest_z_m": predicted_lowest,
        "predicted_achieved_clearance_m": achieved_clearance,
        "checks": checks,
        "pass": all(checks.values()),
    }


def build_f3_clearance_route_targets(
    post_lift_eef_pose: Sequence[float],
    clearance_audit: Mapping[str, Any],
) -> dict:
    """Build the exact raise-then-horizontal carry route and hold contract."""

    pose = np.asarray(post_lift_eef_pose, dtype=np.float64)
    if pose.shape != (7,) or not np.all(np.isfinite(pose)):
        raise ValueError("post_lift_eef_pose must be one finite 7-D pose")
    if float(np.linalg.norm(pose[3:])) <= 1e-12:
        raise ValueError("post_lift_eef_pose quaternion must be nonzero")
    if (
        not isinstance(clearance_audit, Mapping)
        or clearance_audit.get("schema_version") != CLEARANCE_AUDIT_SCHEMA_VERSION
        or clearance_audit.get("pass") is not True
    ):
        raise ValueError("clearance route requires a passing clearance audit")
    selected_z = _finite_scalar(
        clearance_audit.get("selected_central_eef_z_m"),
        label="selected_central_eef_z_m",
    )
    if selected_z + 1e-12 < float(pose[2]):
        raise ValueError("clearance route may not descend from post-lift")

    clearance_raise = pose.copy()
    clearance_raise[2] = selected_z
    center_high = clearance_raise.copy()
    center_high[:2] = np.asarray(F3_CENTRAL_XY_M, dtype=np.float64)
    segments = [
        {
            "segment_id": "f3_prefix_clearance_raise",
            "pose": clearance_raise.tolist(),
            "time_dilation_factor": 1,
        },
        {
            "segment_id": "f3_prefix_center_high",
            "pose": center_high.tolist(),
            "time_dilation_factor": F3_CARRY_TIME_DILATION_FACTOR,
        },
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "route_version": CARRY_ROUTE_VERSION,
        "grasp_contract_sha256": frozen_f3_grasp_contract()["contract_sha256"],
        "arm": FROZEN_ARM,
        "route_order": [item["segment_id"] for item in segments],
        "segments": segments,
        "central_xy_m": list(F3_CENTRAL_XY_M),
        "central_hold_steps": F3_CENTRAL_HOLD_STEPS,
        "central_hold_is_minimum_stationary_confirmation": True,
        "shared_first_event": F3_SHARED_FIRST_EVENT,
        "v_nominal_amplitude_m": F3_V_NOMINAL_AMPLITUDE_M,
        "h_nominal_amplitude_m": F3_H_NOMINAL_AMPLITUDE_M,
        "programs": list(F3_PROGRAMS),
        "checks": {
            "raise_keeps_xy": bool(
                np.array_equal(clearance_raise[:2], pose[:2])
            ),
            "raise_keeps_orientation": bool(
                np.array_equal(clearance_raise[3:], pose[3:])
            ),
            "center_high_keeps_orientation": bool(
                np.array_equal(center_high[3:], pose[3:])
            ),
            "route_never_descends": bool(
                clearance_raise[2] >= pose[2]
                and center_high[2] >= clearance_raise[2]
            ),
            "horizontal_segment_has_constant_z": bool(
                center_high[2] == clearance_raise[2]
            ),
        },
    }
    payload["pass"] = all(payload["checks"].values())
    payload["route_sha256"] = _canonical_sha256(payload)
    return payload


def _interleave_midpoints(values: np.ndarray) -> np.ndarray:
    output = np.empty(
        (2 * values.shape[0] - 1, *values.shape[1:]), dtype=values.dtype
    )
    output[0::2] = values
    output[1::2] = (values[:-1] + values[1:]) / np.asarray(
        2.0, dtype=values.dtype
    )
    return output


def time_dilate_f3_carry_control_2x(control: Mapping[str, Any]) -> dict:
    """Linearly time-dilate one successful planner control at fixed 250 Hz."""

    if not isinstance(control, Mapping) or control.get("status") != "Success":
        raise ValueError("F3 carry time dilation requires a successful control")
    if "position" not in control or "velocity" not in control:
        raise ValueError("F3 carry control requires position and velocity")

    normalized = deepcopy(dict(control))
    arrays: dict[str, np.ndarray] = {}
    step_count = None
    for field in ("position", "velocity", "acceleration", "jerk"):
        if field not in normalized or normalized[field] is None:
            continue
        raw = np.asarray(normalized[field])
        if raw.ndim < 1 or raw.shape[0] < 2 or not np.issubdtype(
            raw.dtype, np.floating
        ):
            raise ValueError(f"F3 carry control {field} must be a floating [N,...] array")
        if not np.all(np.isfinite(raw)):
            raise ValueError(f"F3 carry control {field} contains non-finite values")
        if step_count is None:
            step_count = raw.shape[0]
        elif raw.shape[0] != step_count:
            raise ValueError("F3 carry control arrays must share the same step count")
        arrays[field] = np.ascontiguousarray(raw)
    if step_count is None:
        raise ValueError("F3 carry control has no numeric arrays")

    derivative_order = {"position": 0, "velocity": 1, "acceleration": 2, "jerk": 3}
    scales = {}
    for field, raw in arrays.items():
        scale = float(F3_CARRY_TIME_DILATION_FACTOR ** derivative_order[field])
        dilated = _interleave_midpoints(raw)
        if scale != 1.0:
            dilated = np.ascontiguousarray(
                dilated / np.asarray(scale, dtype=dilated.dtype)
            )
        normalized[field] = dilated
        scales[field] = 1.0 / scale

    output_steps = 2 * int(step_count) - 1
    if not np.array_equal(normalized["position"][0], arrays["position"][0]) or not np.array_equal(
        normalized["position"][-1], arrays["position"][-1]
    ):
        raise RuntimeError("F3 carry time dilation changed a position endpoint")
    normalized["_cmf_time_dilation"] = {
        "version": TIME_DILATION_VERSION,
        "factor": F3_CARRY_TIME_DILATION_FACTOR,
        "input_step_count": int(step_count),
        "output_step_count": output_steps,
        "fixed_frequency_hz": 250,
        "field_scales": scales,
        "position_endpoints_preserved_exactly": True,
    }
    return normalized


def audit_f3_free_space_event_contacts(
    contact_frames: Sequence[Sequence[Mapping[str, Any]]],
    *,
    bottle_actor_name: str = F3_BOTTLE_ACTOR_NAME,
    selected_gripper_link_names: Sequence[str] = F3_SELECTED_GRIPPER_LINK_NAMES,
    support_actor_names: Sequence[str] = F3_SUPPORT_ACTOR_NAMES,
) -> dict:
    """Reject bottle/support or selected-gripper/support contact in a V/H event."""

    frames = list(contact_frames)
    if not frames:
        raise ValueError("F3 event contact audit requires at least one frame")
    bottle = str(bottle_actor_name)
    grippers = {str(name) for name in selected_gripper_link_names}
    supports = {str(name) for name in support_actor_names}
    if not bottle or not grippers or not supports:
        raise ValueError("F3 contact role sets must be nonempty")

    bottle_hits = []
    gripper_hits = []
    for frame_index, pairs in enumerate(frames):
        if not isinstance(pairs, Sequence) or isinstance(pairs, (str, bytes)):
            raise ValueError("each F3 contact frame must be a sequence of pairs")
        for pair_index, pair in enumerate(pairs):
            if not isinstance(pair, Mapping):
                raise ValueError("each F3 contact pair must be a mapping")
            body_a = pair.get("body_a")
            body_b = pair.get("body_b")
            if not isinstance(body_a, str) or not isinstance(body_b, str):
                raise ValueError("F3 contact pair body names must be strings")
            bodies = {body_a, body_b}
            support = sorted(bodies & supports)
            evidence = {
                "frame_index": frame_index,
                "pair_index": pair_index,
                "body_a": body_a,
                "body_b": body_b,
                "support_actor_names": support,
                "point_count": int(pair.get("point_count", 0)),
                "impulse_norm_sum": float(pair.get("impulse_norm_sum", 0.0)),
            }
            if support and bottle in bodies:
                bottle_hits.append(evidence)
            if support and bodies & grippers:
                gripper_hits.append(evidence)

    checks = {
        "bottle_has_no_pad_or_table_contact": not bottle_hits,
        "selected_gripper_has_no_pad_or_table_contact": not gripper_hits,
    }
    return {
        "schema_version": CONTACT_AUDIT_VERSION,
        "frame_count": len(frames),
        "bottle_actor_name": bottle,
        "selected_gripper_link_names": sorted(grippers),
        "support_actor_names": sorted(supports),
        "bottle_support_contacts": bottle_hits,
        "selected_gripper_support_contacts": gripper_hits,
        "first_bottle_support_contact_frame": (
            bottle_hits[0]["frame_index"] if bottle_hits else None
        ),
        "first_selected_gripper_support_contact_frame": (
            gripper_hits[0]["frame_index"] if gripper_hits else None
        ),
        "checks": checks,
        "pass": all(checks.values()),
    }


def _quaternion_angular_error(left: np.ndarray, right: np.ndarray) -> float:
    norm_left = float(np.linalg.norm(left))
    norm_right = float(np.linalg.norm(right))
    if norm_left <= 1e-12 or norm_right <= 1e-12:
        raise ValueError("F3 grasp-boundary quaternion must be nonzero")
    dot = float(np.dot(left / norm_left, right / norm_right))
    return float(2.0 * np.arccos(np.clip(abs(dot), -1.0, 1.0)))


def audit_f3_grasp_boundary_stability(
    boundary_transforms: Mapping[str, Sequence[float]],
) -> dict:
    """Evaluate every frozen T_eef_actor boundary against post-close."""

    if not isinstance(boundary_transforms, Mapping) or set(boundary_transforms) != set(
        F3_GRASP_BOUNDARIES
    ):
        raise ValueError("F3 grasp-boundary audit requires exactly the frozen boundaries")
    transforms = {}
    for name in F3_GRASP_BOUNDARIES:
        value = np.asarray(boundary_transforms[name], dtype=np.float64)
        if value.shape != (7,) or not np.all(np.isfinite(value)):
            raise ValueError(f"F3 grasp boundary {name} must be one finite 7-D pose")
        if float(np.linalg.norm(value[3:])) <= 1e-12:
            raise ValueError(f"F3 grasp boundary {name} has a zero quaternion")
        transforms[name] = value

    baseline = transforms["post_close"]
    translation = {
        name: float(np.linalg.norm(value[:3] - baseline[:3]))
        for name, value in transforms.items()
    }
    orientation = {
        name: _quaternion_angular_error(value[3:], baseline[3:])
        for name, value in transforms.items()
    }
    per_boundary = {
        name: {
            "translation_drift_m": translation[name],
            "orientation_drift_rad": orientation[name],
            "translation_pass": translation[name]
            <= F3_GRASP_TRANSLATION_DRIFT_LIMIT_M,
            "orientation_pass": orientation[name]
            <= F3_GRASP_ORIENTATION_DRIFT_LIMIT_RAD,
        }
        for name in F3_GRASP_BOUNDARIES
    }
    checks = {
        "all_translation_boundaries_stable": all(
            item["translation_pass"] for item in per_boundary.values()
        ),
        "all_orientation_boundaries_stable": all(
            item["orientation_pass"] for item in per_boundary.values()
        ),
    }
    return {
        "schema_version": GRASP_BOUNDARY_AUDIT_VERSION,
        "baseline_boundary": "post_close",
        "boundary_order": list(F3_GRASP_BOUNDARIES),
        "translation_drift_limit_m": F3_GRASP_TRANSLATION_DRIFT_LIMIT_M,
        "orientation_drift_limit_rad": F3_GRASP_ORIENTATION_DRIFT_LIMIT_RAD,
        "per_boundary": per_boundary,
        "maximum_translation_drift_m": max(translation.values()),
        "maximum_orientation_drift_rad": max(orientation.values()),
        "checks": checks,
        "pass": all(checks.values()),
    }


__all__ = [
    "CARRY_ROUTE_VERSION",
    "F3_BOTTLE_ACTOR_NAME",
    "F3_CARRY_TIME_DILATION_FACTOR",
    "F3_CENTRAL_HOLD_STEPS",
    "F3_CENTRAL_XY_M",
    "F3_FROZEN_CLEARANCE_M",
    "F3_GRASP_BOUNDARIES",
    "F3_H_NOMINAL_AMPLITUDE_M",
    "F3_PAD_HALF_EXTENTS_M",
    "F3_PROGRAMS",
    "F3_SELECTED_GRIPPER_LINK_NAMES",
    "F3_SUPPORT_ACTOR_NAMES",
    "F3_V_NOMINAL_AMPLITUDE_M",
    "FROZEN_CONTACT_POINT_ID",
    "FROZEN_ROTATION_CANDIDATE_INDEX",
    "GRASP_CONTRACT_VERSION",
    "TIME_DILATION_VERSION",
    "audit_f3_free_space_event_contacts",
    "audit_f3_grasp_boundary_stability",
    "build_f3_clearance_height_audit",
    "build_f3_clearance_route_targets",
    "frozen_f3_grasp_contract",
    "time_dilate_f3_carry_control_2x",
]
