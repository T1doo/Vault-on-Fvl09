"""Pure contracts for the runtime-v3_3 revision-5 F3 return/release repair.

This module does not import SAPIEN.  It keeps every V/H event unchanged and
only defines one uniform return transport transform plus a physically timed
release boundary for all three F3 programs.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .anchor import quaternion_angular_error
from .f3_clearance_route_v3 import time_dilate_f3_carry_control_2x
from .f3_physical_contact_signal_v8 import (
    classify_f3_preopen_support_contacts_v8,
)


SCHEMA_VERSION = "cmf_f3_return_release_v5"
RETURN_CONTROL_TRANSFORM_VERSION = "f3_return_controls_time_dilation_2x_v5"
RELEASE_BOUNDARY_VERSION = "f3_contact_free_physical_disengagement_v5"
RETURN_SEGMENT_IDS = ("f3_return_preplace", "f3_return_release")
RELEASE_CLEARANCE_WORLD_Z_M = 0.010
PREPLACE_ABOVE_RELEASE_M = 0.100
PRE_OPEN_STABLE_FRAMES = 50
DISENGAGEMENT_SEARCH_MAX_EXTRA_FRAMES = 300
DISENGAGEMENT_CONFIRM_FRAMES = 10
POST_RELEASE_SAMPLE_STEPS = (0, 1, 5, 10, 25, 50, 125, 250)

PRE_OPEN_MAX_POSITION_ERROR_M = 0.005
PRE_OPEN_MAX_ORIENTATION_ERROR_RAD = 0.050
PRE_OPEN_MAX_GRASP_TRANSLATION_DRIFT_M = 0.005
PRE_OPEN_MAX_GRASP_ORIENTATION_DRIFT_RAD = 0.050
PRE_OPEN_MAX_EEF_LINEAR_SPEED_MPS = 0.010
PRE_OPEN_MAX_EEF_ANGULAR_SPEED_RPS = 0.050
PRE_OPEN_MAX_BOTTLE_LINEAR_SPEED_MPS = 0.020
PRE_OPEN_MAX_BOTTLE_ANGULAR_SPEED_RPS = 0.050
ACTUAL_OPEN_MIN_GRIPPER_QPOS_M = 0.040
PRE_OPEN_MAX_GRIPPER_QPOS_RANGE_M = 0.002
PRE_OPEN_MAX_GRIPPER_QPOS_BASELINE_ERROR_M = 0.003
PRE_OPEN_MAX_CLOSED_COMMAND_NORMALIZED = 0.05


def _hash_array(value: Any) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _json_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def contact_free_release_actor_pose(original_actor_pose: Sequence[float]) -> np.ndarray:
    original = np.asarray(original_actor_pose, dtype=np.float64).reshape(-1)
    if original.shape != (7,) or not np.all(np.isfinite(original)):
        raise ValueError("F3 original actor pose must be one finite 7-D pose")
    result = original.copy()
    result[2] += RELEASE_CLEARANCE_WORLD_Z_M
    return result


def time_dilate_f3_return_control_v5(
    control: Mapping[str, Any], *, segment_id: str
) -> tuple[dict, dict]:
    """Return one transformed control and explicit planner/execution provenance."""

    if segment_id not in RETURN_SEGMENT_IDS:
        raise ValueError("F3 return transform may only change the two frozen return segments")
    original = deepcopy(dict(control))
    transformed = time_dilate_f3_carry_control_2x(original)
    input_position = np.asarray(original["position"])
    output_position = np.asarray(transformed["position"])
    input_velocity = np.asarray(original["velocity"])
    output_velocity = np.asarray(transformed["velocity"])
    if not np.array_equal(input_position[0], output_position[0]) or not np.array_equal(
        input_position[-1], output_position[-1]
    ):
        raise RuntimeError("F3 return time dilation changed a position endpoint")
    audit = {
        "schema_version": SCHEMA_VERSION,
        "transform_version": RETURN_CONTROL_TRANSFORM_VERSION,
        "segment_id": segment_id,
        "factor": 2,
        "fixed_frequency_hz": 250,
        "planner_control": {
            "position_shape": list(input_position.shape),
            "velocity_shape": list(input_velocity.shape),
            "position_sha256": _hash_array(input_position),
            "velocity_sha256": _hash_array(input_velocity),
        },
        "executed_control": {
            "position_shape": list(output_position.shape),
            "velocity_shape": list(output_velocity.shape),
            "position_sha256": _hash_array(output_position),
            "velocity_sha256": _hash_array(output_velocity),
        },
        "position_endpoints_preserved_exactly": True,
        "planner_goal_and_terminal_qpos_unchanged": True,
        "planner_query_count_delta": 0,
    }
    audit["receipt_sha256"] = _json_hash(audit)
    transformed["_cmf_execution_transform"] = deepcopy(audit)
    query = transformed.get("_cmf_planner_query")
    if not isinstance(query, Mapping):
        raise ValueError("F3 return control lacks planner-query provenance")
    query = deepcopy(dict(query))
    query["execution_control_transform"] = deepcopy(audit)
    query["planner_control_shape_is_not_executed_control_shape"] = True
    transformed["_cmf_planner_query"] = query
    transformed.pop("_cmf_time_dilation", None)
    return transformed, audit


def transform_f3_return_controls_v5(
    controls: Sequence[Mapping[str, Any]], targets: Sequence[Mapping[str, Any]]
) -> tuple[list[dict], list[dict]]:
    if len(controls) != len(targets):
        raise ValueError("F3 controls and targets must have equal length")
    output = []
    audits = []
    for control, target in zip(controls, targets):
        segment_id = target.get("segment_id")
        if segment_id in RETURN_SEGMENT_IDS:
            transformed, receipt = time_dilate_f3_return_control_v5(
                control, segment_id=segment_id
            )
            output.append(transformed)
            audits.append(receipt)
        else:
            output.append(deepcopy(dict(control)))
    if [item["segment_id"] for item in audits] != list(RETURN_SEGMENT_IDS):
        raise ValueError("F3 return transform did not find exactly the frozen return segments")
    return output, audits


def validate_f3_return_control_transform_receipt(
    receipt: Mapping[str, Any],
) -> dict:
    if not isinstance(receipt, Mapping):
        raise ValueError("F3 return transform receipt must be a mapping")
    value = json.loads(
        json.dumps(
            receipt,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
        )
    )
    digest = value.pop("receipt_sha256", None)
    if not isinstance(digest, str) or _json_hash(value) != digest:
        raise ValueError("F3 return transform receipt hash mismatch")
    if (
        value.get("schema_version") != SCHEMA_VERSION
        or value.get("transform_version") != RETURN_CONTROL_TRANSFORM_VERSION
        or value.get("segment_id") not in RETURN_SEGMENT_IDS
        or value.get("factor") != 2
        or value.get("position_endpoints_preserved_exactly") is not True
        or value.get("planner_query_count_delta") != 0
    ):
        raise ValueError("F3 return transform receipt contract mismatch")
    return dict(receipt)


def build_pre_open_gate_v5(
    rows: Sequence[Mapping[str, Any]],
    *,
    bottle_actor_name: str,
    support_actor_names: Sequence[str],
    target_actor_pose: Sequence[float],
    release_eef_pose: Sequence[float],
    initial_eef_actor_transform: Sequence[float],
    final_eef_actor_transform: Sequence[float],
    expected_closed_gripper_qpos: Sequence[float],
    gripper_assembly_link_names: Sequence[str],
) -> dict:
    frames = list(rows)
    if len(frames) != PRE_OPEN_STABLE_FRAMES:
        raise ValueError("F3 pre-open Gate requires exactly 50 frames")
    target = np.asarray(target_actor_pose, dtype=np.float64).reshape(7)
    release = np.asarray(release_eef_pose, dtype=np.float64).reshape(7)
    initial_transform = np.asarray(initial_eef_actor_transform, dtype=np.float64).reshape(7)
    final_transform = np.asarray(final_eef_actor_transform, dtype=np.float64).reshape(7)
    expected_gripper = np.asarray(
        expected_closed_gripper_qpos, dtype=np.float64
    ).reshape(-1)
    if expected_gripper.shape != (2,) or not np.all(np.isfinite(expected_gripper)):
        raise ValueError("F3 expected closed gripper qpos must be finite shape (2,)")
    supports = {str(value) for value in support_actor_names}
    assembly_links = {str(value) for value in gripper_assembly_link_names}
    if not bottle_actor_name or not supports or not assembly_links:
        raise ValueError("F3 pre-open Gate requires bottle and support names")
    final = frames[-1]
    bottle_pose = np.asarray(final["actor_pose"], dtype=np.float64).reshape(7)
    eef_pose = np.asarray(final["eef"], dtype=np.float64).reshape(7)
    physical_contact_signal = classify_f3_preopen_support_contacts_v8(
        [row.get("contact_pairs", []) for row in frames],
        bottle_actor_name=bottle_actor_name,
        gripper_assembly_link_names=sorted(assembly_links),
        support_actor_names=sorted(supports),
    )
    support_hits = physical_contact_signal["pair_presence_audit"][
        "bottle_support"
    ]
    selected_gripper_support_hits = physical_contact_signal[
        "pair_presence_audit"
    ]["assembly_support"]
    selected = [bool(row.get("selected_gripper_contact")) for row in frames]
    identities = [str(row.get("selected_contact_actor_name")) for row in frames]
    eef_linear = [float(np.linalg.norm(row["eef_linear_velocity"])) for row in frames]
    eef_angular = [float(np.linalg.norm(row["eef_angular_velocity"])) for row in frames]
    bottle_linear = [float(np.linalg.norm(row["actor_linear_velocity"])) for row in frames]
    bottle_angular = [float(np.linalg.norm(row["actor_angular_velocity"])) for row in frames]
    actual_gripper_values = np.asarray(
        [row["realized_left_gripper_joint_qpos"] for row in frames],
        dtype=np.float64,
    )
    if actual_gripper_values.shape != (PRE_OPEN_STABLE_FRAMES, 2):
        raise ValueError("F3 realized left-gripper qpos history has invalid shape")
    actual_gripper = actual_gripper_values[-1]
    gripper_commands = [float(row["gripper_command"][0]) for row in frames]
    gripper_readbacks = [
        float(row["gripper_drive_target_readback"][0]) for row in frames
    ]
    checks = {
        "eef_position": float(np.linalg.norm(eef_pose[:3] - release[:3]))
        <= PRE_OPEN_MAX_POSITION_ERROR_M,
        "eef_orientation": quaternion_angular_error(eef_pose[3:], release[3:])
        <= PRE_OPEN_MAX_ORIENTATION_ERROR_RAD,
        "bottle_position": float(np.linalg.norm(bottle_pose[:3] - target[:3]))
        <= PRE_OPEN_MAX_POSITION_ERROR_M,
        "bottle_orientation": quaternion_angular_error(bottle_pose[3:], target[3:])
        <= PRE_OPEN_MAX_ORIENTATION_ERROR_RAD,
        "grasp_translation_drift": float(
            np.linalg.norm(final_transform[:3] - initial_transform[:3])
        )
        <= PRE_OPEN_MAX_GRASP_TRANSLATION_DRIFT_M,
        "grasp_orientation_drift": quaternion_angular_error(
            final_transform[3:], initial_transform[3:]
        )
        <= PRE_OPEN_MAX_GRASP_ORIENTATION_DRIFT_RAD,
        "eef_linear_stationary": max(eef_linear)
        <= PRE_OPEN_MAX_EEF_LINEAR_SPEED_MPS,
        "eef_angular_stationary": max(eef_angular)
        <= PRE_OPEN_MAX_EEF_ANGULAR_SPEED_RPS,
        "bottle_linear_stationary": max(bottle_linear)
        <= PRE_OPEN_MAX_BOTTLE_LINEAR_SPEED_MPS,
        "bottle_angular_stationary": max(bottle_angular)
        <= PRE_OPEN_MAX_BOTTLE_ANGULAR_SPEED_RPS,
        "selected_gripper_contact_continuous": all(selected),
        "selected_actor_identity": all(
            value == bottle_actor_name for value in identities
        ),
        "closed_command_continuous": max(gripper_commands)
        <= PRE_OPEN_MAX_CLOSED_COMMAND_NORMALIZED,
        "closed_drive_target_readback_continuous": max(gripper_readbacks)
        <= PRE_OPEN_MAX_CLOSED_COMMAND_NORMALIZED,
        "actual_gripper_below_open_threshold": bool(
            np.all(actual_gripper_values < ACTUAL_OPEN_MIN_GRIPPER_QPOS_M)
        ),
        "actual_gripper_qpos_stable": bool(
            np.all(
                np.ptp(actual_gripper_values, axis=0)
                <= PRE_OPEN_MAX_GRIPPER_QPOS_RANGE_M
            )
        ),
        "actual_gripper_matches_post_close_baseline": bool(
            np.all(
                np.abs(actual_gripper - expected_gripper)
                <= PRE_OPEN_MAX_GRIPPER_QPOS_BASELINE_ERROR_M
            )
        ),
        "physical_contact_signal_complete": all(
            physical_contact_signal["checks"][key]
            for key in (
                "all_relevant_pairs_use_v2_contact_schema",
                "all_relevant_pair_impulses_available",
                "all_relevant_points_have_signed_separation",
                "all_relevant_points_have_shape_identity",
            )
        ),
        "contact_free_of_pad_and_table": physical_contact_signal["checks"][
            "bottle_has_no_physical_support_contact"
        ],
        "gripper_assembly_contact_free_of_pad_and_table": (
            physical_contact_signal["checks"][
                "gripper_assembly_has_no_physical_support_contact"
            ]
        ),
    }
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "gate_version": RELEASE_BOUNDARY_VERSION,
        "frame_count": len(frames),
        "checks": checks,
        "maximum_speeds": {
            "eef_linear_mps": max(eef_linear),
            "eef_angular_rps": max(eef_angular),
            "bottle_linear_mps": max(bottle_linear),
            "bottle_angular_rps": max(bottle_angular),
        },
        "actual_gripper_joint_qpos": actual_gripper.tolist(),
        "expected_post_close_gripper_joint_qpos": expected_gripper.tolist(),
        "actual_gripper_joint_qpos_range": np.ptp(
            actual_gripper_values, axis=0
        ).tolist(),
        "pose_errors": {
            "eef_position_m": float(
                np.linalg.norm(eef_pose[:3] - release[:3])
            ),
            "eef_orientation_rad": quaternion_angular_error(
                eef_pose[3:], release[3:]
            ),
            "bottle_position_m": float(
                np.linalg.norm(bottle_pose[:3] - target[:3])
            ),
            "bottle_orientation_rad": quaternion_angular_error(
                bottle_pose[3:], target[3:]
            ),
        },
        "grasp_transform_drift": {
            "translation_m": float(
                np.linalg.norm(final_transform[:3] - initial_transform[:3])
            ),
            "orientation_rad": quaternion_angular_error(
                final_transform[3:], initial_transform[3:]
            ),
        },
        "support_hits": support_hits,
        "selected_gripper_support_hits": selected_gripper_support_hits,
        "support_hits_semantics": "pair_presence_audit_only",
        "physical_contact_signal_v8": physical_contact_signal,
        "r6_runtime_geometry_gate_required_separately": True,
        "gripper_assembly_link_names": sorted(assembly_links),
        "pass": all(checks.values()),
    }
    receipt["receipt_sha256"] = _json_hash(receipt)
    return receipt


def first_confirmed_disengagement_index(
    selected_contact_flags: Sequence[bool],
    actual_gripper_joint_qpos: Sequence[Sequence[float]],
) -> int | None:
    flags = [bool(value) for value in selected_contact_flags]
    qpos = np.asarray(actual_gripper_joint_qpos, dtype=np.float64)
    if qpos.shape != (len(flags), 2) or not np.all(np.isfinite(qpos)):
        raise ValueError(
            "F3 physical disengagement requires aligned finite two-finger qpos"
        )
    physically_open = np.all(
        qpos >= ACTUAL_OPEN_MIN_GRIPPER_QPOS_M, axis=1
    )
    width = DISENGAGEMENT_CONFIRM_FRAMES
    for index in range(0, len(flags) - width + 1):
        if (
            not any(flags[index : index + width])
            and bool(np.all(physically_open[index : index + width]))
        ):
            return index
    return None
