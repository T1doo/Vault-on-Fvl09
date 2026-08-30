"""Pure-CPU F4 r8 top-down block-carry target construction.

Revision 7 accepted the right-arm A top-down 20 mm micro-lift boundary.  This
helper extends that already-proven *target contract* uniformly to A/B/C while
remaining a CPU hypothesis for carry/place.  For each role it:

* reuses the revision-6 top-down pregrasp, grasp, and micro-lift poses;
* treats that micro-lift pose as the full-program ``lift`` endpoint;
* freezes the realized target-space ``T_eef_actor`` from the top-down grasp;
* reconstructs the same-role slot release and +10 cm preplace from it;
* inserts the existing 50% carry midpoint and the same branch-neutral pose.

Only ABC, ACB, and BAC are accepted.  There is no role-specific fallback,
planner query, simulator import, artifact read, GPU work, or authorization.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

import numpy as np

from .anchor import quaternion_angular_error
from .current_hasher import hash_json
from .f4_top_down_clearance_v6 import (
    F4_BLOCK_ROLES,
    MICRO_LIFT_DISTANCE_M,
    SUPPORTED_ARM,
    build_uniform_f4_top_down_clearance_contract_v6,
    canonical_json_sha256,
)
from .f4_json_canonicalization_v9 import (
    CANONICALIZATION_VERSION as JSON_CANONICALIZATION_VERSION,
    json_safe_clone_v9,
)
from .f4_uniform_block_carry_midpoint_v3 import (
    F4_ALLOWED_OBJECT_ORDERS,
    F4_SEGMENTED_BLOCK_SUFFIXES,
    build_uniform_carry_midpoint,
)
from .geometry import (
    actor_target_to_eef_pose,
    compose_pose,
    relative_pose,
    segment_intersects_aabb,
    world_axis_offset_pose,
)
from .project_cube_grasp_pose_v1 import FROZEN_CUBE_HALF_EXTENTS_M


SCHEMA_VERSION = "cmf_f4_top_down_block_carry_v8"
ROUTE_VERSION = "f4_uniform_top_down_block_carry_v8"
DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_3"

PREPLACE_DISTANCE_M = 0.10
MIDPOINT_XY_FRACTION = 0.5
TABLE_TOP_Z_M = 0.740
TABLE_BOUNDS_XY = {"x": (-0.45, 0.45), "y": (-0.35, 0.20)}
TARGET_POSITION_ATOL_M = 1e-9
TARGET_ORIENTATION_ATOL_RAD = 1e-7
FROZEN_LAYOUT_VERSION = "f4_right_arm_workspace_base0_v4_final"
FROZEN_LAYOUT_SHA256 = (
    "d8abbdd62885a814b2eeaa57cb4b9802591b47acea753f02b8014dccfb79dc85"
)

R7_MICRO_ACCEPTED_EVIDENCE = {
    "namespace": (
        "nonformal_runtime_v3_3_f4_common_boundary_A_micro_lift_"
        "seed20260829_revision7_run1_anygpu"
    ),
    "implementation_source_sha256": (
        "2ed82e7a5e6a2a03a3cf7b1cfb3dde82acba637f24c574c64c47099516ee72c8"
    ),
    "evidence_manifest_file_sha256": (
        "d6b7143fe42bc327dfcf7296c04bcfbaa52a53c9e59150e9b887a199c2ccdb7e"
    ),
    "evidence_tree_sha256": (
        "5139caa8e5c63e75fc6b926c18c74acd9e2fa5846a870860e97b6ea6a6f4d1df"
    ),
    "evidence_file_count": 17,
    "impact_review_file_sha256": (
        "7668a2b0138db4100827e4baa1ccb7eea071e0e8ad7bfd066ae2b7d6767e3804"
    ),
    "top_receipt_file_sha256": (
        "95cb024ed24792a991a47b3cd6c615ae2301590d0ff90076f75f4f186031aee2"
    ),
    "gate_receipt_file_sha256": (
        "034a4de726e49e64a4818c77cd768cfc900eb68349a39e5dbab34865fbb1f5f3"
    ),
    "execution_receipt_file_sha256": (
        "6b3647c85395b5a38b4eeafc21a8db59a238522ff147e2f7d593688555c3ccd3"
    ),
    "preflight_receipt_file_sha256": (
        "e9c9c2ff4d562f74f002f249375b23b94a0dbe18240ea171c86cafc04adc6d9d"
    ),
    "suffix_artifact_file_sha256": (
        "b2a4f299cca3c6e571a8237324f4c2048ae02d242eb96ecfb9e25cc5ce27e8a1"
    ),
    "suffix_controls_file_sha256": (
        "4a8aa7c6f88bd8018680a7616ef78534c80734244ed32d64aa4a6d6961e9b5c8"
    ),
    "raw_manifest_file_sha256": (
        "f3e25c9c42d2d35a5f12895a53049cec9a774056c6131397183e2c6583ee5ce6"
    ),
    "raw_streams_file_sha256": (
        "2bb225ebc72b1eabd262bb2b5b71850601a5ae80ed17aa3091271f5638023aca"
    ),
    "trace_file_sha256": (
        "3060072eb196d5cf232c27178d7f56cbd74ced990963c90ac7741ff7a3fd6d23"
    ),
    "guard_file_sha256": (
        "3266fb112c8f33a23905b7298ff153327f563e21ebd5a7a9a022e75b2ebe4f03"
    ),
    "authorization_receipt_sha256": (
        "b26e6fa4cd1bd1d3b26cbc9b7cef4c8b0fc27569f48040e1edc5dfad2ef7aa6c"
    ),
    "uniform_top_down_contract_receipt_sha256": (
        "52c528b8eb433e0cd105736bcc2f70973961610cbec1b9757d7de136063e4791"
    ),
    "status": "accepted",
    "scope": "A-only micro-lift boundary; not a complete F4 root",
    "planner_query_count": 13,
    "execution_attempt_count": 1,
    "recovery_attempt_count": 0,
    "actor_rise_m": 0.017215192317962646,
    "selected_contact_fraction": 1.0,
    "selected_contact_break_count": 0,
    "minimum_selected_contact_count": 2,
    "raw_action_count": 3751,
    "raw_state_count": 3752,
}


def _json_clone(value: Any) -> Any:
    return json_safe_clone_v9(value)


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


def _expected_ids(role: str) -> tuple[str, ...]:
    return tuple(f"{role}_{suffix}" for suffix in F4_SEGMENTED_BLOCK_SUFFIXES)


def _target_actor_pose(
    source_actor_pose: Sequence[float], slot_pose: Sequence[float]
) -> np.ndarray:
    source = _pose(source_actor_pose, label="F4 source actor")
    slot = _pose(slot_pose, label="F4 target slot")
    target = source.copy()
    target[:3] = slot[:3] + np.asarray(
        [0.0, 0.0, FROZEN_CUBE_HALF_EXTENTS_M[2]], dtype=np.float64
    )
    return target


def _build_role_group(
    *,
    role: str,
    source_actor_pose: Sequence[float],
    slot_pose: Sequence[float],
    neutral_pose: Sequence[float],
    top_down_group: Mapping[str, Any],
) -> dict[str, Any]:
    source = _pose(source_actor_pose, label=f"F4 {role} source actor")
    slot = _pose(slot_pose, label=f"F4 {role} slot")
    neutral = _pose(neutral_pose, label="F4 branch-neutral")
    top_targets = _json_clone(top_down_group.get("targets"))
    expected_top_ids = (
        f"{role}_pregrasp",
        f"{role}_grasp",
        f"{role}_micro_lift",
    )
    if tuple(item.get("segment_id") for item in top_targets) != expected_top_ids:
        raise ValueError(f"F4 {role} r6 top-down segment IDs changed")
    pregrasp = _pose(top_targets[0]["pose"], label=f"F4 {role} pregrasp")
    grasp = _pose(top_targets[1]["pose"], label=f"F4 {role} grasp")
    lift = _pose(top_targets[2]["pose"], label=f"F4 {role} micro-lift")
    target_actor = _target_actor_pose(source, slot)

    frozen_eef_to_actor = relative_pose(grasp, source)
    frozen_actor_to_eef = relative_pose(source, grasp)
    release = actor_target_to_eef_pose(grasp, source, target_actor)
    preplace = world_axis_offset_pose(release, PREPLACE_DISTANCE_M)
    carry_mid, midpoint_audit = build_uniform_carry_midpoint(lift, preplace)
    reconstructed_target = compose_pose(release, frozen_eef_to_actor)
    position_error = float(
        np.linalg.norm(reconstructed_target[:3] - target_actor[:3])
    )
    orientation_error = quaternion_angular_error(
        reconstructed_target[3:], target_actor[3:]
    )
    lift_actor = compose_pose(lift, frozen_eef_to_actor)
    lift_delta = lift_actor[:3] - source[:3]

    targets = [
        {"segment_id": f"{role}_pregrasp", "pose": pregrasp.tolist()},
        {"segment_id": f"{role}_grasp", "pose": grasp.tolist()},
        {"segment_id": f"{role}_lift", "pose": lift.tolist()},
        {"segment_id": f"{role}_carry_mid", "pose": carry_mid.tolist()},
        {"segment_id": f"{role}_preplace", "pose": preplace.tolist()},
        {"segment_id": f"{role}_release", "pose": release.tolist()},
        {"segment_id": f"{role}_neutral", "pose": neutral.tolist()},
    ]
    checks = {
        "exact_seven_segment_ids": tuple(
            item["segment_id"] for item in targets
        )
        == _expected_ids(role),
        "r6_pregrasp_pose_reused": np.array_equal(
            np.asarray(targets[0]["pose"]), pregrasp
        ),
        "r6_grasp_pose_reused": np.array_equal(
            np.asarray(targets[1]["pose"]), grasp
        ),
        "r6_micro_lift_pose_reused_as_lift": np.array_equal(
            np.asarray(targets[2]["pose"]), lift
        ),
        "exact_20mm_lift_actor_delta": bool(
            np.allclose(
                lift_delta,
                [0.0, 0.0, MICRO_LIFT_DISTANCE_M],
                atol=1e-9,
                rtol=0.0,
            )
        ),
        "target_actor_position_reconstructed": (
            position_error <= TARGET_POSITION_ATOL_M
        ),
        "target_actor_orientation_reconstructed": (
            orientation_error <= TARGET_ORIENTATION_ATOL_RAD
        ),
        "target_position_is_same_role_slot": bool(
            np.allclose(
                target_actor[:3],
                slot[:3]
                + np.asarray([0.0, 0.0, FROZEN_CUBE_HALF_EXTENTS_M[2]]),
                atol=1e-12,
                rtol=0.0,
            )
        ),
        "target_orientation_preserves_source_actor": (
            quaternion_angular_error(target_actor[3:], source[3:]) <= 1e-12
        ),
        "preplace_exactly_10cm_above_release": bool(
            np.allclose(
                preplace[:3] - release[:3],
                [0.0, 0.0, PREPLACE_DISTANCE_M],
                atol=1e-12,
                rtol=0.0,
            )
        ),
        "carry_mid_uses_existing_50_percent_formula": (
            midpoint_audit["midpoint_xy_fraction"] == MIDPOINT_XY_FRACTION
        ),
        "same_neutral_pose_reused": np.array_equal(
            np.asarray(targets[-1]["pose"]), neutral
        ),
    }
    return {
        "role": role,
        "target_start_index": None,
        "source_actor_pose": source.tolist(),
        "slot_pose": slot.tolist(),
        "target_actor_pose": target_actor.tolist(),
        "frozen_actor_to_eef_pose": frozen_actor_to_eef.tolist(),
        "frozen_eef_to_actor_pose": frozen_eef_to_actor.tolist(),
        "r6_top_down_source_segment_ids": list(expected_top_ids),
        "r6_top_down_grasp_contract": _json_clone(
            top_down_group.get("grasp_contract")
        ),
        "lift_pose_source": f"{role}_micro_lift",
        "targets": targets,
        "target_reconstruction": {
            "reconstructed_actor_pose": reconstructed_target.tolist(),
            "position_error_m": position_error,
            "orientation_error_rad": orientation_error,
            "position_atol_m": TARGET_POSITION_ATOL_M,
            "orientation_atol_rad": TARGET_ORIENTATION_ATOL_RAD,
        },
        "midpoint_audit": midpoint_audit,
        "checks": checks,
        "role_specific_condition": False,
        "pass": all(checks.values()),
    }


def _audit_nominal_noninterference(
    *,
    groups: Sequence[Mapping[str, Any]],
    object_poses: Mapping[str, Sequence[float]],
    object_order: Sequence[str],
) -> dict[str, Any]:
    half = np.asarray(FROZEN_CUBE_HALF_EXTENTS_M, dtype=np.float64)
    states = {
        role: _pose(object_poses[role], label=f"F4 nominal {role} state")
        for role in F4_BLOCK_ROLES
    }
    per_role: dict[str, dict[str, Any]] = {}
    transport_bottom_clearances = []
    release_bottom_clearances = []
    for group in groups:
        role = str(group["role"])
        if role != object_order[len(per_role)]:
            raise ValueError("F4 nominal audit group order changed")
        poses = {
            item["segment_id"].removeprefix(f"{role}_"): _pose(
                item["pose"], label=f"F4 nominal {item['segment_id']}"
            )
            for item in group["targets"]
        }
        eef_to_actor = _pose(
            group["frozen_eef_to_actor_pose"],
            label=f"F4 {role} frozen EEF-to-actor",
        )
        held = {
            suffix: compose_pose(poses[suffix], eef_to_actor)
            for suffix in ("lift", "carry_mid", "preplace", "release")
        }
        segment_collisions = {
            "lift_to_carry_mid": [],
            "carry_mid_to_preplace": [],
        }
        for segment_id, start, end in (
            ("lift_to_carry_mid", held["lift"], held["carry_mid"]),
            ("carry_mid_to_preplace", held["carry_mid"], held["preplace"]),
        ):
            for other_role, obstacle in states.items():
                if other_role == role:
                    continue
                if segment_intersects_aabb(
                    start[:3],
                    end[:3],
                    obstacle[:3] - half,
                    obstacle[:3] + half,
                    swept_half_extents=half,
                ):
                    segment_collisions[segment_id].append(other_role)
        transport = (held["lift"], held["carry_mid"], held["preplace"])
        inside_table = all(
            TABLE_BOUNDS_XY["x"][0] + half[0]
            <= pose[0]
            <= TABLE_BOUNDS_XY["x"][1] - half[0]
            and TABLE_BOUNDS_XY["y"][0] + half[1]
            <= pose[1]
            <= TABLE_BOUNDS_XY["y"][1] - half[1]
            for pose in (*transport, held["release"])
        )
        minimum_transport_bottom = min(
            float(pose[2] - half[2] - TABLE_TOP_Z_M) for pose in transport
        )
        release_bottom = float(
            held["release"][2] - half[2] - TABLE_TOP_Z_M
        )
        transport_bottom_clearances.append(minimum_transport_bottom)
        release_bottom_clearances.append(release_bottom)
        target = _pose(
            group["target_actor_pose"], label=f"F4 {role} target actor"
        )
        release_matches_target = bool(
            np.linalg.norm(held["release"][:3] - target[:3])
            <= TARGET_POSITION_ATOL_M
            and quaternion_angular_error(
                held["release"][3:], target[3:]
            )
            <= TARGET_ORIENTATION_ATOL_RAD
        )
        checks = {
            "nominal_swept_block_avoids_current_other_blocks": all(
                not values for values in segment_collisions.values()
            ),
            "all_held_waypoints_inside_table_xy": bool(inside_table),
            "transport_block_bottom_above_table": minimum_transport_bottom > 0.0,
            "release_reconstructs_same_role_slot_target": release_matches_target,
        }
        per_role[role] = {
            "held_actor_poses": {
                key: value.tolist() for key, value in held.items()
            },
            "state_of_other_blocks_before_role": {
                key: value.tolist()
                for key, value in states.items()
                if key != role
            },
            "segment_non_target_collisions": segment_collisions,
            "minimum_transport_bottom_clearance_m": minimum_transport_bottom,
            "release_bottom_above_table_m": release_bottom,
            "checks": checks,
            "pass": all(checks.values()),
        }
        states[role] = target

    return {
        "schema_version": "cmf_f4_top_down_block_carry_nominal_noninterference_v8",
        "object_order": list(object_order),
        "scope": (
            "nominal carried 44mm block swept AABB versus current A/B/C states; "
            "whole robot, common-X, tray, and runtime contacts remain authoritative"
        ),
        "table_top_z_m": TABLE_TOP_Z_M,
        "table_bounds_xy": {
            key: list(value) for key, value in TABLE_BOUNDS_XY.items()
        },
        "per_role": per_role,
        "minimum_transport_bottom_clearance_m": min(
            transport_bottom_clearances
        ),
        "minimum_release_bottom_above_table_m": min(
            release_bottom_clearances
        ),
        "runtime_whole_robot_collision_required": True,
        "runtime_contact_noninterference_required": True,
        "nominal_only": True,
        "pass": all(value["pass"] for value in per_role.values()),
    }


def build_f4_top_down_block_carry_v8(
    *,
    object_poses: Mapping[str, Sequence[float]],
    slot_poses: Mapping[str, Sequence[float]],
    neutral_pose: Sequence[float],
    object_order: Sequence[str],
    arm: str = SUPPORTED_ARM,
    layout_version: str = FROZEN_LAYOUT_VERSION,
) -> dict[str, Any]:
    """Build one uniform 3-block program in ABC, ACB, or BAC order."""

    if arm != SUPPORTED_ARM:
        raise ValueError("F4 r8 top-down carry requires the right arm")
    if layout_version != FROZEN_LAYOUT_VERSION:
        raise ValueError("F4 r8 layout version changed")
    if not isinstance(object_poses, Mapping) or set(object_poses) != set(
        F4_BLOCK_ROLES
    ):
        raise ValueError("F4 r8 requires exactly A/B/C object poses")
    if not isinstance(slot_poses, Mapping) or set(slot_poses) != set(
        F4_BLOCK_ROLES
    ):
        raise ValueError("F4 r8 requires exactly A/B/C slot poses")
    order = tuple(object_order)
    if order not in F4_ALLOWED_OBJECT_ORDERS:
        raise ValueError("F4 r8 supports only ABC, ACB, or BAC")
    original_inputs = _json_clone(
        {
            "object_poses": object_poses,
            "slot_poses": slot_poses,
            "neutral_pose": neutral_pose,
            "object_order": list(order),
        }
    )
    objects = {
        role: _pose(object_poses[role], label=f"F4 {role} object").tolist()
        for role in F4_BLOCK_ROLES
    }
    slots = {
        role: _pose(slot_poses[role], label=f"F4 {role} slot").tolist()
        for role in F4_BLOCK_ROLES
    }
    neutral = _pose(neutral_pose, label="F4 branch-neutral").tolist()
    top_down = build_uniform_f4_top_down_clearance_contract_v6(
        object_poses=objects, arm=arm
    )
    if top_down["pass"] is not True:
        raise ValueError("F4 r8 r6 top-down contract failed")
    top_group_by_role = {group["role"]: group for group in top_down["groups"]}
    groups = []
    flattened = []
    for role in order:
        group = _build_role_group(
            role=role,
            source_actor_pose=objects[role],
            slot_pose=slots[role],
            neutral_pose=neutral,
            top_down_group=top_group_by_role[role],
        )
        group["target_start_index"] = len(flattened)
        groups.append(group)
        flattened.extend(deepcopy(group["targets"]))
    nominal = _audit_nominal_noninterference(
        groups=groups,
        object_poses=objects,
        object_order=order,
    )
    grasp_hashes = {
        group["r6_top_down_grasp_contract"]["grasp_contract_sha256"]
        for group in groups
    }
    checks = {
        "r6_uniform_top_down_contract_pass": top_down["pass"] is True,
        "three_uniform_groups_pass": all(group["pass"] for group in groups),
        "one_top_down_grasp_contract": len(grasp_hashes) == 1,
        "exact_program_order": tuple(group["role"] for group in groups) == order,
        "exact_flattened_segment_ids": tuple(
            item["segment_id"] for item in flattened
        )
        == tuple(
            segment_id
            for role in order
            for segment_id in _expected_ids(role)
        ),
        "all_target_reconstructions_pass": all(
            group["checks"]["target_actor_position_reconstructed"]
            and group["checks"]["target_actor_orientation_reconstructed"]
            for group in groups
        ),
        "nominal_noninterference_pass": nominal["pass"] is True,
        "inputs_not_mutated": _json_clone(
            {
                "object_poses": object_poses,
                "slot_poses": slot_poses,
                "neutral_pose": neutral_pose,
                "object_order": list(order),
            }
        )
        == original_inputs,
    }
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "route_version": ROUTE_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "json_canonicalization_version": JSON_CANONICALIZATION_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "arm": arm,
        "object_order": list(order),
        "supported_object_orders": [
            list(value) for value in F4_ALLOWED_OBJECT_ORDERS
        ],
        "object_poses": objects,
        "slot_poses": slots,
        "neutral_pose": neutral,
        "frozen_layout_version": FROZEN_LAYOUT_VERSION,
        "frozen_layout_sha256": FROZEN_LAYOUT_SHA256,
        "source_evidence": dict(R7_MICRO_ACCEPTED_EVIDENCE),
        "evidence_scope_boundary": (
            "r7 proves A top-down micro-lift only; B/C and carry/place require "
            "fresh runtime planner/contact/verifier evidence"
        ),
        "r6_top_down_contract": top_down,
        "single_top_down_grasp_contract_sha256": next(iter(grasp_hashes)),
        "object_target_groups": groups,
        "flattened_targets": flattened,
        "nominal_noninterference_audit": nominal,
        "group_width": len(F4_SEGMENTED_BLOCK_SUFFIXES),
        "preplace_distance_m": PREPLACE_DISTANCE_M,
        "midpoint_xy_fraction": MIDPOINT_XY_FRACTION,
        "role_specific_condition": False,
        "candidate_search": False,
        "fallback": False,
        "online_adaptation": False,
        "scene_layout_changed": False,
        "target_object_slot_mapping_changed": False,
        "executing_arm_changed": False,
        "common_prefix_changed": False,
        "neutral_pose_changed": False,
        "program_changed": False,
        "verifier_changed": False,
        "verifier_threshold_changed": False,
        "runtime_planner_collision_contact_required": True,
        "checks": checks,
        "pass": all(checks.values()),
    }
    receipt = _json_clone(receipt)
    receipt["receipt_sha256"] = canonical_json_sha256(receipt)
    return receipt


def validate_f4_top_down_block_carry_v8(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute the complete pure contract and reject any tampering."""

    if not isinstance(receipt, Mapping):
        raise TypeError("F4 r8 top-down carry receipt must be a mapping")
    value = _json_clone(receipt)
    digest = value.pop("receipt_sha256", None)
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("F4 r8 top-down carry schema mismatch")
    if not isinstance(digest, str) or canonical_json_sha256(value) != digest:
        raise ValueError("F4 r8 top-down carry receipt hash mismatch")
    if value.get("source_evidence") != R7_MICRO_ACCEPTED_EVIDENCE:
        raise ValueError("F4 r8 accepted-evidence binding changed")
    invariants = (
        value.get("arm") == SUPPORTED_ARM,
        value.get("json_canonicalization_version")
        == JSON_CANONICALIZATION_VERSION,
        tuple(value.get("object_order", ())) in F4_ALLOWED_OBJECT_ORDERS,
        value.get("group_width") == len(F4_SEGMENTED_BLOCK_SUFFIXES),
        value.get("role_specific_condition") is False,
        value.get("candidate_search") is False,
        value.get("fallback") is False,
        value.get("online_adaptation") is False,
        value.get("scene_layout_changed") is False,
        value.get("target_object_slot_mapping_changed") is False,
        value.get("executing_arm_changed") is False,
        value.get("common_prefix_changed") is False,
        value.get("neutral_pose_changed") is False,
        value.get("program_changed") is False,
        value.get("verifier_changed") is False,
        value.get("verifier_threshold_changed") is False,
        value.get("pass") is True,
    )
    if not all(invariants):
        raise ValueError("F4 r8 top-down carry invariants changed")
    recomputed = build_f4_top_down_block_carry_v8(
        object_poses=value["object_poses"],
        slot_poses=value["slot_poses"],
        neutral_pose=value["neutral_pose"],
        object_order=value["object_order"],
        arm=value["arm"],
        layout_version=value["frozen_layout_version"],
    )
    validated = dict(value)
    validated["receipt_sha256"] = digest
    if recomputed != validated:
        raise ValueError("F4 r8 top-down carry receipt content mismatch")
    return validated


__all__ = [
    "FROZEN_LAYOUT_SHA256",
    "FROZEN_LAYOUT_VERSION",
    "R7_MICRO_ACCEPTED_EVIDENCE",
    "ROUTE_VERSION",
    "SCHEMA_VERSION",
    "build_f4_top_down_block_carry_v8",
    "validate_f4_top_down_block_carry_v8",
]
