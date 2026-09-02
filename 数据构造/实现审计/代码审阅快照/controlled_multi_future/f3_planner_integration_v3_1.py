"""F3 planner Stage-A/Stage-B continuity seal for Generation Repair V2.3."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import numpy as np

from .anchor import quaternion_angular_error
from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .current_hasher import hash_array
from .f3_final_pose_search_v3 import (
    freeze_f3_final_pose_v3,
    validate_f3_final_pose_qualification_v3,
)
from .family_runners_v3_1 import (
    _arm_eef_pose,
    _arm_entity,
    _plan_chain,
    _planner_reset,
    _pose,
)
from .geometry import world_axis_offset_pose
from .official_raw_pose_generation_v1 import generate_official_raw_pose_receipt_v1


STAGE_A_PURPOSE = "f3_final_pose_v3_stage_a_planner"
STAGE_B_PURPOSE = "f3_final_pose_v3_stage_b_planner"
STAGE_A_QUERY_COUNT = 3
STAGE_B_QUERY_COUNT = 7
POSITION_ATOL_M = 0.001
ORIENTATION_ATOL_RAD = 0.005
V_DISTANCE_M = 0.055
H_DISTANCE_M = 0.050
CENTRAL_POSITION_TABLE_FRAME_M = (0.0, -0.05, 0.95)
SCENE_BINDING_FIELDS = (
    "scene_spec_sha256",
    "scene_layout_sha256",
    "bottle_asset_sha256",
    "bottle_actor_pose_sha256",
    "robot_config_sha256",
)


def _self_hashed(value: Mapping[str, Any], key: str, label: str) -> dict[str, Any]:
    result = canonical_jsonable(value)
    payload = dict(result)
    digest = payload.pop(key, None)
    if digest != canonical_hash_json(payload):
        raise ValueError(f"F3 V2.3 {label} hash mismatch")
    return result


def _recipe(value: Mapping[str, Any]) -> dict[str, Any]:
    return _self_hashed(value, "recipe_sha256", "recipe")


def _scene_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    result = canonical_jsonable(value)
    if set(result) != set(SCENE_BINDING_FIELDS):
        raise ValueError("F3 V2.3 scene binding fields changed")
    if any(not isinstance(result[key], str) or len(result[key]) != 64 for key in result):
        raise ValueError("F3 V2.3 scene binding contains invalid SHA")
    return result


def _runtime_scene_binding(scene) -> dict[str, Any]:
    return _scene_binding(getattr(scene, "_cmf_f3_scene_binding_v3_1", None))


def _planner_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "pass": result.get("pass") is True,
        "segment_receipts": deepcopy(result.get("segment_receipts", [])),
        "planner_query_count": int(result.get("planner_query_count", 0)),
        "terminal_qpos": deepcopy(result.get("terminal_qpos")),
        "terminal_qpos_sha256": result.get("terminal_qpos_sha256"),
        "controls_retained_in_receipt": False,
    }


def build_f3_stage_a_planner_spec_v3_1(
    recipe: Mapping[str, Any],
    scene_binding: Mapping[str, Any],
    *,
    slot_id: str,
    panel_sha256: str,
) -> dict[str, Any]:
    recipe_value = _recipe(recipe)
    binding = _scene_binding(scene_binding)
    if binding["bottle_asset_sha256"] != recipe_value["asset_record_sha256"]:
        raise ValueError("F3 V2.3 recipe asset differs from scene binding")
    value = {
        "schema_version": "cmf_f3_stage_a_planner_spec_v3_1",
        "purpose": STAGE_A_PURPOSE,
        "slot_id": str(slot_id),
        "family": "F3",
        "panel_sha256": str(panel_sha256),
        "recipe": recipe_value,
        "recipe_sha256": recipe_value["recipe_sha256"],
        "scene_binding": binding,
        "ordered_segments": ["pregrasp", "grasp", "lift"],
        "planner_query_limit": STAGE_A_QUERY_COUNT,
        "arbitrary_callable_injection_allowed": False,
        "physical_execution_count_limit": 0,
        "planner_execution_authorized": False,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["spec_sha256"] = canonical_hash_json(value)
    return value


def validate_f3_stage_a_planner_spec_v3_1(spec: Mapping[str, Any]) -> dict[str, Any]:
    value = _self_hashed(spec, "spec_sha256", "Stage-A spec")
    rebuilt = build_f3_stage_a_planner_spec_v3_1(
        value["recipe"],
        value["scene_binding"],
        slot_id=value["slot_id"],
        panel_sha256=value["panel_sha256"],
    )
    if value != rebuilt:
        raise ValueError("F3 V2.3 Stage-A spec differs from canonical rebuild")
    return value


def run_f3_stage_a_planner_v3_1(scene, spec: Mapping[str, Any]) -> dict[str, Any]:
    value = validate_f3_stage_a_planner_spec_v3_1(spec)
    runtime_binding = _runtime_scene_binding(scene)
    if runtime_binding != value["scene_binding"]:
        raise ValueError("F3 V2.3 Stage-A runtime scene binding mismatch")
    recipe = value["recipe"]
    raw = generate_official_raw_pose_receipt_v1(
        scene, scene.bottle, recipe, family="F3"
    )
    if raw["actor_pose_sha256"] != runtime_binding["bottle_actor_pose_sha256"]:
        raise ValueError("F3 V2.3 Stage-A bottle actor pose mismatch")
    freeze = freeze_f3_final_pose_v3(recipe, raw_pose_generation_receipt=raw)
    names = ("pregrasp", "grasp", "lift")
    targets = [
        {
            "segment_id": f"f3_v3_stage_a_{name}",
            "pose": freeze["final_goal_poses"][name],
        }
        for name in names
    ]
    reset = _planner_reset(
        scene,
        planner_seed=20260903,
        variant_id=f"{STAGE_A_PURPOSE}:{recipe['recipe_id']}",
        arm=recipe["arm"],
    )
    planned = _plan_chain(
        scene, targets, query_limit=STAGE_A_QUERY_COUNT, arm=recipe["arm"]
    )
    receipts = planned.get("segment_receipts", [])
    statuses = {
        name: next(
            (
                item.get("planner_status")
                for item in receipts
                if item.get("segment_id") == f"f3_v3_stage_a_{name}"
            ),
            None,
        )
        for name in names
    }
    qualification = {
        "recipe_sha256": recipe["recipe_sha256"],
        "arm": recipe["arm"],
        "final_pose_freeze_sha256": freeze["final_pose_freeze_sha256"],
        "ordered_planner_input_sha256": freeze["ordered_final_planner_input_sha256"],
        "goal_pose_hashes": freeze["final_goal_pose_hashes"],
        "planner_statuses": statuses,
        "ik_collision_planner_checked": len(receipts) == STAGE_A_QUERY_COUNT,
        "post_qualification_pose_mutation": False,
    }
    qualification["receipt_sha256"] = canonical_hash_json(qualification)
    validation = validate_f3_final_pose_qualification_v3(
        recipe, freeze, qualification
    )
    terminal_qpos = planned.get("terminal_qpos")
    terminal_qpos_hash_valid = terminal_qpos is not None and hash_array(
        np.asarray(terminal_qpos, dtype=np.float32)
    ) == planned.get("terminal_qpos_sha256")
    passed = (
        planned.get("pass") is True
        and validation["pass"] is True
        and terminal_qpos_hash_valid
    )
    result = {
        "schema_version": "cmf_f3_stage_a_planner_terminal_v3_1",
        "purpose": STAGE_A_PURPOSE,
        "slot_id": value["slot_id"],
        "spec_sha256": value["spec_sha256"],
        "panel_sha256": value["panel_sha256"],
        "recipe_sha256": recipe["recipe_sha256"],
        "arm": recipe["arm"],
        "scene_instance_id": getattr(scene, "_cmf_scene_instance_id", None),
        "scene_binding": runtime_binding,
        "raw_pose_generation_receipt": raw,
        "final_pose_freeze": freeze,
        "stage_a_lift_pose_sha256": freeze["final_goal_pose_hashes"]["lift"],
        "stage_a_terminal_qpos": deepcopy(terminal_qpos),
        "stage_a_terminal_qpos_sha256": planned.get("terminal_qpos_sha256"),
        "planner_rng_reset": canonical_jsonable(reset),
        "planner_result": _planner_summary(planned),
        "stage_a_pass": passed,
        "planner_qualified_for_physical_probe": False,
        "candidate_ready": False,
        "stage1_ready": False,
        "physical_execution_authorized": False,
        "physical_execution_count": 0,
    }
    result["receipt_sha256"] = canonical_hash_json(result)
    return result


def validate_f3_stage_a_terminal_v3_1(
    terminal: Mapping[str, Any], spec: Mapping[str, Any]
) -> dict[str, Any]:
    value = _self_hashed(terminal, "receipt_sha256", "Stage-A terminal")
    checked = validate_f3_stage_a_planner_spec_v3_1(spec)
    if (
        value.get("schema_version") != "cmf_f3_stage_a_planner_terminal_v3_1"
        or value.get("spec_sha256") != checked["spec_sha256"]
        or value.get("scene_binding") != checked["scene_binding"]
        or value.get("candidate_ready") is not False
        or value.get("physical_execution_count") != 0
    ):
        raise ValueError("F3 V2.3 Stage-A terminal binding changed")
    return value


def build_f3_stage_b_planner_spec_v3_1(
    stage_a_terminal: Mapping[str, Any],
    stage_a_spec: Mapping[str, Any],
    *,
    slot_id: str,
    selection_policy_sha256: str,
) -> dict[str, Any]:
    stage_a = validate_f3_stage_a_terminal_v3_1(stage_a_terminal, stage_a_spec)
    if stage_a.get("stage_a_pass") is not True:
        raise ValueError("F3 V2.3 Stage B requires passing Stage A")
    value = {
        "schema_version": "cmf_f3_stage_b_planner_spec_v3_1",
        "purpose": STAGE_B_PURPOSE,
        "slot_id": str(slot_id),
        "family": "F3",
        "selection_policy_sha256": str(selection_policy_sha256),
        "recipe_sha256": stage_a["recipe_sha256"],
        "arm": stage_a["arm"],
        "stage_a_spec_sha256": stage_a["spec_sha256"],
        "stage_a_terminal_receipt_sha256": stage_a["receipt_sha256"],
        "stage_a_terminal_qpos": stage_a["stage_a_terminal_qpos"],
        "stage_a_terminal_qpos_sha256": stage_a["stage_a_terminal_qpos_sha256"],
        "stage_a_lift_pose": stage_a["final_pose_freeze"]["final_goal_poses"]["lift"],
        "stage_a_lift_pose_sha256": stage_a["stage_a_lift_pose_sha256"],
        "scene_binding": stage_a["scene_binding"],
        "ordered_segments": [
            "central_1", "V_plus", "V_minus", "central_2",
            "H_plus", "H_minus", "central_3",
        ],
        "planner_query_limit": STAGE_B_QUERY_COUNT,
        "initial_eef_position_atol_m": POSITION_ATOL_M,
        "initial_eef_orientation_atol_rad": ORIENTATION_ATOL_RAD,
        "arbitrary_callable_injection_allowed": False,
        "physical_execution_count_limit": 0,
        "planner_execution_authorized": False,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["spec_sha256"] = canonical_hash_json(value)
    return value


def validate_f3_stage_b_planner_spec_v3_1(spec: Mapping[str, Any]) -> dict[str, Any]:
    value = _self_hashed(spec, "spec_sha256", "Stage-B spec")
    if (
        value.get("purpose") != STAGE_B_PURPOSE
        or value.get("planner_query_limit") != STAGE_B_QUERY_COUNT
        or value.get("ordered_segments") != [
            "central_1", "V_plus", "V_minus", "central_2",
            "H_plus", "H_minus", "central_3",
        ]
        or canonical_hash_json(value.get("stage_a_lift_pose"))
        != value.get("stage_a_lift_pose_sha256")
        or hash_array(np.asarray(value.get("stage_a_terminal_qpos"), dtype=np.float32))
        != value.get("stage_a_terminal_qpos_sha256")
    ):
        raise ValueError("F3 V2.3 Stage-B spec continuity binding changed")
    _scene_binding(value["scene_binding"])
    return value


def build_f3_stage_b_targets_v3_1(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    value = validate_f3_stage_b_planner_spec_v3_1(spec)
    lift = np.asarray(value["stage_a_lift_pose"], dtype=np.float64)
    central = lift.copy()
    central[:3] = CENTRAL_POSITION_TABLE_FRAME_M
    values = (
        ("central_1", central),
        ("V_plus", world_axis_offset_pose(central, V_DISTANCE_M, axis=(0, 0, 1))),
        ("V_minus", world_axis_offset_pose(central, -V_DISTANCE_M, axis=(0, 0, 1))),
        ("central_2", central),
        ("H_plus", world_axis_offset_pose(central, H_DISTANCE_M, axis=(1, 0, 0))),
        ("H_minus", world_axis_offset_pose(central, -H_DISTANCE_M, axis=(1, 0, 0))),
        ("central_3", central),
    )
    return [
        {"segment_id": f"f3_v3_stage_b_{name}", "pose": pose.tolist()}
        for name, pose in values
    ]


def run_f3_stage_b_planner_v3_1(scene, spec: Mapping[str, Any]) -> dict[str, Any]:
    value = validate_f3_stage_b_planner_spec_v3_1(spec)
    runtime_binding = _runtime_scene_binding(scene)
    if runtime_binding != value["scene_binding"]:
        raise ValueError("F3 V2.3 Stage-B reconstructed scene binding mismatch")
    actor_hash = canonical_hash_json(_pose(scene.bottle).tolist())
    if actor_hash != runtime_binding["bottle_actor_pose_sha256"]:
        raise ValueError("F3 V2.3 Stage-B bottle actor pose mismatch")
    arm = value["arm"]
    if arm not in ("left", "right"):
        raise ValueError("F3 V2.3 Stage-B execution arm is missing")
    reset = _planner_reset(
        scene,
        planner_seed=20260903,
        variant_id=f"{STAGE_B_PURPOSE}:{value['recipe_sha256']}",
        arm=arm,
    )
    entity = _arm_entity(scene, arm)
    terminal_qpos = np.asarray(value["stage_a_terminal_qpos"], dtype=np.float32)
    entity.set_qpos(terminal_qpos)
    initial_qpos = np.asarray(entity.get_qpos(), dtype=np.float32)
    initial_qpos_sha = hash_array(initial_qpos)
    if initial_qpos_sha != value["stage_a_terminal_qpos_sha256"]:
        raise ValueError("F3 V2.3 Stage-B initial qpos differs from Stage A")
    initial_eef = np.asarray(_arm_eef_pose(scene, arm), dtype=np.float64)
    lift = np.asarray(value["stage_a_lift_pose"], dtype=np.float64)
    position_error = float(np.linalg.norm(initial_eef[:3] - lift[:3]))
    orientation_error = quaternion_angular_error(initial_eef[3:], lift[3:])
    continuity_gate = {
        "stage_a_terminal_qpos_sha256": value["stage_a_terminal_qpos_sha256"],
        "stage_b_initial_qpos_sha256": initial_qpos_sha,
        "stage_a_lift_pose_sha256": value["stage_a_lift_pose_sha256"],
        "stage_b_initial_eef_pose_sha256": canonical_hash_json(initial_eef.tolist()),
        "position_error_m": position_error,
        "orientation_error_rad": orientation_error,
        "position_atol_m": POSITION_ATOL_M,
        "orientation_atol_rad": ORIENTATION_ATOL_RAD,
        "pass": position_error <= POSITION_ATOL_M
        and orientation_error <= ORIENTATION_ATOL_RAD,
    }
    continuity_gate["receipt_sha256"] = canonical_hash_json(continuity_gate)
    if continuity_gate["pass"] is not True:
        raise ValueError("F3 V2.3 Stage-B initial EEF differs from frozen lift")
    targets = build_f3_stage_b_targets_v3_1(value)
    planned = _plan_chain(
        scene, targets, query_limit=STAGE_B_QUERY_COUNT, arm=arm
    )
    receipts = planned.get("segment_receipts", [])
    passed = (
        planned.get("pass") is True
        and len(receipts) == STAGE_B_QUERY_COUNT
        and [item.get("segment_id") for item in receipts]
        == [item["segment_id"] for item in targets]
        and all(item.get("planner_status") == "Success" for item in receipts)
    )
    result = {
        "schema_version": "cmf_f3_stage_b_planner_terminal_v3_1",
        "purpose": STAGE_B_PURPOSE,
        "slot_id": value["slot_id"],
        "spec_sha256": value["spec_sha256"],
        "recipe_sha256": value["recipe_sha256"],
        "stage_a_terminal_receipt_sha256": value["stage_a_terminal_receipt_sha256"],
        "scene_instance_id": getattr(scene, "_cmf_scene_instance_id", None),
        "scene_binding": runtime_binding,
        "stage_a_terminal_qpos_sha256": value["stage_a_terminal_qpos_sha256"],
        "stage_a_lift_pose_sha256": value["stage_a_lift_pose_sha256"],
        "stage_b_initial_qpos_sha256": initial_qpos_sha,
        "stage_b_initial_eef_pose_sha256": continuity_gate[
            "stage_b_initial_eef_pose_sha256"
        ],
        "continuity_gate": continuity_gate,
        "planner_rng_reset": canonical_jsonable(reset),
        "targets": targets,
        "targets_sha256": canonical_hash_json(targets),
        "planner_result": _planner_summary(planned),
        "stage_b_pass": passed,
        "planner_qualified_for_physical_probe": False,
        "candidate_ready": False,
        "stage1_ready": False,
        "physical_execution_authorized": False,
        "physical_execution_count": 0,
    }
    result["receipt_sha256"] = canonical_hash_json(result)
    return result


def finalize_f3_candidate_qualification_v3_1(
    stage_a_terminal: Mapping[str, Any],
    stage_a_spec: Mapping[str, Any],
    stage_b_terminal: Mapping[str, Any],
    stage_b_spec: Mapping[str, Any],
) -> dict[str, Any]:
    stage_a = validate_f3_stage_a_terminal_v3_1(stage_a_terminal, stage_a_spec)
    stage_b = _self_hashed(stage_b_terminal, "receipt_sha256", "Stage-B terminal")
    checked_b = validate_f3_stage_b_planner_spec_v3_1(stage_b_spec)
    checks = {
        "stage_a_pass": stage_a.get("stage_a_pass") is True,
        "stage_b_pass": stage_b.get("stage_b_pass") is True,
        "stage_b_spec_bound": stage_b.get("spec_sha256") == checked_b["spec_sha256"],
        "stage_b_binds_stage_a": stage_b.get("stage_a_terminal_receipt_sha256")
        == stage_a["receipt_sha256"],
        "qpos_continuity": stage_b.get("continuity_gate", {}).get("pass") is True,
        "scene_binding_equal": stage_b.get("scene_binding") == stage_a["scene_binding"],
        "physical_execution_zero": stage_b.get("physical_execution_count") == 0,
    }
    result = {
        "schema_version": "cmf_f3_candidate_qualification_v3_1",
        "recipe_sha256": stage_a["recipe_sha256"],
        "checks": checks,
        "planner_qualified_for_physical_probe": all(checks.values()),
        "candidate_ready": False,
        "stage1_ready": False,
        "physical_execution_authorized": False,
    }
    result["receipt_sha256"] = canonical_hash_json(result)
    return result


__all__ = [
    "STAGE_A_PURPOSE", "STAGE_B_PURPOSE",
    "build_f3_stage_a_planner_spec_v3_1",
    "build_f3_stage_b_planner_spec_v3_1",
    "build_f3_stage_b_targets_v3_1",
    "finalize_f3_candidate_qualification_v3_1",
    "run_f3_stage_a_planner_v3_1",
    "run_f3_stage_b_planner_v3_1",
]
