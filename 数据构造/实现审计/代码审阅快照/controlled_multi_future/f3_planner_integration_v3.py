"""Independent F3 V3 planner-only Stage-A/Stage-B interfaces.

This module deliberately does not register either purpose with the legacy
``HighLevelPlannerRunnerV1`` dispatcher.  A future reviewed issuer may call
these runners, but this CPU publication neither authorizes nor executes a
real planner job.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f3_final_pose_search_v3 import (
    freeze_f3_final_pose_v3,
    validate_f3_final_pose_qualification_v3,
)
from .geometry import world_axis_offset_pose
from .official_raw_pose_generation_v1 import (
    generate_official_raw_pose_receipt_v1,
)


STAGE_A_PURPOSE = "f3_final_pose_v3_stage_a_planner"
STAGE_B_PURPOSE = "f3_final_pose_v3_stage_b_planner"
STAGE_A_QUERY_COUNT = 3
STAGE_B_QUERY_COUNT = 8
V_DISTANCE_M = 0.055
H_DISTANCE_M = 0.050
CENTRAL_POSITION_TABLE_FRAME_M = (0.0, -0.05, 0.95)


def _valid_recipe(recipe: Mapping[str, Any]) -> dict[str, Any]:
    value = canonical_jsonable(recipe)
    payload = dict(value)
    digest = payload.pop("recipe_sha256", None)
    if digest != canonical_hash_json(payload):
        raise ValueError("F3 V3 planner spec recipe hash mismatch")
    return value


def _valid_terminal(receipt: Mapping[str, Any], *, schema: str) -> dict[str, Any]:
    value = canonical_jsonable(receipt)
    payload = dict(value)
    digest = payload.pop("receipt_sha256", None)
    if value.get("schema_version") != schema or digest != canonical_hash_json(payload):
        raise ValueError("F3 V3 planner terminal receipt is invalid")
    return value


def _planner_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "pass": result.get("pass") is True,
        "segment_receipts": deepcopy(result.get("segment_receipts", [])),
        "planner_query_count": int(result.get("planner_query_count", 0)),
        "terminal_qpos": deepcopy(result.get("terminal_qpos")),
        "terminal_qpos_sha256": result.get("terminal_qpos_sha256"),
        "controls_retained_in_receipt": False,
    }


def _plan(
    plan_chain_fn: Callable[..., Mapping[str, Any]],
    scene,
    targets: Sequence[Mapping[str, Any]],
    *,
    query_limit: int,
    arm: str,
) -> dict[str, Any]:
    result = plan_chain_fn(scene, targets, query_limit=query_limit, arm=arm)
    if not isinstance(result, Mapping):
        raise TypeError("F3 V3 planner callback must return a mapping")
    return dict(result)


def build_f3_stage_a_planner_spec_v3(
    recipe: Mapping[str, Any], *, slot_id: str
) -> dict[str, Any]:
    recipe_value = _valid_recipe(recipe)
    value = {
        "schema_version": "cmf_f3_final_pose_v3_stage_a_planner_spec",
        "purpose": STAGE_A_PURPOSE,
        "slot_id": str(slot_id),
        "family": "F3",
        "recipe": recipe_value,
        "recipe_sha256": recipe_value["recipe_sha256"],
        "raw_pose_generation_receipt_required": True,
        "external_raw_pose_input_allowed": False,
        "ordered_segments": ["pregrasp", "grasp", "lift"],
        "planner_query_limit": STAGE_A_QUERY_COUNT,
        "stage_a_alone_candidate_ready": False,
        "stage_b_required": True,
        "planner_execution_authorized": False,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
    }
    value["spec_sha256"] = canonical_hash_json(value)
    return value


def run_f3_stage_a_planner_v3(
    scene,
    spec: Mapping[str, Any],
    *,
    plan_chain_fn: Callable[..., Mapping[str, Any]],
    raw_pose_generator: Callable[..., Mapping[str, Any]] = (
        generate_official_raw_pose_receipt_v1
    ),
) -> dict[str, Any]:
    spec_value = canonical_jsonable(spec)
    payload = dict(spec_value)
    digest = payload.pop("spec_sha256", None)
    if (
        digest != canonical_hash_json(payload)
        or spec_value.get("purpose") != STAGE_A_PURPOSE
        or spec_value.get("planner_execution_authorized") is not False
    ):
        raise ValueError("F3 V3 Stage-A spec is invalid or activated")
    recipe = _valid_recipe(spec_value["recipe"])
    raw = raw_pose_generator(scene, scene.bottle, recipe, family="F3")
    freeze = freeze_f3_final_pose_v3(
        recipe, raw_pose_generation_receipt=raw
    )
    targets = [
        {
            "segment_id": f"f3_v3_stage_a_{name}",
            "pose": freeze["final_goal_poses"][name],
        }
        for name in ("pregrasp", "grasp", "lift")
    ]
    planned = _plan(
        plan_chain_fn,
        scene,
        targets,
        query_limit=STAGE_A_QUERY_COUNT,
        arm=recipe["arm"],
    )
    by_id = {
        item.get("segment_id"): item
        for item in planned.get("segment_receipts", [])
        if isinstance(item, Mapping)
    }
    statuses = {
        name: by_id.get(f"f3_v3_stage_a_{name}", {}).get("planner_status")
        for name in ("pregrasp", "grasp", "lift")
    }
    qualification = {
        "schema_version": "cmf_f3_final_pose_v3_stage_a_qualification",
        "recipe_sha256": recipe["recipe_sha256"],
        "final_pose_freeze_sha256": freeze["final_pose_freeze_sha256"],
        "ordered_planner_input_sha256": freeze[
            "ordered_final_planner_input_sha256"
        ],
        "goal_pose_hashes": freeze["final_goal_pose_hashes"],
        "planner_statuses": statuses,
        "ik_collision_planner_checked": len(by_id) == STAGE_A_QUERY_COUNT,
        "post_qualification_pose_mutation": False,
    }
    qualification["receipt_sha256"] = canonical_hash_json(qualification)
    validation = validate_f3_final_pose_qualification_v3(
        recipe, freeze, qualification
    )
    passed = planned.get("pass") is True and validation["pass"] is True
    value = {
        "schema_version": "cmf_f3_final_pose_v3_stage_a_terminal",
        "purpose": STAGE_A_PURPOSE,
        "slot_id": spec_value["slot_id"],
        "spec_sha256": digest,
        "scene_instance_id": getattr(scene, "_cmf_scene_instance_id", None),
        "recipe_sha256": recipe["recipe_sha256"],
        "raw_pose_generation_receipt": canonical_jsonable(raw),
        "final_pose_freeze": freeze,
        "qualification_receipt": qualification,
        "qualification_validation": validation,
        "planner_result": _planner_summary(planned),
        "stage_a_pass": passed,
        "candidate_ready": False,
        "candidate_ready_reason": "Stage B is independently required",
        "planner_execution_authorized_by_this_receipt": False,
        "physical_execution_count": 0,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def build_f3_stage_b_planner_spec_v3(
    stage_a_terminal: Mapping[str, Any], *, slot_id: str
) -> dict[str, Any]:
    stage_a = _valid_terminal(
        stage_a_terminal, schema="cmf_f3_final_pose_v3_stage_a_terminal"
    )
    if stage_a.get("stage_a_pass") is not True:
        raise ValueError("F3 V3 Stage-B requires a passing Stage-A terminal")
    value = {
        "schema_version": "cmf_f3_final_pose_v3_stage_b_planner_spec",
        "purpose": STAGE_B_PURPOSE,
        "slot_id": str(slot_id),
        "family": "F3",
        "recipe_sha256": stage_a["recipe_sha256"],
        "stage_a_terminal_receipt_sha256": stage_a["receipt_sha256"],
        "ordered_segments": [
            "lift",
            "central_1",
            "V_plus",
            "V_minus",
            "central_2",
            "H_plus",
            "H_minus",
            "central_3",
        ],
        "table_frame_axes": {"V": "+/-z_table", "H": "+/-x_table"},
        "planner_query_limit": STAGE_B_QUERY_COUNT,
        "planner_execution_authorized": False,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
    }
    value["spec_sha256"] = canonical_hash_json(value)
    return value


def build_f3_stage_b_targets_v3(
    stage_a_terminal: Mapping[str, Any],
) -> list[dict[str, Any]]:
    stage_a = _valid_terminal(
        stage_a_terminal, schema="cmf_f3_final_pose_v3_stage_a_terminal"
    )
    if stage_a.get("stage_a_pass") is not True:
        raise ValueError("F3 V3 Stage-B targets require passing Stage A")
    freeze = stage_a["final_pose_freeze"]
    lift = np.asarray(freeze["final_goal_poses"]["lift"], dtype=np.float64)
    central = lift.copy()
    central[:3] = CENTRAL_POSITION_TABLE_FRAME_M
    v_plus = world_axis_offset_pose(central, V_DISTANCE_M, axis=(0, 0, 1))
    v_minus = world_axis_offset_pose(central, -V_DISTANCE_M, axis=(0, 0, 1))
    h_plus = world_axis_offset_pose(central, H_DISTANCE_M, axis=(1, 0, 0))
    h_minus = world_axis_offset_pose(central, -H_DISTANCE_M, axis=(1, 0, 0))
    poses = (
        ("lift", lift),
        ("central_1", central),
        ("V_plus", v_plus),
        ("V_minus", v_minus),
        ("central_2", central),
        ("H_plus", h_plus),
        ("H_minus", h_minus),
        ("central_3", central),
    )
    return [
        {"segment_id": f"f3_v3_stage_b_{name}", "pose": pose.tolist()}
        for name, pose in poses
    ]


def run_f3_stage_b_planner_v3(
    scene,
    spec: Mapping[str, Any],
    stage_a_terminal: Mapping[str, Any],
    *,
    plan_chain_fn: Callable[..., Mapping[str, Any]],
) -> dict[str, Any]:
    stage_a = _valid_terminal(
        stage_a_terminal, schema="cmf_f3_final_pose_v3_stage_a_terminal"
    )
    spec_value = canonical_jsonable(spec)
    payload = dict(spec_value)
    digest = payload.pop("spec_sha256", None)
    if (
        digest != canonical_hash_json(payload)
        or spec_value.get("purpose") != STAGE_B_PURPOSE
        or spec_value.get("stage_a_terminal_receipt_sha256")
        != stage_a.get("receipt_sha256")
        or spec_value.get("planner_execution_authorized") is not False
    ):
        raise ValueError("F3 V3 Stage-B spec binding is invalid or activated")
    targets = build_f3_stage_b_targets_v3(stage_a)
    arm = stage_a["raw_pose_generation_receipt"]["arm"]
    planned = _plan(
        plan_chain_fn,
        scene,
        targets,
        query_limit=STAGE_B_QUERY_COUNT,
        arm=arm,
    )
    receipts = planned.get("segment_receipts", [])
    passed = (
        planned.get("pass") is True
        and len(receipts) == STAGE_B_QUERY_COUNT
        and all(item.get("planner_status") == "Success" for item in receipts)
    )
    value = {
        "schema_version": "cmf_f3_final_pose_v3_stage_b_terminal",
        "purpose": STAGE_B_PURPOSE,
        "slot_id": spec_value["slot_id"],
        "spec_sha256": digest,
        "scene_instance_id": getattr(scene, "_cmf_scene_instance_id", None),
        "recipe_sha256": stage_a["recipe_sha256"],
        "stage_a_terminal_receipt_sha256": stage_a["receipt_sha256"],
        "targets": targets,
        "targets_sha256": canonical_hash_json(targets),
        "planner_result": _planner_summary(planned),
        "stage_b_pass": passed,
        "candidate_ready": False,
        "candidate_ready_reason": "combined Stage-A/Stage-B finalizer required",
        "candidate_ready_requires_stage_a_and_stage_b": True,
        "planner_execution_authorized_by_this_receipt": False,
        "physical_execution_count": 0,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def finalize_f3_candidate_qualification_v3(
    stage_a_terminal: Mapping[str, Any],
    stage_b_terminal: Mapping[str, Any],
) -> dict[str, Any]:
    stage_a = _valid_terminal(
        stage_a_terminal, schema="cmf_f3_final_pose_v3_stage_a_terminal"
    )
    stage_b = _valid_terminal(
        stage_b_terminal, schema="cmf_f3_final_pose_v3_stage_b_terminal"
    )
    checks = {
        "stage_a_pass": stage_a.get("stage_a_pass") is True,
        "stage_b_pass": stage_b.get("stage_b_pass") is True,
        "stage_b_binds_stage_a": stage_b.get(
            "stage_a_terminal_receipt_sha256"
        )
        == stage_a.get("receipt_sha256"),
        "same_recipe": stage_b.get("recipe_sha256")
        == stage_a.get("recipe_sha256"),
    }
    value = {
        "schema_version": "cmf_f3_final_pose_v3_candidate_qualification",
        "recipe_sha256": stage_a["recipe_sha256"],
        "stage_a_terminal_receipt_sha256": stage_a["receipt_sha256"],
        "stage_b_terminal_receipt_sha256": stage_b["receipt_sha256"],
        "checks": checks,
        "candidate_ready": all(checks.values()),
        "stage_a_alone_never_candidate_ready": True,
        "physical_execution_authorized": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


__all__ = [
    "STAGE_A_PURPOSE",
    "STAGE_B_PURPOSE",
    "build_f3_stage_a_planner_spec_v3",
    "build_f3_stage_b_planner_spec_v3",
    "build_f3_stage_b_targets_v3",
    "finalize_f3_candidate_qualification_v3",
    "run_f3_stage_a_planner_v3",
    "run_f3_stage_b_planner_v3",
]
