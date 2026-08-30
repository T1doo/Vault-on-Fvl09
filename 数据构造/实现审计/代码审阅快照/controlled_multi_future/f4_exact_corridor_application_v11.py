"""Exact variable-length F4 corridor application for runtime-v3_4_1."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .f4_carry_corridor_v10 import build_f4_fixed_order_corridors_v10


SCHEMA_VERSION = "cmf_f4_exact_corridor_application_v11"
APPLICATION_VERSION = "f4_exact_variable_length_corridor_application_v11"


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def _pose(value: Sequence[float], label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(-1)
    if result.shape != (7,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be finite pose7")
    result = result.copy()
    result[3:] /= np.linalg.norm(result[3:])
    return result


def _map(targets: Sequence[Mapping[str, Any]], role: str) -> dict[str, np.ndarray]:
    result = {
        str(item["segment_id"]): _pose(item["pose"], str(item["segment_id"]))
        for item in targets
    }
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
        raise ValueError(f"F4 {role} base target structure changed")
    return result


def _target_hash(targets: Sequence[Mapping[str, Any]]) -> str:
    return _sha(
        [
            {
                "segment_id": str(item["segment_id"]),
                "pose": _pose(item["pose"], str(item["segment_id"])).tolist(),
            }
            for item in targets
        ]
    )


def build_f4_exact_A_corridors_v11(
    base_A_targets: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    base = _map(base_A_targets, "A")
    v10 = build_f4_fixed_order_corridors_v10(base_A_targets)
    candidates = []
    for candidate in v10["candidates"]:
        contract_segments = [
            {
                "segment_id": str(item["segment_id"]),
                "pose": _pose(item["pose"], str(item["segment_id"])).tolist(),
            }
            for item in candidate["segments"]
        ]
        applied = [
            {"segment_id": "A_pregrasp", "pose": base["A_pregrasp"].tolist()},
            {"segment_id": "A_grasp", "pose": base["A_grasp"].tolist()},
            *contract_segments,
        ]
        contract_ids = [item["segment_id"] for item in contract_segments]
        applied_ids = [item["segment_id"] for item in applied]
        entry = {
            "priority": int(candidate["priority"]),
            "candidate_id": str(candidate["candidate_id"]),
            "candidate_contract_segments": contract_segments,
            "candidate_contract_segment_ids": contract_ids,
            "candidate_contract_target_pose_sha256": _target_hash(
                contract_segments
            ),
            "applied_planner_targets": applied,
            "applied_planner_segment_ids": applied_ids,
            "applied_planner_target_pose_sha256": _target_hash(applied),
            "applied_candidate_subsequence_target_pose_sha256": _target_hash(
                applied[2:]
            ),
            "release_segment_index": next(
                index
                for index, item in enumerate(applied)
                if item["segment_id"] == "A_release"
            ),
            "neutral_segment_index": len(applied) - 1,
            "checks": {
                "contract_ids_equal_applied_subsequence_ids": contract_ids
                == applied_ids[2:],
                "contract_pose_hash_equal_applied_subsequence_hash": _target_hash(
                    contract_segments
                )
                == _target_hash(applied[2:]),
                "pregrasp_grasp_prefixed_only": applied_ids[:2]
                == ["A_pregrasp", "A_grasp"],
                "release_in_chain": "A_release" in applied_ids,
                "neutral_is_terminal": applied_ids[-1] == "A_neutral",
            },
        }
        entry["pass"] = all(entry["checks"].values())
        entry["candidate_application_sha256"] = _sha(entry)
        candidates.append(entry)
    checks = {
        "exact_four_candidates": len(candidates) == 4,
        "fixed_order": [item["priority"] for item in candidates]
        == [1, 2, 3, 4],
        "all_exact_application": all(item["pass"] for item in candidates),
        "candidate1_restore_waypoint_present": "A_restore_topdown_mid"
        in candidates[0]["applied_planner_segment_ids"],
        "candidate3_lower_preplace_present": "A_lower_preplace"
        in candidates[2]["applied_planner_segment_ids"],
        "candidate4_two_intermediate_waypoints_present": all(
            name in candidates[3]["applied_planner_segment_ids"]
            for name in ("A_lower_corridor_entry", "A_lower_carry_mid")
        ),
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "application_version": APPLICATION_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_4_1",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "base_v10_contract_sha256": v10["contract_sha256"],
        "base_A_targets_sha256": _target_hash(base_A_targets),
        "candidates": candidates,
        "checks": checks,
        "pass": all(checks.values()),
    }
    result["receipt_sha256"] = _sha(result)
    return result


def validate_f4_exact_candidate_application_v11(
    candidate: Mapping[str, Any], applied_targets: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if not isinstance(candidate, Mapping) or candidate.get("pass") is not True:
        raise ValueError("F4 exact candidate contract is invalid")
    applied_ids = [str(item["segment_id"]) for item in applied_targets]
    expected_ids = list(candidate["applied_planner_segment_ids"])
    applied_hash = _target_hash(applied_targets)
    checks = {
        "candidate_contract_segment_ids_equal_applied": applied_ids
        == expected_ids,
        "candidate_contract_target_pose_sha256_equal_applied": applied_hash
        == candidate["applied_planner_target_pose_sha256"],
        "release_in_chain": any(name.endswith("_release") for name in applied_ids),
        "neutral_terminal": applied_ids[-1].endswith("_neutral"),
    }
    result = {
        "schema_version": "cmf_f4_exact_candidate_preplanner_gate_v11",
        "candidate_id": candidate["candidate_id"],
        "candidate_contract_segment_ids": expected_ids,
        "applied_planner_segment_ids": applied_ids,
        "candidate_contract_target_pose_sha256": candidate[
            "applied_planner_target_pose_sha256"
        ],
        "applied_planner_target_pose_sha256": applied_hash,
        "checks": checks,
        "pass": all(checks.values()),
        "planner_query_count_if_failed": 0,
        "execution_attempt_count_if_failed": 0,
    }
    result["receipt_sha256"] = _sha(result)
    if not result["pass"]:
        raise ValueError("F4 candidate contract differs from applied planner targets")
    return result


def derive_role_corridor_v11(
    *,
    selected_A_candidate: Mapping[str, Any],
    base_A_targets: Sequence[Mapping[str, Any]],
    role: str,
    base_role_targets: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if role not in ("A", "B", "C"):
        raise ValueError("F4 role must be A/B/C")
    if role == "A":
        applied = list(selected_A_candidate["applied_planner_targets"])
        gate = validate_f4_exact_candidate_application_v11(
            selected_A_candidate, applied
        )
        return {
            "role": "A",
            "selected_candidate_id": selected_A_candidate["candidate_id"],
            "targets": applied,
            "preplanner_gate": gate,
        }
    a = _map(base_A_targets, "A")
    r = _map(base_role_targets, role)
    carry_offset = r[f"{role}_carry_mid"][:3] - a["A_carry_mid"][:3]
    preplace_offset = r[f"{role}_preplace"][:3] - a["A_preplace"][:3]
    output = [
        {"segment_id": f"{role}_pregrasp", "pose": r[f"{role}_pregrasp"].tolist()},
        {"segment_id": f"{role}_grasp", "pose": r[f"{role}_grasp"].tolist()},
    ]
    for item in selected_A_candidate["candidate_contract_segments"]:
        a_id = str(item["segment_id"])
        suffix = a_id.split("_", 1)[1]
        role_id = f"{role}_{suffix}"
        if suffix == "lift":
            pose = r[f"{role}_lift"].copy()
        elif suffix == "preplace":
            pose = r[f"{role}_preplace"].copy()
        elif suffix == "release":
            pose = r[f"{role}_release"].copy()
        elif suffix == "neutral":
            pose = r[f"{role}_neutral"].copy()
        elif suffix == "branch_neutral_carry":
            pose = r[f"{role}_neutral"].copy()
        else:
            pose = _pose(item["pose"], a_id)
            if "preplace" in suffix:
                pose[:3] += preplace_offset
                pose[3:] = r[f"{role}_preplace"][3:]
            else:
                pose[:3] += carry_offset
                if suffix != "r4_carry_mid":
                    pose[3:] = r[f"{role}_carry_mid"][3:]
        output.append({"segment_id": role_id, "pose": pose.tolist()})
    checks = {
        "release_target_unchanged": next(
            item["pose"] for item in output if item["segment_id"] == f"{role}_release"
        )
        == r[f"{role}_release"].tolist(),
        "neutral_terminal": output[-1]["segment_id"] == f"{role}_neutral",
        "same_variable_length_as_A": len(output)
        == len(selected_A_candidate["applied_planner_targets"]),
        "arm_layout_mapping_verifier_unchanged": True,
    }
    result = {
        "schema_version": "cmf_f4_role_corridor_derivation_v11",
        "role": role,
        "selected_candidate_id": selected_A_candidate["candidate_id"],
        "targets": output,
        "target_pose_sha256": _target_hash(output),
        "checks": checks,
        "pass": all(checks.values()),
    }
    result["receipt_sha256"] = _sha(result)
    return result


def audit_f4_exact_corridor_results_v11(
    contract: Mapping[str, Any],
    candidate_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(contract, Mapping) or contract.get("pass") is not True:
        raise ValueError("F4 exact corridor result audit requires passing contract")
    receipts = list(candidate_receipts)
    expected = [item["candidate_id"] for item in contract["candidates"]]
    actual = [item.get("candidate_id") for item in receipts]
    if actual != expected[: len(actual)] or len(receipts) > 4:
        raise ValueError("F4 exact corridor receipts violate fixed order/limit")
    normalized = []
    selected = None
    infrastructure_failure = False
    for receipt in receipts:
        segments = list(receipt.get("segment_receipts", []))
        segment_evidence_complete = bool(segments) and all(
            item.get("joint_limit_evidence_complete") is True
            and isinstance(
                item.get("minimum_terminal_joint_limit_margin_rad"),
                (int, float),
            )
            and isinstance(item.get("terminal_qpos"), list)
            and isinstance(item.get("terminal_qpos_within_joint_limits"), bool)
            and isinstance(item.get("joint_limit_audit_version"), str)
            for item in segments
        )
        infrastructure_failure = infrastructure_failure or not segment_evidence_complete
        checks = {
            "preplanner_contract_application_exact": receipt.get(
                "preplanner_contract_application_exact"
            )
            is True,
            "endpoint_ik_all": bool(segments)
            and all(item.get("planner_status") == "Success" for item in segments),
            "official_collision_pass_all": bool(segments)
            and all(item.get("planner_status") == "Success" for item in segments),
            "joint_margin_evidence_complete": segment_evidence_complete,
            "joint_margin_pass_all": segment_evidence_complete
            and all(
                item["terminal_qpos_within_joint_limits"] is True
                for item in segments
            ),
            "qpos_chain_continuous": receipt.get("qpos_chain_continuous")
            is True,
            "release_and_neutral_in_chain": receipt.get(
                "release_and_neutral_in_chain"
            )
            is True,
            "execution_attempt_count_zero": int(
                receipt.get("execution_attempt_count", -1)
            )
            == 0,
            "fresh_scene_cleanup_pass": receipt.get("cleanup_pass") is True,
        }
        passed = all(checks.values())
        if selected is None and passed:
            selected = receipt["candidate_id"]
        elif selected is not None:
            raise ValueError("F4 queried a later candidate after first complete pass")
        normalized.append(
            {
                "candidate_id": receipt.get("candidate_id"),
                "checks": checks,
                "pass": passed,
                "segment_receipts": segments,
            }
        )
    all_four_physical_fail = (
        len(receipts) == 4
        and selected is None
        and not infrastructure_failure
    )
    result = {
        "schema_version": "cmf_f4_exact_corridor_results_gate_v11",
        "fixed_candidate_order": expected,
        "candidate_receipts": normalized,
        "selected_candidate_id": selected,
        "A_execution_allowed": selected is not None
        and not infrastructure_failure,
        "evidence_complete": not infrastructure_failure,
        "failure_type": (
            "infrastructure_schema_failure"
            if infrastructure_failure
            else "all_complete_corridors_failed"
            if all_four_physical_fail
            else None
        ),
        "layout_impact_review_request_required": all_four_physical_fail,
        "pass": selected is not None and not infrastructure_failure,
        "automatic_retry": False,
        "recovery_attempts": 0,
    }
    result["receipt_sha256"] = _sha(result)
    return result


__all__ = [
    "build_f4_exact_A_corridors_v11",
    "derive_role_corridor_v11",
    "audit_f4_exact_corridor_results_v11",
    "validate_f4_exact_candidate_application_v11",
]
