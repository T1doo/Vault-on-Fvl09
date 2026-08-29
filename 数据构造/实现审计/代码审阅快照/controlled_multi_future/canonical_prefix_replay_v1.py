"""Exact canonical-prefix replay for runtime-v3_3 fresh scenes."""

from __future__ import annotations

from typing import Any, Callable, Mapping

import numpy as np

from .anchor import compare_anchors
from .canonical_prefix_artifact_v1 import (
    array_sha256,
    prefix_action_sha256,
    validate_canonical_prefix_artifact,
)
from .current_hasher import hash_array, require_same_current
from .probes.runtime_trace import _dual_entity_values


REPLAY_SCHEMA_VERSION = "cmf_canonical_prefix_replay_v1"


def replay_canonical_prefix(
    scene: Any,
    *,
    manifest: Mapping[str, Any],
    arrays: Mapping[str, Any],
    reference_current: Mapping[str, Any],
    capture_current: Callable[[Any], Mapping[str, Any]],
    capture_anchor: Callable[[Any], Mapping[str, Any]],
) -> dict:
    artifact, normalized = validate_canonical_prefix_artifact(manifest, arrays)
    if not hasattr(scene, "replay_effective_setpoint_step"):
        raise TypeError("scene does not implement exact effective-setpoint replay")
    current = dict(capture_current(scene))
    require_same_current(reference_current, current)
    start_anchor = dict(capture_anchor(scene))
    if start_anchor.get("anchor_sha256") != artifact.get("reference_anchor_sha256"):
        start_equivalence = compare_anchors(artifact["reference_anchor"], start_anchor)
        if not start_equivalence["equivalent"]:
            raise ValueError(f"canonical prefix replay start anchor mismatch: {start_equivalence['failures']}")
    else:
        start_equivalence = {
            "equivalent": True,
            "failures": [],
            "reference_sha256": artifact.get("reference_anchor_sha256"),
            "candidate_sha256": start_anchor.get("anchor_sha256"),
        }

    planner_before = int(getattr(scene, "planner_query_count", 0))
    trace_start = len(getattr(scene, "trace", []))
    scene.mark("canonical_prefix_replay_start")
    for index in range(artifact["prefix_step_count"]):
        scene.replay_effective_setpoint_step(
            normalized["effective_setpoint_actions"][index],
            requested_command=normalized["requested_commands"][index],
            component_mask=normalized["component_masks"][index],
            left_gripper_joint_drive_target=normalized[
                "left_gripper_joint_drive_targets"
            ][index],
            right_gripper_joint_drive_target=normalized[
                "right_gripper_joint_drive_targets"
            ][index],
            left_gripper_joint_drive_velocity_target=normalized[
                "left_gripper_joint_drive_velocity_targets"
            ][index],
            right_gripper_joint_drive_velocity_target=normalized[
                "right_gripper_joint_drive_velocity_targets"
            ][index],
        )
    scene.mark("canonical_prefix_end")
    semantic_end_anchor = dict(capture_anchor(scene))
    semantic_result = compare_anchors(
        artifact["semantic_prefix_end_anchor"], semantic_end_anchor
    )

    settling_steps = int(artifact["settling_step_count_excluded_from_semantic_prefix"])
    if settling_steps:
        policy = artifact.get("settling_policy", {})
        if (
            policy.get("mode") != "hold_last_effective_setpoint"
            or policy.get("component_mask_policy")
            != "all_false_no_new_control_command"
            or policy.get("transition_operator")
            != "replay_effective_setpoint_step_v1_1"
        ):
            raise ValueError("unsupported canonical prefix settling policy")
        scene.mark("canonical_prefix_settling_start")
        hold_action = normalized["effective_setpoint_actions"][-1]
        hold_requested = normalized["requested_commands"][-1]
        hold_mask = np.zeros(hold_action.shape, dtype=bool)
        for _ in range(settling_steps):
            scene.replay_effective_setpoint_step(
                hold_action,
                requested_command=hold_requested,
                component_mask=hold_mask,
                left_gripper_joint_drive_target=normalized[
                    "left_gripper_joint_drive_targets"
                ][-1],
                right_gripper_joint_drive_target=normalized[
                    "right_gripper_joint_drive_targets"
                ][-1],
                left_gripper_joint_drive_velocity_target=normalized[
                    "left_gripper_joint_drive_velocity_targets"
                ][-1],
                right_gripper_joint_drive_velocity_target=normalized[
                    "right_gripper_joint_drive_velocity_targets"
                ][-1],
            )
        scene.mark("canonical_prefix_settling_end")
    acceptance_end_anchor = dict(capture_anchor(scene))
    acceptance_result = compare_anchors(
        artifact["acceptance_prefix_end_anchor"], acceptance_end_anchor
    )

    planner_after = int(getattr(scene, "planner_query_count", 0))
    if planner_after != planner_before:
        raise RuntimeError("canonical prefix replay invoked planner")
    rows = scene.trace[trace_start : trace_start + artifact["prefix_step_count"]]
    executed_actions = np.ascontiguousarray(
        np.asarray([row["effective_setpoint"] for row in rows], dtype=np.float64)
    )
    executed_hash = prefix_action_sha256(executed_actions)
    if executed_hash != artifact["prefix_action_sha256"]:
        raise ValueError("canonical prefix replay effective action bytes differ from artifact")
    if not np.array_equal(
        executed_actions,
        normalized["effective_setpoint_actions"],
    ):
        raise ValueError("canonical prefix replay action array is not byte-identical")
    executed_requested = np.ascontiguousarray(
        np.asarray([row["requested_command"] for row in rows], dtype=np.float64)
    )
    executed_masks = np.ascontiguousarray(
        np.asarray([row["component_mask"] for row in rows], dtype=bool)
    )
    if not np.array_equal(executed_requested, normalized["requested_commands"]):
        raise ValueError("canonical prefix replay requested commands differ from artifact")
    if not np.array_equal(executed_masks, normalized["component_masks"]):
        raise ValueError("canonical prefix replay component masks differ from artifact")
    gripper_fields = {
        "left_gripper_joint_drive_targets": "left_gripper_joint_drive_target",
        "right_gripper_joint_drive_targets": "right_gripper_joint_drive_target",
        "left_gripper_joint_drive_velocity_targets": "left_gripper_joint_drive_velocity_target",
        "right_gripper_joint_drive_velocity_targets": "right_gripper_joint_drive_velocity_target",
    }
    executed_gripper_hashes = {}
    for artifact_key, row_key in gripper_fields.items():
        executed = np.ascontiguousarray(
            np.asarray([row[row_key] for row in rows], dtype=np.float64)
        )
        if not np.array_equal(executed, normalized[artifact_key]):
            raise ValueError(
                f"canonical prefix replay {artifact_key} differ from artifact"
            )
        executed_gripper_hashes[artifact_key] = array_sha256(executed)
    arm = artifact.get("prefix_contract", {}).get("arm")
    if arm not in ("left", "right"):
        raise ValueError("canonical prefix contract must name one executing arm")
    actual_qpos = np.asarray(
        getattr(scene.robot, f"{arm}_entity").get_qpos(), dtype=np.float64
    )
    actual_dual_qpos = _dual_entity_values(scene.robot, "get_qpos")
    return {
        "schema_version": REPLAY_SCHEMA_VERSION,
        "artifact_sha256": artifact["artifact_sha256"],
        "reference_current_sha256": reference_current.get("aggregate_sha256"),
        "branch_current_sha256": current.get("aggregate_sha256"),
        "start_anchor_equivalence": start_equivalence,
        "executed_prefix_action_sha256": executed_hash,
        "executed_requested_commands_sha256": array_sha256(executed_requested),
        "executed_component_masks_sha256": array_sha256(executed_masks),
        "executed_gripper_drive_array_sha256": executed_gripper_hashes,
        "executed_prefix_step_count": artifact["prefix_step_count"],
        "canonical_prefix_end_step": artifact["prefix_step_count"],
        "semantic_prefix_end_anchor": semantic_end_anchor,
        "semantic_prefix_end_equivalence": semantic_result,
        "settling_step_count_excluded_from_semantic_prefix": settling_steps,
        "acceptance_prefix_end_anchor": acceptance_end_anchor,
        "acceptance_prefix_end_equivalence": acceptance_result,
        "prefix_end_equivalent": bool(
            semantic_result["equivalent"] and acceptance_result["equivalent"]
        ),
        "reference_prefix_physical_acceptance": dict(
            artifact["prefix_physical_acceptance"]
        ),
        "planner_query_delta": planner_after - planner_before,
        "actual_prefix_end_qpos_sha256": hash_array(actual_qpos),
        "actual_prefix_end_qpos": np.asarray(actual_qpos, dtype=np.float64).tolist(),
        "actual_dual_prefix_end_qpos_sha256": hash_array(actual_dual_qpos),
        "actual_dual_prefix_end_qpos": np.asarray(
            actual_dual_qpos, dtype=np.float64
        ).tolist(),
        "execution_arm": arm,
        "trace_replay_start_row": trace_start,
        "reference_event_boundaries": dict(
            artifact.get("reference_event_boundaries", {})
        ),
        "start_anchor": start_anchor,
        "target_role_visible_during_prefix": False,
        "formal_data": False,
        "stage0_data": False,
    }
