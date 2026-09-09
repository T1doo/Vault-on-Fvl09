"""Action-before-observation capture and readback for v2 cells."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from .canonical import atomic_write_json, canonical_sha256


MODEL_CAMERAS = ("front_camera", "head_camera", "left_camera", "right_camera")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _pose(actor: Any) -> list[float]:
    p = actor.get_pose()
    return [float(x) for x in (*p.p, *p.q)]


def _native(actor: Any) -> Any:
    return actor.actor if hasattr(actor, "actor") else actor


def _capture_images(scene: Any) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    if not hasattr(scene, "cameras"):
        raise ValueError("scene has no camera registry")
    scene._update_render()
    scene.cameras.update_picture()
    available = scene.cameras.get_rgb()
    images: dict[str, np.ndarray] = {}
    metadata: dict[str, Any] = {}
    for name in MODEL_CAMERAS:
        if name not in available:
            raise ValueError(f"required model camera missing: {name}")
        image = np.asarray(available[name]["rgb"])
        if image.ndim != 3 or image.shape[-1] != 3 or image.dtype != np.uint8:
            raise ValueError(f"camera {name} is not rectangular uint8 RGB")
        images[name] = np.ascontiguousarray(image)
        metadata[name] = {"shape": list(image.shape), "dtype": str(image.dtype), "sha256": _sha_bytes(image.tobytes())}
    if not images:
        raise ValueError("no model RGB cameras captured")
    return images, metadata


def _drive_values(joints: Any, method: str) -> list[float]:
    values = []
    for item in joints:
        joint = item[0] if isinstance(item, (tuple, list)) else item
        value = getattr(joint, method)()
        values.extend(np.asarray(value, dtype=np.float64).reshape(-1).tolist())
    return values


def _component_vector(actor: Any, name: str) -> tuple[list[float] | None, bool]:
    native = _native(actor)
    for component in getattr(native, "get_components", lambda: [])():
        if not hasattr(component, name):
            continue
        try:
            value = getattr(component, name)
            value = value() if callable(value) else value
            return np.asarray(value, dtype=np.float64).reshape(-1).tolist(), True
        except BaseException:
            return None, False
    return None, False


def _state(scene: Any) -> dict[str, Any]:
    entity = scene.robot.left_entity
    qpos = np.asarray(entity.get_qpos(), dtype=np.float64)
    qvel = np.asarray(entity.get_qvel(), dtype=np.float64)
    if qpos.shape != (38,) or qvel.shape != (38,):
        raise ValueError("model state must be exactly 38qpos+38qvel")
    roles = {role: _pose(actor) for role, actor in scene.role_actors.items()}
    role_linear_velocity = {}
    role_angular_velocity = {}
    role_velocity_available = {}
    for role, actor in scene.role_actors.items():
        linear, linear_ok = _component_vector(actor, "linear_velocity")
        angular, angular_ok = _component_vector(actor, "angular_velocity")
        role_linear_velocity[role] = linear
        role_angular_velocity[role] = angular
        role_velocity_available[role] = {"linear": linear_ok, "angular": angular_ok}
    qf = np.asarray(entity.get_qf(), dtype=np.float64)
    state = {
        "joint_qpos": qpos.tolist(), "joint_qvel": qvel.tolist(),
        "joint_qf": qf.tolist(),
        "eef_pose": np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64).tolist(),
        "gripper_command": np.asarray(scene.robot.get_normal_real_gripper_val(), dtype=np.float64).tolist(),
        "left_gripper_drive_target": _drive_values(scene.robot.left_gripper, "get_drive_target"),
        "right_gripper_drive_target": _drive_values(scene.robot.right_gripper, "get_drive_target"),
        "left_gripper_drive_velocity_target": _drive_values(scene.robot.left_gripper, "get_drive_velocity_target"),
        "right_gripper_drive_velocity_target": _drive_values(scene.robot.right_gripper, "get_drive_velocity_target"),
        "role_object_pose": roles,
        "role_object_linear_velocity": role_linear_velocity,
        "role_object_angular_velocity": role_angular_velocity,
        "role_velocity_available": role_velocity_available,
    }
    state["state76_sha256"] = _sha_bytes(np.concatenate([qpos, qvel]).tobytes())
    return state


def _camera_config(scene: Any) -> dict[str, Any]:
    config = scene.cameras.get_config()
    result = {}
    for name, value in config.items():
        result[name] = {key: np.asarray(item).tolist() for key, item in value.items()}
    return result


def capture_t0(*, scene: Any, output: Path, root_id: str, cell_key: str, spec: dict[str, Any], rest_target: list[float] | None = None, trace_row: dict[str, Any] | None = None) -> dict[str, Any]:
    """Capture one model-visible t0 before any action and read it back."""
    output.mkdir(parents=True, exist_ok=False)
    images, image_meta = _capture_images(scene)
    state = _state(scene)
    metadata = {
        "schema_version": "cmf_f2_f3_t0_capture_metadata_v2",
        "root_id": root_id, "cell_key": cell_key, "step_index": 0, "sim_time_seconds": 0.0,
        "capture_order": "render_update_then_camera_picture_then_rgb_then_state_without_physics_step",
        "camera_names": sorted(images), "camera_images": image_meta, "camera_config": _camera_config(scene),
        "scene_spec_sha256": spec["spec_sha256"], "scene_spec": spec, "state_sha256": state["state76_sha256"],
        "rest_target": rest_target, "rest_target_source": spec.get("f3", {}).get("rest_source") if spec["family"] == "F3" else None,
        "fresh_reconstruction": {"scene_class": type(scene).__name__, "setup_completed_before_t0": True, "capture_before_first_action": True},
    }
    if trace_row is not None:
        q = np.asarray(trace_row["joint_qpos"], dtype=float); v = np.asarray(trace_row["joint_qvel"], dtype=float)
        row_eef = trace_row.get("eef", trace_row.get("eef_pose"))
        row_gripper = trace_row.get("gripper_command")
        role_rows = trace_row.get("role_actor_poses", {})
        matches = {
            "joint_qpos": bool(np.array_equal(q, np.asarray(state["joint_qpos"]))),
            "joint_qvel": bool(np.array_equal(v, np.asarray(state["joint_qvel"]))),
            "eef_pose": row_eef is None or bool(np.array_equal(np.asarray(row_eef), np.asarray(state["eef_pose"]))),
            "gripper_command": row_gripper is None or bool(np.array_equal(np.asarray(row_gripper), np.asarray(state["gripper_command"]))),
            "role_object_pose": not role_rows or all(role in state["role_object_pose"] and np.array_equal(np.asarray(value), np.asarray(state["role_object_pose"][role])) for role, value in role_rows.items()),
        }
        metadata["trace_row0_matches_state"] = matches
        if not all(matches.values()):
            raise ValueError(f"t0 observation/state is not aligned with trace row0: {matches}")
    rgb_path = output / "rgb.npz"
    np.savez_compressed(rgb_path, **{f"{name}__rgb": image for name, image in images.items()})
    state_path = output / "state.json"
    atomic_write_json(state_path, state)
    anchor = {
        "schema_version": "cmf_f2_f3_anchor_bundle_v2",
        "state": state,
        "scene_spec": spec,
        "asset_spec": getattr(scene, "_cmf_redesign_asset_spec", None),
        "box_contract": getattr(scene, "_cmf_f2_box_contract", None),
        "runtime_actor_info": scene.runtime_actor_info() if hasattr(scene, "runtime_actor_info") else None,
        "camera_config": metadata["camera_config"],
        "rest_target": rest_target,
        "fresh_reconstruction": metadata["fresh_reconstruction"],
    }
    anchor_path = output / "anchor.json"
    atomic_write_json(anchor_path, anchor)
    metadata["rgb_npz_sha256"] = _sha_bytes(rgb_path.read_bytes())
    metadata["state_json_sha256"] = _sha_bytes(state_path.read_bytes())
    metadata["anchor_json_sha256"] = _sha_bytes(anchor_path.read_bytes())
    metadata["capture_metadata_sha256"] = canonical_sha256(metadata)
    atomic_write_json(output / "capture_metadata.json", metadata)
    readback = read_bundle(output)
    if not readback["checks"]["pass"]:
        raise ValueError(f"t0 readback failed: {readback['checks']}")
    return {"path": str(output), "metadata": metadata, "state": state, "readback": readback["checks"]}


def read_bundle(path: Path) -> dict[str, Any]:
    metadata = json.loads((path / "capture_metadata.json").read_text(encoding="utf-8"))
    state = json.loads((path / "state.json").read_text(encoding="utf-8"))
    anchor = json.loads((path / "anchor.json").read_text(encoding="utf-8"))
    with np.load(path / "rgb.npz", allow_pickle=False) as arrays:
        images = {key: arrays[key].copy() for key in arrays.files}
    metadata_without_hash = dict(metadata)
    stored_metadata_hash = metadata_without_hash.pop("capture_metadata_sha256", None)
    role_pose_values = [np.asarray(value, dtype=float) for value in state.get("role_object_pose", {}).values()]
    role_velocity_values = [np.asarray(value, dtype=float) for value in state.get("role_object_linear_velocity", {}).values() if value is not None]
    role_angular_values = [np.asarray(value, dtype=float) for value in state.get("role_object_angular_velocity", {}).values() if value is not None]
    checks = {
        "metadata_exists": True,
        "state_76": len(state["joint_qpos"]) == 38 and len(state["joint_qvel"]) == 38,
        "state_finite": bool(np.isfinite(np.asarray(state["joint_qpos"], dtype=float)).all() and np.isfinite(np.asarray(state["joint_qvel"], dtype=float)).all()),
        "anchor_role_poses_finite": all(np.isfinite(value).all() for value in role_pose_values),
        "anchor_role_velocities_finite": all(np.isfinite(value).all() for value in role_velocity_values),
        "anchor_role_angular_velocities_finite": all(np.isfinite(value).all() for value in role_angular_values),
        "anchor_drive_state_present": all(key in state for key in ("joint_qf", "left_gripper_drive_target", "right_gripper_drive_target", "left_gripper_drive_velocity_target", "right_gripper_drive_velocity_target")),
        "rgb_present": bool(images),
        "rgb_uint8_rectangular": all(v.ndim == 3 and v.shape[-1] == 3 and v.dtype == np.uint8 for v in images.values()),
        "rgb_camera_set": set(metadata.get("camera_names", [])) == {key.removesuffix("__rgb") for key in images},
        "rgb_hashes_match": all(metadata["camera_images"].get(key.removesuffix("__rgb"), {}).get("sha256") == _sha_bytes(value.tobytes()) for key, value in images.items()),
        "rgb_file_hash_match": metadata.get("rgb_npz_sha256") == _sha_bytes((path / "rgb.npz").read_bytes()),
        "state_hash_match": metadata["state_sha256"] == _sha_bytes(np.concatenate([np.asarray(state["joint_qpos"], dtype=np.float64), np.asarray(state["joint_qvel"], dtype=np.float64)]).tobytes()) == state["state76_sha256"],
        "state_file_hash_match": metadata.get("state_json_sha256") == _sha_bytes((path / "state.json").read_bytes()),
        "metadata_hash_match": stored_metadata_hash == canonical_sha256(metadata_without_hash),
        "anchor_exists": bool(anchor.get("schema_version") == "cmf_f2_f3_anchor_bundle_v2"),
        "anchor_file_hash_match": metadata.get("anchor_json_sha256") == _sha_bytes((path / "anchor.json").read_bytes()),
        "anchor_state_matches": anchor.get("state") == state,
        "no_target_in_model_capture": "target" not in state and "target" not in metadata and "target" not in anchor,
    }
    checks["pass"] = all(checks.values())
    return {"metadata": metadata, "state": state, "images": images, "checks": checks}


def model_envelopes(*, bundle: dict[str, Any], future: np.ndarray, candidates: list[dict[str, Any]], target: dict[str, Any]) -> dict[str, Any]:
    """Return fixed-array inputs plus separate supervision and audit envelopes."""
    if not bundle.get("checks", {}).get("pass", True):
        raise ValueError("cannot export a bundle that failed its disk readback checks")
    if future.ndim != 2 or future.shape[1] != 26 or future.shape[0] < 2:
        raise ValueError("future must be [N,26]")
    rgb = {name: np.ascontiguousarray(bundle["images"][f"{name}__rgb"] if f"{name}__rgb" in bundle["images"] else bundle["images"][name]) for name in MODEL_CAMERAS if f"{name}__rgb" in bundle["images"] or name in bundle["images"]}
    if tuple(rgb) != tuple(name for name in MODEL_CAMERAS if f"{name}__rgb" in bundle["images"] or name in bundle["images"]):
        raise ValueError("camera order is not deterministic")
    inputs = {"rgb": rgb, "state": np.ascontiguousarray(np.r_[bundle["state"]["joint_qpos"], bundle["state"]["joint_qvel"]], dtype=np.float64), "future": np.ascontiguousarray(future[1:], dtype=np.float64), "candidate_set": candidates}
    supervision = {"target": target}
    audit = {"capture_metadata": bundle["metadata"], "source": "audit-only", "interface": "cmf_numpy_observable_inputs_v1", "camera_order": list(rgb), "future_row0_removed_once": True}
    if "target" in inputs:
        raise ValueError("target leaked into model inputs")
    from .strict_exit import validate_numpy_observable_inputs
    validate_numpy_observable_inputs(inputs)
    return {"inputs": inputs, "supervision": supervision, "audit": audit}
