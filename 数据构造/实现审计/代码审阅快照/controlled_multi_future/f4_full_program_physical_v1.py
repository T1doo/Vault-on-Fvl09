"""F4 same-layout real ABC/ACB/BAC full-program physical qualification."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import numpy as np

from .anchor import quaternion_angular_error
from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f4_bounded_physical_micro_v1 import (
    SEGMENTS_PER_ROLE,
    TARGET_CONSTRUCTION_QUERY_LIMIT,
)
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


PROGRAM_IDS = ("F4-ABC", "F4-ACB", "F4-BAC")
PLANNER_QUERY_LIMIT = TARGET_CONSTRUCTION_QUERY_LIMIT + 3 * SEGMENTS_PER_ROLE


def _self_hashed(value: Mapping[str, Any], key: str, label: str) -> dict[str, Any]:
    result = canonical_jsonable(value)
    payload = dict(result)
    digest = payload.pop(key, None)
    if digest != canonical_hash_json(payload):
        raise ValueError(f"F4 full-program {label} hash mismatch")
    return result


def build_f4_full_program_physical_spec_v1(
    source_candidate: Mapping[str, Any],
    slot_candidate: Mapping[str, Any],
    planner_terminal: Mapping[str, Any],
    *,
    program_id: str,
    slot_id: str,
    planner_reset_nonce: int,
    isolation_gate_receipt_sha256: str,
) -> dict[str, Any]:
    if program_id not in PROGRAM_IDS:
        raise ValueError("F4 full-program id is outside ABC/ACB/BAC")
    if (
        not isinstance(isolation_gate_receipt_sha256, str)
        or len(isolation_gate_receipt_sha256) != 64
    ):
        raise ValueError("F4 full-program requires the isolation Gate receipt SHA")
    planner_spec = build_f4_program_planner_spec_v2(
        source_candidate,
        slot_candidate,
        program_id=program_id,
        slot_id=slot_id,
        planner_reset_nonce=planner_reset_nonce,
    )
    terminal = _self_hashed(planner_terminal, "receipt_sha256", "planner terminal")
    if (
        terminal.get("spec_sha256") != planner_spec["spec_sha256"]
        or terminal.get("candidate_sha256") != planner_spec["candidate_sha256"]
        or terminal.get("program_id") != program_id
        or terminal.get("robot_kinematic_table_world_planner_pass") is not True
        or terminal.get("physical_execution_count") != 0
    ):
        raise ValueError("F4 full-program requires its exact passing planner terminal")
    legacy_scene_spec = build_f4_runtime_spec_v1(
        slot_candidate["candidate_id"],
        purpose="f4_stage_b_planner",
        stage_a_terminal=_f4_synthetic_stage_a_terminal(),
    )
    value = {
        "schema_version": "cmf_f4_full_program_physical_spec_v1",
        "purpose": "f4_same_layout_real_full_program_qualification_v1",
        "family": "F4",
        "slot_id": str(slot_id),
        "program_id": program_id,
        "program_order": list(PROGRAMS[program_id]),
        "role_sequence": list(PROGRAMS[program_id]),
        "f4_source_grasp_candidate_v1": deepcopy(source_candidate),
        "f4_stage_b_candidate_v1": deepcopy(slot_candidate),
        "candidate_sha256": planner_spec["candidate_sha256"],
        "source_planner_spec": planner_spec,
        "source_planner_spec_sha256": planner_spec["spec_sha256"],
        "source_planner_terminal_receipt_sha256": terminal["receipt_sha256"],
        "isolation_gate_receipt_sha256": isolation_gate_receipt_sha256,
        "legacy_scene_spec": legacy_scene_spec,
        "legacy_scene_spec_sha256": legacy_scene_spec["planned_scope_spec_sha256"],
        "planner_reset_nonce": int(planner_reset_nonce),
        "target_construction_query_limit": TARGET_CONSTRUCTION_QUERY_LIMIT,
        "segments_per_role": SEGMENTS_PER_ROLE,
        "planner_query_limit": PLANNER_QUERY_LIMIT,
        "common_x_prefix_required": True,
        "all_three_slot_states_required": True,
        "final_state_equivalence_required_across_programs": True,
        "physical_execution_count_limit": 1,
        "automatic_next_program": False,
        "accepted_trajectory_count": 0,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
        "formal_data": False,
    }
    value["spec_sha256"] = canonical_hash_json(value)
    return value


def validate_f4_full_program_physical_spec_v1(
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    value = _self_hashed(spec, "spec_sha256", "spec")
    program_id = value.get("program_id")
    if (
        program_id not in PROGRAM_IDS
        or value.get("program_order") != list(PROGRAMS[program_id])
        or value.get("role_sequence") != list(PROGRAMS[program_id])
        or value.get("planner_query_limit") != PLANNER_QUERY_LIMIT
        or value.get("all_three_slot_states_required") is not True
        or value.get("final_state_equivalence_required_across_programs") is not True
        or value.get("automatic_next_program") is not False
        or value.get("accepted_trajectory_count") != 0
        or value.get("physical_execution_authorized") is not False
        or value.get("stage1_authorized") is not False
        or value.get("formal_data") is not False
    ):
        raise ValueError("F4 full-program physical semantics changed")
    return value


def execute_f4_full_program_physical_v1(
    scene,
    spec: Mapping[str, Any],
    *,
    capture_anchor_callback,
) -> dict[str, Any]:
    value = validate_f4_full_program_physical_spec_v1(spec)
    if not callable(capture_anchor_callback):
        raise TypeError("F4 full-program requires adapter-bound anchor capture")
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
            "program_id": value["program_id"],
            "prefix": prefix,
            "program_sequence_complete": False,
            "earliest_failure": "COMMON_X_PREFIX_PHYSICAL_GATE_FAILED",
        }

    common_after_prefix = _pose(scene.common_x).copy()
    first_role = value["role_sequence"][0]
    scene.initialize_trace(
        getattr(scene, first_role.lower()),
        value["f4_source_grasp_candidate_v1"]["arm"],
        role_actors=scene.role_actors,
    )
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
        variant_id=(
            f"f4_full_program:{value['program_id']}:{value['candidate_sha256']}"
        ),
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
            "program_id": value["program_id"],
            "prefix": prefix,
            "target_construction": target_audit,
            "planner_reset_receipt": reset,
            "planner_result": planned,
            "program_sequence_complete": False,
            "earliest_failure": "FULL_PROGRAM_PLANNER_FAILED",
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
            f"f4_full_{role}_close",
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
            f"f4_full_{role}_open",
        )
        for local_index in (8, 9):
            executions.append(
                _execute_planned_segment(
                    scene, controls, selected_targets, offset + local_index, arm
                )
            )
        _wait_and_record(scene, 75)
        role_receipts.append(
            {
                "role": role,
                "slot_state": controller._slot_state_receipt(
                    scene,
                    role=role,
                    actor=getattr(scene, role.lower()),
                    slot=getattr(scene, f"slot_{role.lower()}"),
                ),
            }
        )

    slot_checks = {
        item["role"]: item["slot_state"]["pass"] is True for item in role_receipts
    }
    common_displacement = float(
        np.linalg.norm(_pose(scene.common_x)[:3] - common_after_prefix[:3])
    )
    neutral = np.asarray(selected_targets[-1]["pose"], dtype=np.float64)
    realized = _arm_eef_pose(scene, arm)
    checks = {
        "common_x_prefix_physical_acceptance": prefix_pass,
        "planner_chain": planned.get("pass") is True,
        "realized_role_order_exact": [
            item["role"] for item in role_receipts
        ]
        == value["role_sequence"],
        "all_three_role_slots": set(slot_checks) == {"A", "B", "C"}
        and all(slot_checks.values()),
        "common_x_preserved": common_displacement
        <= PROVISIONAL_RUNTIME_THRESHOLDS["non_target_displacement_m"],
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
    final_state = {
        "common_x_pose": _pose(scene.common_x).tolist(),
        "A_pose": _pose(scene.a).tolist(),
        "B_pose": _pose(scene.b).tolist(),
        "C_pose": _pose(scene.c).tolist(),
        "executing_eef_pose": realized.tolist(),
        "executing_gripper_open": _arm_gripper_open(scene, arm),
        "execution_arm": arm,
    }
    passed = all(checks.values())
    return {
        "program_id": value["program_id"],
        "prefix": prefix,
        "target_construction": target_audit,
        "planner_reset_receipt": reset,
        "planner_result": planned,
        "execution_receipts": executions,
        "role_receipts": role_receipts,
        "final_state_equivalence_payload": final_state,
        "verifier": {
            "checks": checks,
            "slot_checks": slot_checks,
            "common_x_displacement_m": common_displacement,
            "pass": passed,
        },
        "program_sequence_complete": passed,
        "earliest_failure": None if passed else "FULL_PROGRAM_PHYSICAL_GATE_FAILED",
    }


def run_f4_full_program_physical_v1(
    scene,
    spec: Mapping[str, Any],
    *,
    capture_anchor_callback,
) -> dict[str, Any]:
    value = validate_f4_full_program_physical_spec_v1(spec)
    result = execute_f4_full_program_physical_v1(
        scene, value, capture_anchor_callback=capture_anchor_callback
    )
    passed = result.get("program_sequence_complete") is True
    terminal = {
        "schema_version": "cmf_f4_full_program_physical_terminal_v1",
        "purpose": value["purpose"],
        "slot_id": value["slot_id"],
        "program_id": value["program_id"],
        "spec_sha256": value["spec_sha256"],
        "candidate_sha256": value["candidate_sha256"],
        "isolation_gate_receipt_sha256": value[
            "isolation_gate_receipt_sha256"
        ],
        "physical_result": canonical_jsonable(result),
        "planner_query_count": int(getattr(scene, "planner_query_count", 0)),
        "physical_execution_count": 1,
        "full_program_physically_qualified": passed,
        "candidate_ready": False,
        "accepted_trajectory_count": 0,
        "stage1_ready": False,
        "formal_data": False,
    }
    terminal["receipt_sha256"] = canonical_hash_json(terminal)
    return terminal


__all__ = [
    "PLANNER_QUERY_LIMIT",
    "PROGRAM_IDS",
    "build_f4_full_program_physical_spec_v1",
    "execute_f4_full_program_physical_v1",
    "run_f4_full_program_physical_v1",
    "validate_f4_full_program_physical_spec_v1",
]
