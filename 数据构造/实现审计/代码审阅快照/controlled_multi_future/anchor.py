"""Canonical anchor capture and equivalence checks."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from .current_hasher import hash_array, hash_json


def capture_anchor(*, robot_qpos, robot_qvel, actor_poses: Mapping[str, Any], gripper_state, metadata: Mapping[str, Any]) -> dict:
    payload = {
        "robot_qpos": np.asarray(robot_qpos, dtype=np.float64).tolist(),
        "robot_qvel": np.asarray(robot_qvel, dtype=np.float64).tolist(),
        "actor_poses": {key: np.asarray(actor_poses[key], dtype=np.float64).tolist() for key in sorted(actor_poses)},
        "gripper_state": np.asarray(gripper_state, dtype=np.float64).tolist(),
        "metadata": dict(metadata),
    }
    payload["anchor_sha256"] = hash_json(payload)
    return payload


def compare_anchors(reference: Mapping[str, Any], candidate: Mapping[str, Any], *, position_atol=1e-6, velocity_atol=1e-6) -> dict:
    failures = []
    for key, tolerance in (("robot_qpos", position_atol), ("robot_qvel", velocity_atol), ("gripper_state", position_atol)):
        if not np.allclose(reference[key], candidate[key], rtol=0.0, atol=tolerance):
            failures.append(key)
    if set(reference["actor_poses"]) != set(candidate["actor_poses"]):
        failures.append("actor_role_set")
    else:
        for role in reference["actor_poses"]:
            if not np.allclose(reference["actor_poses"][role], candidate["actor_poses"][role], rtol=0.0, atol=position_atol):
                failures.append(f"actor_pose:{role}")
    if reference.get("metadata") != candidate.get("metadata"):
        failures.append("metadata")
    return {"equivalent": not failures, "failures": failures, "reference_sha256": reference.get("anchor_sha256"), "candidate_sha256": candidate.get("anchor_sha256")}
