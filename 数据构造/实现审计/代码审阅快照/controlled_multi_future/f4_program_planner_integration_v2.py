"""Program-bound F4 planner-only interface for the eight hv2 candidates.

Each candidate must be checked in three independent fresh/reconstructed scenes,
one for each frozen order.  This module is intentionally not registered with an
issuer and does not authorize planner, GPU, physical, or Stage-1 execution.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .family_runners_v3_1 import _plan_chain
from .high_level_planner_runner_v1 import build_f4_stage_b_targets_v1


PURPOSE = "f4_program_v2_planner"
PROGRAMS = {
    "F4-ABC": ("A", "B", "C"),
    "F4-ACB": ("A", "C", "B"),
    "F4-BAC": ("B", "A", "C"),
}
SEGMENTS_PER_ROLE = 10
PLANNER_COLLISION_SCOPE = {
    "configured_world_objects": ["table"],
    "scene_dynamic_objects_in_curobo_world": False,
    "attached_carried_object_modeled": False,
    "cpu_object_sweep_audit": True,
    "robot_link_vs_scene_object_collision_proven": False,
}


def _self_hashed(value: Mapping[str, Any], key: str) -> dict[str, Any]:
    normalized = canonical_jsonable(value)
    payload = dict(normalized)
    digest = payload.pop(key, None)
    if digest != canonical_hash_json(payload):
        raise ValueError(f"F4 V2 {key} mismatch")
    return normalized


def build_f4_program_planner_spec_v2(
    source_candidate: Mapping[str, Any],
    slot_candidate: Mapping[str, Any],
    *,
    program_id: str,
    slot_id: str,
) -> dict[str, Any]:
    source = _self_hashed(source_candidate, "candidate_sha256")
    candidate = _self_hashed(slot_candidate, "candidate_sha256")
    if program_id not in PROGRAMS:
        raise ValueError("F4 V2 program must be ABC, ACB, or BAC")
    if candidate.get("construction_valid") is not True:
        raise ValueError("F4 V2 planner spec requires a geometry-valid candidate")
    if candidate.get("source_grasp_candidate_sha256") != source[
        "candidate_sha256"
    ]:
        raise ValueError("F4 V2 source/slot candidates are not bound")
    value = {
        "schema_version": "cmf_f4_program_planner_spec_v2",
        "purpose": PURPOSE,
        "slot_id": str(slot_id),
        "family": "F4",
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": candidate["candidate_sha256"],
        "source_candidate_sha256": source["candidate_sha256"],
        "program_id": program_id,
        "program_order": list(PROGRAMS[program_id]),
        "f4_source_grasp_candidate_v1": source,
        "f4_stage_b_candidate_v1": candidate,
        "fresh_or_reconstructed_scene_required": True,
        "actual_source_layout_gate_required": True,
        "actual_source_geometry_v2_rerun_required": True,
        "planner_collision_scope": PLANNER_COLLISION_SCOPE,
        "planner_query_limit": SEGMENTS_PER_ROLE * 3,
        "planner_execution_authorized": False,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["spec_sha256"] = canonical_hash_json(value)
    return value


def run_f4_program_planner_v2(
    scene,
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    checked = _self_hashed(spec, "spec_sha256")
    program_id = checked.get("program_id")
    if (
        checked.get("purpose") != PURPOSE
        or PROGRAMS.get(program_id) != tuple(checked.get("program_order", ()))
        or checked.get("planner_execution_authorized") is not False
        or checked.get("planner_collision_scope") != PLANNER_COLLISION_SCOPE
    ):
        raise ValueError("F4 V2 planner spec purpose/order is invalid or activated")
    lifecycle = getattr(scene, "_cmf_scene_lifecycle", None)
    if lifecycle not in ("fresh", "reconstructed"):
        raise ValueError("F4 V2 program planner requires a fresh/reconstructed scene")
    targets, audit = build_f4_stage_b_targets_v1(scene, checked)
    expected_roles = list(PROGRAMS[program_id])
    if (
        audit.get("program_id") != program_id
        or audit.get("program_order") != expected_roles
        or audit.get("actual_source_layout_gate_v2", {}).get("pass") is not True
        or audit.get("actual_source_construction_geometry_v2", {}).get(
            "construction_valid"
        )
        is not True
    ):
        raise ValueError("F4 V2 target builder did not prove program/source binding")
    planned = _plan_chain(
        scene,
        targets,
        query_limit=int(checked["planner_query_limit"]),
        arm=checked["f4_source_grasp_candidate_v1"]["arm"],
    )
    if not isinstance(planned, Mapping):
        raise TypeError("F4 V2 planner callback must return a mapping")
    receipts = deepcopy(planned.get("segment_receipts", []))
    observed_roles = []
    for item in receipts:
        role = str(item.get("segment_id", "")).split("_", 1)[0]
        if not observed_roles or observed_roles[-1] != role:
            observed_roles.append(role)
    passed = (
        planned.get("pass") is True
        and len(receipts) == SEGMENTS_PER_ROLE * 3
        and all(item.get("planner_status") == "Success" for item in receipts)
        and observed_roles == expected_roles
    )
    value = {
        "schema_version": "cmf_f4_program_planner_terminal_v2",
        "purpose": PURPOSE,
        "slot_id": checked["slot_id"],
        "spec_sha256": checked["spec_sha256"],
        "candidate_id": checked["candidate_id"],
        "candidate_sha256": checked["candidate_sha256"],
        "program_id": program_id,
        "program_order": expected_roles,
        "scene_instance_id": getattr(scene, "_cmf_scene_instance_id", None),
        "scene_lifecycle": lifecycle,
        "target_construction": canonical_jsonable(audit),
        "targets_sha256": canonical_hash_json(targets),
        "planner_result": {
            "pass": planned.get("pass") is True,
            "segment_receipts": receipts,
            "planner_query_count": int(planned.get("planner_query_count", 0)),
            "terminal_qpos": deepcopy(planned.get("terminal_qpos")),
            "terminal_qpos_sha256": planned.get("terminal_qpos_sha256"),
            "controls_retained_in_receipt": False,
        },
        "planner_collision_scope": deepcopy(PLANNER_COLLISION_SCOPE),
        "result_semantics": {
            "robot_kinematic_table_world_planner_pass": passed,
        },
        "robot_kinematic_table_world_planner_pass": passed,
        "planner_qualified_for_physical_probe": False,
        "candidate_ready": False,
        "stage1_ready": False,
        "all_three_programs_required": True,
        "physical_execution_count": 0,
        "planner_execution_authorized_by_this_receipt": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def finalize_f4_candidate_program_qualification_v2(
    slot_candidate: Mapping[str, Any],
    program_terminals: list[Mapping[str, Any]],
) -> dict[str, Any]:
    candidate = _self_hashed(slot_candidate, "candidate_sha256")
    terminals = [
        _self_hashed(item, "receipt_sha256") for item in program_terminals
    ]
    program_ids = [item.get("program_id") for item in terminals]
    scene_ids = [item.get("scene_instance_id") for item in terminals]
    checks = {
        "exact_program_order": program_ids == list(PROGRAMS),
        "all_bind_same_candidate": all(
            item.get("candidate_sha256") == candidate["candidate_sha256"]
            for item in terminals
        ),
        "all_programs_table_world_planner_pass": all(
            item.get("robot_kinematic_table_world_planner_pass") is True
            for item in terminals
        ),
        "collision_scope_exact": all(
            item.get("planner_collision_scope") == PLANNER_COLLISION_SCOPE
            for item in terminals
        ),
        "three_independent_scene_ids": len(scene_ids) == 3
        and None not in scene_ids
        and len(set(scene_ids)) == 3,
        "all_scenes_fresh_or_reconstructed": all(
            item.get("scene_lifecycle") in ("fresh", "reconstructed")
            for item in terminals
        ),
        "no_physical_execution": all(
            item.get("physical_execution_count") == 0 for item in terminals
        ),
    }
    value = {
        "schema_version": "cmf_f4_candidate_program_qualification_v2",
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": candidate["candidate_sha256"],
        "program_terminal_receipt_sha256s": [
            item["receipt_sha256"] for item in terminals
        ],
        "checks": checks,
        "planner_qualified_for_physical_probe": all(checks.values()),
        "candidate_ready": False,
        "stage1_ready": False,
        "abc_only_never_sufficient": True,
        "planner_execution_authorized": False,
        "physical_execution_authorized": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


__all__ = [
    "PROGRAMS",
    "PURPOSE",
    "build_f4_program_planner_spec_v2",
    "finalize_f4_candidate_program_qualification_v2",
    "run_f4_program_planner_v2",
]
