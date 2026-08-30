"""Runtime-v3_4 F3 common-grasp robustness contract and diagnostic Gate.

Revision 8 and 9 used different prefix action bytes, while Revision 9 showed
orientation slip during the first suffix event despite continuous contact.
This module freezes one geometry-driven, program-independent side grasp and a
pre-release diagnostic.  It does not modify V/H, release, return, the bottle,
or any frozen verifier threshold.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .anchor import quaternion_angular_error
from .geometry import quaternion_matrix, relative_pose


SCHEMA_VERSION = "cmf_f3_common_grasp_contract_v10"
DIAGNOSTIC_SCHEMA_VERSION = "cmf_f3_grasp_robustness_diagnostic_v10"
CONTRACT_VERSION = "f3_geometry_midbody_contact0_candidate0_v10"
DIAGNOSTIC_VERSION = "f3_shared_v_plus_one_suffix_preopen_v10"
PROGRAMS = ("VVHH", "VHVH", "VHHV")
ARM = "left"
BOTTLE = {"modelname": "001_bottle", "model_id": 13}
CONTACT_POINT_ID = 0
ROTATION_CANDIDATE_INDEX = 0
PREGRASP_DISTANCE_M = 0.09
TARGET_DISTANCE_M = 0.0
CLOSE_NORMALIZED_TARGET = 0.0
POST_CLOSE_SETTLE_FRAMES = 250

# Frozen scientific/diagnostic thresholds inherited from runtime-v3_3.
MAX_GRASP_TRANSLATION_DRIFT_M = 0.005
MAX_GRASP_ORIENTATION_DRIFT_RAD = 0.050
MIN_SELECTED_CONTACT_FRACTION = 1.0
MAX_CONTACT_BREAK_COUNT = 0

R9_REFERENCE_ACTOR_POSE = (
    -0.1849084049463272,
    -0.05993383005261421,
    0.7838152647018433,
    0.07213852554559708,
    0.0003441395238041878,
    0.9973942637443542,
    -0.0009695073240436614,
)
R9_CONTACT0_CANDIDATE0_PREGRASP_POSE = (
    0.023006705567240715,
    0.06190032139420509,
    0.8138048648834229,
    0.05125296860933304,
    -0.05076628178358078,
    0.7059496641159058,
    0.7045785784721375,
)
R9_CONTACT0_ORDERED_GOAL_POSE_SHA256 = (
    "27b603b70a06c9a0ac1940057aa28b13a5c21f4b5bcd23139fc9e0a9057f7f88"
)
R9_FORENSIC_OUTPUT_SHA256 = (
    "23024fd44dff71febf3736b6654eb431b6971ea5a258c7f9c3b4365c5cbfee4f"
)


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _target_from_pregrasp(pregrasp: Sequence[float]) -> np.ndarray:
    pose = np.asarray(pregrasp, dtype=np.float64).reshape(7).copy()
    pose[3:] /= np.linalg.norm(pose[3:])
    direction = quaternion_matrix(pose[3:])
    pose[:3] += (
        np.asarray([PREGRASP_DISTANCE_M - TARGET_DISTANCE_M, 0.0, 0.0])
        @ np.linalg.inv(direction)
    )
    return pose


def build_f3_common_grasp_contract_v10() -> dict[str, Any]:
    target = _target_from_pregrasp(R9_CONTACT0_CANDIDATE0_PREGRASP_POSE)
    actor_to_eef = relative_pose(R9_REFERENCE_ACTOR_POSE, target)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_4",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "arm": ARM,
        "asset": dict(BOTTLE),
        "contact_point_id": CONTACT_POINT_ID,
        "rotation_candidate_index": ROTATION_CANDIDATE_INDEX,
        "pregrasp_distance_m": PREGRASP_DISTANCE_M,
        "target_distance_m": TARGET_DISTANCE_M,
        "close_normalized_target": CLOSE_NORMALIZED_TARGET,
        "post_close_settle_frames": POST_CLOSE_SETTLE_FRAMES,
        "grasp_region": "asset side mid-body; avoids the revision-8/9 upper-neck contact3 grasp",
        "reference_pregrasp_pose": list(R9_CONTACT0_CANDIDATE0_PREGRASP_POSE),
        "reference_target_grasp_pose": target.tolist(),
        "reference_T_actor_eef": actor_to_eef.tolist(),
        "reference_contact0_ordered_goal_pose_sha256": (
            R9_CONTACT0_ORDERED_GOAL_POSE_SHA256
        ),
        "reference_candidate0_planner_status": "Success",
        "selection_rule": (
            "use exactly official contact point 0 and rotation candidate 0 in all "
            "three program contexts; any other callback selection fails closed"
        ),
        "evidence": {
            "asset_extents_m": [0.06866, 0.247941, 0.067626],
            "asset_contact_point_count": 8,
            "revision9_contact0_all_ten_planner_candidates_success": True,
            "revision8_revision9_diff_forensic_output_sha256": (
                R9_FORENSIC_OUTPUT_SHA256
            ),
            "revision9_existing_contact3_slipped_in_suffix": True,
        },
        "invariants": {
            "same_contract_all_programs": True,
            "program_specific_grasp_forbidden": True,
            "online_success_selection_forbidden": True,
            "fallback_forbidden": True,
            "automatic_retry": False,
            "recovery_attempts": 0,
            "release_strategy_changed": False,
            "return_verifier_changed": False,
            "vh_axes_or_programs_changed": False,
            "orientation_threshold_changed": False,
            "bottle_changed": False,
        },
    }
    payload["contract_sha256"] = _canonical_sha256(payload)
    return payload


def validate_f3_common_grasp_contract_v10(value: Mapping[str, Any]) -> dict[str, Any]:
    result = json.loads(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    )
    digest = result.pop("contract_sha256", None)
    if not isinstance(digest, str) or digest != _canonical_sha256(result):
        raise ValueError("F3 common-grasp contract hash mismatch")
    expected = build_f3_common_grasp_contract_v10()
    if value != expected:
        raise ValueError("F3 common-grasp contract differs from frozen v10")
    return dict(expected)


def _boundary_metric(
    baseline: Sequence[float], value: Sequence[float]
) -> dict[str, float]:
    first = np.asarray(baseline, dtype=np.float64).reshape(7)
    second = np.asarray(value, dtype=np.float64).reshape(7)
    return {
        "translation_drift_m": float(np.linalg.norm(second[:3] - first[:3])),
        "orientation_drift_rad": float(
            quaternion_angular_error(second[3:], first[3:])
        ),
    }


def audit_f3_grasp_robustness_diagnostic_v10(
    *,
    program: str,
    grasp_contract: Mapping[str, Any],
    canonical_prefix_action_sha256: str,
    expected_canonical_prefix_action_sha256: str,
    boundary_T_eef_actor: Mapping[str, Sequence[float]],
    selected_contact_fraction: float,
    selected_contact_break_count: int,
    shared_v_motion_pass: bool,
    first_suffix_event_motion_pass: bool,
    eef_tracking_pass: bool,
    stopped_before_release: bool,
) -> dict[str, Any]:
    if program not in PROGRAMS:
        raise ValueError("F3 diagnostic program must be VVHH/VHVH/VHHV")
    contract = validate_f3_common_grasp_contract_v10(grasp_contract)
    required = ("post_close", "post_shared_V", "post_first_suffix_event")
    if tuple(boundary_T_eef_actor) != required:
        raise ValueError("F3 diagnostic boundary order must be exact")
    baseline = boundary_T_eef_actor["post_close"]
    drifts = {
        name: _boundary_metric(baseline, boundary_T_eef_actor[name])
        for name in required
    }
    checks = {
        "frozen_common_grasp_contract": (
            contract["contract_version"] == CONTRACT_VERSION
        ),
        "prefix_action_hash_matches": (
            isinstance(canonical_prefix_action_sha256, str)
            and canonical_prefix_action_sha256
            == expected_canonical_prefix_action_sha256
        ),
        "selected_contact_fraction": float(selected_contact_fraction)
        >= MIN_SELECTED_CONTACT_FRACTION,
        "selected_contact_break_count": int(selected_contact_break_count)
        <= MAX_CONTACT_BREAK_COUNT,
        "grasp_translation_drift": all(
            item["translation_drift_m"] <= MAX_GRASP_TRANSLATION_DRIFT_M
            for item in drifts.values()
        ),
        "grasp_orientation_drift": all(
            item["orientation_drift_rad"] <= MAX_GRASP_ORIENTATION_DRIFT_RAD
            for item in drifts.values()
        ),
        "shared_v_motion": shared_v_motion_pass is True,
        "first_suffix_event_motion": first_suffix_event_motion_pass is True,
        "eef_tracking": eef_tracking_pass is True,
        "release_not_executed": stopped_before_release is True,
    }
    receipt = {
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_4",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "program": program,
        "required_execution": "canonical prefix + shared first V + one suffix event; stop before release",
        "grasp_contract_sha256": contract["contract_sha256"],
        "canonical_prefix_action_sha256": canonical_prefix_action_sha256,
        "expected_canonical_prefix_action_sha256": (
            expected_canonical_prefix_action_sha256
        ),
        "boundary_T_eef_actor": {
            name: list(map(float, boundary_T_eef_actor[name])) for name in required
        },
        "boundary_grasp_drift": drifts,
        "selected_contact_fraction": float(selected_contact_fraction),
        "selected_contact_break_count": int(selected_contact_break_count),
        "thresholds": {
            "maximum_grasp_translation_drift_m": MAX_GRASP_TRANSLATION_DRIFT_M,
            "maximum_grasp_orientation_drift_rad": MAX_GRASP_ORIENTATION_DRIFT_RAD,
            "thresholds_changed": False,
        },
        "checks": checks,
        "pass": all(checks.values()),
    }
    receipt["receipt_sha256"] = _canonical_sha256(receipt)
    return receipt


def audit_f3_three_context_gate_v10(
    receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    values = list(receipts)
    programs = [item.get("program") for item in values]
    hashes = [item.get("grasp_contract_sha256") for item in values]
    prefix_hashes = [item.get("canonical_prefix_action_sha256") for item in values]
    checks = {
        "exactly_three_contexts": len(values) == 3,
        "fixed_program_order": programs == list(PROGRAMS),
        "all_pass": len(values) == 3 and all(item.get("pass") is True for item in values),
        "one_grasp_contract": len(set(hashes)) == 1,
        "one_prefix_action_hash": len(set(prefix_hashes)) == 1,
        "all_stopped_before_release": len(values) == 3
        and all(item.get("checks", {}).get("release_not_executed") is True for item in values),
    }
    result = {
        "schema_version": "cmf_f3_three_context_grasp_gate_v10",
        "program_order": programs,
        "diagnostic_execution_count": len(values),
        "full_root_allowed": all(checks.values()),
        "checks": checks,
        "pass": all(checks.values()),
        "automatic_retry": False,
        "recovery_attempts": 0,
    }
    result["receipt_sha256"] = _canonical_sha256(result)
    return result


__all__ = [
    "CONTRACT_VERSION",
    "DIAGNOSTIC_VERSION",
    "PROGRAMS",
    "audit_f3_grasp_robustness_diagnostic_v10",
    "audit_f3_three_context_gate_v10",
    "build_f3_common_grasp_contract_v10",
    "validate_f3_common_grasp_contract_v10",
]
