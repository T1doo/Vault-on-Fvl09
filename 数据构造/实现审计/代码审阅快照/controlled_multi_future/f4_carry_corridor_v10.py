"""Runtime-v3_4 fixed-order F4 planner-only carry corridor contracts."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .anchor import quaternion_angular_error


SCHEMA_VERSION = "cmf_f4_fixed_order_carry_corridors_v10"
AUDIT_SCHEMA_VERSION = "cmf_f4_carry_corridor_planner_audit_v10"
CORRIDOR_VERSION = "f4_revision4_evidence_fixed_order_corridors_v10"
ROLE = "A"
ARM = "right"
R4_SUCCESSFUL_CARRY_MID = (
    0.1549994685589866,
    -0.013921714285871883,
    0.9240019948107627,
    0.6830110770159924,
    -0.18302253901568033,
    0.18301608186480636,
    0.6830107851744089,
)
R4_SUCCESSFUL_CARRY_MID_PLANNER_STATUS = "Success"
R4_SUCCESSFUL_CARRY_MID_END_QPOS_SHA256 = (
    "d18eb398ebf997f498001622a5f765605de01246d3777a93b02a00abe89e6988"
)
R4_FORENSIC_OUTPUT_SHA256 = (
    "48b1ec4ceada8c6875db983b7bf7237c0c1d48d41d9426103e639bbb4e05dd4c"
)
LOWER_CARRY_HEIGHT_M = R4_SUCCESSFUL_CARRY_MID[2]


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


def _pose(value: Sequence[float], label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(-1)
    if result.shape != (7,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be one finite 7-D pose")
    result = result.copy()
    norm = float(np.linalg.norm(result[3:]))
    if norm <= 1e-12:
        raise ValueError(f"{label} quaternion must be nonzero")
    result[3:] /= norm
    return result


def _target_map(targets: Sequence[Mapping[str, Any]]) -> dict[str, np.ndarray]:
    result = {}
    for item in targets:
        segment_id = str(item.get("segment_id"))
        if segment_id in result:
            raise ValueError("F4 base target IDs must be unique")
        result[segment_id] = _pose(item.get("pose"), segment_id)
    prefixes = {name.split("_", 1)[0] for name in result}
    if len(prefixes) != 1:
        raise ValueError("F4 base targets must contain exactly one role")
    role = next(iter(prefixes))
    expected = {
        f"{role}_pregrasp",
        f"{role}_grasp",
        f"{role}_lift",
        f"{role}_carry_mid",
        f"{role}_preplace",
        f"{role}_release",
        f"{role}_neutral",
    }
    if set(result) != expected:
        raise ValueError("F4 A corridor requires the exact seven base targets")
    return result


def _segments(items: Sequence[tuple[str, np.ndarray]]) -> list[dict[str, Any]]:
    return [{"segment_id": name, "pose": value.tolist()} for name, value in items]


def build_f4_fixed_order_corridors_v10(
    base_targets: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    base = _target_map(base_targets)
    if "A_carry_mid" not in base:
        raise ValueError("F4 fixed corridor reference must be role A")
    lift = base["A_lift"]
    midpoint = base["A_carry_mid"]
    preplace = base["A_preplace"]
    release = base["A_release"]
    neutral = base["A_neutral"]
    r4 = _pose(R4_SUCCESSFUL_CARRY_MID, "Revision-4 carry-mid")

    restore_current_orientation = r4.copy()
    restore_current_orientation[:2] = midpoint[:2]
    restore_current_orientation[3:] = midpoint[3:]

    lower_mid = midpoint.copy()
    lower_mid[2] = LOWER_CARRY_HEIGHT_M
    lower_preplace = preplace.copy()
    lower_preplace[2] = LOWER_CARRY_HEIGHT_M

    entry = lower_mid.copy()
    entry[:3] = 0.5 * (lower_mid[:3] + neutral[:3])

    candidates = [
        {
            "priority": 1,
            "candidate_id": "r4_successful_carry_orientation_and_corridor",
            "replacement_A_carry_mid_pose": r4.tolist(),
            "segments": _segments(
                (
                    ("A_lift", lift),
                    ("A_r4_carry_mid", r4),
                    ("A_restore_topdown_mid", restore_current_orientation),
                    ("A_preplace", preplace),
                    ("A_release", release),
                    ("A_neutral", neutral),
                )
            ),
        },
        {
            "priority": 2,
            "candidate_id": "proven_branch_neutral_carry_pose",
            "replacement_A_carry_mid_pose": neutral.tolist(),
            "segments": _segments(
                (
                    ("A_lift", lift),
                    ("A_branch_neutral_carry", neutral),
                    ("A_preplace", preplace),
                    ("A_release", release),
                    ("A_neutral", neutral),
                )
            ),
        },
        {
            "priority": 3,
            "candidate_id": "lower_carry_height",
            "replacement_A_carry_mid_pose": lower_mid.tolist(),
            "segments": _segments(
                (
                    ("A_lift", lift),
                    ("A_lower_carry_mid", lower_mid),
                    ("A_lower_preplace", lower_preplace),
                    ("A_release", release),
                    ("A_neutral", neutral),
                )
            ),
        },
        {
            "priority": 4,
            "candidate_id": "intermediate_corridor_waypoint",
            "replacement_A_carry_mid_pose": entry.tolist(),
            "segments": _segments(
                (
                    ("A_lift", lift),
                    ("A_lower_corridor_entry", entry),
                    ("A_lower_carry_mid", lower_mid),
                    ("A_lower_preplace", lower_preplace),
                    ("A_release", release),
                    ("A_neutral", neutral),
                )
            ),
        },
    ]
    checks = {
        "exact_four_candidates": len(candidates) == 4,
        "fixed_priority_order": [item["priority"] for item in candidates]
        == [1, 2, 3, 4],
        "candidate_ids_unique": len({item["candidate_id"] for item in candidates})
        == 4,
        "r4_pose_exact": candidates[0]["segments"][1]["pose"] == list(
            R4_SUCCESSFUL_CARRY_MID
        ),
        "lower_height_exact": bool(lower_mid[2] == LOWER_CARRY_HEIGHT_M),
        "base_release_unchanged": all(
            quaternion_angular_error(
                next(
                    item["pose"]
                    for item in candidate["segments"]
                    if item["segment_id"] == "A_release"
                )[3:],
                release[3:],
            )
            <= 1e-12
            and np.allclose(
                next(
                    item["pose"]
                    for item in candidate["segments"]
                    if item["segment_id"] == "A_release"
                )[:3],
                release[:3],
                atol=1e-12,
                rtol=0.0,
            )
            for candidate in candidates
        ),
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "corridor_version": CORRIDOR_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_4",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "role": ROLE,
        "arm": ARM,
        "selection_rule": (
            "planner-only, fixed priority, select the first candidate whose entire "
            "qpos-chained route passes endpoint IK, collision and joint-margin audits"
        ),
        "execution_success_selection_forbidden": True,
        "endpoint_ik_cannot_be_replaced_by_waypoint_reachability": True,
        "candidate_limit": 4,
        "candidates": candidates,
        "source_evidence": {
            "revision4_successful_carry_mid": list(R4_SUCCESSFUL_CARRY_MID),
            "revision4_planner_status": R4_SUCCESSFUL_CARRY_MID_PLANNER_STATUS,
            "revision4_end_qpos_sha256": R4_SUCCESSFUL_CARRY_MID_END_QPOS_SHA256,
            "forensic_output_sha256": R4_FORENSIC_OUTPUT_SHA256,
        },
        "invariants": {
            "tray_changed": False,
            "arm_changed": False,
            "layout_changed": False,
            "object_slot_mapping_changed": False,
            "common_X_changed": False,
            "programs_changed": False,
            "final_verifier_changed": False,
            "automatic_retry": False,
            "recovery_attempts": 0,
        },
        "checks": checks,
        "pass": all(checks.values()),
    }
    payload["contract_sha256"] = _canonical_sha256(payload)
    return payload


def validate_f4_fixed_order_corridors_v10(value: Mapping[str, Any]) -> dict[str, Any]:
    result = json.loads(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    )
    digest = result.pop("contract_sha256", None)
    if not isinstance(digest, str) or digest != _canonical_sha256(result):
        raise ValueError("F4 corridor contract hash mismatch")
    if result.get("schema_version") != SCHEMA_VERSION or result.get("pass") is not True:
        raise ValueError("F4 corridor contract is invalid")
    if [item.get("priority") for item in result.get("candidates", [])] != [1, 2, 3, 4]:
        raise ValueError("F4 corridor priority changed")
    result["contract_sha256"] = digest
    return result


def apply_f4_corridor_candidate_v10(
    base_targets: Sequence[Mapping[str, Any]],
    *,
    selected_candidate_id: str,
    reference_A_base_targets: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Apply the A-selected carry waypoint uniformly to another role group."""

    role_base = _target_map(base_targets)
    reference = build_f4_fixed_order_corridors_v10(reference_A_base_targets)
    selected = [
        item
        for item in reference["candidates"]
        if item["candidate_id"] == selected_candidate_id
    ]
    if len(selected) != 1:
        raise ValueError("F4 selected corridor candidate is not frozen")
    reference_map = _target_map(reference_A_base_targets)
    reference_mid = reference_map["A_carry_mid"]
    replacement = _pose(
        selected[0]["replacement_A_carry_mid_pose"],
        "F4 selected replacement carry-mid",
    )
    delta = replacement[:3] - reference_mid[:3]
    role_prefix = next(iter(role_base)).split("_", 1)[0]
    expected = [
        f"{role_prefix}_pregrasp",
        f"{role_prefix}_grasp",
        f"{role_prefix}_lift",
        f"{role_prefix}_carry_mid",
        f"{role_prefix}_preplace",
        f"{role_prefix}_release",
        f"{role_prefix}_neutral",
    ]
    if set(role_base) != set(expected):
        raise ValueError("F4 role corridor requires one seven-target role group")
    if selected_candidate_id == "proven_branch_neutral_carry_pose":
        carry = role_base[f"{role_prefix}_neutral"].copy()
    else:
        carry = role_base[f"{role_prefix}_carry_mid"].copy()
        carry[:3] += delta
    # Candidate 1 carries the proven Revision-4 orientation; candidates 2–4
    # retain the current top-down orientation except candidate 2, whose exact
    # branch-neutral pose is itself the replacement.
    if selected_candidate_id in (
        "r4_successful_carry_orientation_and_corridor",
        "proven_branch_neutral_carry_pose",
    ):
        carry[3:] = replacement[3:]
    output = []
    for segment_id in expected:
        pose = carry if segment_id.endswith("_carry_mid") else role_base[segment_id]
        output.append({"segment_id": segment_id, "pose": pose.tolist()})
    return output


def audit_f4_corridor_planner_results_v10(
    contract: Mapping[str, Any],
    candidate_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    frozen = validate_f4_fixed_order_corridors_v10(contract)
    receipts = list(candidate_receipts)
    if len(receipts) > 4:
        raise ValueError("F4 corridor audit exceeds four candidates")
    expected = [item["candidate_id"] for item in frozen["candidates"]]
    actual = [str(item.get("candidate_id")) for item in receipts]
    if actual != expected[: len(actual)]:
        raise ValueError("F4 corridor candidates were not tested in fixed order")
    passed = []
    normalized = []
    terminal_seen = False
    for receipt in receipts:
        segments = list(receipt.get("segment_receipts", []))
        checks = {
            "endpoint_ik_all": bool(segments)
            and all(item.get("endpoint_ik_pass") is True for item in segments),
            "collision_all": bool(segments)
            and all(item.get("collision_pass") is True for item in segments),
            "joint_margin_all": bool(segments)
            and all(item.get("joint_margin_pass") is True for item in segments),
            "qpos_chain_continuous": bool(segments)
            and all(item.get("chain_continuity_pass") is True for item in segments),
            "execution_attempt_count_zero": int(
                receipt.get("execution_attempt_count", -1)
            )
            == 0,
            "fresh_scene": receipt.get("fresh_scene") is True,
            "cleanup_pass": receipt.get("cleanup_pass") is True,
        }
        item_pass = all(checks.values())
        if terminal_seen:
            raise ValueError("F4 tested a later corridor after a passing first candidate")
        if item_pass:
            passed.append(str(receipt["candidate_id"]))
            terminal_seen = True
        normalized.append(
            {
                "candidate_id": str(receipt["candidate_id"]),
                "segment_receipts": segments,
                "checks": checks,
                "pass": item_pass,
            }
        )
    selected = passed[0] if len(passed) == 1 else None
    all_four_failed = len(receipts) == 4 and not passed
    checks = {
        "fixed_order": actual == expected[: len(actual)],
        "at_most_one_pass": len(passed) <= 1,
        "first_pass_is_terminal": not passed or actual[-1] == passed[0],
        "no_execution_selection": all(
            item["checks"]["execution_attempt_count_zero"] for item in normalized
        ),
    }
    result = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "corridor_version": CORRIDOR_VERSION,
        "contract_sha256": frozen["contract_sha256"],
        "candidate_receipts": normalized,
        "selected_candidate_id": selected,
        "A_execution_allowed": selected is not None and all(checks.values()),
        "layout_impact_review_required": all_four_failed,
        "checks": checks,
        "pass": selected is not None and all(checks.values()),
        "automatic_retry": False,
        "recovery_attempts": 0,
    }
    result["receipt_sha256"] = _canonical_sha256(result)
    return result


__all__ = [
    "CORRIDOR_VERSION",
    "audit_f4_corridor_planner_results_v10",
    "apply_f4_corridor_candidate_v10",
    "build_f4_fixed_order_corridors_v10",
    "validate_f4_fixed_order_corridors_v10",
]
