"""Finite, rank-ordered F4 development template qualification contract."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f4_layout_candidate_search_v2 import (
    MAXIMUM_CANDIDATE_COUNT,
    PROGRAM_ORDERS,
    SELECTED_EXISTING_CORRIDOR_ID,
    build_f4_layout_candidate_search_v2,
)


SCHEMA_VERSION = "cmf_f4_template_qualification_v1"
IMPLEMENTATION_VERSION = "controlled_multi_future_f4_template_qualification_v1"
SCOPE = "F4_TEMPLATE_QUALIFICATION_V1"
PROGRAM_IDS = ("F4-ABC", "F4-ACB", "F4-BAC")
ROLES = ("A", "B", "C")
REQUIRED_ROLE_SEGMENT_SUFFIXES = (
    "pregrasp",
    "grasp",
    "lift",
    "carry_mid",
    "preplace",
    "release",
    "neutral",
)


def build_f4_template_qualification_v1() -> dict[str, Any]:
    search = build_f4_layout_candidate_search_v2()
    if not 0 < search["candidate_count"] <= MAXIMUM_CANDIDATE_COUNT:
        raise ValueError("F4 template qualification candidate count is outside bound")
    if not all(item["cpu_pass"] is True for item in search["cpu_audits"]):
        raise ValueError("F4 template qualification only dispatches CPU-passing candidates")
    value = {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "family": "F4",
        "candidate_count": search["candidate_count"],
        "maximum_candidate_count": MAXIMUM_CANDIDATE_COUNT,
        "fixed_candidate_order": list(search["fixed_candidate_order"]),
        "candidate_manifest_sha256": search["candidate_manifest_sha256"],
        "source_search_contract_sha256": search["search_contract_sha256"],
        "candidates": canonical_jsonable(search["candidates"]),
        "cpu_audits": canonical_jsonable(search["cpu_audits"]),
        "candidate_gate": {
            "fresh_scene_reconstruction": True,
            "rendered_head_camera_instance_segmentation_visibility": True,
            "common_x_prefix_planner_feasibility": True,
            "A_B_C_full_endpoint_ik": True,
            "A_B_C_complete_neutral_to_neutral_chains": True,
            "noninterference_audit": True,
            "suffix_execution_count": 0,
        },
        "program_ids": list(PROGRAM_IDS),
        "program_orders": [list(order) for order in PROGRAM_ORDERS],
        "selection_rule": "lowest-ranked fully template-qualified candidate",
        "temporary_waypoint_allowed": False,
        "online_slot_move_allowed": False,
        "program_specific_orientation_allowed": False,
        "different_layout_per_program_allowed": False,
        "verifier_threshold_change_allowed": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["qualification_contract_sha256"] = canonical_hash_json(value)
    return value


def validate_f4_template_qualification_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    normalized = canonical_jsonable(value)
    expected = build_f4_template_qualification_v1()
    if normalized != expected:
        raise ValueError("F4 template qualification V1 contract changed")
    return expected


def build_f4_template_candidate_spec_v1(candidate_id: str) -> dict[str, Any]:
    qualification = build_f4_template_qualification_v1()
    matches = [
        item for item in qualification["candidates"] if item["candidate_id"] == candidate_id
    ]
    if len(matches) != 1:
        raise ValueError("F4 template candidate is outside the frozen set")
    candidate = matches[0]
    rank = int(candidate["candidate_index"])
    value = {
        "schema_version": "cmf_f4_template_candidate_planned_spec_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "slot_id": f"f4-template-qv1-candidate-{rank:02d}",
        "family": "F4",
        "arm": "right",
        "seed": 2026090100 + rank,
        "generator": "controlled_multi_future_f4_template_qualification_v1_adapter",
        "scene_layout": candidate["layout"],
        "scene_layout_sha256": candidate["layout_sha256"],
        "f4_template_qualification_v1": qualification,
        "f4_template_qualification_contract_sha256": qualification[
            "qualification_contract_sha256"
        ],
        "selected_layout_candidate_id": candidate["candidate_id"],
        "selected_layout_candidate_sha256": candidate["candidate_sha256"],
        "post_stage0_selected_f4_corridor_id": SELECTED_EXISTING_CORRIDOR_ID,
        "canonical_program_ids": list(PROGRAM_IDS),
        "rendered_actor_segmentation_visibility_required": True,
        "complete_program_planner_chains_required": True,
        "suffix_execution_count": 0,
        "release_execution_count": 0,
        "recovery_attempts": 0,
        "temporary_waypoint_allowed": False,
        "automatic_retry": False,
        "automatic_fallback": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["planned_scope_spec_sha256"] = canonical_hash_json(value)
    return value


def validate_f4_template_candidate_spec_v1(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = canonical_jsonable(value)
    candidate_id = normalized.get("selected_layout_candidate_id")
    if not isinstance(candidate_id, str):
        raise ValueError("F4 template candidate spec lacks candidate ID")
    expected = build_f4_template_candidate_spec_v1(candidate_id)
    if normalized != expected:
        raise ValueError("F4 template candidate planned spec changed")
    return expected


def _segment_matrix(program_receipts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    matrix = {role: {} for role in ROLES}
    for program in program_receipts:
        program_id = str(program.get("program_id"))
        segments = (
            program.get("planner_receipt", {})
            .get("evidence", {})
            .get("segment_receipts", [])
        )
        by_id = {str(item.get("segment_id")): item for item in segments}
        for role in ROLES:
            expected_ids = [f"{role}_{suffix}" for suffix in REQUIRED_ROLE_SEGMENT_SUFFIXES]
            values = [by_id.get(segment_id) for segment_id in expected_ids]
            matrix[role][program_id] = {
                "segment_ids": expected_ids,
                "planner_statuses": [
                    None if item is None else item.get("planner_status") for item in values
                ],
                "endpoint_ik_and_collision_pass": all(
                    isinstance(item, Mapping)
                    and item.get("planner_status") == "Success"
                    and item.get("joint_limit_evidence_complete") is True
                    and item.get("terminal_qpos_within_joint_limits") is True
                    for item in values
                ),
            }
    return matrix


def summarize_f4_template_candidate_result_v1(
    *, candidate_spec: Mapping[str, Any], planner_result: Mapping[str, Any]
) -> dict[str, Any]:
    spec = validate_f4_template_candidate_spec_v1(candidate_spec)
    visibility = canonical_jsonable(planner_result.get("rendered_visibility_receipts", []))
    programs = canonical_jsonable(planner_result.get("program_receipts", []))
    matrix = _segment_matrix(programs)
    program_ids = [item.get("program_id") for item in programs]
    checks = {
        "fresh_scene_reconstruction": len(planner_result.get("cleanup_records", [])) == 4,
        "rendered_visibility": len(visibility) == 4
        and all(item.get("pass") is True for item in visibility),
        "common_x_prefix": int(
            planner_result.get("canonical_prefix_reference_execution_count", -1)
        )
        == 1,
        "all_programs_reported": program_ids == list(PROGRAM_IDS),
        "all_role_endpoint_sets": all(
            matrix[role].get(program_id, {}).get("endpoint_ik_and_collision_pass")
            is True
            for role in ROLES
            for program_id in PROGRAM_IDS
        ),
        "complete_chains": len(programs) == 3
        and all(item.get("segment_chain_audit", {}).get("pass") is True for item in programs),
        "noninterference": all(
            item.get("planner_receipt", {})
            .get("evidence", {})
            .get("block_carry_route_audit", {})
            .get("pass")
            is True
            for item in programs
        ),
        "suffix_never_executed": int(
            planner_result.get("suffix_execution_attempt_count", -1)
        )
        == 0,
        "release_never_executed": int(planner_result.get("release_execution_count", -1))
        == 0,
        "cleanup": bool(planner_result.get("cleanup_records"))
        and all(
            item.get("cleanup_safety_pass") is True
            and int(item.get("orphan_process_count", -1)) == 0
            for item in planner_result["cleanup_records"]
        ),
    }
    value = {
        "schema_version": "cmf_f4_template_candidate_terminal_v1",
        "candidate_id": spec["selected_layout_candidate_id"],
        "candidate_sha256": spec["selected_layout_candidate_sha256"],
        "candidate_rank": next(
            item["candidate_index"]
            for item in spec["f4_template_qualification_v1"]["candidates"]
            if item["candidate_id"] == spec["selected_layout_candidate_id"]
        ),
        "visibility_receipts": visibility,
        "endpoint_ik_planner_matrix": matrix,
        "program_receipts": programs,
        "checks": checks,
        "pass": all(checks.values()),
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def select_f4_template_v1(
    candidate_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    qualification = build_f4_template_qualification_v1()
    by_id = {str(item.get("candidate_id")): canonical_jsonable(item) for item in candidate_receipts}
    order = qualification["fixed_candidate_order"]
    if set(by_id) != set(order) or len(by_id) != len(order):
        raise ValueError("F4 qualification must report every frozen candidate exactly once")
    ordered = [by_id[candidate_id] for candidate_id in order]
    candidates = {item["candidate_id"]: item for item in qualification["candidates"]}
    for receipt in ordered:
        candidate = candidates[receipt["candidate_id"]]
        if receipt.get("candidate_sha256") != candidate["candidate_sha256"]:
            raise ValueError("F4 candidate receipt hash binding changed")
    passing = [item for item in ordered if item.get("pass") is True]
    selected = candidates[passing[0]["candidate_id"]] if passing else None
    status = (
        "TEMPLATE_PASS_REQUIRES_A_ONLY_EXECUTION"
        if selected is not None
        else "BOUNDED_LAYOUT_SEARCH_EXHAUSTED_REQUIRES_HIGHER_LEVEL_LAYOUT_REDESIGN"
    )
    value = {
        "schema_version": "cmf_f4_template_selection_terminal_v1",
        "qualification_contract_sha256": qualification[
            "qualification_contract_sha256"
        ],
        "candidate_receipts": ordered,
        "selected_template": selected,
        "selection_rule": qualification["selection_rule"],
        "status": status,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


__all__ = [
    "IMPLEMENTATION_VERSION",
    "PROGRAM_IDS",
    "REQUIRED_ROLE_SEGMENT_SUFFIXES",
    "ROLES",
    "SCOPE",
    "build_f4_template_candidate_spec_v1",
    "build_f4_template_qualification_v1",
    "select_f4_template_v1",
    "summarize_f4_template_candidate_result_v1",
    "validate_f4_template_candidate_spec_v1",
    "validate_f4_template_qualification_v1",
]
