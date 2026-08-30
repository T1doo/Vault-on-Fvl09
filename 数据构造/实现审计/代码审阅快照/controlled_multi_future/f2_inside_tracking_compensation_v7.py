"""Pure-CPU, immutable-evidence F2 inside tracking compensation.

The correction is frozen from the revision-6 F2 inside branch.  It changes
only the first commanded EEF target.  Desired actor/cavity semantics and the
retreat/rest targets remain untouched.  Alignment thresholds are reported as
diagnostics only; this module does not add a scientific verifier or hard Gate.

Importing this module does not read Vault artifacts, create a scene, query a
planner, execute an action, authorize a GPU probe, or authorize Stage 0.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .anchor import quaternion_angular_error
from .current_hasher import hash_json
from .geometry import (
    compose_pose,
    matrix_pose,
    obb_corners,
    pose_matrix,
    relative_pose,
)


SCHEMA_VERSION = "cmf_f2_inside_tracking_compensation_v7"
DIAGNOSTIC_SCHEMA_VERSION = "cmf_f2_inside_alignment_diagnostic_v7"
DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_3"
IMPLEMENTATION_PROPOSAL = "f2_r7_r6_evidence_fixed_inside_first_command_compensation"

PROGRAM_ID = "F2-inside"
SEGMENT_IDS = (
    "inside_drop_release_10cm",
    "inside_drop_retreat_16cm",
    "f2_rest",
)
CHANGED_TARGET_INDICES = (0,)
MINIMUM_RIM_CLEARANCE_M = 0.020

# These are reference-only comparisons.  They do not gate or modify the F2
# scientific verifier in this pure helper.
REFERENCE_ALIGNMENT_POSITION_M = 0.005
REFERENCE_ALIGNMENT_ORIENTATION_RAD = 0.050

R6_EVIDENCE = {
    "namespace": "nonformal_runtime_v3_3_f2_root_seed20260829_revision6_run1_anygpu",
    "implementation_source_sha256": "3b771f97a5b2b53db53bf71ec9f1fe15727614a1303e2f415197e65655580a7d",
    "evidence_manifest_file_sha256": "4c31f139945130908aabfb43d8ce0fe75981087e88a1a1a05472f0a22cc744b4",
    "evidence_tree_sha256": "3e23874fc20c7fa7bacaa2d5ed3ce84e9d13fd4c53415671863b06809f2ec487",
    "evidence_file_count": 42,
    "inside_branch_receipt_file_sha256": "fd854e892f2250b63bd73266343fc2ae201ac3145fff89ae3bd064db346685a5",
    "inside_trace_sha256": "98ca052e4316e38f6ba263da26f67447b7bbfce52a70373fd55a99d49b03d1a6",
    "inside_before_release_trace_row": 1974,
    "suffix_artifact_file_sha256": "2a35552afe8c923981538fc913f43a056af9fabd4f8f63a2b6d2d25e9d5bd5c0",
    "suffix_artifact_sha256": "7f4b524efef2f6c15913c677ba328aed480ce9296add4af74b082f62a83fcb79",
    "suffix_execution_spec_sha256": "5090caf455b60936ba53eb4c0308c3be899910788a767635435eb05e6913d7bb",
    "suffix_controls_file_sha256": "c819a517208c18b87773a2331ac6f69c3e24d5fdbff99b5a55dbe6d32e49ad55",
}

R6_DESIRED_PRE_RELEASE_ACTOR_POSE = (
    -0.2901713007200062,
    -0.15267864896059247,
    0.9432698593315743,
    7.850462293418875e-17,
    -0.7071067811865476,
    7.850462293418875e-17,
    -0.7071067811865475,
)
R6_REALIZED_PRE_RELEASE_ACTOR_POSE = (
    -0.3010794520378113,
    -0.1494094282388687,
    0.9400912523269653,
    0.008754035457968712,
    0.6950646638870239,
    0.042682114988565445,
    0.7176259160041809,
)
R6_ORIGINAL_FIRST_EEF_COMMAND = (
    -0.28960503546923777,
    -0.3441847144870369,
    0.9419717072948476,
    0.6530027337490018,
    0.26990055979022415,
    0.2698351383914301,
    0.6541636764835937,
)
R6_REALIZED_PRE_RELEASE_EEF_POSE = (
    -0.2916126251220703,
    -0.34027332067489624,
    0.9529452919960022,
    0.6506669402624332,
    0.22906497980034696,
    0.28929658866326335,
    0.6636785755668093,
)

R6_ORIGINAL_TARGETS = (
    {
        "segment_id": "inside_drop_release_10cm",
        "pose": list(R6_ORIGINAL_FIRST_EEF_COMMAND),
    },
    {
        "segment_id": "inside_drop_retreat_16cm",
        "pose": [
            -0.28960503546923777,
            -0.3441847144870369,
            1.0019717072948475,
            0.6530027337490018,
            0.26990055979022415,
            0.2698351383914301,
            0.6541636764835937,
        ],
    },
    {
        "segment_id": "f2_rest",
        "pose": [
            -0.297923743724823,
            -0.31380218267440796,
            0.9419903755187988,
            0.7000005275036494,
            -1.61680875200991e-05,
            6.60717435563285e-06,
            0.7141423255833185,
        ],
    },
)

R6_DESIRED_ROUTE_SHA256 = "538f695cf7fbcc98be7daeb6c8011c191b8c2d8da5319c41748320644b04b0cc"
R6_DESIRED_ROUTE_TARGETS_SHA256 = "f371afe0005961565b785855f373722cd1c76b0f465a2805e011f4aae4ff200a"
R6_DESIRED_TARGET_ACTOR_SHA256 = "c8441e9267900f1e819c1b97933c52ad2497b79ef2cd7bfa1ca4b3c4a68ea914"
R6_DESIRED_PRE_RELEASE_ACTOR_SHA256 = "7c83550a3527f74f49ec8143658a7d54f0f0b85af3c01919a4297e06787b4b2c"
R6_DESIRED_FINAL_FIT_SHA256 = "f9b0787724da7bf7f14430ab24066166e92f8d3949c5df32c0bdb658cce5f2a8"
R6_TARGET_SHA256 = (
    "505e39b07eb35344e3bb63c19b5a3c317dd2c382564cf1e45887f0fab1d3997e",
    "d67eb6a730f81f1c1619f24839e2cdc34f89b35b1ad3f0edbe1f36d0126c3624",
    "2bf0a3b05a6db86f9ae41b3499089c87d9d3c38b75bdd711dbd5f078917275e7",
)

R6_BOX_POSE = (
    -0.28999999165534973,
    -0.20000000298023224,
    0.7799999713897705,
    0.5,
    0.5,
    0.5,
    0.5,
)
R6_CAN_LOCAL_GEOMETRY_CENTER_M = (
    -4.492628302420404e-06,
    0.04756748877763528,
    -5.966823217269159e-05,
)
R6_CAN_HALF_EXTENTS_M = (
    0.03254198611123893,
    0.04828508321025152,
    0.03263935967162212,
)
R6_CAVITY_LOWER_M = (
    -0.07824613475799559,
    0.02176539531350136,
    -0.07823097729682921,
)
R6_CAVITY_UPPER_M = (
    0.07775386524200455,
    0.10476539531350136,
    0.07776902270317093,
)

# Internal consistency tolerances only; not task/verifier thresholds.
DERIVATION_CONSISTENCY_POSITION_ATOL_M = 0.0002
DERIVATION_CONSISTENCY_ORIENTATION_ATOL_RAD = 0.0005


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


def _frozen_compensation() -> dict[str, np.ndarray]:
    desired_actor = _pose(
        R6_DESIRED_PRE_RELEASE_ACTOR_POSE,
        label="r6 desired pre-release actor",
    )
    realized_actor = _pose(
        R6_REALIZED_PRE_RELEASE_ACTOR_POSE,
        label="r6 realized pre-release actor",
    )
    desired_eef = _pose(
        R6_ORIGINAL_FIRST_EEF_COMMAND,
        label="r6 original first EEF command",
    )
    realized_eef = _pose(
        R6_REALIZED_PRE_RELEASE_EEF_POSE,
        label="r6 realized pre-release EEF",
    )

    actor_world_correction = (
        pose_matrix(desired_actor) @ np.linalg.inv(pose_matrix(realized_actor))
    )
    eef_world_correction = (
        pose_matrix(desired_eef) @ np.linalg.inv(pose_matrix(realized_eef))
    )
    compensated_actor = matrix_pose(
        actor_world_correction @ pose_matrix(desired_actor)
    )
    compensated_eef = matrix_pose(
        eef_world_correction @ pose_matrix(desired_eef)
    )
    planned_grasp = relative_pose(desired_eef, desired_actor)
    implied_actor = compose_pose(compensated_eef, planned_grasp)
    return {
        "desired_actor": desired_actor,
        "realized_actor": realized_actor,
        "desired_eef": desired_eef,
        "realized_eef": realized_eef,
        "actor_world_correction": actor_world_correction,
        "eef_world_correction": eef_world_correction,
        "compensated_actor": compensated_actor,
        "compensated_eef": compensated_eef,
        "planned_grasp": planned_grasp,
        "implied_actor": implied_actor,
    }


def _compensated_geometry_audit(compensated_actor: Sequence[float]) -> dict[str, Any]:
    actor = _pose(compensated_actor, label="compensated actor command")
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
    projection_inside = bool(
        np.all(np.min(local[:, opening_axes], axis=0) >= lower[list(opening_axes)])
        and np.all(
            np.max(local[:, opening_axes], axis=0) <= upper[list(opening_axes)]
        )
    )
    clearance = float(np.min(local[:, 1]) - upper[1])
    checks = {
        "opening_projection_inside": projection_inside,
        "rim_clearance_at_least_20mm": clearance
        >= MINIMUM_RIM_CLEARANCE_M,
    }
    return {
        "local_corner_min": np.min(local, axis=0).tolist(),
        "local_corner_max": np.max(local, axis=0).tolist(),
        "cavity_lower": lower.tolist(),
        "cavity_upper": upper.tolist(),
        "rim_clearance_m": clearance,
        "rim_clearance_headroom_over_20mm_m": clearance
        - MINIMUM_RIM_CLEARANCE_M,
        "checks": checks,
        "pass": all(checks.values()),
    }


def build_f2_inside_tracking_compensation_v7(
    *,
    program_id: str,
    original_targets: Sequence[Mapping[str, Any]],
    desired_route: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return a copy with only target zero corrected and a sealed receipt."""

    if program_id != PROGRAM_ID:
        raise ValueError("F2 r7 tracking compensation is inside-only")
    if not isinstance(desired_route, Mapping):
        raise ValueError("F2 r7 desired route must be a mapping")
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
        raise ValueError("F2 r7 requires the exact three inside segments")
    if desired_route.get("relation") != "inside" or desired_route.get(
        "release_target_index"
    ) != 0:
        raise ValueError("F2 r7 desired route identity changed")
    if hash_json(desired_route.get("target_actor_pose")) != R6_DESIRED_TARGET_ACTOR_SHA256:
        raise ValueError("F2 r7 desired final actor target changed")
    if (
        hash_json(desired_route.get("pre_release_actor_pose"))
        != R6_DESIRED_PRE_RELEASE_ACTOR_SHA256
    ):
        raise ValueError("F2 r7 desired pre-release actor target changed")
    if hash_json(desired_route.get("final_target_fit")) != R6_DESIRED_FINAL_FIT_SHA256:
        raise ValueError("F2 r7 desired cavity fit changed")
    if hash_json(desired_route.get("targets")) != hash_json(targets):
        raise ValueError("F2 r7 desired route targets differ from planner inputs")

    original_target_hashes = [hash_json(item) for item in targets]
    original_targets_sha256 = hash_json(targets)
    desired_route_sha256 = hash_json(desired_route)
    frozen = _frozen_compensation()
    consistency_position_error = float(
        np.linalg.norm(
            frozen["implied_actor"][:3] - frozen["compensated_actor"][:3]
        )
    )
    consistency_orientation_error = quaternion_angular_error(
        frozen["implied_actor"][3:], frozen["compensated_actor"][3:]
    )
    if (
        consistency_position_error > DERIVATION_CONSISTENCY_POSITION_ATOL_M
        or consistency_orientation_error
        > DERIVATION_CONSISTENCY_ORIENTATION_ATOL_RAD
    ):
        raise ValueError("F2 r7 actor/EEF compensation derivations disagree")

    geometry_audit = _compensated_geometry_audit(frozen["compensated_actor"])
    if geometry_audit["pass"] is not True:
        raise ValueError("F2 r7 compensated command fails opening/rim geometry")
    targets[0]["pose"] = frozen["compensated_eef"].tolist()
    changed_indices = [
        index
        for index, (before, after) in enumerate(
            zip(original_target_hashes, [hash_json(item) for item in targets])
        )
        if before != after
    ]
    if changed_indices != list(CHANGED_TARGET_INDICES):
        raise RuntimeError("F2 r7 changed target indices differ from [0]")
    if hash_json(targets[1]) != original_target_hashes[1] or hash_json(
        targets[2]
    ) != original_target_hashes[2]:
        raise RuntimeError("F2 r7 mutated retreat or rest")

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_proposal": IMPLEMENTATION_PROPOSAL,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "program_id": PROGRAM_ID,
        "source_evidence": dict(R6_EVIDENCE),
        "formula": {
            "actor": "A_cmd = A_desired @ inverse(A_realized_r6) @ A_desired",
            "eef": "C_cmd = C_desired @ inverse(C_realized_r6) @ C_desired",
            "runtime_adaptation": False,
            "r7_outcome_may_change_compensation": False,
        },
        "r6_desired_actor_pose": frozen["desired_actor"].tolist(),
        "r6_realized_actor_pose": frozen["realized_actor"].tolist(),
        "r6_original_eef_command": frozen["desired_eef"].tolist(),
        "r6_realized_eef_pose": frozen["realized_eef"].tolist(),
        "actor_world_correction_matrix": frozen[
            "actor_world_correction"
        ].tolist(),
        "eef_world_correction_matrix": frozen["eef_world_correction"].tolist(),
        "compensated_actor_command_pose": frozen["compensated_actor"].tolist(),
        "compensated_first_eef_command_pose": frozen["compensated_eef"].tolist(),
        "actor_pose_implied_by_compensated_eef": frozen[
            "implied_actor"
        ].tolist(),
        "actor_eef_derivation_consistency": {
            "position_error_m": consistency_position_error,
            "orientation_error_rad": consistency_orientation_error,
            "position_atol_m": DERIVATION_CONSISTENCY_POSITION_ATOL_M,
            "orientation_atol_rad": DERIVATION_CONSISTENCY_ORIENTATION_ATOL_RAD,
            "pass": True,
        },
        "compensated_command_geometry_audit": geometry_audit,
        "desired_route_sha256": desired_route_sha256,
        "desired_route_matches_exact_r6_evidence": desired_route_sha256
        == R6_DESIRED_ROUTE_SHA256,
        "desired_route_semantics_mutated": False,
        "desired_final_actor_target_sha256": R6_DESIRED_TARGET_ACTOR_SHA256,
        "desired_pre_release_actor_target_sha256": R6_DESIRED_PRE_RELEASE_ACTOR_SHA256,
        "desired_final_fit_sha256": R6_DESIRED_FINAL_FIT_SHA256,
        "input_targets_sha256": original_targets_sha256,
        "input_target_sha256": original_target_hashes,
        "r6_evidence_target_sha256": list(R6_TARGET_SHA256),
        "input_targets_match_exact_r6_evidence": [
            value == expected
            for value, expected in zip(
                original_target_hashes, R6_TARGET_SHA256
            )
        ],
        "output_targets_sha256": hash_json(targets),
        "output_target_sha256": [hash_json(item) for item in targets],
        "changed_target_indices": changed_indices,
        "retreat_target_byte_and_hash_equal": targets[1]
        == json.loads(json.dumps(list(original_targets)[1])),
        "rest_target_byte_and_hash_equal": targets[2]
        == json.loads(json.dumps(list(original_targets)[2])),
        "planner_query_count_delta": 0,
        "scientific_target_changed": False,
        "cavity_changed": False,
        "verifier_threshold_changed": False,
        "alignment_is_diagnostic_only": True,
        "hard_alignment_gate_added": False,
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


def build_f2_inside_alignment_diagnostic_v7(
    *,
    realized_eef_pose: Sequence[float],
    realized_actor_pose: Sequence[float],
    desired_eef_pose: Sequence[float],
    desired_actor_pose: Sequence[float],
    compensation_receipt_sha256: str,
) -> dict[str, Any]:
    """Record alignment against reference values without creating a hard Gate."""

    if not isinstance(compensation_receipt_sha256, str) or len(
        compensation_receipt_sha256
    ) != 64:
        raise ValueError("F2 r7 compensation receipt SHA is invalid")
    realized_eef = _pose(realized_eef_pose, label="realized EEF pose")
    realized_actor = _pose(realized_actor_pose, label="realized actor pose")
    desired_eef = _pose(desired_eef_pose, label="desired EEF pose")
    desired_actor = _pose(desired_actor_pose, label="desired actor pose")
    metrics = {
        "eef_position_error_m": float(
            np.linalg.norm(realized_eef[:3] - desired_eef[:3])
        ),
        "eef_orientation_error_rad": quaternion_angular_error(
            realized_eef[3:], desired_eef[3:]
        ),
        "actor_position_error_m": float(
            np.linalg.norm(realized_actor[:3] - desired_actor[:3])
        ),
        "actor_orientation_error_rad": quaternion_angular_error(
            realized_actor[3:], desired_actor[3:]
        ),
    }
    reference_comparison = {
        "reference_position_m": REFERENCE_ALIGNMENT_POSITION_M,
        "reference_orientation_rad": REFERENCE_ALIGNMENT_ORIENTATION_RAD,
        "eef_within_reference": metrics["eef_position_error_m"]
        <= REFERENCE_ALIGNMENT_POSITION_M
        and metrics["eef_orientation_error_rad"]
        <= REFERENCE_ALIGNMENT_ORIENTATION_RAD,
        "actor_within_reference": metrics["actor_position_error_m"]
        <= REFERENCE_ALIGNMENT_POSITION_M
        and metrics["actor_orientation_error_rad"]
        <= REFERENCE_ALIGNMENT_ORIENTATION_RAD,
        "reference_source": "cross-family implementation diagnostic only; not an F2 scientific threshold",
    }
    receipt = {
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "program_id": PROGRAM_ID,
        "compensation_receipt_sha256": compensation_receipt_sha256,
        "metrics": metrics,
        "reference_comparison": reference_comparison,
        "diagnostic_only": True,
        "hard_gate": False,
        "scientific_threshold_added": False,
        "attempt_stop_condition_changed": False,
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


def validate_f2_inside_tracking_compensation_receipt_v7(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise ValueError("F2 r7 compensation receipt must be a mapping")
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
        raise ValueError("F2 r7 compensation receipt hash mismatch")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("F2 r7 compensation receipt schema mismatch")
    if (
        value.get("changed_target_indices") != [0]
        or value.get("retreat_target_byte_and_hash_equal") is not True
        or value.get("rest_target_byte_and_hash_equal") is not True
        or value.get("desired_route_semantics_mutated") is not False
        or value.get("verifier_threshold_changed") is not False
        or value.get("hard_alignment_gate_added") is not False
    ):
        raise ValueError("F2 r7 compensation receipt invariants changed")
    validated = dict(value)
    validated["receipt_sha256"] = digest
    return validated
