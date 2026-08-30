"""Pure CPU contracts for the F4 revision-5 boundary and grasp diagnostic.

Revision-4 reached every planned A endpoint but exposed two independent
physical blockers: the common-X prefix ended with one actual gripper finger
pinned against the tray, and the angled A grasp closed before the realized EEF
reached its target.  This module contains no SAPIEN, planner, runner, or GPU
dependency.  It defines only:

* a common-prefix target rewrite that inserts a vertical withdraw and uses the
  already-planned high center pose as the new branch-neutral target;
* an actual-joint/open/contact boundary receipt; and
* an A top-down pregrasp/grasp plus 20 mm micro-lift diagnostic Gate.

The contracts do not authorize Stage 0 and do not change common-X-to-tray,
right-arm execution, A/B/C slot semantics, or ABC/ACB/BAC programs.  Real
CuRobo, collision, contact, and cleanup evidence remains authoritative.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .geometry import world_axis_offset_pose
from .project_cube_grasp_pose_v1 import (
    FROZEN_CUBE_HALF_EXTENTS_M,
    build_project_cube_grasp_poses,
)


IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_3"
ROUTE_VERSION = "f4_collision_free_boundary_top_down_micro_lift_v5"

COMMON_PREFIX_LEGACY_IDS = (
    "common_pregrasp",
    "common_grasp",
    "common_lift",
    "common_safe_vertical",
    "common_center_high",
    "common_above_tray",
    "common_preplace",
    "common_release",
    "common_neutral",
)
COMMON_PREFIX_REPAIRED_IDS = (
    "common_pregrasp",
    "common_grasp",
    "common_lift",
    "common_safe_vertical",
    "common_center_high",
    "common_above_tray",
    "common_preplace",
    "common_release",
    "common_withdraw",
    "common_neutral",
)

BOUNDARY_SCHEMA_VERSION = "cmf_f4_actual_open_contact_boundary_v5"
BOUNDARY_FRAME_COUNT = 50
ACTUAL_GRIPPER_OPEN_MIN_QPOS_M = 0.040
COMMAND_OPEN_MIN_NORMALIZED = 0.95
BOUNDARY_EEF_POSITION_ATOL_M = 0.005
BOUNDARY_EEF_ORIENTATION_ATOL_RAD = 0.020
BOUNDARY_EEF_LINEAR_SPEED_MPS = 0.010
BOUNDARY_EEF_ANGULAR_SPEED_RPS = 0.050
NONZERO_CONTACT_IMPULSE_EPS = 1e-10

A_DIAGNOSTIC_TARGET_SCHEMA_VERSION = "cmf_f4_a_top_down_micro_lift_targets_v5"
A_DIAGNOSTIC_SEGMENT_IDS = (
    "A_pregrasp",
    "A_grasp",
    "A_micro_lift",
)
A_PREGRASP_DISTANCE_M = 0.09
A_MICRO_LIFT_DISTANCE_M = 0.020

MICRO_LIFT_GATE_SCHEMA_VERSION = "cmf_f4_a_micro_lift_gate_v5"
MICRO_LIFT_FRAME_COUNT = 50  # minimum complete realized-window length
MICRO_LIFT_TABLE_FREE_TAIL_FRAMES = 10
MICRO_LIFT_MIN_ACTOR_RISE_M = 0.015
MICRO_LIFT_MIN_CONTACT_FRACTION = 0.95
MICRO_LIFT_MIN_BILATERAL_CONTACT_COUNT = 2
MICRO_LIFT_MAX_CONTACT_BREAK_COUNT = 0
MICRO_LIFT_NON_TARGET_DISPLACEMENT_M = 0.010
GRASP_BOUNDARY_POSITION_ATOL_M = 0.005
GRASP_BOUNDARY_ORIENTATION_ATOL_RAD = 0.020
GRASP_BOUNDARY_LINEAR_SPEED_MPS = 0.010
GRASP_BOUNDARY_ANGULAR_SPEED_RPS = 0.050


def _json_safe(value: Any, *, path: str = "value") -> Any:
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
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist(), path=path)
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} mapping keys must be strings")
            result[key] = _json_safe(item, path=f"{path}.{key}")
        return result
    if isinstance(value, (list, tuple)):
        return [
            _json_safe(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    raise TypeError(f"{path} contains unsupported type {type(value).__name__}")


def canonical_json_sha256(value: Any) -> str:
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
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if result.shape != shape or not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be finite shape {shape}")
    return np.ascontiguousarray(result)


def _pose(value: Any, *, label: str) -> np.ndarray:
    result = _finite_vector(value, shape=(7,), label=label)
    if float(np.linalg.norm(result[3:])) <= 1e-12:
        raise ValueError(f"{label} quaternion must be nonzero")
    return result


def _quaternion_angular_error(left: Sequence[float], right: Sequence[float]) -> float:
    first = _finite_vector(left, shape=(4,), label="left quaternion")
    second = _finite_vector(right, shape=(4,), label="right quaternion")
    first_norm = float(np.linalg.norm(first))
    second_norm = float(np.linalg.norm(second))
    if first_norm <= 1e-12 or second_norm <= 1e-12:
        raise ValueError("quaternion norm must be nonzero")
    cosine = float(
        np.clip(abs(np.dot(first / first_norm, second / second_norm)), 0.0, 1.0)
    )
    return float(2.0 * np.arccos(cosine))


def _target(item: Mapping[str, Any], *, expected_id: str) -> dict:
    if not isinstance(item, Mapping) or item.get("segment_id") != expected_id:
        raise ValueError(f"expected common target {expected_id}")
    return {
        **deepcopy(dict(item)),
        "segment_id": expected_id,
        "pose": _pose(item.get("pose"), label=f"{expected_id} pose").tolist(),
    }


def build_repaired_common_prefix_targets_v5(
    common_targets: Sequence[Mapping[str, Any]],
) -> tuple[list[dict], dict]:
    """Insert a vertical withdraw and reuse center-high as branch-neutral."""

    if isinstance(common_targets, (str, bytes)) or not isinstance(
        common_targets, Sequence
    ):
        raise TypeError("common_targets must be a target sequence")
    if len(common_targets) != len(COMMON_PREFIX_LEGACY_IDS):
        raise ValueError("legacy F4 common prefix must contain exactly nine targets")
    original = _json_safe(common_targets, path="common_targets")
    normalized = [
        _target(item, expected_id=segment_id)
        for item, segment_id in zip(common_targets, COMMON_PREFIX_LEGACY_IDS)
    ]
    center_high = np.asarray(normalized[4]["pose"], dtype=np.float64)
    preplace = np.asarray(normalized[6]["pose"], dtype=np.float64)
    release = np.asarray(normalized[7]["pose"], dtype=np.float64)
    old_neutral = np.asarray(normalized[8]["pose"], dtype=np.float64)
    xy_error = float(np.linalg.norm(preplace[:2] - release[:2]))
    orientation_error = _quaternion_angular_error(preplace[3:], release[3:])
    withdraw_height = float(preplace[2] - release[2])
    if xy_error > 1e-12 or orientation_error > 1e-7 or withdraw_height <= 0.0:
        raise ValueError(
            "common preplace/release must define one positive vertical withdraw"
        )
    if center_high[2] < release[2]:
        raise ValueError("common center-high cannot be below release")

    repaired = deepcopy(normalized[:8])
    repaired.append(
        {"segment_id": "common_withdraw", "pose": preplace.tolist()}
    )
    repaired.append(
        {"segment_id": "common_neutral", "pose": center_high.tolist()}
    )
    validation = validate_repaired_common_prefix_targets_v5(repaired)
    if _json_safe(common_targets, path="common_targets") != original:
        raise RuntimeError("common prefix repair mutated its input")
    audit = {
        "schema_version": "cmf_f4_common_prefix_target_repair_v5",
        "route_version": ROUTE_VERSION,
        "legacy_segment_ids": list(COMMON_PREFIX_LEGACY_IDS),
        "repaired_segment_ids": list(COMMON_PREFIX_REPAIRED_IDS),
        "release_pose": release.tolist(),
        "withdraw_pose_source": "exact legacy common_preplace pose",
        "withdraw_pose": preplace.tolist(),
        "withdraw_height_m": withdraw_height,
        "neutral_pose_source": "exact legacy common_center_high pose",
        "neutral_pose": center_high.tolist(),
        "superseded_old_neutral_pose": old_neutral.tolist(),
        "common_actor_release_target_changed": False,
        "common_tray_changed": False,
        "right_arm_changed": False,
        "program_changed": False,
        "semantic_verifier_changed": False,
        "canonical_prefix_target_structure_changed": True,
        "canonical_prefix_must_refreeze": True,
        "runtime_collision_gate_required": True,
        "validation": validation,
        "pass": validation["pass"],
    }
    return repaired, audit


def validate_repaired_common_prefix_targets_v5(
    targets: Sequence[Mapping[str, Any]],
) -> dict:
    if isinstance(targets, (str, bytes)) or not isinstance(targets, Sequence):
        raise TypeError("repaired common targets must be a sequence")
    if len(targets) != len(COMMON_PREFIX_REPAIRED_IDS):
        raise ValueError("repaired F4 common prefix must contain ten targets")
    normalized = [
        _target(item, expected_id=segment_id)
        for item, segment_id in zip(targets, COMMON_PREFIX_REPAIRED_IDS)
    ]
    center = np.asarray(normalized[4]["pose"], dtype=np.float64)
    preplace = np.asarray(normalized[6]["pose"], dtype=np.float64)
    release = np.asarray(normalized[7]["pose"], dtype=np.float64)
    withdraw = np.asarray(normalized[8]["pose"], dtype=np.float64)
    neutral = np.asarray(normalized[9]["pose"], dtype=np.float64)
    checks = {
        "withdraw_reuses_preplace": bool(np.array_equal(withdraw, preplace)),
        "neutral_reuses_center_high": bool(np.array_equal(neutral, center)),
        "release_to_withdraw_xy_fixed": float(
            np.linalg.norm(withdraw[:2] - release[:2])
        )
        <= 1e-12,
        "release_to_withdraw_orientation_fixed": _quaternion_angular_error(
            withdraw[3:], release[3:]
        )
        <= 1e-7,
        "release_to_withdraw_is_upward": bool(withdraw[2] > release[2]),
        "high_neutral_not_below_release": bool(neutral[2] >= release[2]),
    }
    return {
        "schema_version": "cmf_f4_common_prefix_target_validation_v5",
        "segment_ids": list(COMMON_PREFIX_REPAIRED_IDS),
        "checks": checks,
        "pass": all(checks.values()),
    }


def _canonical_pair(left: str, right: str) -> tuple[str, str]:
    if not isinstance(left, str) or not left or not isinstance(right, str) or not right:
        raise ValueError("contact body names must be nonempty strings")
    return tuple(sorted((left, right)))


def _allowed_pair_set(values: Sequence[Sequence[str]]) -> set[tuple[str, str]]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError("allowed_nonzero_contact_pairs must be a sequence")
    output = set()
    for index, value in enumerate(values):
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 2:
            raise ValueError(f"allowed contact pair {index} must contain two names")
        pair = _canonical_pair(value[0], value[1])
        if pair in output:
            raise ValueError("allowed contact pairs must be unique")
        output.add(pair)
    return output


def _normalize_contact_pairs(value: Any, *, label: str) -> list[dict]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{label} must be a contact sequence")
    output = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise TypeError(f"{label}[{index}] must be a mapping")
        body_a = item.get("body_a")
        body_b = item.get("body_b")
        pair = _canonical_pair(body_a, body_b)
        try:
            impulse = float(item.get("impulse_norm_sum", 0.0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label}[{index}] impulse must be numeric") from exc
        if not np.isfinite(impulse) or impulse < 0.0:
            raise ValueError(f"{label}[{index}] impulse must be finite nonnegative")
        output.append(
            {
                "body_a": body_a,
                "body_b": body_b,
                "canonical_pair": list(pair),
                "impulse_norm_sum": impulse,
            }
        )
    return output


def build_actual_open_contact_boundary_receipt_v5(
    *,
    phase: str,
    rows: Sequence[Mapping[str, Any]],
    target_neutral_pose: Sequence[float],
    allowed_nonzero_contact_pairs: Sequence[Sequence[str]],
) -> dict:
    """Build a 50-frame boundary receipt from actual qpos and contacts."""

    if not isinstance(phase, str) or not phase:
        raise ValueError("boundary phase must be a nonempty string")
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        raise TypeError("boundary rows must be a sequence")
    if len(rows) != BOUNDARY_FRAME_COUNT:
        raise ValueError(f"boundary rows must contain exactly {BOUNDARY_FRAME_COUNT} frames")
    target = _pose(target_neutral_pose, label="target neutral pose")
    allowed = _allowed_pair_set(allowed_nonzero_contact_pairs)
    frames = []
    forbidden = []
    for frame_index, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise TypeError(f"boundary row {frame_index} must be a mapping")
        qpos = _finite_vector(
            raw.get("realized_right_gripper_joint_qpos"),
            shape=(2,),
            label=f"boundary row {frame_index} actual gripper qpos",
        )
        command = float(raw.get("right_gripper_command"))
        readback = float(raw.get("right_gripper_drive_target_readback"))
        if not np.isfinite(command) or not np.isfinite(readback):
            raise ValueError("boundary gripper command/readback must be finite")
        eef = _pose(raw.get("eef_pose"), label=f"boundary row {frame_index} EEF pose")
        linear = _finite_vector(
            raw.get("eef_linear_velocity"),
            shape=(3,),
            label=f"boundary row {frame_index} EEF linear velocity",
        )
        angular = _finite_vector(
            raw.get("eef_angular_velocity"),
            shape=(3,),
            label=f"boundary row {frame_index} EEF angular velocity",
        )
        contacts = _normalize_contact_pairs(
            raw.get("contact_pairs"), label=f"boundary row {frame_index} contacts"
        )
        frame_forbidden = [
            item
            for item in contacts
            if item["impulse_norm_sum"] > NONZERO_CONTACT_IMPULSE_EPS
            and tuple(item["canonical_pair"]) not in allowed
        ]
        for item in frame_forbidden:
            forbidden.append({"frame_index": frame_index, **item})
        frames.append(
            {
                "frame_index": frame_index,
                "step_index": int(raw.get("step_index")),
                "timestamp": float(raw.get("timestamp")),
                "actual_right_gripper_joint_qpos_m": qpos.tolist(),
                "right_gripper_command": command,
                "right_gripper_drive_target_readback": readback,
                "eef_pose": eef.tolist(),
                "eef_position_error_m": float(np.linalg.norm(eef[:3] - target[:3])),
                "eef_orientation_error_rad": _quaternion_angular_error(
                    eef[3:], target[3:]
                ),
                "eef_linear_speed_mps": float(np.linalg.norm(linear)),
                "eef_angular_speed_rps": float(np.linalg.norm(angular)),
                "contact_pairs": contacts,
                "forbidden_nonzero_contacts": frame_forbidden,
            }
        )
    qpos_values = np.asarray(
        [frame["actual_right_gripper_joint_qpos_m"] for frame in frames],
        dtype=np.float64,
    )
    checks = {
        "actual_both_fingers_open": bool(
            np.all(qpos_values >= ACTUAL_GRIPPER_OPEN_MIN_QPOS_M)
        ),
        "command_open": all(
            frame["right_gripper_command"] >= COMMAND_OPEN_MIN_NORMALIZED
            for frame in frames
        ),
        "drive_target_readback_open": all(
            frame["right_gripper_drive_target_readback"]
            >= COMMAND_OPEN_MIN_NORMALIZED
            for frame in frames
        ),
        "neutral_position": max(frame["eef_position_error_m"] for frame in frames)
        <= BOUNDARY_EEF_POSITION_ATOL_M,
        "neutral_orientation": max(
            frame["eef_orientation_error_rad"] for frame in frames
        )
        <= BOUNDARY_EEF_ORIENTATION_ATOL_RAD,
        "eef_linear_stationary": max(
            frame["eef_linear_speed_mps"] for frame in frames
        )
        <= BOUNDARY_EEF_LINEAR_SPEED_MPS,
        "eef_angular_stationary": max(
            frame["eef_angular_speed_rps"] for frame in frames
        )
        <= BOUNDARY_EEF_ANGULAR_SPEED_RPS,
        "no_forbidden_nonzero_contact": not forbidden,
    }
    receipt = {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "route_version": ROUTE_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "phase": phase,
        "frame_count": len(frames),
        "target_neutral_pose": target.tolist(),
        "thresholds": {
            "actual_gripper_open_min_qpos_m": ACTUAL_GRIPPER_OPEN_MIN_QPOS_M,
            "command_open_min_normalized": COMMAND_OPEN_MIN_NORMALIZED,
            "neutral_position_atol_m": BOUNDARY_EEF_POSITION_ATOL_M,
            "neutral_orientation_atol_rad": BOUNDARY_EEF_ORIENTATION_ATOL_RAD,
            "eef_linear_speed_mps": BOUNDARY_EEF_LINEAR_SPEED_MPS,
            "eef_angular_speed_rps": BOUNDARY_EEF_ANGULAR_SPEED_RPS,
            "nonzero_contact_impulse_eps": NONZERO_CONTACT_IMPULSE_EPS,
        },
        "allowed_nonzero_contact_pairs": [list(pair) for pair in sorted(allowed)],
        "minimum_actual_right_gripper_joint_qpos_m": qpos_values.min(axis=0).tolist(),
        "final_actual_right_gripper_joint_qpos_m": qpos_values[-1].tolist(),
        "maximum_neutral_position_error_m": max(
            frame["eef_position_error_m"] for frame in frames
        ),
        "maximum_neutral_orientation_error_rad": max(
            frame["eef_orientation_error_rad"] for frame in frames
        ),
        "maximum_eef_linear_speed_mps": max(
            frame["eef_linear_speed_mps"] for frame in frames
        ),
        "maximum_eef_angular_speed_rps": max(
            frame["eef_angular_speed_rps"] for frame in frames
        ),
        "first_forbidden_contact_frame": None
        if not forbidden
        else forbidden[0]["frame_index"],
        "forbidden_nonzero_contacts": forbidden,
        "frames": frames,
        "checks": checks,
        "pass": all(checks.values()),
    }
    receipt["receipt_sha256"] = canonical_json_sha256(receipt)
    return receipt


def validate_actual_open_contact_boundary_receipt_v5(receipt: Mapping[str, Any]) -> dict:
    if not isinstance(receipt, Mapping):
        raise TypeError("boundary receipt must be a mapping")
    value = _json_safe(receipt)
    digest = value.pop("receipt_sha256", None)
    if value.get("schema_version") != BOUNDARY_SCHEMA_VERSION:
        raise ValueError("boundary receipt schema mismatch")
    if not isinstance(digest, str) or canonical_json_sha256(value) != digest:
        raise ValueError("boundary receipt hash mismatch")
    if value.get("frame_count") != BOUNDARY_FRAME_COUNT:
        raise ValueError("boundary receipt frame count mismatch")
    if value.get("pass") != all(value.get("checks", {}).values()):
        raise ValueError("boundary receipt aggregate mismatch")
    return _json_safe(receipt)


def build_a_top_down_micro_lift_targets_v5(
    *,
    actor_pose: Sequence[float],
    arm: str = "right",
    pregrasp_distance_m: float = A_PREGRASP_DISTANCE_M,
    micro_lift_distance_m: float = A_MICRO_LIFT_DISTANCE_M,
) -> tuple[list[dict], dict]:
    """Build A's proven top-down grasp followed by exactly 20 mm lift."""

    actor = _pose(actor_pose, label="A actor pose")
    pregrasp_distance = float(pregrasp_distance_m)
    lift_distance = float(micro_lift_distance_m)
    if not np.isfinite(pregrasp_distance) or pregrasp_distance <= 0.0:
        raise ValueError("A pregrasp distance must be finite positive")
    if not np.isfinite(lift_distance) or abs(
        lift_distance - A_MICRO_LIFT_DISTANCE_M
    ) > 1e-12:
        raise ValueError("A diagnostic micro-lift must remain exactly 20 mm")
    pregrasp, grasp, grasp_contract = build_project_cube_grasp_poses(
        actor,
        cube_half_extents_m=FROZEN_CUBE_HALF_EXTENTS_M,
        arm=arm,
        pregrasp_distance_m=pregrasp_distance,
    )
    micro_lift = world_axis_offset_pose(grasp, lift_distance)
    targets = [
        {"segment_id": "A_pregrasp", "pose": pregrasp.tolist()},
        {"segment_id": "A_grasp", "pose": grasp.tolist()},
        {"segment_id": "A_micro_lift", "pose": micro_lift.tolist()},
    ]
    audit = {
        "schema_version": A_DIAGNOSTIC_TARGET_SCHEMA_VERSION,
        "route_version": ROUTE_VERSION,
        "segment_ids": list(A_DIAGNOSTIC_SEGMENT_IDS),
        "arm": arm,
        "actor_pose": actor.tolist(),
        "pregrasp_distance_m": pregrasp_distance,
        "micro_lift_distance_m": lift_distance,
        "micro_lift_world_delta_m": (micro_lift[:3] - grasp[:3]).tolist(),
        "grasp_contract": grasp_contract,
        "uses_existing_project_top_down_grasp_v1": True,
        "diagnostic_only": True,
        "place_target_defined": False,
        "program_changed": False,
        "verifier_threshold_changed": False,
        "pass": bool(
            [item["segment_id"] for item in targets]
            == list(A_DIAGNOSTIC_SEGMENT_IDS)
            and np.allclose(
                micro_lift[:3] - grasp[:3],
                [0.0, 0.0, A_MICRO_LIFT_DISTANCE_M],
                rtol=0.0,
                atol=1e-12,
            )
        ),
    }
    return targets, audit


def _contact_break_count(values: Sequence[bool]) -> int:
    return sum(
        bool(previous) and not bool(current)
        for previous, current in zip(values, values[1:])
    )


def build_a_micro_lift_gate_receipt_v5(
    *,
    targets: Sequence[Mapping[str, Any]],
    realized_pregrasp_pose: Sequence[float],
    realized_grasp_pose: Sequence[float],
    pregrasp_linear_velocity: Sequence[float],
    pregrasp_angular_velocity: Sequence[float],
    grasp_linear_velocity: Sequence[float],
    grasp_angular_velocity: Sequence[float],
    preclose_right_gripper_joint_qpos: Sequence[float],
    micro_lift_rows: Sequence[Mapping[str, Any]],
    expected_actor_name: str,
    allowed_nonzero_contact_pairs: Sequence[Sequence[str]],
) -> dict:
    """Evaluate a finite top-down grasp-acquisition and 20 mm lift Gate."""

    if len(targets) != len(A_DIAGNOSTIC_SEGMENT_IDS):
        raise ValueError("A micro-lift Gate requires exactly three targets")
    normalized_targets = [
        _target(item, expected_id=segment_id)
        for item, segment_id in zip(targets, A_DIAGNOSTIC_SEGMENT_IDS)
    ]
    planned_pregrasp = np.asarray(normalized_targets[0]["pose"], dtype=np.float64)
    planned_grasp = np.asarray(normalized_targets[1]["pose"], dtype=np.float64)
    planned_lift = np.asarray(normalized_targets[2]["pose"], dtype=np.float64)
    if not np.allclose(
        planned_lift[:3] - planned_grasp[:3],
        [0.0, 0.0, A_MICRO_LIFT_DISTANCE_M],
        rtol=0.0,
        atol=1e-12,
    ):
        raise ValueError("A micro-lift target is not an exact 20 mm world-z lift")
    actual_pregrasp = _pose(realized_pregrasp_pose, label="realized A pregrasp")
    actual_grasp = _pose(realized_grasp_pose, label="realized A grasp")
    pre_linear = _finite_vector(
        pregrasp_linear_velocity,
        shape=(3,),
        label="pregrasp linear velocity",
    )
    pre_angular = _finite_vector(
        pregrasp_angular_velocity,
        shape=(3,),
        label="pregrasp angular velocity",
    )
    grasp_linear = _finite_vector(
        grasp_linear_velocity,
        shape=(3,),
        label="grasp linear velocity",
    )
    grasp_angular = _finite_vector(
        grasp_angular_velocity,
        shape=(3,),
        label="grasp angular velocity",
    )
    preclose_qpos = _finite_vector(
        preclose_right_gripper_joint_qpos,
        shape=(2,),
        label="preclose actual gripper qpos",
    )
    if not isinstance(expected_actor_name, str) or not expected_actor_name:
        raise ValueError("expected A actor name must be nonempty")
    if isinstance(micro_lift_rows, (str, bytes)) or not isinstance(
        micro_lift_rows, Sequence
    ):
        raise TypeError("micro_lift_rows must be a sequence")
    if len(micro_lift_rows) < MICRO_LIFT_FRAME_COUNT:
        raise ValueError(
            f"micro_lift_rows must contain at least {MICRO_LIFT_FRAME_COUNT} frames"
        )
    allowed = _allowed_pair_set(allowed_nonzero_contact_pairs)
    frames = []
    forbidden = []
    for frame_index, raw in enumerate(micro_lift_rows):
        if not isinstance(raw, Mapping):
            raise TypeError(f"micro-lift row {frame_index} must be a mapping")
        actor_pose = _pose(
            raw.get("actor_pose"), label=f"micro-lift row {frame_index} actor pose"
        )
        selected = raw.get("selected_gripper_contact")
        if not isinstance(selected, (bool, np.bool_)):
            raise TypeError("micro-lift selected contact must be bool")
        count = raw.get("selected_gripper_contact_count")
        if not isinstance(count, (int, np.integer)) or isinstance(count, bool) or int(count) < 0:
            raise TypeError("micro-lift selected contact count must be nonnegative int")
        actor_name = raw.get("selected_contact_actor_name")
        if not isinstance(actor_name, str):
            raise TypeError("micro-lift selected actor name must be str")
        table_contact = raw.get("actor_table_contact")
        if not isinstance(table_contact, (bool, np.bool_)):
            raise TypeError("micro-lift actor_table_contact must be bool")
        contacts = _normalize_contact_pairs(
            raw.get("contact_pairs"), label=f"micro-lift row {frame_index} contacts"
        )
        frame_forbidden = [
            item
            for item in contacts
            if item["impulse_norm_sum"] > NONZERO_CONTACT_IMPULSE_EPS
            and tuple(item["canonical_pair"]) not in allowed
        ]
        for item in frame_forbidden:
            forbidden.append({"frame_index": frame_index, **item})
        frames.append(
            {
                "frame_index": frame_index,
                "actor_pose": actor_pose.tolist(),
                "selected_gripper_contact": bool(selected),
                "selected_gripper_contact_count": int(count),
                "selected_contact_actor_name": actor_name,
                "actor_table_contact": bool(table_contact),
                "contact_pairs": contacts,
                "forbidden_nonzero_contacts": frame_forbidden,
            }
        )
    selected_values = [frame["selected_gripper_contact"] for frame in frames]
    actor_start_z = float(frames[0]["actor_pose"][2])
    actor_end_z = float(frames[-1]["actor_pose"][2])
    actor_rise = actor_end_z - actor_start_z
    pregrasp_position_error = float(
        np.linalg.norm(actual_pregrasp[:3] - planned_pregrasp[:3])
    )
    pregrasp_orientation_error = _quaternion_angular_error(
        actual_pregrasp[3:], planned_pregrasp[3:]
    )
    grasp_position_error = float(
        np.linalg.norm(actual_grasp[:3] - planned_grasp[:3])
    )
    grasp_orientation_error = _quaternion_angular_error(
        actual_grasp[3:], planned_grasp[3:]
    )
    table_free_tail = [
        not frame["actor_table_contact"]
        for frame in frames[-MICRO_LIFT_TABLE_FREE_TAIL_FRAMES:]
    ]
    checks = {
        "pregrasp_position_boundary": pregrasp_position_error
        <= GRASP_BOUNDARY_POSITION_ATOL_M,
        "pregrasp_orientation_boundary": pregrasp_orientation_error
        <= GRASP_BOUNDARY_ORIENTATION_ATOL_RAD,
        "pregrasp_stationary": float(np.linalg.norm(pre_linear))
        <= GRASP_BOUNDARY_LINEAR_SPEED_MPS
        and float(np.linalg.norm(pre_angular))
        <= GRASP_BOUNDARY_ANGULAR_SPEED_RPS,
        "grasp_position_boundary": grasp_position_error
        <= GRASP_BOUNDARY_POSITION_ATOL_M,
        "grasp_orientation_boundary": grasp_orientation_error
        <= GRASP_BOUNDARY_ORIENTATION_ATOL_RAD,
        "grasp_stationary": float(np.linalg.norm(grasp_linear))
        <= GRASP_BOUNDARY_LINEAR_SPEED_MPS
        and float(np.linalg.norm(grasp_angular))
        <= GRASP_BOUNDARY_ANGULAR_SPEED_RPS,
        "actual_both_fingers_open_before_close": bool(
            np.all(preclose_qpos >= ACTUAL_GRIPPER_OPEN_MIN_QPOS_M)
        ),
        "selected_contact_fraction": float(np.mean(selected_values))
        >= MICRO_LIFT_MIN_CONTACT_FRACTION,
        "selected_contact_break_count": _contact_break_count(selected_values)
        <= MICRO_LIFT_MAX_CONTACT_BREAK_COUNT,
        "bilateral_contact": all(
            frame["selected_gripper_contact_count"]
            >= MICRO_LIFT_MIN_BILATERAL_CONTACT_COUNT
            for frame in frames
        ),
        "selected_actor_identity": all(
            frame["selected_contact_actor_name"] == expected_actor_name
            for frame in frames
        ),
        "actor_rise": actor_rise >= MICRO_LIFT_MIN_ACTOR_RISE_M,
        "table_contact_cleared_in_tail": all(table_free_tail),
        "no_forbidden_nonzero_contact": not forbidden,
    }
    receipt = {
        "schema_version": MICRO_LIFT_GATE_SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "route_version": ROUTE_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "expected_actor_name": expected_actor_name,
        "target_segment_ids": list(A_DIAGNOSTIC_SEGMENT_IDS),
        "targets": normalized_targets,
        "thresholds": {
            "pregrasp_distance_m": A_PREGRASP_DISTANCE_M,
            "micro_lift_distance_m": A_MICRO_LIFT_DISTANCE_M,
            "minimum_actor_rise_m": MICRO_LIFT_MIN_ACTOR_RISE_M,
            "minimum_contact_fraction": MICRO_LIFT_MIN_CONTACT_FRACTION,
            "minimum_bilateral_contact_count": MICRO_LIFT_MIN_BILATERAL_CONTACT_COUNT,
            "maximum_contact_break_count": MICRO_LIFT_MAX_CONTACT_BREAK_COUNT,
            "table_free_tail_frames": MICRO_LIFT_TABLE_FREE_TAIL_FRAMES,
            "position_boundary_atol_m": GRASP_BOUNDARY_POSITION_ATOL_M,
            "orientation_boundary_atol_rad": GRASP_BOUNDARY_ORIENTATION_ATOL_RAD,
            "actual_gripper_open_min_qpos_m": ACTUAL_GRIPPER_OPEN_MIN_QPOS_M,
            "nonzero_contact_impulse_eps": NONZERO_CONTACT_IMPULSE_EPS,
        },
        "boundary_metrics": {
            "pregrasp_position_error_m": pregrasp_position_error,
            "pregrasp_orientation_error_rad": pregrasp_orientation_error,
            "grasp_position_error_m": grasp_position_error,
            "grasp_orientation_error_rad": grasp_orientation_error,
            "preclose_actual_right_gripper_joint_qpos_m": preclose_qpos.tolist(),
        },
        "micro_lift_metrics": {
            "frame_count": len(frames),
            "actor_start_z_m": actor_start_z,
            "actor_end_z_m": actor_end_z,
            "actor_rise_m": actor_rise,
            "selected_contact_fraction": float(np.mean(selected_values)),
            "selected_contact_break_count": _contact_break_count(selected_values),
            "minimum_selected_contact_count": min(
                frame["selected_gripper_contact_count"] for frame in frames
            ),
            "table_contact_tail": [
                frame["actor_table_contact"]
                for frame in frames[-MICRO_LIFT_TABLE_FREE_TAIL_FRAMES:]
            ],
        },
        "allowed_nonzero_contact_pairs": [list(pair) for pair in sorted(allowed)],
        "first_forbidden_contact_frame": None
        if not forbidden
        else forbidden[0]["frame_index"],
        "forbidden_nonzero_contacts": forbidden,
        "frames": frames,
        "checks": checks,
        "pass": all(checks.values()),
    }
    receipt["receipt_sha256"] = canonical_json_sha256(receipt)
    return receipt


def build_micro_lift_noninterference_receipt_v5(
    *,
    baseline_poses: Mapping[str, Sequence[float]],
    stage_states: Sequence[Mapping[str, Any]],
) -> dict:
    roles = ("common_x", "B", "C")
    if set(baseline_poses) != set(roles):
        raise ValueError("F4 micro noninterference baseline roles changed")
    baseline = {
        role: _pose(baseline_poses[role], label=f"baseline {role}")
        for role in roles
    }
    if not stage_states:
        raise ValueError("F4 micro noninterference requires staged states")
    stages = []
    aggregate_checks = {}
    for index, raw in enumerate(stage_states):
        if not isinstance(raw, Mapping):
            raise TypeError("F4 micro noninterference stage must be a mapping")
        stage_id = raw.get("stage_id")
        poses = raw.get("poses")
        stability = raw.get("stability_and_support")
        if (
            not isinstance(stage_id, str)
            or not stage_id
            or not isinstance(poses, Mapping)
            or set(poses) != set(roles)
            or not isinstance(stability, Mapping)
            or set(stability) != set(roles)
        ):
            raise ValueError("F4 micro noninterference stage schema changed")
        current = {
            role: _pose(poses[role], label=f"{stage_id} {role}")
            for role in roles
        }
        displacement = {
            role: float(np.linalg.norm(current[role][:3] - baseline[role][:3]))
            for role in roles
        }
        orientation = {
            role: _quaternion_angular_error(
                current[role][3:], baseline[role][3:]
            )
            for role in roles
        }
        stage_checks = {
            "all_non_target_displacements_within_10mm": all(
                value <= MICRO_LIFT_NON_TARGET_DISPLACEMENT_M
                for value in displacement.values()
            ),
            "common_x_tray_predicate_preserved": raw.get(
                "common_x_tray_predicate"
            )
            is True,
            "all_non_targets_stable_and_supported": all(
                stability.get(role) is True for role in roles
            ),
        }
        aggregate_checks[stage_id] = all(stage_checks.values())
        stages.append(
            {
                "stage_id": stage_id,
                "poses": {role: current[role].tolist() for role in roles},
                "position_displacement_m": displacement,
                "orientation_displacement_rad_audit_only": orientation,
                "stability_and_support": {
                    role: bool(stability[role]) for role in roles
                },
                "common_x_tray_predicate": bool(
                    raw.get("common_x_tray_predicate")
                ),
                "checks": stage_checks,
                "pass": all(stage_checks.values()),
            }
        )
    receipt = {
        "schema_version": "cmf_f4_micro_lift_noninterference_v5",
        "formal_data": False,
        "stage0_data": False,
        "roles": list(roles),
        "maximum_position_displacement_m": MICRO_LIFT_NON_TARGET_DISPLACEMENT_M,
        "baseline_poses": {
            role: baseline[role].tolist() for role in roles
        },
        "stages": stages,
        "stage_pass": aggregate_checks,
        "pass": all(aggregate_checks.values()),
    }
    receipt["receipt_sha256"] = canonical_json_sha256(receipt)
    return receipt


def validate_a_micro_lift_gate_receipt_v5(receipt: Mapping[str, Any]) -> dict:
    if not isinstance(receipt, Mapping):
        raise TypeError("micro-lift receipt must be a mapping")
    value = _json_safe(receipt)
    digest = value.pop("receipt_sha256", None)
    if value.get("schema_version") != MICRO_LIFT_GATE_SCHEMA_VERSION:
        raise ValueError("micro-lift receipt schema mismatch")
    if not isinstance(digest, str) or canonical_json_sha256(value) != digest:
        raise ValueError("micro-lift receipt hash mismatch")
    frame_count = value.get("micro_lift_metrics", {}).get("frame_count")
    if not isinstance(frame_count, int) or frame_count < MICRO_LIFT_FRAME_COUNT:
        raise ValueError("micro-lift receipt frame count is below the minimum")
    if value.get("pass") != all(value.get("checks", {}).values()):
        raise ValueError("micro-lift receipt aggregate mismatch")
    return _json_safe(receipt)


__all__ = [
    "ACTUAL_GRIPPER_OPEN_MIN_QPOS_M",
    "A_DIAGNOSTIC_SEGMENT_IDS",
    "A_MICRO_LIFT_DISTANCE_M",
    "A_PREGRASP_DISTANCE_M",
    "BOUNDARY_FRAME_COUNT",
    "BOUNDARY_SCHEMA_VERSION",
    "COMMON_PREFIX_LEGACY_IDS",
    "COMMON_PREFIX_REPAIRED_IDS",
    "MICRO_LIFT_FRAME_COUNT",
    "MICRO_LIFT_GATE_SCHEMA_VERSION",
    "MICRO_LIFT_MIN_ACTOR_RISE_M",
    "MICRO_LIFT_TABLE_FREE_TAIL_FRAMES",
    "ROUTE_VERSION",
    "build_a_micro_lift_gate_receipt_v5",
    "build_a_top_down_micro_lift_targets_v5",
    "build_actual_open_contact_boundary_receipt_v5",
    "build_repaired_common_prefix_targets_v5",
    "build_micro_lift_noninterference_receipt_v5",
    "canonical_json_sha256",
    "validate_a_micro_lift_gate_receipt_v5",
    "validate_actual_open_contact_boundary_receipt_v5",
    "validate_repaired_common_prefix_targets_v5",
]
