"""Bounded, rank-ordered F3 nuisance-grasp qualification contract.

The grasp is development infrastructure.  V/H axes, VVHH/VHVH/VHHV,
same-start/end semantics, and every existing motion/verifier threshold remain
unchanged.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .canonical_artifact import canonical_hash_json, canonical_jsonable


SCHEMA_VERSION = "cmf_f3_grasp_qualification_v1"
IMPLEMENTATION_VERSION = "controlled_multi_future_f3_grasp_qualification_v1"
SCOPE = "F3_GRASP_QUALIFICATION_V1"
ASSET = {"modelname": "001_bottle", "model_id": 13}
PROGRAM_IDS = ("F3-VVHH", "F3-VHVH", "F3-VHHV")
MAXIMUM_CANDIDATE_COUNT = 12
MAXIMUM_PHYSICAL_CANDIDATE_COUNT = 4
PREGRASP_DISTANCE_M = 0.09
TARGET_DISTANCE_M = 0.0
CLOSE_NORMALIZED_TARGET = 0.50
POST_CLOSE_SETTLE_FRAMES = 250

REQUIRED_PHYSICAL_GATES = (
    "planner_success",
    "selected_gripper_contact_continuity",
    "grasp_transform_translation_stable",
    "grasp_transform_orientation_stable",
    "bottle_off_support_after_lift",
    "bottle_linear_stability",
    "bottle_angular_stability",
    "shared_v_realized_amplitude",
    "shared_v_closed_loop_return",
    "eef_tracking",
)


def preregistered_f3_grasp_candidates_v1() -> list[dict[str, Any]]:
    # Contact 0 has ten official rotation candidates and historical evidence
    # that all ten endpoint plans succeeded.  Contact 3 is retained only as a
    # lower-priority official fallback; its earlier slip evidence is explicit.
    definitions = [(0, index) for index in range(10)] + [(3, 0), (3, 1)]
    values = []
    for rank, (contact_id, rotation_index) in enumerate(definitions, start=1):
        value = {
            "rank": rank,
            "candidate_id": f"f3-grasp-qv1-r{rank:02d}",
            "asset": dict(ASSET),
            "arm": "left",
            "source": "official_contact_and_rotation_candidate",
            "contact_point_id": contact_id,
            "rotation_candidate_index": rotation_index,
            "pregrasp_distance_m": PREGRASP_DISTANCE_M,
            "target_distance_m": TARGET_DISTANCE_M,
            "close_normalized_target": CLOSE_NORMALIZED_TARGET,
            "post_close_settle_frames": POST_CLOSE_SETTLE_FRAMES,
            "program_independent": True,
            "historical_contact3_slip_evidence": contact_id == 3,
            "vh_axes_changed": False,
            "programs_changed": False,
            "verifier_thresholds_changed": False,
            "online_fallback": False,
        }
        value["candidate_sha256"] = canonical_hash_json(value)
        values.append(value)
    if len(values) != MAXIMUM_CANDIDATE_COUNT:
        raise AssertionError("F3 qualification candidate bound changed")
    return values


def build_f3_grasp_qualification_v1() -> dict[str, Any]:
    candidates = preregistered_f3_grasp_candidates_v1()
    value = {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "family": "F3",
        "asset": dict(ASSET),
        "program_ids": list(PROGRAM_IDS),
        "candidate_count": len(candidates),
        "maximum_candidate_count": MAXIMUM_CANDIDATE_COUNT,
        "maximum_physical_candidate_count": MAXIMUM_PHYSICAL_CANDIDATE_COUNT,
        "fixed_candidate_order": [item["candidate_id"] for item in candidates],
        "candidate_manifest_sha256": canonical_hash_json(candidates),
        "candidates": candidates,
        "cpu_screen": {
            "asset_contact_point_count_required_minimum": 4,
            "rotation_candidate_count_per_contact": 10,
            "finite_pose7_required": True,
            "official_candidate_construction_required": True,
        },
        "planner_screen_rule": (
            "evaluate all 12 in frozen rank order; select the first at most four "
            "with successful pregrasp and grasp endpoint planning"
        ),
        "physical_selection_rule": "lowest-ranked candidate passing every frozen physical Gate",
        "three_scene_confirmation_rule": "same selected contract must pass three fresh scenes exactly",
        "qualification_sequence": [
            "fresh_scene",
            "approach",
            "grasp",
            "close",
            "lift",
            "move_central",
            "settle",
            "one_complete_V",
            "return_central",
            "settle",
        ],
        "required_physical_gates": list(REQUIRED_PHYSICAL_GATES),
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
        "training_authorized": False,
    }
    value["qualification_contract_sha256"] = canonical_hash_json(value)
    return value


def validate_f3_grasp_qualification_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    normalized = canonical_jsonable(value)
    expected = build_f3_grasp_qualification_v1()
    if normalized != expected:
        raise ValueError("F3 grasp qualification V1 contract changed")
    return expected


def select_f3_physical_candidates_v1(
    planner_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    qualification = build_f3_grasp_qualification_v1()
    by_id = {str(item.get("candidate_id")): canonical_jsonable(item) for item in planner_receipts}
    expected_ids = qualification["fixed_candidate_order"]
    if set(by_id) != set(expected_ids) or len(by_id) != len(expected_ids):
        raise ValueError("F3 planner screen must report all 12 candidates exactly once")
    ordered = [by_id[candidate_id] for candidate_id in expected_ids]
    for candidate, receipt in zip(qualification["candidates"], ordered):
        if (
            receipt.get("candidate_sha256") != candidate["candidate_sha256"]
            or receipt.get("candidate_id") != candidate["candidate_id"]
            or not isinstance(receipt.get("planner_success"), bool)
        ):
            raise ValueError("F3 planner screen receipt is not candidate-bound")
    selected = [
        receipt["candidate_id"]
        for receipt in ordered
        if receipt["planner_success"] is True
    ][:MAXIMUM_PHYSICAL_CANDIDATE_COUNT]
    result = {
        "schema_version": "cmf_f3_grasp_planner_screen_terminal_v1",
        "qualification_contract_sha256": qualification[
            "qualification_contract_sha256"
        ],
        "planner_receipts": ordered,
        "physical_candidate_ids": selected,
        "maximum_physical_candidate_count": MAXIMUM_PHYSICAL_CANDIDATE_COUNT,
        "planner_screen_exhausted": len(selected) == 0,
    }
    result["receipt_sha256"] = canonical_hash_json(result)
    return result


def physical_receipt_pass_v1(receipt: Mapping[str, Any]) -> bool:
    gates = receipt.get("gates")
    return (
        isinstance(gates, Mapping)
        and set(gates) == set(REQUIRED_PHYSICAL_GATES)
        and all(gates[name] is True for name in REQUIRED_PHYSICAL_GATES)
        and receipt.get("qualification_sequence_complete") is True
        and receipt.get("cleanup_safety_pass") is True
        and int(receipt.get("orphan_process_count", -1)) == 0
    )


def select_stable_f3_grasp_v1(
    planner_terminal: Mapping[str, Any],
    physical_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    qualification = build_f3_grasp_qualification_v1()
    selected_for_physical = list(planner_terminal.get("physical_candidate_ids", []))
    by_id = {str(item.get("candidate_id")): canonical_jsonable(item) for item in physical_receipts}
    if set(by_id) != set(selected_for_physical) or len(by_id) != len(selected_for_physical):
        raise ValueError("F3 physical receipts must cover the selected bounded set")
    candidates = {item["candidate_id"]: item for item in qualification["candidates"]}
    ordered = [by_id[candidate_id] for candidate_id in selected_for_physical]
    for receipt in ordered:
        candidate = candidates[receipt["candidate_id"]]
        if receipt.get("candidate_sha256") != candidate["candidate_sha256"]:
            raise ValueError("F3 physical receipt candidate hash mismatch")
    passing = [item["candidate_id"] for item in ordered if physical_receipt_pass_v1(item)]
    stable_id = passing[0] if passing else None
    stable = candidates.get(stable_id)
    status = (
        "PHYSICAL_CANDIDATE_PASS_REQUIRES_THREE_SCENE_CONFIRMATION"
        if stable is not None
        else "BOUNDED_GRASP_SEARCH_EXHAUSTED_REQUIRES_ASSET_REDESIGN"
    )
    result = {
        "schema_version": "cmf_f3_grasp_physical_selection_terminal_v1",
        "qualification_contract_sha256": qualification[
            "qualification_contract_sha256"
        ],
        "physical_receipts": ordered,
        "stable_candidate": stable,
        "selection_rule": qualification["physical_selection_rule"],
        "status": status,
    }
    result["receipt_sha256"] = canonical_hash_json(result)
    return result


def build_f3_selected_grasp_contract_v1(candidate: Mapping[str, Any]) -> dict[str, Any]:
    qualification = build_f3_grasp_qualification_v1()
    matches = [
        item
        for item in qualification["candidates"]
        if item["candidate_id"] == candidate.get("candidate_id")
        and item["candidate_sha256"] == candidate.get("candidate_sha256")
    ]
    if len(matches) != 1:
        raise ValueError("F3 selected grasp is outside the frozen candidate set")
    value = {
        "schema_version": "cmf_f3_selected_stable_grasp_contract_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "qualification_contract_sha256": qualification[
            "qualification_contract_sha256"
        ],
        "candidate": matches[0],
        "program_ids": list(PROGRAM_IDS),
        "same_contract_all_programs": True,
        "vh_axes_changed": False,
        "programs_changed": False,
        "verifier_thresholds_changed": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["contract_sha256"] = canonical_hash_json(value)
    return value


def build_f3_grasp_candidate_spec_v1(
    candidate_id: str, *, purpose: str
) -> dict[str, Any]:
    if purpose not in {"planner_screen", "physical", "three_scene_confirmation", "full_root"}:
        raise ValueError("unsupported F3 grasp qualification purpose")
    qualification = build_f3_grasp_qualification_v1()
    matches = [
        item for item in qualification["candidates"] if item["candidate_id"] == candidate_id
    ]
    if len(matches) != 1:
        raise ValueError("F3 grasp candidate spec is outside frozen set")
    candidate = matches[0]
    value = {
        "schema_version": "cmf_f3_grasp_candidate_planned_spec_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "slot_id": f"f3-grasp-qv1-{purpose}-{candidate['rank']:02d}",
        "family": "F3",
        "arm": "left",
        "seed": 2026090200 + int(candidate["rank"]),
        "generator": "controlled_multi_future_f3_grasp_qualification_v1_adapter",
        "origin": "development_pipeline_consolidation_and_template_convergence_v1",
        "purpose": purpose,
        "f3_grasp_qualification_v1": qualification,
        "f3_grasp_qualification_contract_sha256": qualification[
            "qualification_contract_sha256"
        ],
        "selected_grasp_candidate": candidate,
        "selected_grasp_contract": build_f3_selected_grasp_contract_v1(candidate),
        "canonical_program_ids": list(PROGRAM_IDS),
        "prefix_only": purpose != "full_root",
        "suffix_allowed": purpose == "full_root",
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["planned_scope_spec_sha256"] = canonical_hash_json(value)
    return value


def validate_f3_grasp_candidate_spec_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    normalized = canonical_jsonable(value)
    candidate = normalized.get("selected_grasp_candidate")
    purpose = normalized.get("purpose")
    if not isinstance(candidate, Mapping) or not isinstance(purpose, str):
        raise ValueError("F3 grasp candidate planned spec is incomplete")
    expected = build_f3_grasp_candidate_spec_v1(
        str(candidate.get("candidate_id")), purpose=purpose
    )
    if normalized != expected:
        raise ValueError("F3 grasp candidate planned spec changed")
    return expected


__all__ = [
    "ASSET",
    "CLOSE_NORMALIZED_TARGET",
    "IMPLEMENTATION_VERSION",
    "MAXIMUM_CANDIDATE_COUNT",
    "MAXIMUM_PHYSICAL_CANDIDATE_COUNT",
    "PROGRAM_IDS",
    "REQUIRED_PHYSICAL_GATES",
    "SCOPE",
    "build_f3_grasp_qualification_v1",
    "build_f3_grasp_candidate_spec_v1",
    "build_f3_selected_grasp_contract_v1",
    "physical_receipt_pass_v1",
    "preregistered_f3_grasp_candidates_v1",
    "select_f3_physical_candidates_v1",
    "select_stable_f3_grasp_v1",
    "validate_f3_grasp_qualification_v1",
    "validate_f3_grasp_candidate_spec_v1",
]
