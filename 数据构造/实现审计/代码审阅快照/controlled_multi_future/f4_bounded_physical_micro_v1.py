"""Bounded F4 physical noninterference stages for one development root."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import numpy as np

from .anchor import quaternion_angular_error
from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f4_program_planner_integration_v2 import (
    PROGRAMS,
    build_f4_program_planner_spec_v2,
)
from .family_runners_v3_1 import (
    _arm_eef_pose,
    _arm_gripper_open,
    _arm_tag,
    _must_action,
    _plan_chain,
    _planner_reset,
    _pose,
    _wait_and_record,
)
from .family_runners_v3_3 import get_family_controller_v3_3
from .high_level_physical_runner_v1 import _execute_planned_segment
from .high_level_planner_runner_v1 import build_f4_stage_b_targets_v1
from .high_level_runtime_specs_v1 import build_f4_runtime_spec_v1
from .planner_qualification_scene_bridges_v2_3_1 import (
    _f4_synthetic_stage_a_terminal,
)
from .runtime_v2_contracts import PROVISIONAL_RUNTIME_THRESHOLDS


STAGES = {
    "A_ONLY": {"program_id": "F4-ABC", "roles": ("A",)},
    "B_ONLY": {"program_id": "F4-BAC", "roles": ("B",)},
    "C_ONLY": {"program_id": "F4-ACB", "roles": ("C",)},
    "AB_NONINTERFERENCE": {"program_id": "F4-ABC", "roles": ("A", "B")},
    "AC_NONINTERFERENCE": {"program_id": "F4-ACB", "roles": ("A", "C")},
}
TARGET_CONSTRUCTION_QUERY_LIMIT = 12
SEGMENTS_PER_ROLE = 10


def _self_hashed(value: Mapping[str, Any], key: str, label: str) -> dict[str, Any]:
    result = canonical_jsonable(value)
    payload = dict(result)
    digest = payload.pop(key, None)
    if digest != canonical_hash_json(payload):
        raise ValueError(f"F4 physical micro {label} hash mismatch")
    return result


def build_f4_bounded_physical_micro_spec_v1(
    source_candidate: Mapping[str, Any],
    slot_candidate: Mapping[str, Any],
    planner_terminal: Mapping[str, Any],
    *,
    stage: str,
    slot_id: str,
    planner_reset_nonce: int,
) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError("F4 physical micro stage is outside the frozen sequence")
    contract = STAGES[stage]
    planner_spec = build_f4_program_planner_spec_v2(
        source_candidate,
        slot_candidate,
        program_id=contract["program_id"],
        slot_id=f"{slot_id}-planner-source",
        planner_reset_nonce=planner_reset_nonce,
    )
    terminal = _self_hashed(planner_terminal, "receipt_sha256", "planner terminal")
    if (
        terminal.get("spec_sha256") != planner_spec["spec_sha256"]
        or terminal.get("candidate_sha256") != planner_spec["candidate_sha256"]
        or terminal.get("program_id") != contract["program_id"]
        or terminal.get("robot_kinematic_table_world_planner_pass") is not True
        or terminal.get("physical_execution_count") != 0
    ):
        raise ValueError("F4 physical micro requires its exact passing planner terminal")
    query_limit = TARGET_CONSTRUCTION_QUERY_LIMIT + SEGMENTS_PER_ROLE * len(
        contract["roles"]
    )
    legacy_scene_spec = build_f4_runtime_spec_v1(
        slot_candidate["candidate_id"],
        purpose="f4_stage_b_planner",
        stage_a_terminal=_f4_synthetic_stage_a_terminal(),
    )
    value = {
        "schema_version": "cmf_f4_bounded_physical_micro_spec_v1",
        "purpose": "f4_bounded_physical_noninterference_v1",
        "family": "F4",
        "slot_id": str(slot_id),
        "stage": stage,
        "program_id": contract["program_id"],
        "program_order": list(PROGRAMS[contract["program_id"]]),
        "role_sequence": list(contract["roles"]),
        "f4_source_grasp_candidate_v1": deepcopy(source_candidate),
        "f4_stage_b_candidate_v1": deepcopy(slot_candidate),
        "candidate_sha256": planner_spec["candidate_sha256"],
        "source_planner_spec": planner_spec,
        "source_planner_spec_sha256": planner_spec["spec_sha256"],
        "source_planner_terminal_receipt_sha256": terminal["receipt_sha256"],
        "legacy_scene_spec": legacy_scene_spec,
        "legacy_scene_spec_sha256": legacy_scene_spec[
            "planned_scope_spec_sha256"
        ],
        "planner_reset_nonce": int(planner_reset_nonce),
        "target_construction_query_limit": TARGET_CONSTRUCTION_QUERY_LIMIT,
        "segments_per_role": SEGMENTS_PER_ROLE,
        "planner_query_limit": query_limit,
        "common_x_prefix_required": True,
        "slot_state_required_for_completed_roles": True,
        "non_target_preservation_required": True,
        "physical_execution_count_limit": 1,
        "automatic_next_stage": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
        "formal_data": False,
    }
    value["spec_sha256"] = canonical_hash_json(value)
    return value


def validate_f4_bounded_physical_micro_spec_v1(
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    value = _self_hashed(spec, "spec_sha256", "spec")
    stage = value.get("stage")
    contract = STAGES.get(stage)
    if (
        contract is None
        or value.get("program_id") != contract["program_id"]
        or value.get("role_sequence") != list(contract["roles"])
        or value.get("planner_query_limit")
        != TARGET_CONSTRUCTION_QUERY_LIMIT
        + SEGMENTS_PER_ROLE * len(contract["roles"])
        or value.get("automatic_next_stage") is not False
        or value.get("physical_execution_authorized") is not False
        or value.get("stage1_authorized") is not False
        or value.get("formal_data") is not False
    ):
        raise ValueError("F4 bounded physical micro semantics changed")
    return value


def execute_f4_bounded_physical_micro_v1(
    scene,
    spec: Mapping[str, Any],
    *,
    capture_anchor_callback,
) -> dict[str, Any]:
    value = validate_f4_bounded_physical_micro_spec_v1(spec)
    if not callable(capture_anchor_callback):
        raise TypeError("F4 physical micro requires adapter-bound anchor capture")
    controller = get_family_controller_v3_3("F4")
    controller.initialize_prefix_replay_trace(scene)
    prefix = controller.plan_and_execute_canonical_prefix(
        scene,
        controller.canonical_prefix_contract([]),
        capture_anchor=capture_anchor_callback,
    )
    prefix_pass = prefix.get("prefix_physical_acceptance", {}).get("pass") is True
    if not prefix_pass:
        return {
            "prefix": prefix,
            "stage": value["stage"],
            "sequence_complete": False,
            "earliest_failure": "COMMON_X_PREFIX_PHYSICAL_GATE_FAILED",
        }
    common_after_prefix = _pose(scene.common_x).copy()
    initial = {
        role: _pose(getattr(scene, role.lower())).copy() for role in ("A", "B", "C")
    }
    first_actor = getattr(scene, value["role_sequence"][0].lower())
    scene.initialize_trace(first_actor, value["f4_source_grasp_candidate_v1"]["arm"], role_actors=scene.role_actors)
    scene.planner_query_limit = int(value["planner_query_limit"])
    targets, target_audit = build_f4_stage_b_targets_v1(
        scene, value["source_planner_spec"]
    )
    chunks = {
        role: targets[index * SEGMENTS_PER_ROLE : (index + 1) * SEGMENTS_PER_ROLE]
        for index, role in enumerate(value["program_order"])
    }
    selected_targets = [
        target for role in value["role_sequence"] for target in chunks[role]
    ]
    arm = value["f4_source_grasp_candidate_v1"]["arm"]
    reset = _planner_reset(
        scene,
        planner_seed=value["planner_reset_nonce"],
        variant_id=f"f4_physical_micro:{value['stage']}:{value['candidate_sha256']}",
        arm=arm,
    )
    planned = _plan_chain(
        scene,
        selected_targets,
        query_limit=value["planner_query_limit"],
        arm=arm,
    )
    if planned.get("pass") is not True:
        return {
            "prefix": prefix,
            "stage": value["stage"],
            "target_construction": target_audit,
            "planner_reset_receipt": reset,
            "planner_result": planned,
            "sequence_complete": False,
            "earliest_failure": "ROLE_CHAIN_PLANNER_FAILED",
        }
    controls = planned["controls"]
    executions = []
    role_receipts = []
    for role_index, role in enumerate(value["role_sequence"]):
        offset = role_index * SEGMENTS_PER_ROLE
        for local_index in (0, 1, 2):
            executions.append(
                _execute_planned_segment(
                    scene, controls, selected_targets, offset + local_index, arm
                )
            )
        _must_action(
            scene,
            scene.close_gripper(_arm_tag(arm), pos=0.0),
            f"f4_micro_{role}_close",
        )
        for local_index in (3, 4, 5, 6, 7):
            executions.append(
                _execute_planned_segment(
                    scene, controls, selected_targets, offset + local_index, arm
                )
            )
        _must_action(
            scene,
            scene.open_gripper(_arm_tag(arm), pos=1.0),
            f"f4_micro_{role}_open",
        )
        for local_index in (8, 9):
            executions.append(
                _execute_planned_segment(
                    scene, controls, selected_targets, offset + local_index, arm
                )
            )
        _wait_and_record(scene, 75)
        slot = controller._slot_state_receipt(
            scene,
            role=role,
            actor=getattr(scene, role.lower()),
            slot=getattr(scene, f"slot_{role.lower()}"),
        )
        role_receipts.append({"role": role, "slot_state": slot})
    completed = set(value["role_sequence"])
    slot_checks = {
        item["role"]: item["slot_state"]["pass"] is True for item in role_receipts
    }
    non_target_displacements = {
        role: float(
            np.linalg.norm(_pose(getattr(scene, role.lower()))[:3] - initial[role][:3])
        )
        for role in ("A", "B", "C")
        if role not in completed
    }
    common_displacement = float(
        np.linalg.norm(_pose(scene.common_x)[:3] - common_after_prefix[:3])
    )
    neutral = np.asarray(selected_targets[-1]["pose"], dtype=np.float64)
    realized = _arm_eef_pose(scene, arm)
    checks = {
        "common_x_prefix_physical_acceptance": prefix_pass,
        "planner_chain": planned.get("pass") is True,
        "all_completed_role_slots": all(slot_checks.values()),
        "common_x_preserved": common_displacement
        <= PROVISIONAL_RUNTIME_THRESHOLDS["non_target_displacement_m"],
        "uncompleted_roles_preserved": all(
            displacement
            <= PROVISIONAL_RUNTIME_THRESHOLDS["non_target_displacement_m"]
            for displacement in non_target_displacements.values()
        ),
        "selected_gripper_open": _arm_gripper_open(scene, arm),
        "selected_arm_neutral_position": float(
            np.linalg.norm(realized[:3] - neutral[:3])
        )
        <= PROVISIONAL_RUNTIME_THRESHOLDS["neutral_position_error_m"],
        "selected_arm_neutral_orientation": quaternion_angular_error(
            realized[3:], neutral[3:]
        )
        <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
    }
    return {
        "prefix": prefix,
        "stage": value["stage"],
        "target_construction": target_audit,
        "planner_reset_receipt": reset,
        "planner_result": planned,
        "execution_receipts": executions,
        "role_receipts": role_receipts,
        "verifier": {
            "checks": checks,
            "slot_checks": slot_checks,
            "common_x_displacement_m": common_displacement,
            "non_target_displacements_m": non_target_displacements,
            "pass": all(checks.values()),
        },
        "sequence_complete": all(checks.values()),
        "earliest_failure": None
        if all(checks.values())
        else "STAGED_PHYSICAL_NONINTERFERENCE_GATE_FAILED",
    }


def run_f4_bounded_physical_micro_v1(
    scene,
    spec: Mapping[str, Any],
    *,
    capture_anchor_callback,
) -> dict[str, Any]:
    value = validate_f4_bounded_physical_micro_spec_v1(spec)
    result = execute_f4_bounded_physical_micro_v1(
        scene, value, capture_anchor_callback=capture_anchor_callback
    )
    passed = result.get("sequence_complete") is True
    terminal = {
        "schema_version": "cmf_f4_bounded_physical_micro_terminal_v1",
        "purpose": value["purpose"],
        "slot_id": value["slot_id"],
        "stage": value["stage"],
        "spec_sha256": value["spec_sha256"],
        "candidate_sha256": value["candidate_sha256"],
        "physical_result": canonical_jsonable(result),
        "planner_query_count": int(getattr(scene, "planner_query_count", 0)),
        "physical_execution_count": 1,
        "stage_physically_qualified": passed,
        "automatic_next_stage": False,
        "candidate_ready": False,
        "stage1_ready": False,
        "formal_data": False,
    }
    terminal["receipt_sha256"] = canonical_hash_json(terminal)
    return terminal


__all__ = [
    "STAGES",
    "build_f4_bounded_physical_micro_spec_v1",
    "execute_f4_bounded_physical_micro_v1",
    "run_f4_bounded_physical_micro_v1",
    "validate_f4_bounded_physical_micro_spec_v1",
]
