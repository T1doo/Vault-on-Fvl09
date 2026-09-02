"""Audited RoboTwin official raw grasp-pose generation.

Callers do not supply one arbitrary pregrasp/grasp pair.  This helper reads the
actor contact matrix, invokes the official ten-rotation target-list generator,
derives all ten grasp endpoints, and emits a recipe-bound receipt.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np
from scipy.spatial.transform import Rotation

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .geometry import pose_matrix


SCHEMA_VERSION = "cmf_official_raw_pose_generation_v1"
OFFICIAL_GENERATOR_VERSION = (
    "RoboTwin_Base_Task_get_grasp_pose_plus_Robot_create_target_pose_list_ROTATE_NUM_10"
)
ROTATION_CANDIDATE_COUNT = 10


def _pose7(value: Sequence[float], label: str) -> np.ndarray:
    pose = np.asarray(value, dtype=np.float64).reshape(-1)
    if pose.shape != (7,) or not np.all(np.isfinite(pose)):
        raise ValueError(f"{label} must be one finite pose7")
    norm = float(np.linalg.norm(pose[3:]))
    if norm <= 1e-12:
        raise ValueError(f"{label} quaternion norm must be positive")
    pose = pose.copy()
    pose[3:] /= norm
    return pose


def _actor_pose(actor) -> np.ndarray:
    pose = actor.get_pose()
    return _pose7([*pose.p, *pose.q], "runtime actor pose")


def _arm_tag(arm: str):
    from envs.utils.action import ArmTag

    if arm not in ("left", "right"):
        raise ValueError("raw-pose arm must be left or right")
    return ArmTag(arm)


def generate_official_raw_pose_receipt_v1(
    scene,
    actor,
    recipe: Mapping[str, Any],
    *,
    family: str,
) -> dict[str, Any]:
    recipe_value = canonical_jsonable(recipe)
    recipe_key = "recipe_sha256"
    recipe_payload = dict(recipe_value)
    recipe_digest = recipe_payload.pop(recipe_key, None)
    if recipe_digest != canonical_hash_json(recipe_payload):
        raise ValueError("raw-pose recipe hash mismatch")
    arm = str(recipe_value["arm"])
    contact_id = int(recipe_value["official_contact_point_id"])
    rotation_index = int(recipe_value["official_rotation_candidate_index"])
    pregrasp_distance = float(recipe_value["pregrasp_distance_m"])
    target_distance = float(recipe_value.get("target_distance_m", 0.0))
    if rotation_index not in range(ROTATION_CANDIDATE_COUNT):
        raise ValueError("raw-pose rotation index is outside ROTATE_NUM=10")
    contact_matrix = np.asarray(
        actor.get_contact_point(contact_id, "matrix"), dtype=np.float64
    )
    if contact_matrix.shape != (4, 4) or not np.all(np.isfinite(contact_matrix)):
        raise ValueError("official contact matrix is invalid")
    official_frame = contact_matrix @ np.asarray(
        [
            [0.0, 0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0, 0.0],
            [0.0, -1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    rotation = official_frame[:3, :3]
    position = official_frame[:3, 3] + rotation @ np.asarray(
        [-0.12 - pregrasp_distance, 0.0, 0.0], dtype=np.float64
    )
    quat_xyzw = Rotation.from_matrix(rotation).as_quat()
    base_pregrasp = [
        *position.tolist(),
        float(quat_xyzw[3]),
        float(quat_xyzw[0]),
        float(quat_xyzw[1]),
        float(quat_xyzw[2]),
    ]
    center_pose = actor.get_contact_point(contact_id, "list")
    ordered_pregrasps = scene.robot.create_target_pose_list(
        base_pregrasp, center_pose, _arm_tag(arm)
    )
    if not isinstance(ordered_pregrasps, list) or len(ordered_pregrasps) != 10:
        raise ValueError("official raw-pose generator did not return ten rotations")
    ordered = []
    for index, raw_pregrasp in enumerate(ordered_pregrasps):
        pregrasp = _pose7(raw_pregrasp, f"official pregrasp {index}")
        grasp = pregrasp.copy()
        direction = pose_matrix(pregrasp)[:3, :3]
        grasp[:3] += np.asarray(
            [pregrasp_distance - target_distance, 0.0, 0.0],
            dtype=np.float64,
        ) @ np.linalg.inv(direction)
        ordered.append(
            {
                "rotation_candidate_index": index,
                "raw_pregrasp_pose": pregrasp.tolist(),
                "raw_grasp_pose": grasp.tolist(),
                "raw_pregrasp_sha256": canonical_hash_json(pregrasp.tolist()),
                "raw_grasp_sha256": canonical_hash_json(grasp.tolist()),
            }
        )
    selected = ordered[rotation_index]
    actor_pose = _actor_pose(actor)
    value = {
        "schema_version": SCHEMA_VERSION,
        "official_generator_version": OFFICIAL_GENERATOR_VERSION,
        "family": str(family),
        "recipe_id": recipe_value["recipe_id"],
        "recipe_sha256": recipe_digest,
        "asset": canonical_jsonable(recipe_value.get("asset", {})),
        "main_object_model_id": recipe_value.get("main_object_model_id"),
        "arm": arm,
        "contact_point_id": contact_id,
        "rotation_candidate_index": rotation_index,
        "pregrasp_distance_m": pregrasp_distance,
        "target_distance_m": target_distance,
        "actor_pose": actor_pose.tolist(),
        "actor_pose_sha256": canonical_hash_json(actor_pose.tolist()),
        "ordered_rotation_candidate_count": len(ordered),
        "ordered_rotation_candidates_sha256": canonical_hash_json(ordered),
        "selected_raw_pregrasp_pose": selected["raw_pregrasp_pose"],
        "selected_raw_grasp_pose": selected["raw_grasp_pose"],
        "raw_pregrasp_sha256": selected["raw_pregrasp_sha256"],
        "raw_grasp_sha256": selected["raw_grasp_sha256"],
        "source_calls": [
            "actor.get_contact_point(contact_id, matrix/list)",
            "scene.robot.create_target_pose_list(..., ROTATE_NUM=10)",
        ],
        "external_raw_pose_input_allowed": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def validate_official_raw_pose_receipt_v1(
    receipt: Mapping[str, Any],
    recipe: Mapping[str, Any],
    *,
    family: str,
) -> dict[str, Any]:
    value = canonical_jsonable(receipt)
    payload = dict(value)
    digest = payload.pop("receipt_sha256", None)
    recipe_value = canonical_jsonable(recipe)
    checks = {
        "receipt_hash_valid": digest == canonical_hash_json(payload),
        "schema_valid": value.get("schema_version") == SCHEMA_VERSION,
        "generator_version_bound": value.get("official_generator_version")
        == OFFICIAL_GENERATOR_VERSION,
        "family_bound": value.get("family") == family,
        "recipe_bound": value.get("recipe_id") == recipe_value.get("recipe_id")
        and value.get("recipe_sha256") == recipe_value.get("recipe_sha256"),
        "asset_bound": value.get("asset")
        == canonical_jsonable(recipe_value.get("asset", {})),
        "main_object_bound": value.get("main_object_model_id")
        == recipe_value.get("main_object_model_id"),
        "arm_bound": value.get("arm") == recipe_value.get("arm"),
        "contact_bound": value.get("contact_point_id")
        == recipe_value.get("official_contact_point_id"),
        "rotation_bound": value.get("rotation_candidate_index")
        == recipe_value.get("official_rotation_candidate_index"),
        "distance_bound": value.get("pregrasp_distance_m")
        == recipe_value.get("pregrasp_distance_m")
        and value.get("target_distance_m")
        == recipe_value.get("target_distance_m", 0.0),
        "actor_pose_hash_valid": value.get("actor_pose_sha256")
        == canonical_hash_json(value.get("actor_pose")),
        "raw_pose_hashes_valid": value.get("raw_pregrasp_sha256")
        == canonical_hash_json(value.get("selected_raw_pregrasp_pose"))
        and value.get("raw_grasp_sha256")
        == canonical_hash_json(value.get("selected_raw_grasp_pose")),
        "ten_rotation_candidates_bound": value.get(
            "ordered_rotation_candidate_count"
        )
        == ROTATION_CANDIDATE_COUNT,
        "external_raw_pose_forbidden": value.get(
            "external_raw_pose_input_allowed"
        )
        is False,
    }
    result = {
        "schema_version": "cmf_official_raw_pose_receipt_validation_v1",
        "receipt_sha256": digest,
        "recipe_sha256": recipe_value.get("recipe_sha256"),
        "checks": checks,
        "pass": all(checks.values()),
    }
    result["validation_sha256"] = canonical_hash_json(result)
    return result


__all__ = [
    "OFFICIAL_GENERATOR_VERSION",
    "generate_official_raw_pose_receipt_v1",
    "validate_official_raw_pose_receipt_v1",
]
