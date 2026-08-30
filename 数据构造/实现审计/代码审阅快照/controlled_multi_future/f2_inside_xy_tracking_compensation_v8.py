"""Pure-CPU, evidence-bound F2 revision-8 XY-only compensation.

Revision 7 applied a frozen full-SE(3) correction to the first F2-inside
command.  The command was delivered exactly, but CuRobo returned IK_FAIL on
that first endpoint.  This source-distinct proposal keeps the revision-6
planner-successful world-z and orientation, takes only x/y from the frozen
full-compensated *actor* pose, and converts that single actor command back to
one EEF command through the frozen revision-6 ``T_eef_actor`` transform.

The helper changes only inside target zero.  It performs no artifact I/O,
candidate search, fallback, online adaptation, planner query, scene creation,
GPU work, or collection authorization.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .anchor import quaternion_angular_error
from .current_hasher import hash_json
from .f2_inside_tracking_compensation_v7 import (
    R6_BOX_POSE,
    R6_CAN_HALF_EXTENTS_M,
    R6_CAN_LOCAL_GEOMETRY_CENTER_M,
    R6_CAVITY_LOWER_M,
    R6_CAVITY_UPPER_M,
    R6_DESIRED_FINAL_FIT_SHA256,
    R6_DESIRED_PRE_RELEASE_ACTOR_POSE,
    R6_DESIRED_PRE_RELEASE_ACTOR_SHA256,
    R6_DESIRED_ROUTE_SHA256,
    R6_DESIRED_TARGET_ACTOR_SHA256,
    R6_EVIDENCE,
    R6_ORIGINAL_FIRST_EEF_COMMAND,
    R6_REALIZED_PRE_RELEASE_ACTOR_POSE,
    R6_TARGET_SHA256,
)
from .geometry import (
    compose_pose,
    matrix_pose,
    obb_corners,
    pose_matrix,
    relative_pose,
)


SCHEMA_VERSION = "cmf_f2_inside_xy_tracking_compensation_v8"
DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_3"
IMPLEMENTATION_PROPOSAL = (
    "f2_r8_r6_r7_evidence_fixed_xy_only_inside_first_command_compensation"
)

PROGRAM_ID = "F2-inside"
SEGMENT_IDS = (
    "inside_drop_release_10cm",
    "inside_drop_retreat_16cm",
    "f2_rest",
)
CHANGED_TARGET_INDICES = (0,)
MINIMUM_RIM_CLEARANCE_M = 0.020

R7_EVIDENCE = {
    "namespace": "nonformal_runtime_v3_3_f2_root_seed20260829_revision7_run1_anygpu",
    "implementation_source_sha256": "2ed82e7a5e6a2a03a3cf7b1cfb3dde82acba637f24c574c64c47099516ee72c8",
    "evidence_manifest_file_sha256": "d6a2a237ededcfbf773de174440ac96e3e7e02e569b6cf6eb5aa707862d997a5",
    "evidence_tree_sha256": "3cc23996b115d3f23cc3aa2a551ffd2ad7543d7b072fa7581e50027292641cca",
    "evidence_file_count": 28,
    "impact_review_file_sha256": "7668a2b0138db4100827e4baa1ccb7eea071e0e8ad7bfd066ae2b7d6767e3804",
    "top_receipt_file_sha256": "2842841550c9e8e5569e73ce33c211aa859c711cfeee5b4b97b02ceebdd1e4a2",
    "root_receipt_file_sha256": "f4cb6fc0168f94687284a454856c55b9416f198daf0fc9f136b0bb9365b00276",
    "inside_preflight_receipt_file_sha256": "c9700a9ab244d3961bd0c818d681b75dfc6975896c48475513bba4e0d1f545a7",
    "inside_preflight_trace_sha256": "7995804a36469165f7a063bbc0b8919d3742e336cc154957cf5b5da2dd0e5f3d",
    "family_suffix_gate_file_sha256": "0aa84cc91616391efa00817ce19acbca0f089805b00a1af52d3fd9775d7692d5",
    "guard_file_sha256": "b41127a72dcb2042a18b742d79f945aa33d0861fd9ed9a1a3eedf7be35400f68",
    "authorization_receipt_sha256": "66098bf9dfc1dbd3610837edccb90333bb94fd6c3e11c8cd01e4d8f103bd91f7",
    "planner_query_count": 30,
    "execution_attempt_count": 0,
    "recovery_attempt_count": 0,
    "inside_failure_segment": "inside_drop_release_10cm",
    "inside_failure_query_id": 1,
    "inside_failure_status": "MotionGenStatus.IK_FAIL",
    "inside_failure_attempts": 10,
    "full_se3_compensation_receipt_sha256_reconstructed_not_persisted": "1df583850b43faceac8c2cbdb7f26f3b43a914edd152bcb9d78cb03038b06ccb",
    "normal_planner_false_partial_receipt_was_persisted": False,
}

R7_FULL_SE3_COMPENSATED_ACTOR_POSE = (
    -0.2793459837400959,
    -0.1566790261836197,
    0.9458366873638312,
    0.008754034414567177,
    -0.7176258304696753,
    0.0426821099012443,
    -0.6950645810416147,
)
R7_FULL_SE3_COMPENSATED_EEF_POSE = (
    -0.28812338400652177,
    -0.3473733292264533,
    0.930685147856833,
    0.6539396113143634,
    0.310157936702657,
    0.24979562519322943,
    0.6432473744125923,
)
R7_APPLIED_GOAL_FLOAT32 = (
    -0.28812336921691895,
    -0.3473733365535736,
    0.9306851625442505,
    0.6539396047592163,
    0.3101579248905182,
    0.24979563057422638,
    0.6432473659515381,
)

EXPECTED_XY_ONLY_ACTOR_COMMAND_POSE = (
    -0.2793459837400959,
    -0.1566790261836197,
    0.9432698593315743,
    7.850462293418875e-17,
    -0.7071067811865476,
    7.850462293418875e-17,
    -0.7071067811865475,
)
EXPECTED_XY_ONLY_FIRST_EEF_COMMAND_POSE = (
    -0.27877971848932753,
    -0.3481850917100642,
    0.9419717072948476,
    0.6530027337490016,
    0.2699005597902242,
    0.2698351383914301,
    0.6541636764835939,
)

# Internal deterministic derivation checks, not scientific/verifier thresholds.
DERIVATION_POSITION_ATOL_M = 1e-12
DERIVATION_ORIENTATION_ATOL_RAD = 1e-12


def _pose(value: Sequence[float], *, label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(-1)
    if result.shape != (7,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be one finite 7-D pose")
    norm = float(np.linalg.norm(result[3:]))
    if norm <= 1e-12:
        raise ValueError(f"{label} quaternion norm must be positive")
    result = result.copy()
    result[3:] /= norm
    return result


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _geometry_audit(actor_pose: Sequence[float]) -> dict[str, Any]:
    actor = _pose(actor_pose, label="F2 r8 actor command")
    geometry_center = compose_pose(
        actor,
        [*R6_CAN_LOCAL_GEOMETRY_CENTER_M, 1.0, 0.0, 0.0, 0.0],
    )
    corners = obb_corners(geometry_center, R6_CAN_HALF_EXTENTS_M)
    homogeneous = np.concatenate(
        (corners, np.ones((len(corners), 1), dtype=np.float64)), axis=1
    )
    local = (
        np.linalg.inv(pose_matrix(R6_BOX_POSE)) @ homogeneous.T
    ).T[:, :3]
    lower = np.asarray(R6_CAVITY_LOWER_M, dtype=np.float64)
    upper = np.asarray(R6_CAVITY_UPPER_M, dtype=np.float64)
    opening_axes = (0, 2)
    opening_projection_inside = bool(
        np.all(np.min(local[:, opening_axes], axis=0) >= lower[list(opening_axes)])
        and np.all(
            np.max(local[:, opening_axes], axis=0) <= upper[list(opening_axes)]
        )
    )
    rim_clearance = float(np.min(local[:, 1]) - upper[1])
    checks = {
        "opening_projection_inside": opening_projection_inside,
        "rim_clearance_at_least_20mm": (
            rim_clearance >= MINIMUM_RIM_CLEARANCE_M
        ),
    }
    return {
        "local_corner_min": np.min(local, axis=0).tolist(),
        "local_corner_max": np.max(local, axis=0).tolist(),
        "cavity_lower": lower.tolist(),
        "cavity_upper": upper.tolist(),
        "rim_clearance_m": rim_clearance,
        "rim_clearance_headroom_over_20mm_m": (
            rim_clearance - MINIMUM_RIM_CLEARANCE_M
        ),
        "checks": checks,
        "pass": all(checks.values()),
    }


def _derive_xy_only_contract() -> dict[str, Any]:
    desired_actor = _pose(
        R6_DESIRED_PRE_RELEASE_ACTOR_POSE,
        label="r6 desired pre-release actor",
    )
    realized_actor = _pose(
        R6_REALIZED_PRE_RELEASE_ACTOR_POSE,
        label="r6 realized pre-release actor",
    )
    original_eef = _pose(
        R6_ORIGINAL_FIRST_EEF_COMMAND,
        label="r6 original first EEF command",
    )

    full_actor = matrix_pose(
        pose_matrix(desired_actor)
        @ np.linalg.inv(pose_matrix(realized_actor))
        @ pose_matrix(desired_actor)
    )
    if not np.allclose(
        full_actor,
        np.asarray(R7_FULL_SE3_COMPENSATED_ACTOR_POSE, dtype=np.float64),
        atol=1e-12,
        rtol=0.0,
    ):
        raise RuntimeError("F2 r8 full actor correction differs from r7 evidence")
    if not np.array_equal(
        np.asarray(R7_FULL_SE3_COMPENSATED_EEF_POSE, dtype=np.float32),
        np.asarray(R7_APPLIED_GOAL_FLOAT32, dtype=np.float32),
    ):
        raise RuntimeError("F2 r8 r7 applied-goal evidence is inconsistent")

    xy_actor = desired_actor.copy()
    xy_actor[:2] = full_actor[:2]
    frozen_t_eef_actor = relative_pose(original_eef, desired_actor)
    xy_eef = matrix_pose(
        pose_matrix(xy_actor) @ np.linalg.inv(pose_matrix(frozen_t_eef_actor))
    )
    implied_actor = compose_pose(xy_eef, frozen_t_eef_actor)
    position_error = float(np.linalg.norm(implied_actor[:3] - xy_actor[:3]))
    orientation_error = quaternion_angular_error(
        implied_actor[3:], xy_actor[3:]
    )
    if (
        position_error > DERIVATION_POSITION_ATOL_M
        or orientation_error > DERIVATION_ORIENTATION_ATOL_RAD
    ):
        raise RuntimeError("F2 r8 actor-to-EEF inversion is inconsistent")
    if not np.allclose(
        xy_actor,
        np.asarray(EXPECTED_XY_ONLY_ACTOR_COMMAND_POSE, dtype=np.float64),
        atol=1e-12,
        rtol=0.0,
    ) or not np.allclose(
        xy_eef,
        np.asarray(EXPECTED_XY_ONLY_FIRST_EEF_COMMAND_POSE, dtype=np.float64),
        atol=1e-12,
        rtol=0.0,
    ):
        raise RuntimeError("F2 r8 fixed XY-only target changed")

    observed_world_error = (
        pose_matrix(realized_actor) @ np.linalg.inv(pose_matrix(desired_actor))
    )
    predicted_realized_actor = matrix_pose(
        observed_world_error @ pose_matrix(xy_actor)
    )
    command_geometry = _geometry_audit(xy_actor)
    if command_geometry["pass"] is not True:
        raise RuntimeError("F2 r8 XY-only command fails opening/rim geometry")
    predicted_geometry = _geometry_audit(predicted_realized_actor)
    return {
        "desired_actor": desired_actor,
        "realized_actor": realized_actor,
        "original_eef": original_eef,
        "full_actor": full_actor,
        "xy_actor": xy_actor,
        "frozen_t_eef_actor": frozen_t_eef_actor,
        "xy_eef": xy_eef,
        "implied_actor": implied_actor,
        "position_error": position_error,
        "orientation_error": orientation_error,
        "observed_world_error": observed_world_error,
        "predicted_realized_actor": predicted_realized_actor,
        "predicted_position_error": float(
            np.linalg.norm(predicted_realized_actor[:3] - desired_actor[:3])
        ),
        "predicted_orientation_error": quaternion_angular_error(
            predicted_realized_actor[3:], desired_actor[3:]
        ),
        "command_geometry": command_geometry,
        "predicted_geometry": predicted_geometry,
    }


def build_f2_inside_xy_tracking_compensation_v8(
    *,
    program_id: str,
    original_targets: Sequence[Mapping[str, Any]],
    desired_route: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return the one frozen XY-only target and a self-hashed receipt."""

    if program_id != PROGRAM_ID:
        raise ValueError("F2 r8 XY-only compensation is inside-only")
    if not isinstance(desired_route, Mapping):
        raise ValueError("F2 r8 desired route must be a mapping")
    targets = json.loads(
        json.dumps(
            list(original_targets),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
        )
    )
    if len(targets) != 3 or tuple(
        item.get("segment_id") for item in targets
    ) != SEGMENT_IDS:
        raise ValueError("F2 r8 requires the exact three inside segments")
    if desired_route.get("relation") != "inside" or desired_route.get(
        "release_target_index"
    ) != 0:
        raise ValueError("F2 r8 desired route identity changed")
    if hash_json(desired_route.get("target_actor_pose")) != R6_DESIRED_TARGET_ACTOR_SHA256:
        raise ValueError("F2 r8 desired final actor target changed")
    if (
        hash_json(desired_route.get("pre_release_actor_pose"))
        != R6_DESIRED_PRE_RELEASE_ACTOR_SHA256
    ):
        raise ValueError("F2 r8 desired pre-release actor target changed")
    if hash_json(desired_route.get("final_target_fit")) != R6_DESIRED_FINAL_FIT_SHA256:
        raise ValueError("F2 r8 desired cavity fit changed")
    if hash_json(desired_route.get("targets")) != hash_json(targets):
        raise ValueError("F2 r8 desired route targets differ from planner inputs")

    original_target_hashes = [hash_json(item) for item in targets]
    original_targets_sha256 = hash_json(targets)
    desired_route_sha256 = hash_json(desired_route)
    frozen = _derive_xy_only_contract()
    targets[0]["pose"] = frozen["xy_eef"].tolist()
    output_target_hashes = [hash_json(item) for item in targets]
    changed_indices = [
        index
        for index, (before, after) in enumerate(
            zip(original_target_hashes, output_target_hashes)
        )
        if before != after
    ]
    if changed_indices != list(CHANGED_TARGET_INDICES):
        raise RuntimeError("F2 r8 changed target indices differ from [0]")
    if targets[1] != list(original_targets)[1] or targets[2] != list(
        original_targets
    )[2]:
        raise RuntimeError("F2 r8 mutated retreat or rest")

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_proposal": IMPLEMENTATION_PROPOSAL,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "program_id": PROGRAM_ID,
        "source_evidence": {
            "revision6": dict(R6_EVIDENCE),
            "revision7": dict(R7_EVIDENCE),
        },
        "formula": {
            "full_actor": "A_full = A_desired @ inverse(A_realized_r6) @ A_desired",
            "xy_actor": "A_xy = [A_full.x, A_full.y, A_desired.z, A_desired.quaternion]",
            "frozen_grasp": "T_eef_actor = inverse(T_world_eef_r6) @ T_world_actor_desired",
            "eef": "T_world_eef_xy = T_world_actor_xy @ inverse(T_eef_actor)",
        },
        "r6_desired_pre_release_actor_pose": frozen["desired_actor"].tolist(),
        "r6_realized_pre_release_actor_pose": frozen["realized_actor"].tolist(),
        "r6_planner_successful_first_eef_command_pose": frozen[
            "original_eef"
        ].tolist(),
        "r7_full_se3_compensated_actor_pose": frozen["full_actor"].tolist(),
        "r7_full_se3_compensated_eef_pose": list(
            R7_FULL_SE3_COMPENSATED_EEF_POSE
        ),
        "r7_applied_goal_float32": list(R7_APPLIED_GOAL_FLOAT32),
        "r7_full_se3_endpoint_abandoned": True,
        "r7_full_se3_target_reused": False,
        "xy_only_actor_command_pose": frozen["xy_actor"].tolist(),
        "frozen_t_eef_actor": frozen["frozen_t_eef_actor"].tolist(),
        "xy_only_first_eef_command_pose": frozen["xy_eef"].tolist(),
        "actor_pose_implied_by_xy_only_eef": frozen["implied_actor"].tolist(),
        "actor_eef_derivation_consistency": {
            "position_error_m": frozen["position_error"],
            "orientation_error_rad": frozen["orientation_error"],
            "position_atol_m": DERIVATION_POSITION_ATOL_M,
            "orientation_atol_rad": DERIVATION_ORIENTATION_ATOL_RAD,
            "pass": True,
        },
        "preserved_components": {
            "actor_world_z_exactly_preserved": bool(
                frozen["xy_actor"][2] == frozen["desired_actor"][2]
            ),
            "actor_quaternion_exactly_preserved": bool(
                np.array_equal(
                    frozen["xy_actor"][3:], frozen["desired_actor"][3:]
                )
            ),
            "eef_world_z_matches_r6_planner_successful_command": bool(
                abs(frozen["xy_eef"][2] - frozen["original_eef"][2]) <= 1e-12
            ),
            "eef_orientation_matches_r6_planner_successful_command": bool(
                quaternion_angular_error(
                    frozen["xy_eef"][3:], frozen["original_eef"][3:]
                )
                <= 1e-12
            ),
        },
        "xy_only_command_geometry_audit": frozen["command_geometry"],
        "predicted_repeated_r6_tracking_error_diagnostic": {
            "predicted_realized_actor_pose": frozen[
                "predicted_realized_actor"
            ].tolist(),
            "position_error_to_desired_m": frozen["predicted_position_error"],
            "orientation_error_to_desired_rad": frozen[
                "predicted_orientation_error"
            ],
            "geometry_audit": frozen["predicted_geometry"],
            "diagnostic_only": True,
            "hard_gate": False,
            "future_outcome_claimed": False,
        },
        "desired_route_sha256": desired_route_sha256,
        "desired_route_matches_exact_r6_evidence": (
            desired_route_sha256 == R6_DESIRED_ROUTE_SHA256
        ),
        "desired_route_semantics_mutated": False,
        "desired_final_actor_target_sha256": R6_DESIRED_TARGET_ACTOR_SHA256,
        "desired_pre_release_actor_target_sha256": (
            R6_DESIRED_PRE_RELEASE_ACTOR_SHA256
        ),
        "desired_final_fit_sha256": R6_DESIRED_FINAL_FIT_SHA256,
        "input_targets_sha256": original_targets_sha256,
        "input_target_sha256": original_target_hashes,
        "r6_evidence_target_sha256": list(R6_TARGET_SHA256),
        "input_targets_match_exact_r6_evidence": [
            value == expected
            for value, expected in zip(original_target_hashes, R6_TARGET_SHA256)
        ],
        "output_targets_sha256": hash_json(targets),
        "output_target_sha256": output_target_hashes,
        "changed_target_indices": changed_indices,
        "retreat_target_byte_and_hash_equal": targets[1]
        == json.loads(json.dumps(list(original_targets)[1])),
        "rest_target_byte_and_hash_equal": targets[2]
        == json.loads(json.dumps(list(original_targets)[2])),
        "unique_candidate_count": 1,
        "candidate_search": False,
        "fallback": False,
        "online_adaptation": False,
        "runtime_artifact_read": False,
        "planner_query_count_delta": 0,
        "inside_command_target_zero_changed": True,
        "on_beside_affected": False,
        "scientific_target_changed": False,
        "cavity_changed": False,
        "verifier_threshold_changed": False,
        "scientific_threshold_added": False,
        "attempt_stop_condition_changed": False,
    }
    receipt["receipt_sha256"] = _canonical_sha256(receipt)
    return targets, json.loads(
        json.dumps(
            receipt,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
        )
    )


def validate_f2_inside_xy_tracking_compensation_receipt_v8(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Fail closed on hash, provenance, formula, or invariant tampering."""

    if not isinstance(receipt, Mapping):
        raise ValueError("F2 r8 XY-only compensation receipt must be a mapping")
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
        raise ValueError("F2 r8 XY-only compensation receipt hash mismatch")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("F2 r8 XY-only compensation receipt schema mismatch")
    if value.get("source_evidence") != {
        "revision6": dict(R6_EVIDENCE),
        "revision7": dict(R7_EVIDENCE),
    }:
        raise ValueError("F2 r8 immutable evidence binding changed")
    if not np.allclose(
        np.asarray(value.get("xy_only_first_eef_command_pose"), dtype=np.float64),
        np.asarray(EXPECTED_XY_ONLY_FIRST_EEF_COMMAND_POSE, dtype=np.float64),
        atol=1e-12,
        rtol=0.0,
    ) or not np.allclose(
        np.asarray(value.get("xy_only_actor_command_pose"), dtype=np.float64),
        np.asarray(EXPECTED_XY_ONLY_ACTOR_COMMAND_POSE, dtype=np.float64),
        atol=1e-12,
        rtol=0.0,
    ):
        raise ValueError("F2 r8 frozen XY-only target changed")
    command_geometry = value.get("xy_only_command_geometry_audit", {})
    predicted = value.get("predicted_repeated_r6_tracking_error_diagnostic", {})
    invariants = (
        value.get("program_id") == PROGRAM_ID,
        value.get("changed_target_indices") == [0],
        value.get("retreat_target_byte_and_hash_equal") is True,
        value.get("rest_target_byte_and_hash_equal") is True,
        value.get("unique_candidate_count") == 1,
        value.get("candidate_search") is False,
        value.get("fallback") is False,
        value.get("online_adaptation") is False,
        value.get("runtime_artifact_read") is False,
        value.get("r7_full_se3_endpoint_abandoned") is True,
        value.get("r7_full_se3_target_reused") is False,
        value.get("on_beside_affected") is False,
        value.get("desired_route_semantics_mutated") is False,
        value.get("scientific_target_changed") is False,
        value.get("cavity_changed") is False,
        value.get("verifier_threshold_changed") is False,
        value.get("scientific_threshold_added") is False,
        value.get("attempt_stop_condition_changed") is False,
        command_geometry.get("pass") is True,
        abs(command_geometry.get("rim_clearance_m", 0.0) - 0.02595801388876108)
        <= 1e-12,
        predicted.get("diagnostic_only") is True,
        predicted.get("hard_gate") is False,
        predicted.get("future_outcome_claimed") is False,
    )
    if not all(invariants):
        raise ValueError("F2 r8 XY-only compensation receipt invariants changed")
    validated = dict(value)
    validated["receipt_sha256"] = digest
    return validated
