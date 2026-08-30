"""Fresh-scene tolerant F4 candidate equivalence for Stage 0 smoke.

The frozen semantic object is the candidate ID and ordered segment program.
Fresh SAPIEN reconstructions may differ by sub-micrometre floating-point pose
noise even after the physical-anchor Gate passes, so raw JSON pose hashes are
audit evidence but are not a semantic identity test.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .anchor import quaternion_angular_error


SCHEMA_VERSION = "cmf_f4_candidate_equivalence_v12"
EQUIVALENCE_VERSION = "f4_stage0_candidate_structure_exact_pose_tolerant_v1"
POSITION_ATOL_M = 1.0e-5
ORIENTATION_ATOL_RAD = 1.0e-5


def _sha(value: Any) -> str:
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
        raise ValueError(f"{label} must be a finite pose7")
    result = result.copy()
    norm = float(np.linalg.norm(result[3:]))
    if norm <= 0:
        raise ValueError(f"{label} quaternion has zero norm")
    result[3:] /= norm
    return result


def candidate_design_payload(candidate: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "priority",
        "candidate_id",
        "candidate_contract_segment_ids",
        "applied_planner_segment_ids",
        "release_segment_index",
        "neutral_segment_index",
    }
    if not isinstance(candidate, Mapping) or not required.issubset(candidate):
        raise ValueError("F4 candidate lacks its frozen structural fields")
    return {
        "equivalence_version": EQUIVALENCE_VERSION,
        "priority": int(candidate["priority"]),
        "candidate_id": str(candidate["candidate_id"]),
        "candidate_contract_segment_ids": list(
            candidate["candidate_contract_segment_ids"]
        ),
        "applied_planner_segment_ids": list(
            candidate["applied_planner_segment_ids"]
        ),
        "release_segment_index": int(candidate["release_segment_index"]),
        "neutral_segment_index": int(candidate["neutral_segment_index"]),
        "arm": "right",
        "layout_changed": False,
        "release_target_semantics_changed": False,
    }


def candidate_design_sha256(candidate: Mapping[str, Any]) -> str:
    return _sha(candidate_design_payload(candidate))


def _targets(candidate: Mapping[str, Any], label: str) -> list[dict[str, Any]]:
    values = candidate.get("applied_planner_targets")
    if not isinstance(values, list) or not values:
        raise ValueError(f"{label} lacks applied planner targets")
    result = []
    for index, item in enumerate(values):
        if not isinstance(item, Mapping) or not isinstance(
            item.get("segment_id"), str
        ):
            raise ValueError(f"{label} target {index} is invalid")
        result.append(
            {
                "segment_id": item["segment_id"],
                "pose": _pose(item.get("pose"), f"{label}:{index}"),
            }
        )
    return result


def audit_f4_candidate_equivalence_v12(
    frozen_candidate: Mapping[str, Any],
    reconstructed_candidate: Mapping[str, Any],
    *,
    position_atol_m: float = POSITION_ATOL_M,
    orientation_atol_rad: float = ORIENTATION_ATOL_RAD,
) -> dict[str, Any]:
    if not (0 < position_atol_m <= 1.0e-4):
        raise ValueError("F4 candidate position tolerance is outside pre-Stage0 bound")
    if not (0 < orientation_atol_rad <= 1.0e-4):
        raise ValueError("F4 candidate orientation tolerance is outside pre-Stage0 bound")
    frozen_design = candidate_design_payload(frozen_candidate)
    reconstructed_design = candidate_design_payload(reconstructed_candidate)
    frozen_targets = _targets(frozen_candidate, "frozen")
    current_targets = _targets(reconstructed_candidate, "reconstructed")
    target_count_equal = len(frozen_targets) == len(current_targets)
    ids_equal = target_count_equal and all(
        left["segment_id"] == right["segment_id"]
        for left, right in zip(frozen_targets, current_targets)
    )
    pose_errors = []
    if target_count_equal and ids_equal:
        for left, right in zip(frozen_targets, current_targets):
            pose_errors.append(
                {
                    "segment_id": left["segment_id"],
                    "position_error_m": float(
                        np.linalg.norm(left["pose"][:3] - right["pose"][:3])
                    ),
                    "orientation_error_rad": quaternion_angular_error(
                        left["pose"][3:], right["pose"][3:]
                    ),
                }
            )
    maximum_position_error = (
        max(item["position_error_m"] for item in pose_errors)
        if pose_errors
        else None
    )
    maximum_orientation_error = (
        max(item["orientation_error_rad"] for item in pose_errors)
        if pose_errors
        else None
    )
    checks = {
        "candidate_design_payload_exact": frozen_design == reconstructed_design,
        "candidate_design_sha256_exact": candidate_design_sha256(
            frozen_candidate
        )
        == candidate_design_sha256(reconstructed_candidate),
        "target_count_exact": target_count_equal,
        "ordered_segment_ids_exact": ids_equal,
        "positions_within_preregistered_tolerance": maximum_position_error
        is not None
        and maximum_position_error <= position_atol_m,
        "orientations_within_preregistered_tolerance": maximum_orientation_error
        is not None
        and maximum_orientation_error <= orientation_atol_rad,
        "raw_pose_hash_is_not_semantic_identity": True,
        "layout_arm_release_semantics_unchanged": True,
    }
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "equivalence_version": EQUIVALENCE_VERSION,
        "candidate_id": frozen_design["candidate_id"],
        "frozen_candidate_design_sha256": candidate_design_sha256(
            frozen_candidate
        ),
        "reconstructed_candidate_design_sha256": candidate_design_sha256(
            reconstructed_candidate
        ),
        "frozen_raw_candidate_application_sha256": frozen_candidate.get(
            "candidate_application_sha256"
        ),
        "reconstructed_raw_candidate_application_sha256": (
            reconstructed_candidate.get("candidate_application_sha256")
        ),
        "raw_candidate_hash_equal_diagnostic": frozen_candidate.get(
            "candidate_application_sha256"
        )
        == reconstructed_candidate.get("candidate_application_sha256"),
        "position_atol_m": float(position_atol_m),
        "orientation_atol_rad": float(orientation_atol_rad),
        "maximum_position_error_m": maximum_position_error,
        "maximum_orientation_error_rad": maximum_orientation_error,
        "per_segment_pose_errors": pose_errors,
        "checks": checks,
        "pass": all(checks.values()),
        "formal_data": False,
        "stage0_data": False,
    }
    receipt["receipt_sha256"] = _sha(receipt)
    return receipt


__all__ = [
    "EQUIVALENCE_VERSION",
    "ORIENTATION_ATOL_RAD",
    "POSITION_ATOL_M",
    "audit_f4_candidate_equivalence_v12",
    "candidate_design_payload",
    "candidate_design_sha256",
]
