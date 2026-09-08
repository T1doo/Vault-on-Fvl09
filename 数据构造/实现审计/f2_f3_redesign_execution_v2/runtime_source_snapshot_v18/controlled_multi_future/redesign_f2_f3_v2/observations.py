"""Action-before-observation capture and readback for v2 cells."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from .canonical import atomic_write_json, canonical_sha256


MODEL_CAMERAS = ("head_camera", "left_camera", "right_camera", "front_camera")


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
            if name == "front_camera":
                continue
            raise ValueError(f"required model camera missing: {name}")
        image = np.asarray(available[name]["rgb"])
        if image.ndim != 3 or image.shape[-1] != 3 or image.dtype != np.uint8:
            raise ValueError(f"camera {name} is not rectangular uint8 RGB")
        images[name] = np.ascontiguousarray(image)
        metadata[name] = {"shape": list(image.shape), "dtype": str(image.dtype), "sha256": _sha_bytes(image.tobytes())}
    if not images:
        raise ValueError("no model RGB cameras captured")
    return images, metadata


def _state(scene: Any) -> dict[str, Any]:
    entity = scene.robot.left_entity
    qpos = np.asarray(entity.get_qpos(), dtype=np.float64)
    qvel = np.asarray(entity.get_qvel(), dtype=np.float64)
    if qpos.shape != (38,) or qvel.shape != (38,):
        raise ValueError("model state must be exactly 38qpos+38qvel")
    roles = {role: _pose(actor) for role, actor in scene.role_actors.items()}
    state = {
        "joint_qpos": qpos.tolist(), "joint_qvel": qvel.tolist(),
        "eef_pose": np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64).tolist(),
        "gripper_command": np.asarray(scene.robot.get_normal_real_gripper_val(), dtype=np.float64).tolist(),
        "role_object_pose": roles,
    }
    state["state76_sha256"] = _sha_bytes(np.concatenate([qpos, qvel]).tobytes())
    return state


def _camera_config(scene: Any) -> dict[str, Any]:
    config = scene.cameras.get_config()
    result = {}
    for name, value in config.items():
        result[name] = {key: np.asarray(item).tolist() for key, item in value.items()}
    return result


def capture_t0(*, scene: Any, output: Path, root_id: str, cell_key: str, spec: dict[str, Any], trace_row: dict[str, Any] | None = None) -> dict[str, Any]:
    """Capture one model-visible t0 before any action and read it back."""
    output.mkdir(parents=True, exist_ok=False)
    images, image_meta = _capture_images(scene)
    state = _state(scene)
    metadata = {
        "schema_version": "cmf_f2_f3_t0_capture_metadata_v2",
        "root_id": root_id, "cell_key": cell_key, "step_index": 0, "sim_time_seconds": 0.0,
        "capture_order": "render_update_then_camera_picture_then_rgb_then_state_without_physics_step",
        "camera_names": sorted(images), "camera_images": image_meta, "camera_config": _camera_config(scene),
        "scene_spec_sha256": spec["spec_sha256"], "state_sha256": state["state76_sha256"],
    }
    if trace_row is not None:
        q = np.asarray(trace_row["joint_qpos"], dtype=float); v = np.asarray(trace_row["joint_qvel"], dtype=float)
        metadata["trace_row0_matches_state"] = bool(np.array_equal(q, np.asarray(state["joint_qpos"])) and np.array_equal(v, np.asarray(state["joint_qvel"])))
        if not metadata["trace_row0_matches_state"]:
            raise ValueError("t0 image/state is not aligned with trace row0")
    rgb_path = output / "rgb.npz"
    np.savez_compressed(rgb_path, **{f"{name}__rgb": image for name, image in images.items()})
    state_path = output / "state.json"
    atomic_write_json(state_path, state)
    metadata["rgb_npz_sha256"] = _sha_bytes(rgb_path.read_bytes())
    metadata["state_json_sha256"] = _sha_bytes(state_path.read_bytes())
    metadata["capture_metadata_sha256"] = canonical_sha256(metadata)
    atomic_write_json(output / "capture_metadata.json", metadata)
    readback = read_bundle(output)
    if readback["metadata"]["capture_metadata_sha256"] != metadata["capture_metadata_sha256"]:
        raise ValueError("t0 metadata readback hash mismatch")
    return {"path": str(output), "metadata": metadata, "state": state, "readback": readback["checks"]}


def read_bundle(path: Path) -> dict[str, Any]:
    metadata = json.loads((path / "capture_metadata.json").read_text(encoding="utf-8"))
    state = json.loads((path / "state.json").read_text(encoding="utf-8"))
    with np.load(path / "rgb.npz", allow_pickle=False) as arrays:
        images = {key: arrays[key].copy() for key in arrays.files}
    metadata_without_hash = dict(metadata)
    stored_metadata_hash = metadata_without_hash.pop("capture_metadata_sha256", None)
    checks = {
        "metadata_exists": True,
        "state_76": len(state["joint_qpos"]) == 38 and len(state["joint_qvel"]) == 38,
        "rgb_present": bool(images),
        "rgb_uint8_rectangular": all(v.ndim == 3 and v.shape[-1] == 3 and v.dtype == np.uint8 for v in images.values()),
        "rgb_hashes_match": all(metadata["camera_images"][key.removesuffix("__rgb")]["sha256"] == _sha_bytes(value.tobytes()) for key, value in images.items()),
        "state_hash_match": metadata["state_sha256"] == state["state76_sha256"],
        "metadata_hash_match": stored_metadata_hash == canonical_sha256(metadata_without_hash),
        "no_target_in_model_capture": "target" not in state and "target" not in metadata,
    }
    checks["pass"] = all(checks.values())
    return {"metadata": metadata, "state": state, "images": images, "checks": checks}


def model_envelopes(*, bundle: dict[str, Any], future: np.ndarray, candidates: list[dict[str, Any]], target: dict[str, Any]) -> dict[str, Any]:
    """Return separate inputs/supervision/audit envelopes; target is excluded from inputs."""
    if future.ndim != 2 or future.shape[1] != 26:
        raise ValueError("future must be [N,26]")
    inputs = {"rgb": {key.removesuffix("__rgb"): value for key, value in bundle["images"].items()}, "state": np.r_[bundle["state"]["joint_qpos"], bundle["state"]["joint_qvel"]], "future": future[1:].copy(), "candidate_set": candidates}
    supervision = {"target": target}
    audit = {"capture_metadata": bundle["metadata"], "source": "audit-only"}
    if "target" in inputs:
        raise ValueError("target leaked into model inputs")
    return {"inputs": inputs, "supervision": supervision, "audit": audit}
