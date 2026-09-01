"""Hierarchical F4 source/grasp then slot/corridor template search.

Stage A changes the source/grasp entry point and contains no slot search.
Every source candidate derives from the F1 five-root, 15-trajectory accepted
reachability envelope and its planner-assisted target construction.  Stage B
is inaccessible until one Stage-A candidate fully passes.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .project_cube_grasp_pose_v1 import build_project_cube_grasp_poses


SCHEMA_VERSION = "cmf_f4_hierarchical_template_search_v1"
IMPLEMENTATION_VERSION = "controlled_multi_future_f4_hierarchical_template_search_v1"
SCOPE = "F4_HIERARCHICAL_TEMPLATE_SEARCH_V1"
PROGRAM_IDS = ("F4-ABC", "F4-ACB", "F4-BAC")
ROLES = ("A", "B", "C")
MAXIMUM_SOURCE_GRASP_CANDIDATES = 8
MAXIMUM_SLOT_CORRIDOR_CANDIDATES = 8
F1_ACCEPTED_ROOT_COUNT = 5
F1_ACCEPTED_TRAJECTORY_COUNT = 15
F1_REPORT_PAYLOAD_SHA256 = (
    "dd3d371c54b7abe3b3f54d511a4c848d3262ec67f858e4829456d9a7f92b166c"
)
BLOCK_HALF_EXTENTS_M = (0.022, 0.022, 0.022)
F1_SOURCE_ENVELOPE = {
    "x_min_m": -0.20,
    "x_max_m": -0.02,
    "y_m": 0.02,
    "z_m": 0.762,
    "bilateral_mirror_allowed_for_right_arm": True,
}
F1_TARGET_CONSTRUCTION = {
    "policy": "f1_planner_assisted_top_down_v3_3",
    "pregrasp_offset_world_m": [0.0, 0.0, 0.210],
    "grasp_offset_world_m": [0.0, 0.0, 0.120],
    "lift_mid_offset_world_m": [0.0, 0.0, 0.160],
    "lift_total_offset_world_m": [0.0, 0.0, 0.200],
    "collision_aware_orientation_adjustment": True,
    "uniform_carry_hub": True,
}
RIGHT_PROJECT_CUBE_TARGET_CONSTRUCTION = {
    "policy": "project_cube_grasp_pose_v1",
    "arm": "right",
    "source": "successful F4 common-X right-arm grasp/transport",
    "local_grasp_contract_module": "project_cube_grasp_pose_v1.py",
    "cube_half_extents_m": list(BLOCK_HALF_EXTENTS_M),
    "collision_aware_orientation_adjustment": False,
    "f1_geometry_compatible": True,
    "f1_15_of_15_execution_claimed": False,
}

_SOURCE_ROWS = (
    ("left", (-0.20, -0.11, -0.02)),
    ("left", (-0.17, -0.08, -0.02)),
    ("left", (-0.11, -0.20, -0.02)),
    ("left", (-0.02, -0.20, -0.11)),
    ("right", (0.02, 0.11, 0.20)),
    ("right", (0.08, 0.02, 0.17)),
    ("right", (0.11, 0.20, 0.02)),
    ("right", (0.20, 0.02, 0.11)),
)

_SLOT_ROWS = (
    (0.100, 0.205, 0.355),
    (0.080, 0.200, 0.360),
    (0.070, 0.195, 0.360),
    (0.060, 0.180, 0.340),
)
_CORRIDOR_POLICIES = (
    "lower_carry_height",
    "f1_uniform_cluster_center_carry_hub",
)


def _pairwise_surface_clearance_m(xs: Sequence[float]) -> float:
    values = [float(value) for value in xs]
    return min(
        abs(values[left] - values[right]) - 2.0 * BLOCK_HALF_EXTENTS_M[0]
        for left in range(len(values))
        for right in range(left + 1, len(values))
    )


def _target_pose(source_pose: Sequence[float], offset: Sequence[float]) -> list[float]:
    # Orientation is intentionally absent here: the real adapter must call the
    # F1 planner-assisted constructor, including its collision-aware adjustment.
    return [float(source_pose[index]) + float(offset[index]) for index in range(3)]


def preregistered_f4_source_grasp_candidates_v1() -> list[dict[str, Any]]:
    candidates = []
    old_a_source_xyz = [0.06, 0.12, 0.762]
    for rank, (arm, xs) in enumerate(_SOURCE_ROWS, start=1):
        poses = {
            role: [float(x), F1_SOURCE_ENVELOPE["y_m"], F1_SOURCE_ENVELOPE["z_m"], 1.0, 0.0, 0.0, 0.0]
            for role, x in zip(ROLES, xs)
        }
        grasp_policy = (
            deepcopy(F1_TARGET_CONSTRUCTION)
            if arm == "left"
            else deepcopy(RIGHT_PROJECT_CUBE_TARGET_CONSTRUCTION)
        )
        if arm == "left":
            a_pregrasp_xyz = _target_pose(
                poses["A"], F1_TARGET_CONSTRUCTION["pregrasp_offset_world_m"]
            )
        else:
            a_pregrasp, _, _ = build_project_cube_grasp_poses(
                poses["A"],
                cube_half_extents_m=BLOCK_HALF_EXTENTS_M,
                arm="right",
                pregrasp_distance_m=0.09,
            )
            a_pregrasp_xyz = a_pregrasp[:3].tolist()
        candidate = {
            "rank": rank,
            "candidate_id": f"f4-source-grasp-hv1-r{rank:02d}",
            "arm": arm,
            "source_layout": poses,
            "source_layout_sha256": canonical_hash_json(poses),
            "grasp_policy": grasp_policy,
            "grasp_policy_source": (
                "F1 accepted 5-root/15-trajectory development batch"
                if arm == "left"
                else "F4 common-X successful right-arm project-cube contract"
            ),
            "f1_report_payload_sha256": F1_REPORT_PAYLOAD_SHA256,
            "f1_15_of_15_execution_claim_applies_to_candidate": arm == "left",
            "block_half_extents_m": list(BLOCK_HALF_EXTENTS_M),
            "A_pregrasp_xyz_m": a_pregrasp_xyz,
            "A_pregrasp_differs_from_old_f4": a_pregrasp_xyz[:2]
            != old_a_source_xyz[:2],
            "minimum_pairwise_block_surface_clearance_m": _pairwise_surface_clearance_m(xs),
            "slot_fields_present": False,
            "branch_neutral_policy": "arm_original_pose_after_each_role",
            "common_x_tray_changed": False,
            "object_slot_mapping_changed": False,
            "programs_changed": False,
            "verifier_thresholds_changed": False,
            "automatic_retry": False,
            "online_fallback": False,
        }
        candidate["candidate_sha256"] = canonical_hash_json(candidate)
        candidates.append(candidate)
    if len(candidates) != MAXIMUM_SOURCE_GRASP_CANDIDATES:
        raise AssertionError("F4 Stage-A source/grasp candidate bound changed")
    if len({tuple(item["A_pregrasp_xyz_m"]) for item in candidates}) != len(candidates):
        raise AssertionError("F4 every Stage-A candidate must change A_pregrasp")
    if not all(item["minimum_pairwise_block_surface_clearance_m"] > 0 for item in candidates):
        raise AssertionError("F4 Stage-A source rows overlap")
    return candidates


def build_f4_hierarchical_template_search_v1() -> dict[str, Any]:
    candidates = preregistered_f4_source_grasp_candidates_v1()
    value = {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "family": "F4",
        "program_ids": list(PROGRAM_IDS),
        "program_orders": [["A", "B", "C"], ["A", "C", "B"], ["B", "A", "C"]],
        "common_x_completed_first": True,
        "equal_final_world_state_required": True,
        "same_object_slot_mapping_required": True,
        "f1_reference": {
            "accepted_root_count": F1_ACCEPTED_ROOT_COUNT,
            "accepted_trajectory_count": F1_ACCEPTED_TRAJECTORY_COUNT,
            "report_payload_sha256": F1_REPORT_PAYLOAD_SHA256,
            "source_envelope": deepcopy(F1_SOURCE_ENVELOPE),
            "target_construction": deepcopy(F1_TARGET_CONSTRUCTION),
            "same_block_half_extents_m": list(BLOCK_HALF_EXTENTS_M),
        },
        "stage_a_candidates": candidates,
        "fixed_stage_a_order": [item["candidate_id"] for item in candidates],
        "maximum_stage_a_candidates": MAXIMUM_SOURCE_GRASP_CANDIDATES,
        "stage_a_has_slot_search": False,
        "stage_a_required_gates": [
            "rendered_visibility",
            "A_pregrasp_grasp_lift_planner",
            "B_pregrasp_grasp_lift_planner",
            "C_pregrasp_grasp_lift_planner",
            "all_roles_return_one_neutral",
        ],
        "stage_a_selection_rule": "lowest-ranked full pass",
        "stage_a_exhaustion_status": (
            "HIERARCHICAL_SOURCE_GRASP_OR_SLOT_SEARCH_EXHAUSTED"
        ),
        "stage_b_allowed_only_after_stage_a_pass": True,
        "maximum_stage_b_candidates": MAXIMUM_SLOT_CORRIDOR_CANDIDATES,
        "stage_b_required_gates": [
            "complete_A_neutral_grasp_slot_neutral",
            "complete_B_neutral_grasp_slot_neutral",
            "complete_C_neutral_grasp_slot_neutral",
            "rendered_visibility",
            "noninterference",
            "prior_slot_preservation",
        ],
        "single_role_execution_order": ["A-only", "B-only", "C-only"],
        "full_root_allowed_only_after_single_role_3_of_3": True,
        "success_status": "PASS_F4_SOURCE_GRASP_SLOT_TEMPLATE_AND_TEMPORAL_ROOT",
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
        "training_authorized": False,
    }
    value["search_contract_sha256"] = canonical_hash_json(value)
    return value


def validate_f4_hierarchical_template_search_v1(
    value: Mapping[str, Any]
) -> dict[str, Any]:
    expected = build_f4_hierarchical_template_search_v1()
    if canonical_jsonable(value) != expected:
        raise ValueError("F4 hierarchical template search V1 contract changed")
    return expected


def select_f4_stage_a_source_v1(
    contract: Mapping[str, Any], planner_receipts: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    checked = validate_f4_hierarchical_template_search_v1(contract)
    order = checked["fixed_stage_a_order"]
    by_id = {str(item.get("candidate_id")): canonical_jsonable(item) for item in planner_receipts}
    if set(by_id) != set(order):
        raise ValueError("F4 Stage-A receipts must cover all eight candidates")
    candidates = {item["candidate_id"]: item for item in checked["stage_a_candidates"]}
    ordered = [by_id[candidate_id] for candidate_id in order]
    passing = []
    for receipt in ordered:
        candidate = candidates[receipt["candidate_id"]]
        checks = receipt.get("checks")
        if receipt.get("candidate_sha256") != candidate["candidate_sha256"]:
            raise ValueError("F4 Stage-A receipt candidate hash mismatch")
        if (
            isinstance(checks, Mapping)
            and set(checks) == set(checked["stage_a_required_gates"])
            and all(checks[name] is True for name in checked["stage_a_required_gates"])
            and receipt.get("cleanup_safety_pass") is True
            and receipt.get("orphan_process_count") == 0
        ):
            passing.append(candidate)
    selected = passing[0] if passing else None
    value = {
        "schema_version": "cmf_f4_hierarchical_stage_a_terminal_v1",
        "search_contract_sha256": checked["search_contract_sha256"],
        "planner_receipts": ordered,
        "selected_source_grasp": selected,
        "stage_b_authorized_by_result": selected is not None,
        "status": (
            "SOURCE_GRASP_PASS_REQUIRES_STAGE_B_SLOT_SEARCH"
            if selected is not None
            else checked["stage_a_exhaustion_status"]
        ),
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def build_f4_stage_b_candidates_v1(
    contract: Mapping[str, Any], stage_a_terminal: Mapping[str, Any]
) -> dict[str, Any]:
    checked = validate_f4_hierarchical_template_search_v1(contract)
    source = stage_a_terminal.get("selected_source_grasp")
    if not isinstance(source, Mapping) or stage_a_terminal.get("stage_b_authorized_by_result") is not True:
        raise ValueError("F4 Stage B cannot be built before a Stage-A pass")
    canonical_source = next(
        (
            item
            for item in checked["stage_a_candidates"]
            if item["candidate_id"] == source.get("candidate_id")
            and item["candidate_sha256"] == source.get("candidate_sha256")
        ),
        None,
    )
    if canonical_source is None:
        raise ValueError("F4 Stage-A selected source is outside the frozen set")
    mirror = -1.0 if canonical_source["arm"] == "left" else 1.0
    candidates = []
    for slot_row in _SLOT_ROWS:
        for corridor_policy in _CORRIDOR_POLICIES:
            slot_poses = {
                role: [mirror * float(x), 0.04, 0.742, 1.0, 0.0, 0.0, 0.0]
                for role, x in zip(ROLES, slot_row)
            }
            candidate = {
                "rank": len(candidates) + 1,
                "candidate_id": f"f4-slot-corridor-hv1-r{len(candidates) + 1:02d}",
                "source_grasp_candidate_id": canonical_source["candidate_id"],
                "source_grasp_candidate_sha256": canonical_source["candidate_sha256"],
                "arm": canonical_source["arm"],
                "slot_poses": slot_poses,
                "slot_poses_sha256": canonical_hash_json(slot_poses),
                "corridor_policy": corridor_policy,
                "object_slot_mapping": {role: f"slot_{role}" for role in ROLES},
                "temporary_waypoint_allowed": False,
                "program_specific_layout_allowed": False,
                "automatic_retry": False,
                "online_fallback": False,
            }
            candidate["candidate_sha256"] = canonical_hash_json(candidate)
            candidates.append(candidate)
    if len(candidates) != MAXIMUM_SLOT_CORRIDOR_CANDIDATES:
        raise AssertionError("F4 Stage-B slot/corridor candidate bound changed")
    value = {
        "schema_version": "cmf_f4_hierarchical_stage_b_contract_v1",
        "parent_search_contract_sha256": checked["search_contract_sha256"],
        "selected_source_grasp": deepcopy(canonical_source),
        "candidates": candidates,
        "fixed_candidate_order": [item["candidate_id"] for item in candidates],
        "maximum_candidate_count": MAXIMUM_SLOT_CORRIDOR_CANDIDATES,
        "selection_rule": "lowest-ranked full planner-only pass",
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["stage_b_contract_sha256"] = canonical_hash_json(value)
    return value


def select_f4_stage_b_layout_v1(
    contract: Mapping[str, Any],
    stage_a_terminal: Mapping[str, Any],
    planner_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    checked = validate_f4_hierarchical_template_search_v1(contract)
    stage_b = build_f4_stage_b_candidates_v1(checked, stage_a_terminal)
    order = stage_b["fixed_candidate_order"]
    by_id = {
        str(item.get("candidate_id")): canonical_jsonable(item)
        for item in planner_receipts
    }
    if set(by_id) != set(order) or len(by_id) != len(order):
        raise ValueError("F4 Stage-B receipts must cover all eight candidates")
    candidates = {
        item["candidate_id"]: item for item in stage_b["candidates"]
    }
    ordered = [by_id[candidate_id] for candidate_id in order]
    passing = []
    for receipt in ordered:
        candidate = candidates[receipt["candidate_id"]]
        checks = receipt.get("checks")
        if receipt.get("candidate_sha256") != candidate["candidate_sha256"]:
            raise ValueError("F4 Stage-B receipt candidate hash mismatch")
        if (
            isinstance(checks, Mapping)
            and set(checks) == set(checked["stage_b_required_gates"])
            and all(
                checks[name] is True
                for name in checked["stage_b_required_gates"]
            )
            and receipt.get("cleanup_safety_pass") is True
            and receipt.get("orphan_process_count") == 0
        ):
            passing.append(candidate)
    selected = passing[0] if passing else None
    value = {
        "schema_version": "cmf_f4_hierarchical_stage_b_terminal_v1",
        "parent_search_contract_sha256": checked["search_contract_sha256"],
        "stage_a_terminal_sha256": stage_a_terminal.get("receipt_sha256"),
        "stage_b_contract_sha256": stage_b["stage_b_contract_sha256"],
        "planner_receipts": ordered,
        "selected_slot_corridor": selected,
        "single_role_physical_authorized_by_result": selected is not None,
        "status": (
            "SLOT_CORRIDOR_PASS_REQUIRES_A_ONLY_EXECUTION"
            if selected is not None
            else checked["stage_a_exhaustion_status"]
        ),
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


__all__ = [
    "MAXIMUM_SLOT_CORRIDOR_CANDIDATES",
    "MAXIMUM_SOURCE_GRASP_CANDIDATES",
    "build_f4_hierarchical_template_search_v1",
    "build_f4_stage_b_candidates_v1",
    "preregistered_f4_source_grasp_candidates_v1",
    "select_f4_stage_a_source_v1",
    "select_f4_stage_b_layout_v1",
    "validate_f4_hierarchical_template_search_v1",
]
