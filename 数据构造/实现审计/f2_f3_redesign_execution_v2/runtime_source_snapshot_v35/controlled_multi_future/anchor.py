"""Canonical anchor capture and sign-invariant physical equivalence checks."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from .current_hasher import hash_json


PHYSICAL_ANCHOR_SCHEMA_VERSION = "physical_anchor_v2"
REQUIRED_ACTOR_STATE_FIELDS = ("pose", "linear_velocity", "angular_velocity", "sleep_state")


def quaternion_angular_error(left, right) -> float:
    """Return the sign-invariant rotation angle between two wxyz quaternions."""

    q0 = np.asarray(left, dtype=np.float64).reshape(4)
    q1 = np.asarray(right, dtype=np.float64).reshape(4)
    n0 = float(np.linalg.norm(q0))
    n1 = float(np.linalg.norm(q1))
    if n0 <= 0 or n1 <= 0:
        raise ValueError("anchor quaternion must have nonzero norm")
    dot = float(np.dot(q0 / n0, q1 / n1))
    return float(2.0 * np.arccos(np.clip(abs(dot), -1.0, 1.0)))


def _actor_state_payload(value: Mapping[str, Any]) -> dict:
    missing = [field for field in REQUIRED_ACTOR_STATE_FIELDS if field not in value]
    if missing:
        raise ValueError(f"actor state missing {missing}")
    pose = np.asarray(value["pose"], dtype=np.float64).reshape(7)
    linear = np.asarray(value["linear_velocity"], dtype=np.float64).reshape(3)
    angular = np.asarray(value["angular_velocity"], dtype=np.float64).reshape(3)
    sleep_state = value["sleep_state"]
    if not isinstance(sleep_state, (bool, str)):
        raise ValueError("actor sleep_state must be bool or an explicit string")
    return {
        "pose": pose.tolist(),
        "linear_velocity": linear.tolist(),
        "angular_velocity": angular.tolist(),
        "sleep_state": sleep_state,
    }


def capture_physical_anchor_v2(
    *,
    robot_qpos,
    robot_qvel,
    robot_drive_target,
    gripper_joint_qpos,
    actor_states: Mapping[str, Mapping[str, Any]],
    facility_poses: Mapping[str, Any],
    physics_config: Mapping[str, Any],
    source_commit: str,
    metadata: Mapping[str, Any],
) -> dict:
    """Capture verifier-only physical state; this payload is not a model input."""

    if not isinstance(source_commit, str) or not source_commit:
        raise ValueError("physical anchor requires a source commit")
    if not actor_states:
        raise ValueError("physical anchor requires at least one dynamic actor state")
    payload = {
        "schema_version": PHYSICAL_ANCHOR_SCHEMA_VERSION,
        "model_visible": False,
        "robot_qpos": np.asarray(robot_qpos, dtype=np.float64).reshape(-1).tolist(),
        "robot_qvel": np.asarray(robot_qvel, dtype=np.float64).reshape(-1).tolist(),
        "robot_drive_target": np.asarray(robot_drive_target, dtype=np.float64).reshape(-1).tolist(),
        "gripper_joint_qpos": np.asarray(gripper_joint_qpos, dtype=np.float64).reshape(-1).tolist(),
        "actor_states": {role: _actor_state_payload(actor_states[role]) for role in sorted(actor_states)},
        "facility_poses": {
            role: np.asarray(facility_poses[role], dtype=np.float64).reshape(7).tolist()
            for role in sorted(facility_poses)
        },
        "physics_config": dict(physics_config),
        "source_commit": source_commit,
        "metadata": dict(metadata),
    }
    payload["anchor_sha256"] = hash_json(payload)
    return payload


def capture_anchor(*, robot_qpos, robot_qvel, actor_poses: Mapping[str, Any], gripper_state, metadata: Mapping[str, Any]) -> dict:
    payload = {
        "schema_version": "physical_anchor_v1_legacy",
        "robot_qpos": np.asarray(robot_qpos, dtype=np.float64).tolist(),
        "robot_qvel": np.asarray(robot_qvel, dtype=np.float64).tolist(),
        "actor_poses": {key: np.asarray(actor_poses[key], dtype=np.float64).tolist() for key in sorted(actor_poses)},
        "gripper_state": np.asarray(gripper_state, dtype=np.float64).tolist(),
        "metadata": dict(metadata),
    }
    payload["anchor_sha256"] = hash_json(payload)
    return payload


def _compare_pose(reference, candidate, *, position_atol: float, orientation_atol_rad: float) -> list[str]:
    left = np.asarray(reference, dtype=np.float64).reshape(7)
    right = np.asarray(candidate, dtype=np.float64).reshape(7)
    failures = []
    if float(np.linalg.norm(left[:3] - right[:3])) > position_atol:
        failures.append("position")
    if quaternion_angular_error(left[3:], right[3:]) > orientation_atol_rad:
        failures.append("orientation")
    return failures


def compare_anchors(
    reference: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    position_atol=1e-6,
    orientation_atol_rad=1e-6,
    velocity_atol=1e-6,
    angular_velocity_atol=1e-6,
) -> dict:
    failures = []
    if reference.get("schema_version") != candidate.get("schema_version"):
        failures.append("schema_version")
    for key, tolerance in (("robot_qpos", position_atol), ("robot_qvel", velocity_atol)):
        if not np.allclose(reference[key], candidate[key], rtol=0.0, atol=tolerance):
            failures.append(key)

    if reference.get("schema_version") == PHYSICAL_ANCHOR_SCHEMA_VERSION:
        for key, tolerance in (("robot_drive_target", position_atol), ("gripper_joint_qpos", position_atol)):
            if not np.allclose(reference[key], candidate[key], rtol=0.0, atol=tolerance):
                failures.append(key)
        if set(reference["actor_states"]) != set(candidate["actor_states"]):
            failures.append("actor_role_set")
        else:
            for role in reference["actor_states"]:
                left = reference["actor_states"][role]
                right = candidate["actor_states"][role]
                for component in _compare_pose(
                    left["pose"], right["pose"],
                    position_atol=position_atol,
                    orientation_atol_rad=orientation_atol_rad,
                ):
                    failures.append(f"actor_{component}:{role}")
                if not np.allclose(left["linear_velocity"], right["linear_velocity"], rtol=0.0, atol=velocity_atol):
                    failures.append(f"actor_linear_velocity:{role}")
                if not np.allclose(left["angular_velocity"], right["angular_velocity"], rtol=0.0, atol=angular_velocity_atol):
                    failures.append(f"actor_angular_velocity:{role}")
                if left["sleep_state"] != right["sleep_state"]:
                    failures.append(f"actor_sleep_state:{role}")
        if set(reference["facility_poses"]) != set(candidate["facility_poses"]):
            failures.append("facility_role_set")
        else:
            for role in reference["facility_poses"]:
                for component in _compare_pose(
                    reference["facility_poses"][role], candidate["facility_poses"][role],
                    position_atol=position_atol,
                    orientation_atol_rad=orientation_atol_rad,
                ):
                    failures.append(f"facility_{component}:{role}")
        for key in ("physics_config", "source_commit", "metadata"):
            if reference.get(key) != candidate.get(key):
                failures.append(key)
    else:
        if not np.allclose(reference["gripper_state"], candidate["gripper_state"], rtol=0.0, atol=position_atol):
            failures.append("gripper_state")
        if set(reference["actor_poses"]) != set(candidate["actor_poses"]):
            failures.append("actor_role_set")
        else:
            for role in reference["actor_poses"]:
                for component in _compare_pose(
                    reference["actor_poses"][role], candidate["actor_poses"][role],
                    position_atol=position_atol,
                    orientation_atol_rad=orientation_atol_rad,
                ):
                    failures.append(f"actor_{component}:{role}")
        if reference.get("metadata") != candidate.get("metadata"):
            failures.append("metadata")
    return {"equivalent": not failures, "failures": failures, "reference_sha256": reference.get("anchor_sha256"), "candidate_sha256": candidate.get("anchor_sha256")}
