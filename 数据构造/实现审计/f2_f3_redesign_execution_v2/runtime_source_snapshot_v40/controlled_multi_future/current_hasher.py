"""Deterministic hashes for model-visible current and hidden physical context."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

import numpy as np

from .canonical_artifact import (
    canonical_hash_json,
    canonical_json_bytes,
    canonical_jsonable,
)


CURRENT_CONTEXT_SCHEMA_VERSION = "current_context_hash_v2"


class SameCurrentMismatch(ValueError):
    """Structured fail-closed mismatch preserving component-level hashes."""

    def __init__(self, message: str, receipt: Mapping[str, Any]):
        super().__init__(message)
        self.receipt = dict(receipt)


def _same_current_mismatch_receipt(
    reference: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    failure_code: str,
) -> dict:
    component_groups = (
        "model_visible_components",
        "reconstruction_spec_components",
    )
    component_differences = {}
    for group in component_groups:
        left = reference.get(group)
        right = candidate.get(group)
        if isinstance(left, Mapping) and isinstance(right, Mapping):
            keys = sorted(set(left) | set(right))
            differences = {
                key: {
                    "reference": left.get(key),
                    "candidate": right.get(key),
                }
                for key in keys
                if left.get(key) != right.get(key)
            }
            if differences:
                component_differences[group] = differences
    receipt = {
        "schema_version": "cmf_same_current_mismatch_receipt_v1",
        "formal_data": False,
        "stage0_data": False,
        "failure_code": failure_code,
        "reference_schema_version": reference.get("schema_version"),
        "candidate_schema_version": candidate.get("schema_version"),
        "reference_hashes": {
            key: reference.get(key)
            for key in (
                "aggregate_sha256",
                "model_visible_aggregate_sha256",
                "hidden_physical_aggregate_sha256",
                "reconstruction_spec_aggregate_sha256",
            )
        },
        "candidate_hashes": {
            key: candidate.get(key)
            for key in (
                "aggregate_sha256",
                "model_visible_aggregate_sha256",
                "hidden_physical_aggregate_sha256",
                "reconstruction_spec_aggregate_sha256",
            )
        },
        "reference_reconstruction_spec_audit": reference.get(
            "reconstruction_spec_audit"
        ),
        "candidate_reconstruction_spec_audit": candidate.get(
            "reconstruction_spec_audit"
        ),
        "component_differences": component_differences,
        "pass": False,
    }
    receipt["receipt_sha256"] = hash_json(receipt)
    return receipt
CAMERA_REQUIRED_FIELDS = ("resolution", "intrinsics_or_fov", "extrinsics", "mount_link", "near_far")
PHYSICAL_ENTITY_REQUIRED_FIELDS = (
    "role",
    "actor_name",
    "modelname",
    "model_id",
    "visual_asset_hash",
    "collision_asset_hash",
    "scale",
    "static_or_dynamic",
    "mass",
    "friction",
    "collision_mode",
    "pose",
    "linear_velocity",
    "angular_velocity",
    "sleep_state",
)


def _json_bytes(value: Any) -> bytes:
    return canonical_json_bytes(value)


def hash_array(array) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode("ascii"))
    digest.update(_json_bytes(list(value.shape)))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def hash_json(value: Any) -> str:
    return canonical_hash_json(value)


def _jsonable(value: Any) -> Any:
    return canonical_jsonable(value)


def validate_camera_configuration(value: Mapping[str, Any]) -> dict:
    if not isinstance(value, Mapping):
        raise ValueError("camera_configuration must be a mapping")
    camera_names = value.get("camera_names")
    cameras = value.get("cameras")
    if not isinstance(camera_names, (list, tuple)) or not camera_names:
        raise ValueError("camera_configuration.camera_names must be non-empty")
    if len(set(camera_names)) != len(camera_names) or not all(isinstance(name, str) and name for name in camera_names):
        raise ValueError("camera names must be unique non-empty strings")
    if not isinstance(cameras, Mapping) or set(cameras) != set(camera_names):
        raise ValueError("camera_configuration.cameras must match camera_names exactly")
    normalized_cameras = {}
    for name in sorted(camera_names):
        item = cameras[name]
        if not isinstance(item, Mapping):
            raise ValueError(f"camera {name} configuration must be a mapping")
        missing = [field for field in CAMERA_REQUIRED_FIELDS if field not in item]
        if missing:
            raise ValueError(f"camera {name} configuration missing {missing}")
        resolution = np.asarray(item["resolution"], dtype=np.int64).reshape(2)
        if np.any(resolution <= 0):
            raise ValueError(f"camera {name} resolution must be positive")
        near_far = np.asarray(item["near_far"], dtype=np.float64).reshape(2)
        if not (0 < near_far[0] < near_far[1]):
            raise ValueError(f"camera {name} near/far must be ordered and positive")
        normalized = {field: _jsonable(item[field]) for field in CAMERA_REQUIRED_FIELDS}
        normalized["resolution"] = resolution.tolist()
        normalized["near_far"] = near_far.tolist()
        if "field_sources" in item:
            if not isinstance(item["field_sources"], Mapping):
                raise ValueError(f"camera {name} field_sources must be a mapping")
            normalized["field_sources"] = _jsonable(item["field_sources"])
        normalized_cameras[name] = normalized
    renderer_version = value.get("renderer_version")
    if not isinstance(renderer_version, str) or not renderer_version:
        raise ValueError("camera configuration requires renderer_version")
    render_settings = value.get("render_settings")
    if not isinstance(render_settings, Mapping):
        raise ValueError("camera configuration requires render_settings")
    normalized = {
        "camera_names": sorted(camera_names),
        "cameras": normalized_cameras,
        "renderer_version": renderer_version,
        "render_settings": _jsonable(render_settings),
    }
    for field in ("renderer_version_source", "render_settings_source"):
        if field in value:
            normalized[field] = _jsonable(value[field])
    return normalized


def validate_physical_entities(value: Mapping[str, Mapping[str, Any]]) -> dict:
    if not isinstance(value, Mapping) or not value:
        raise ValueError("physical_entities must be a non-empty role mapping")
    normalized = {}
    for role in sorted(value):
        item = value[role]
        if not isinstance(item, Mapping):
            raise ValueError(f"physical entity {role} must be a mapping")
        missing = [field for field in PHYSICAL_ENTITY_REQUIRED_FIELDS if field not in item]
        if missing:
            raise ValueError(f"physical entity {role} missing {missing}")
        if item["role"] != role:
            raise ValueError(f"physical entity role mismatch for {role}")
        if item["static_or_dynamic"] not in ("static", "dynamic", "kinematic"):
            raise ValueError(f"physical entity {role} has invalid body type")
        pose = np.asarray(item["pose"], dtype=np.float64).reshape(7)
        linear_velocity = np.asarray(item["linear_velocity"], dtype=np.float64).reshape(3)
        angular_velocity = np.asarray(item["angular_velocity"], dtype=np.float64).reshape(3)
        scale = np.asarray(item["scale"], dtype=np.float64).reshape(-1)
        if scale.size not in (1, 3) or np.any(scale <= 0):
            raise ValueError(f"physical entity {role} has invalid scale")
        normalized_item = {field: _jsonable(item[field]) for field in PHYSICAL_ENTITY_REQUIRED_FIELDS}
        normalized_item.update(
            {
                "pose": pose.tolist(),
                "linear_velocity": linear_velocity.tolist(),
                "angular_velocity": angular_velocity.tolist(),
                "scale": scale.tolist(),
            }
        )
        for field in (
            "mass_source",
            "friction_source",
            "procedural_asset_spec_sha256",
            "procedural_creation",
            "velocity_source",
        ):
            if field in item:
                normalized_item[field] = _jsonable(item[field])
        normalized[role] = normalized_item
    return normalized


def build_current_hashes_v2(
    *,
    head_rgb,
    wrist_rgb: Mapping[str, Any],
    model_visible_robot_state,
    gripper_actual_state,
    visible_object_roles: Mapping[str, Any],
    camera_configuration: Mapping[str, Any],
    physical_entities: Mapping[str, Mapping[str, Any]],
    scene_seed: int,
    generator_version: str,
    simulation_configuration: Mapping[str, Any],
    source_commit: str,
) -> dict:
    """Hash visible model inputs separately from verifier-only physical state."""

    if set(wrist_rgb) != {"left", "right"}:
        raise ValueError("same-current hashing requires both left and right wrist RGB")
    if not isinstance(visible_object_roles, Mapping) or not visible_object_roles:
        raise ValueError("visible_object_roles must be a non-empty mapping")
    if not isinstance(generator_version, str) or not generator_version:
        raise ValueError("generator_version must be non-empty")
    if not isinstance(source_commit, str) or not source_commit:
        raise ValueError("source_commit must be non-empty")
    camera = validate_camera_configuration(camera_configuration)
    entities = validate_physical_entities(physical_entities)
    if not isinstance(simulation_configuration, Mapping):
        raise ValueError("simulation_configuration must be a mapping")

    model_visible_components = {
        "head_rgb_sha256": hash_array(head_rgb),
        "wrist_rgb_sha256": {name: hash_array(wrist_rgb[name]) for name in sorted(wrist_rgb)},
        "robot_state_sha256": hash_array(model_visible_robot_state),
        "gripper_actual_state_sha256": hash_array(gripper_actual_state),
        "visible_object_roles_sha256": hash_json(_jsonable(visible_object_roles)),
        "camera_configuration_sha256": hash_json(camera),
    }
    hidden_physical_components = {
        "physical_entities_state_sha256": hash_json(entities),
    }
    reconstruction_spec_components = {
        "simulation_configuration_sha256": hash_json(_jsonable(simulation_configuration)),
        "scene_spec_sha256": hash_json(
            {
                "scene_seed": int(scene_seed),
                "generator_version": generator_version,
                "source_commit": source_commit,
            }
        ),
    }
    result = {
        "schema_version": CURRENT_CONTEXT_SCHEMA_VERSION,
        "model_visible_components": model_visible_components,
        "model_visible_aggregate_sha256": hash_json(model_visible_components),
        "hidden_physical_components": hidden_physical_components,
        "hidden_physical_aggregate_sha256": hash_json(hidden_physical_components),
        "reconstruction_spec_components": reconstruction_spec_components,
        "reconstruction_spec_aggregate_sha256": hash_json(reconstruction_spec_components),
        "reconstruction_spec_audit": {
            "scene_seed": int(scene_seed),
            "generator_version": generator_version,
            "source_commit": source_commit,
            "simulation_configuration": _jsonable(
                simulation_configuration
            ),
        },
        "model_input_allows_hidden_physical_components": False,
    }
    result["aggregate_sha256"] = hash_json(
        {
            "model_visible": result["model_visible_aggregate_sha256"],
            "reconstruction_spec": result["reconstruction_spec_aggregate_sha256"],
        }
    )
    result["audit_full_aggregate_sha256"] = hash_json(
        {
            "same_current": result["aggregate_sha256"],
            "hidden_physical_state": result["hidden_physical_aggregate_sha256"],
        }
    )
    return result


def build_current_hashes(
    *,
    head_rgb,
    wrist_rgb: Mapping[str, Any],
    robot_state,
    gripper_actual_state,
    object_role_layout: Mapping[str, Any],
    camera_config_version: str,
    scene_seed: int,
    generator_version: str,
) -> dict:
    if set(wrist_rgb) != {"left", "right"}:
        raise ValueError("same-current hashing requires both left and right wrist RGB")
    if not isinstance(camera_config_version, str) or not camera_config_version:
        raise ValueError("camera_config_version must be a non-empty string")
    components = {
        "head_rgb_sha256": hash_array(head_rgb),
        "wrist_rgb_sha256": {name: hash_array(wrist_rgb[name]) for name in sorted(wrist_rgb)},
        "robot_state_sha256": hash_array(robot_state),
        "gripper_actual_state_sha256": hash_array(gripper_actual_state),
        "object_role_layout_sha256": hash_json(object_role_layout),
        "camera_config_version_sha256": hash_json(camera_config_version),
        "scene_spec_sha256": hash_json({"scene_seed": int(scene_seed), "generator_version": generator_version}),
    }
    return {"components": components, "aggregate_sha256": hash_json(components)}


def require_same_current(reference: Mapping[str, Any], candidate: Mapping[str, Any]) -> None:
    if reference.get("schema_version") == CURRENT_CONTEXT_SCHEMA_VERSION or candidate.get("schema_version") == CURRENT_CONTEXT_SCHEMA_VERSION:
        if reference.get("schema_version") != candidate.get("schema_version"):
            message = "fresh reconstruction changed current hash schema"
            raise SameCurrentMismatch(
                message,
                _same_current_mismatch_receipt(
                    reference, candidate, failure_code="current_hash_schema_mismatch"
                ),
            )
        for key in ("model_visible_aggregate_sha256", "reconstruction_spec_aggregate_sha256"):
            if reference.get(key) != candidate.get(key):
                message = f"fresh reconstruction failed same-current {key}"
                raise SameCurrentMismatch(
                    message,
                    _same_current_mismatch_receipt(
                        reference,
                        candidate,
                        failure_code=f"same_current_{key}_mismatch",
                    ),
                )
        return
    if reference.get("aggregate_sha256") != candidate.get("aggregate_sha256"):
        message = "fresh reconstruction failed same-current aggregate hash"
        raise SameCurrentMismatch(
            message,
            _same_current_mismatch_receipt(
                reference, candidate, failure_code="legacy_current_aggregate_mismatch"
            ),
        )
