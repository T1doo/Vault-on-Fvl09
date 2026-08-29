"""Pure-CPU contracts for a possible F2 revision-3 suffix repair.

This module is additive design support only.  Importing it does not create a
scene, query a planner, authorize a GPU probe, or authorize Stage 0.  It keeps
the frozen F2 identity and layout while making two implementation choices
explicit:

* ``inside`` releases the can from a rim-clear pose 10 cm above the strict
  full-OBB target and lets physics settle it into the box;
* ``beside`` evaluates exactly six preregistered pose candidates in a fixed
  order, each through the same seven-segment chained route.

The final relation predicates are intentionally outside this helper and must
remain the existing strict runtime-v3_3 predicates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from .f2_mutually_exclusive_region_layout_v2 import (
    BESIDE_INNER_M,
    BESIDE_OUTER_M,
    BOX_INSIDE_CENTER_OFFSET_WORLD_M,
    BOX_INSIDE_HALF_XY_M,
    LAYOUT,
    SCALE_TOP_CENTER_OFFSET_WORLD_M,
    SCALE_TOP_HALF_XY_M,
    TABLE_BOUNDS_XY,
)
from .geometry import (
    actor_target_to_eef_pose,
    compose_pose,
    matrix_pose,
    obb_inside_local_cavity,
    pose_matrix,
    world_axis_offset_pose,
    world_z_yaw_pose,
)
from .runtime_v3_2_contracts import (
    F2_INSIDE_LOCAL_QUATERNION_WXYZ,
    F2_PLASTICBOX_BASE2_CAVITY,
)


SCHEMA_VERSION = "cmf_f2_suffix_routes_v3"
DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_PROPOSAL = "f2_gravity_drop_inside_and_fixed_sector_routes_v1"

F2_MAIN_OBJECT = "071_can/base1"
F2_EXECUTION_ARM = "left"
F2_BOX = "062_plasticbox/base2"
F2_SCALE = "072_electronicscale/base0"
F2_STAND = "074_displaystand/base3"

INSIDE_DROP_RELEASE_OFFSET_M = 0.10
INSIDE_DROP_RETREAT_OFFSET_M = 0.16
INSIDE_MINIMUM_RIM_CLEARANCE_M = 0.02
INSIDE_SETTLE_STEPS = 250
INSIDE_SAMPLE_STEPS = (1, 5, 10, 25, 50, 125, 250)
INSIDE_SEGMENT_IDS = (
    "inside_drop_release_10cm",
    "inside_drop_retreat_16cm",
    "f2_rest",
)

BESIDE_PLANNER_SEED = 20260828
BESIDE_SEGMENT_IDS = (
    "beside_source_high",
    "beside_midpoint_high",
    "beside_preplace",
    "beside_release",
    "beside_retreat",
    "beside_midpoint_return",
    "f2_rest",
)
BESIDE_EXHAUSTION_TERMINAL = "f2_stand_layout_impact_review_v5"
FROZEN_CAN_UPRIGHT_QUATERNION_WXYZ = (0.5, 0.5, 0.5, 0.5)


@dataclass(frozen=True)
class BesideCandidate:
    candidate_id: str
    stand_relative_xy_m: tuple[float, float]
    yaw_radians: float
    height_margin_m: float
    upright_yaw_id: str
    preplace_height_rule: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "stand_relative_xy_m": list(self.stand_relative_xy_m),
            "yaw_radians": float(self.yaw_radians),
            "height_margin_m": float(self.height_margin_m),
            "upright_yaw_id": self.upright_yaw_id,
            "preplace_height_rule": self.preplace_height_rule,
        }


# This is the exact order already preregistered by runtime_v3_contracts.py.
# Position, yaw, and height are paired before any planner result is observed.
BESIDE_CANDIDATES: tuple[BesideCandidate, ...] = (
    BesideCandidate(
        "p0_y0_h0",
        (0.00, 0.15),
        0.0,
        0.08,
        "asset_yaw_0",
        "obstacle_top_plus_min_margin",
    ),
    BesideCandidate(
        "p0_y1_h1",
        (0.00, 0.15),
        float(np.pi / 2.0),
        0.10,
        "asset_yaw_1",
        "facility_top_plus_extended_margin",
    ),
    BesideCandidate(
        "p1_y0_h1",
        (-0.08, 0.13),
        0.0,
        0.10,
        "asset_yaw_0",
        "facility_top_plus_extended_margin",
    ),
    BesideCandidate(
        "p1_y1_h0",
        (-0.08, 0.13),
        float(np.pi / 2.0),
        0.08,
        "asset_yaw_1",
        "obstacle_top_plus_min_margin",
    ),
    BesideCandidate(
        "p2_y0_h0",
        (-0.12, 0.10),
        0.0,
        0.08,
        "asset_yaw_0",
        "obstacle_top_plus_min_margin",
    ),
    BesideCandidate(
        "p2_y1_h1",
        (-0.12, 0.10),
        float(np.pi / 2.0),
        0.10,
        "asset_yaw_1",
        "facility_top_plus_extended_margin",
    ),
)

_CANDIDATE_BY_ID = {item.candidate_id: item for item in BESIDE_CANDIDATES}


def _pose(value: Sequence[float], *, label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(7)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be finite")
    quaternion_norm = float(np.linalg.norm(result[3:]))
    if not np.isclose(quaternion_norm, 1.0, atol=1e-6, rtol=0.0):
        raise ValueError(f"{label} quaternion must be normalized")
    return result.copy()


def _half_extents(value: Sequence[float]) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(3)
    if not np.all(np.isfinite(result)) or np.any(result <= 0):
        raise ValueError("can_half_extents_m must be finite and positive")
    return result


def beside_candidate_registry() -> list[dict[str, Any]]:
    """Return a fresh, serializable copy of the immutable candidate table."""

    return [item.as_dict() for item in BESIDE_CANDIDATES]


def proposed_static_planner_envelope() -> dict[str, Any]:
    """Return the exact source-structural planner maximum for this proposal."""

    components = {
        "canonical_prefix": 19,
        "inside": len(INSIDE_SEGMENT_IDS),
        "on": 4,
        "beside": len(BESIDE_CANDIDATES) * len(BESIDE_SEGMENT_IDS),
    }
    total = int(sum(components.values()))
    return {
        "schema_version": SCHEMA_VERSION,
        "components": components,
        "planner_query_count": total,
        "execution_attempt_count": 3,
        "recovery_attempt_count": 0,
        "existing_scope_planner_limit": 96,
        "within_existing_numeric_planner_limit": total <= 96,
        "authorization_note": (
            "numeric headroom is not revision authorization; a separately "
            "approved revision-3 impact addendum is required"
        ),
    }


def build_inside_gravity_drop_route(
    *,
    current_eef_pose: Sequence[float],
    current_actor_pose: Sequence[float],
    box_pose: Sequence[float],
    can_half_extents_m: Sequence[float],
    can_local_geometry_center_m: Sequence[float],
    rest_eef_pose: Sequence[float],
) -> dict[str, Any]:
    """Build the deterministic rim-clear inside route and its CPU gates."""

    current_eef = _pose(current_eef_pose, label="current_eef_pose")
    current_actor = _pose(current_actor_pose, label="current_actor_pose")
    box = _pose(box_pose, label="box_pose")
    rest = _pose(rest_eef_pose, label="rest_eef_pose")
    half = _half_extents(can_half_extents_m)
    local_geometry_center = np.asarray(
        can_local_geometry_center_m, dtype=np.float64
    ).reshape(3)
    if not np.all(np.isfinite(local_geometry_center)):
        raise ValueError("can_local_geometry_center_m must be finite")
    local_geometry_center_pose = np.asarray(
        [*local_geometry_center, 1.0, 0.0, 0.0, 0.0], dtype=np.float64
    )

    target_geometry_center = compose_pose(
        box,
        [
            *F2_PLASTICBOX_BASE2_CAVITY["target_center_local_m"],
            *F2_INSIDE_LOCAL_QUATERNION_WXYZ,
        ],
    )
    target_actor = matrix_pose(
        pose_matrix(target_geometry_center)
        @ np.linalg.inv(pose_matrix(local_geometry_center_pose))
    )
    final_fit = obb_inside_local_cavity(
        target_geometry_center,
        half,
        box,
        F2_PLASTICBOX_BASE2_CAVITY["lower_m"],
        F2_PLASTICBOX_BASE2_CAVITY["upper_m"],
    )
    release_eef = actor_target_to_eef_pose(
        current_eef, current_actor, target_actor
    )
    drop_release_eef = world_axis_offset_pose(
        release_eef, INSIDE_DROP_RELEASE_OFFSET_M
    )
    retreat_eef = world_axis_offset_pose(
        release_eef, INSIDE_DROP_RETREAT_OFFSET_M
    )
    pre_release_actor = world_axis_offset_pose(
        target_actor, INSIDE_DROP_RELEASE_OFFSET_M
    )
    pre_release_geometry_center = compose_pose(
        pre_release_actor, local_geometry_center_pose
    )

    actor_corners_local = _obb_corners_in_frame(
        pre_release_geometry_center, half, box
    )
    opening_axis = 1
    local_bottom = float(np.min(actor_corners_local[:, opening_axis]))
    rim = float(F2_PLASTICBOX_BASE2_CAVITY["upper_m"][opening_axis])
    rim_clearance = local_bottom - rim
    opening_half_axes = (0, 2)
    lower = np.asarray(F2_PLASTICBOX_BASE2_CAVITY["lower_m"], dtype=np.float64)
    upper = np.asarray(F2_PLASTICBOX_BASE2_CAVITY["upper_m"], dtype=np.float64)
    opening_projection_inside = bool(
        np.all(
            np.min(actor_corners_local[:, opening_half_axes], axis=0)
            >= lower[list(opening_half_axes)]
        )
        and np.all(
            np.max(actor_corners_local[:, opening_half_axes], axis=0)
            <= upper[list(opening_half_axes)]
        )
    )
    gates = {
        "final_target_full_obb_inside": bool(final_fit["pass_true_cavity_obb"]),
        "pre_release_opening_projection_inside": opening_projection_inside,
        "pre_release_actor_fully_above_cavity_rim": rim_clearance >= 0.0,
        "pre_release_rim_clearance_at_least_20mm": (
            rim_clearance >= INSIDE_MINIMUM_RIM_CLEARANCE_M
        ),
        "selected_gripper_contact_required_until_release": True,
        "final_full_obb_verifier_relaxed": False,
        "final_box_contact_and_stability_required": True,
    }
    route = {
        "schema_version": SCHEMA_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_proposal": IMPLEMENTATION_PROPOSAL,
        "formal_data": False,
        "stage0_data": False,
        "relation": "inside",
        "main_object": F2_MAIN_OBJECT,
        "arm": F2_EXECUTION_ARM,
        "reference": F2_BOX,
        "target_actor_pose": target_actor.tolist(),
        "can_local_geometry_center_m": local_geometry_center.tolist(),
        "target_geometry_center_pose": target_geometry_center.tolist(),
        "pre_release_actor_pose": pre_release_actor.tolist(),
        "pre_release_geometry_center_pose": pre_release_geometry_center.tolist(),
        "release_target_index": 0,
        "drop_offset_m": INSIDE_DROP_RELEASE_OFFSET_M,
        "retreat_offset_m": INSIDE_DROP_RETREAT_OFFSET_M,
        "settle_steps": INSIDE_SETTLE_STEPS,
        "sample_steps": list(INSIDE_SAMPLE_STEPS),
        "rim_clearance_m": rim_clearance,
        "final_target_fit": final_fit,
        "gates": gates,
        "targets": [
            {
                "segment_id": INSIDE_SEGMENT_IDS[0],
                "pose": drop_release_eef.tolist(),
            },
            {
                "segment_id": INSIDE_SEGMENT_IDS[1],
                "pose": retreat_eef.tolist(),
            },
            {"segment_id": INSIDE_SEGMENT_IDS[2], "pose": rest.tolist()},
        ],
    }
    route["audit"] = audit_inside_gravity_drop_route(route)
    return route


def _obb_corners_in_frame(
    actor_pose: Sequence[float],
    half_extents: Sequence[float],
    frame_pose: Sequence[float],
) -> np.ndarray:
    half = _half_extents(half_extents)
    local = np.asarray(
        [
            [x, y, z, 1.0]
            for x in (-half[0], half[0])
            for y in (-half[1], half[1])
            for z in (-half[2], half[2])
        ],
        dtype=np.float64,
    )
    world = (pose_matrix(actor_pose) @ local.T).T
    return (np.linalg.inv(pose_matrix(frame_pose)) @ world.T).T[:, :3]


def audit_inside_gravity_drop_route(route: Mapping[str, Any]) -> dict[str, Any]:
    """Fail-closed structural audit for an inside route artifact."""

    targets = route.get("targets")
    segment_ids = (
        tuple(item.get("segment_id") for item in targets)
        if isinstance(targets, list)
        and all(isinstance(item, Mapping) for item in targets)
        else ()
    )
    gates = route.get("gates")
    gates = gates if isinstance(gates, Mapping) else {}
    checks = {
        "identity": route.get("main_object") == F2_MAIN_OBJECT
        and route.get("arm") == F2_EXECUTION_ARM
        and route.get("reference") == F2_BOX,
        "relation_inside": route.get("relation") == "inside",
        "local_geometry_center_recorded": bool(
            np.asarray(
                route.get("can_local_geometry_center_m", []), dtype=np.float64
            ).shape
            == (3,)
            and np.all(
                np.isfinite(route.get("can_local_geometry_center_m", []))
            )
        ),
        "exact_segment_order": segment_ids == INSIDE_SEGMENT_IDS,
        "release_at_first_target": route.get("release_target_index") == 0,
        "exact_drop_offset": route.get("drop_offset_m")
        == INSIDE_DROP_RELEASE_OFFSET_M,
        "exact_retreat_offset": route.get("retreat_offset_m")
        == INSIDE_DROP_RETREAT_OFFSET_M,
        "exact_settle_and_samples": route.get("settle_steps")
        == INSIDE_SETTLE_STEPS
        and tuple(route.get("sample_steps", ())) == INSIDE_SAMPLE_STEPS,
        "final_target_full_obb_inside": gates.get(
            "final_target_full_obb_inside"
        )
        is True,
        "opening_projection_inside": gates.get(
            "pre_release_opening_projection_inside"
        )
        is True,
        "rim_clearance": isinstance(route.get("rim_clearance_m"), (int, float))
        and float(route["rim_clearance_m"])
        >= INSIDE_MINIMUM_RIM_CLEARANCE_M,
        "selected_contact_until_release": gates.get(
            "selected_gripper_contact_required_until_release"
        )
        is True,
        "strict_final_verifier": gates.get("final_full_obb_verifier_relaxed")
        is False
        and gates.get("final_box_contact_and_stability_required") is True,
    }
    return {"checks": checks, "pass": all(checks.values())}


def get_beside_candidate(candidate_id: str) -> BesideCandidate:
    try:
        return _CANDIDATE_BY_ID[candidate_id]
    except KeyError as exc:
        raise ValueError(f"unknown F2 beside candidate {candidate_id!r}") from exc


def build_beside_actor_target(
    candidate_id: str,
    *,
    stand_pose: Sequence[float],
) -> np.ndarray:
    """Build one frozen table-supported upright can target."""

    candidate = get_beside_candidate(candidate_id)
    stand = _pose(stand_pose, label="stand_pose")
    target = np.asarray(
        [
            stand[0] + candidate.stand_relative_xy_m[0],
            stand[1] + candidate.stand_relative_xy_m[1],
            float(LAYOUT["can_xyz"][2]),
            *FROZEN_CAN_UPRIGHT_QUATERNION_WXYZ,
        ],
        dtype=np.float64,
    )
    return world_z_yaw_pose(target, candidate.yaw_radians)


def build_beside_route(
    candidate_id: str,
    *,
    current_eef_pose: Sequence[float],
    current_actor_pose: Sequence[float],
    stand_pose: Sequence[float],
    rest_eef_pose: Sequence[float],
) -> dict[str, Any]:
    """Build the exact seven-target chained route for one candidate."""

    candidate = get_beside_candidate(candidate_id)
    current_eef = _pose(current_eef_pose, label="current_eef_pose")
    current_actor = _pose(current_actor_pose, label="current_actor_pose")
    rest = _pose(rest_eef_pose, label="rest_eef_pose")
    target_actor = build_beside_actor_target(
        candidate_id, stand_pose=stand_pose
    )
    release = actor_target_to_eef_pose(
        current_eef, current_actor, target_actor
    )
    preplace = world_axis_offset_pose(release, candidate.height_margin_m)
    source_high = current_eef.copy()
    source_high[2] = max(float(current_eef[2]), float(preplace[2]))
    midpoint_high = preplace.copy()
    midpoint_high[:2] = (source_high[:2] + preplace[:2]) / 2.0
    midpoint_high[2] = source_high[2]

    targets = [
        {"segment_id": BESIDE_SEGMENT_IDS[0], "pose": source_high.tolist()},
        {
            "segment_id": BESIDE_SEGMENT_IDS[1],
            "pose": midpoint_high.tolist(),
        },
        {"segment_id": BESIDE_SEGMENT_IDS[2], "pose": preplace.tolist()},
        {"segment_id": BESIDE_SEGMENT_IDS[3], "pose": release.tolist()},
        {"segment_id": BESIDE_SEGMENT_IDS[4], "pose": preplace.tolist()},
        {
            "segment_id": BESIDE_SEGMENT_IDS[5],
            "pose": midpoint_high.tolist(),
        },
        {"segment_id": BESIDE_SEGMENT_IDS[6], "pose": rest.tolist()},
    ]
    route = {
        "schema_version": SCHEMA_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_proposal": IMPLEMENTATION_PROPOSAL,
        "formal_data": False,
        "stage0_data": False,
        "relation": "beside",
        "main_object": F2_MAIN_OBJECT,
        "arm": F2_EXECUTION_ARM,
        "reference": F2_STAND,
        "candidate": candidate.as_dict(),
        "target_actor_pose": target_actor.tolist(),
        "release_target_index": 3,
        "targets": targets,
    }
    route["audit"] = audit_beside_route(route, stand_pose=stand_pose)
    return route


def _inside_xy(point: np.ndarray) -> bool:
    center = (
        np.asarray(LAYOUT["box_xyz"][:2], dtype=np.float64)
        + BOX_INSIDE_CENTER_OFFSET_WORLD_M[:2]
    )
    return bool(np.all(np.abs(point - center) <= BOX_INSIDE_HALF_XY_M))


def _on_xy(point: np.ndarray) -> bool:
    center = (
        np.asarray(LAYOUT["scale_xyz"][:2], dtype=np.float64)
        + SCALE_TOP_CENTER_OFFSET_WORLD_M[:2]
    )
    return bool(np.all(np.abs(point - center) <= SCALE_TOP_HALF_XY_M))


def audit_beside_route(
    route: Mapping[str, Any], *, stand_pose: Sequence[float]
) -> dict[str, Any]:
    """Audit fixed identity, geometry, and route structure without planning."""

    stand = _pose(stand_pose, label="stand_pose")
    candidate_value = route.get("candidate")
    candidate_id = (
        candidate_value.get("candidate_id")
        if isinstance(candidate_value, Mapping)
        else None
    )
    try:
        candidate = get_beside_candidate(str(candidate_id))
    except ValueError:
        candidate = None
    target = np.asarray(route.get("target_actor_pose", []), dtype=np.float64)
    targets = route.get("targets")
    segment_ids = (
        tuple(item.get("segment_id") for item in targets)
        if isinstance(targets, list)
        and all(isinstance(item, Mapping) for item in targets)
        else ()
    )
    target_finite = target.shape == (7,) and bool(np.all(np.isfinite(target)))
    point = target[:2] if target_finite else np.asarray([np.nan, np.nan])
    radial = (
        float(np.linalg.norm(point - stand[:2])) if target_finite else np.nan
    )
    within_table = bool(
        target_finite
        and TABLE_BOUNDS_XY[0, 0] <= point[0] <= TABLE_BOUNDS_XY[1, 0]
        and TABLE_BOUNDS_XY[0, 1] <= point[1] <= TABLE_BOUNDS_XY[1, 1]
    )
    candidate_exact = bool(
        candidate is not None and candidate_value == candidate.as_dict()
    )
    expected_target = (
        build_beside_actor_target(candidate.candidate_id, stand_pose=stand)
        if candidate is not None
        else None
    )
    target_exact = bool(
        expected_target is not None
        and target_finite
        and np.allclose(target, expected_target, atol=1e-12, rtol=0.0)
    )
    poses_finite = bool(
        isinstance(targets, list)
        and all(
            np.asarray(item.get("pose", []), dtype=np.float64).shape == (7,)
            and np.all(np.isfinite(item["pose"]))
            for item in targets
        )
    )
    reciprocal_waypoints = bool(
        isinstance(targets, list)
        and len(targets) == 7
        and np.allclose(targets[2]["pose"], targets[4]["pose"], atol=0, rtol=0)
        and np.allclose(targets[1]["pose"], targets[5]["pose"], atol=0, rtol=0)
    )
    checks = {
        "identity": route.get("main_object") == F2_MAIN_OBJECT
        and route.get("arm") == F2_EXECUTION_ARM
        and route.get("reference") == F2_STAND,
        "relation_beside": route.get("relation") == "beside",
        "candidate_exact": candidate_exact,
        "target_exact": target_exact,
        "target_table_support_height": bool(
            target_finite
            and np.isclose(
                target[2], LAYOUT["can_xyz"][2], atol=1e-12, rtol=0.0
            )
        ),
        "target_inside_table": within_table,
        "target_in_beside_annulus": target_finite
        and BESIDE_INNER_M <= radial <= BESIDE_OUTER_M,
        "target_excludes_inside_on": target_finite
        and not _inside_xy(point)
        and not _on_xy(point),
        "exact_segment_order": segment_ids == BESIDE_SEGMENT_IDS,
        "release_at_fourth_target": route.get("release_target_index") == 3,
        "finite_target_poses": poses_finite,
        "reciprocal_waypoints": reciprocal_waypoints,
    }
    return {
        "candidate_id": candidate_id,
        "radial_distance_m": radial,
        "checks": checks,
        "pass": all(checks.values()),
    }


def audit_beside_candidate_receipts(
    receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Select the first full-chain success from a fixed-order receipt prefix.

    A failed candidate may contain only the queried prefix of the seven target
    segments, ending in one planner failure.  A successful candidate must
    contain all seven successful segments.  Supplying receipts after the first
    success is rejected, which makes the stop rule machine-checkable.
    """

    if len(receipts) > len(BESIDE_CANDIDATES):
        raise ValueError("more than six beside candidates were evaluated")
    expected_ids = [item.candidate_id for item in BESIDE_CANDIDATES]
    actual_ids = [item.get("candidate_id") for item in receipts]
    if actual_ids != expected_ids[: len(actual_ids)]:
        raise ValueError("beside candidate receipts are not a fixed-order prefix")

    evaluated = []
    selected = None
    shared_seed = set()
    shared_start = set()
    shared_reset = set()
    shared_planner_instance = set()
    total_queries = 0
    for receipt in receipts:
        if selected is not None:
            raise ValueError("a beside candidate was queried after first success")
        segments = receipt.get("segment_receipts")
        if not isinstance(segments, list) or not 1 <= len(segments) <= 7:
            raise ValueError("candidate must receipt one to seven planner queries")
        segment_ids = [item.get("segment_id") for item in segments]
        if segment_ids != list(BESIDE_SEGMENT_IDS[: len(segments)]):
            raise ValueError("candidate planner segments are not a route prefix")
        if receipt.get("planner_query_count") != len(segments):
            raise ValueError("candidate planner query count is inconsistent")
        statuses = [item.get("planner_status") for item in segments]
        if any(status not in ("Success", "Fail") for status in statuses):
            raise ValueError("candidate planner status is invalid")
        if "Fail" in statuses and (
            statuses[-1] != "Fail" or statuses.count("Fail") != 1
        ):
            raise ValueError("candidate must stop at its first planner failure")
        chain_continuity = all(
            segments[index - 1].get("end_qpos_sha256")
            == segments[index].get("start_qpos_sha256")
            for index in range(1, len(segments))
        )
        full_planner_success = len(segments) == 7 and all(
            status == "Success" for status in statuses
        )
        identity = (
            receipt.get("main_object") == F2_MAIN_OBJECT
            and receipt.get("arm") == F2_EXECUTION_ARM
            and receipt.get("reference") == F2_STAND
        )
        candidate_checks = {
            "identity": identity,
            "route_audit": receipt.get("route_audit_pass") is True,
            "planner_reset": receipt.get("planner_reset_performed") is True,
            "planner_input_prefix_start_link": receipt.get(
                "first_segment_start_matches_planner_input_prefix_end"
            )
            is True,
            "chain_continuity": chain_continuity,
            "upright_axis": receipt.get("upright_axis_audited") is True,
            "joint_limits": receipt.get("terminal_qpos_within_joint_limits")
            is True,
            "waypoint_envelope": receipt.get(
                "waypoint_envelope_pass"
            )
            is True,
            "actual_transport_contact_gate_bound": receipt.get(
                "actual_held_transport_contact_gate_required"
            )
            is True,
            "facility_distance": receipt.get("facility_distance_pass") is True,
            "full_planner_chain": full_planner_success,
        }
        shared_seed.add(receipt.get("planner_seed"))
        shared_start.add(receipt.get("planner_start_state_sha256"))
        shared_reset.add(receipt.get("rng_state_after_reset_sha256"))
        shared_planner_instance.add(receipt.get("planner_instance_id"))
        total_queries += len(segments)
        item = dict(receipt)
        item["checks"] = candidate_checks
        item["verified"] = all(candidate_checks.values())
        evaluated.append(item)
        if item["verified"]:
            selected = item

    if receipts and (
        None in shared_seed
        or None in shared_start
        or None in shared_reset
        or None in shared_planner_instance
        or len(shared_seed) != 1
        or len(shared_start) != 1
        or len(shared_reset) != 1
        or len(shared_planner_instance) != 1
        or shared_seed != {BESIDE_PLANNER_SEED}
    ):
        raise ValueError("beside candidates did not share one frozen planner state")
    exhausted = len(receipts) == len(BESIDE_CANDIDATES) and selected is None
    return {
        "schema_version": SCHEMA_VERSION,
        "pass": selected is not None,
        "selected_candidate_id": None
        if selected is None
        else selected["candidate_id"],
        "evaluated": evaluated,
        "planner_query_count": total_queries,
        "exhausted": exhausted,
        "terminal_if_exhausted": BESIDE_EXHAUSTION_TERMINAL
        if exhausted
        else None,
    }


def audit_f2_held_transport_contacts(
    rows: Sequence[Mapping[str, Any]],
    *,
    relation: str,
    can_actor_name: str,
    selected_gripper_body_names: Sequence[str],
    named_facility_body_names: Sequence[str],
    relation_support_body_names: Sequence[str] = (),
    support_contact_start_relative_row: int | None = None,
    held_segment_trace_windows: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Hard-Gate actual held-can continuity and body contacts before release."""

    rows = list(rows)
    if not rows:
        raise ValueError("F2 held transport contact audit requires trace rows")
    if relation not in ("inside", "on", "beside"):
        raise ValueError("F2 held transport relation is invalid")
    can_name = str(can_actor_name)
    grippers = {str(name) for name in selected_gripper_body_names}
    facilities = {str(name) for name in named_facility_body_names}
    supports = {str(name) for name in relation_support_body_names}
    if not can_name or not grippers:
        raise ValueError("F2 held transport roles must be nonempty")
    if relation in ("on", "beside"):
        if not supports or not isinstance(support_contact_start_relative_row, int):
            raise ValueError(
                "F2 on/beside transport requires a support-contact boundary"
            )
        if not 0 <= support_contact_start_relative_row < len(rows):
            raise ValueError(
                "F2 on/beside support-contact boundary is outside trace rows"
            )
        if relation == "on" and (
            not supports.issubset(facilities)
            or not any("scale" in name.lower() for name in supports)
        ):
            raise ValueError("F2 on may whitelist only the scale support")
        if relation == "beside" and (
            len(supports) != 1
            or not all("table" in name.lower() for name in supports)
            or not supports.isdisjoint(facilities)
        ):
            raise ValueError("F2 beside may whitelist only the table support")
    elif supports or support_contact_start_relative_row is not None:
        raise ValueError("F2 inside may not allow a held support contact")

    unintended = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError("F2 held transport row must be a mapping")
        pairs = row.get("contact_pairs")
        if not isinstance(pairs, list):
            raise ValueError("F2 held transport row lacks contact_pairs")
        allowed_supports = (
            supports
            if support_contact_start_relative_row is not None
            and row_index >= support_contact_start_relative_row
            else set()
        )
        allowed = grippers | allowed_supports
        for pair in pairs:
            bodies = {pair.get("body_a"), pair.get("body_b")}
            if can_name not in bodies:
                continue
            collided = sorted(str(name) for name in bodies - {can_name} - allowed)
            if collided:
                unintended.append(
                    {
                        "relative_trace_row": row_index,
                        "body_a": pair.get("body_a"),
                        "body_b": pair.get("body_b"),
                        "unintended_body_names": collided,
                        "contains_named_frozen_facility": bool(
                            set(collided) & facilities
                        ),
                        "contains_table_or_support": any(
                            "table" in name.lower() or "support" in name.lower()
                            for name in collided
                        ),
                        "point_count": int(pair.get("point_count", 0)),
                        "impulse_norm_sum": float(
                            pair.get("impulse_norm_sum", 0.0)
                        ),
                    }
                )
    contact_flags = [bool(row.get("selected_gripper_contact")) for row in rows]
    actor_identity = all(
        str(row.get("selected_contact_actor_name")) == can_name for row in rows
    )
    checks = {
        "selected_gripper_contact_continuous": all(contact_flags),
        "selected_contact_actor_identity": actor_identity,
        "no_unintended_body_contact": not unintended,
    }
    return {
        "schema_version": "cmf_f2_held_transport_contact_gate_v1",
        "relation": relation,
        "evaluated_trace_row_count": len(rows),
        "selected_gripper_body_names": sorted(grippers),
        "relation_support_body_names": sorted(supports),
        "named_facility_body_names": sorted(facilities),
        "support_contact_allowed_from_relative_trace_row": (
            support_contact_start_relative_row
        ),
        "held_segment_trace_windows": [dict(item) for item in held_segment_trace_windows],
        "selected_gripper_contact_fraction": float(np.mean(contact_flags)),
        "selected_contact_actor_identity_pass": actor_identity,
        "unintended_facility_contacts": unintended,
        "policy": (
            "while held, can must remain continuously attached to the selected "
            "left gripper and may contact only selected gripper links plus an "
            "explicit relation support from the frozen release-segment boundary"
        ),
        "checks": checks,
        "pass": all(checks.values()),
    }
