"""Immutable per-program suffix planner artifact for runtime-v3_3."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .canonical_prefix_artifact_v1 import array_sha256, canonical_json_sha256, file_sha256
from .current_hasher import hash_array, hash_json
from .planner_dtype_v3_2 import normalize_planner_control


SCHEMA_VERSION = "cmf_frozen_suffix_artifact_v1"


def build_frozen_suffix_artifact(
    *,
    root_slot_id: str,
    family: str,
    program_id: str,
    candidate_universe_sha256: str,
    prefix_artifact_sha256: str,
    actual_prefix_end_qpos: Any,
    execution_spec: Mapping[str, Any],
    controls: Sequence[Mapping[str, Any]],
    planner_query_receipts: Sequence[Mapping[str, Any]],
) -> tuple[dict, dict[str, np.ndarray]]:
    targets = execution_spec.get("targets")
    if not isinstance(targets, list) or not targets or len(targets) != len(controls):
        raise ValueError("frozen suffix targets/controls must be nonempty and aligned")
    qpos = np.ascontiguousarray(np.asarray(actual_prefix_end_qpos, dtype=np.float64))
    if execution_spec.get("actual_prefix_end_qpos_sha256") != hash_array(qpos):
        raise ValueError("suffix execution spec start qpos hash mismatch")
    for label, value in (
        ("candidate_universe_sha256", candidate_universe_sha256),
        ("prefix_artifact_sha256", prefix_artifact_sha256),
    ):
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"frozen suffix {label} is invalid")
    if execution_spec.get("program_id") != program_id:
        raise ValueError("suffix execution spec program ID mismatch")
    arrays: dict[str, np.ndarray] = {"actual_prefix_end_qpos": qpos}
    segments = []
    for index, (target, raw_control) in enumerate(zip(targets, controls)):
        control = normalize_planner_control(raw_control)
        if control.get("status") != "Success":
            raise ValueError(f"suffix control {index} is not successful")
        position = np.ascontiguousarray(np.asarray(control["position"], dtype=np.float32))
        velocity = np.ascontiguousarray(np.asarray(control["velocity"], dtype=np.float32))
        if position.ndim != 2 or position.shape[0] < 1 or velocity.shape != position.shape:
            raise ValueError(f"suffix control {index} has invalid position/velocity")
        if not np.all(np.isfinite(position)) or not np.all(np.isfinite(velocity)):
            raise ValueError(f"suffix control {index} contains non-finite values")
        pos_key = f"segment_{index:03d}_position"
        vel_key = f"segment_{index:03d}_velocity"
        arrays[pos_key] = position
        arrays[vel_key] = velocity
        segments.append(
            {
                "segment_index": index,
                "segment_id": target["segment_id"],
                "goal_pose": list(target["pose"]),
                "position_array_key": pos_key,
                "velocity_array_key": vel_key,
                "position_sha256": array_sha256(position),
                "velocity_sha256": array_sha256(velocity),
                "control_step_count": int(position.shape[0]),
                "planner_query": json.loads(
                    json.dumps(raw_control.get("_cmf_planner_query"), sort_keys=True)
                )
                if isinstance(raw_control, Mapping)
                and isinstance(raw_control.get("_cmf_planner_query"), Mapping)
                else None,
            }
        )
    public_spec = json.loads(json.dumps(execution_spec, ensure_ascii=False, sort_keys=True))
    public_spec.pop("control_cache_key", None)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_3",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "root_slot_id": root_slot_id,
        "family": family,
        "program_id": program_id,
        "candidate_universe_sha256": candidate_universe_sha256,
        "prefix_artifact_sha256": prefix_artifact_sha256,
        "actual_prefix_end_qpos_sha256": hash_array(qpos),
        "execution_spec": public_spec,
        "execution_spec_sha256": hash_json(public_spec),
        "planner_query_receipts": json.loads(
            json.dumps(planner_query_receipts, ensure_ascii=False, sort_keys=True)
        ),
        "segments": segments,
        "array_hashes": {key: array_sha256(value) for key, value in arrays.items()},
        "arrays_file": "suffix_controls.npz",
    }
    manifest["artifact_sha256"] = canonical_json_sha256(manifest)
    return manifest, arrays


def validate_frozen_suffix_artifact(
    manifest: Mapping[str, Any], arrays: Mapping[str, Any]
) -> tuple[dict, dict[str, np.ndarray], list[dict]]:
    if not isinstance(manifest, Mapping) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("frozen suffix artifact schema mismatch")
    value = json.loads(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    expected_hash = value.pop("artifact_sha256", None)
    value.pop("arrays_file_sha256", None)
    if not isinstance(expected_hash, str) or canonical_json_sha256(value) != expected_hash:
        raise ValueError("frozen suffix artifact hash mismatch")
    if manifest.get("formal_data") is not False or manifest.get("stage0_data") is not False:
        raise ValueError("frozen suffix artifact must remain nonformal")
    if manifest.get("stage0_authorized") is not False:
        raise ValueError("frozen suffix artifact cannot authorize Stage 0")
    for key in ("candidate_universe_sha256", "prefix_artifact_sha256"):
        if not isinstance(manifest.get(key), str) or len(manifest[key]) != 64:
            raise ValueError(f"frozen suffix {key} is invalid")
    normalized = {
        key: np.ascontiguousarray(np.asarray(item)) for key, item in arrays.items()
    }
    expected_array_hashes = {
        key: array_sha256(item) for key, item in normalized.items()
    }
    if manifest.get("array_hashes") != expected_array_hashes:
        raise ValueError("frozen suffix array hash mismatch")
    qpos = np.asarray(normalized.get("actual_prefix_end_qpos"), dtype=np.float64)
    if hash_array(qpos) != manifest.get("actual_prefix_end_qpos_sha256"):
        raise ValueError("frozen suffix start qpos hash mismatch")
    spec = manifest.get("execution_spec", {})
    if spec.get("program_id") != manifest.get("program_id"):
        raise ValueError("frozen suffix program linkage mismatch")
    if spec.get("actual_prefix_end_qpos_sha256") != manifest.get(
        "actual_prefix_end_qpos_sha256"
    ):
        raise ValueError("frozen suffix execution-spec qpos linkage mismatch")
    segment_receipts = spec.get("segment_receipts")
    if not isinstance(segment_receipts, list) or len(segment_receipts) != len(
        manifest.get("segments", [])
    ):
        raise ValueError("frozen suffix segment receipts are misaligned")
    execution_transforms = spec.get("execution_control_transforms", [])
    if not isinstance(execution_transforms, list):
        raise ValueError("frozen suffix execution transforms must be a list")
    transform_by_segment = {}
    if execution_transforms:
        from .f3_return_release_v5 import (
            validate_f3_return_control_transform_receipt,
        )

        for transform in execution_transforms:
            validated_transform = validate_f3_return_control_transform_receipt(
                transform
            )
            segment_id = validated_transform["segment_id"]
            if segment_id in transform_by_segment:
                raise ValueError("duplicate frozen suffix execution transform")
            transform_by_segment[segment_id] = validated_transform
    controls = []
    for index, segment in enumerate(manifest.get("segments", [])):
        position = np.asarray(normalized[segment["position_array_key"]], dtype=np.float32)
        velocity = np.asarray(normalized[segment["velocity_array_key"]], dtype=np.float32)
        if array_sha256(position) != segment["position_sha256"]:
            raise ValueError("frozen suffix position segment hash mismatch")
        if array_sha256(velocity) != segment["velocity_sha256"]:
            raise ValueError("frozen suffix velocity segment hash mismatch")
        receipt = segment_receipts[index]
        if (
            receipt.get("segment_id") != segment.get("segment_id")
            or receipt.get("planner_status") != "Success"
        ):
            raise ValueError("frozen suffix segment receipt linkage mismatch")
        transform = transform_by_segment.get(segment.get("segment_id"))
        if transform is not None:
            executed = transform["executed_control"]
            if (
                executed.get("position_shape") != list(position.shape)
                or executed.get("velocity_shape") != list(velocity.shape)
                or executed.get("position_sha256") != array_sha256(position)
                or executed.get("velocity_sha256") != array_sha256(velocity)
                or segment.get("planner_query", {}).get(
                    "execution_control_transform"
                )
                != transform
            ):
                raise ValueError(
                    "frozen suffix transformed-control provenance differs from arrays"
                )
        control = {
                "status": "Success",
                "position": position,
                "velocity": velocity,
            }
        if segment.get("planner_query") is not None:
            control["_cmf_planner_query"] = dict(segment["planner_query"])
        controls.append(control)
    if len(controls) != len(manifest.get("execution_spec", {}).get("targets", [])):
        raise ValueError("frozen suffix control count mismatch")
    if set(transform_by_segment) != {
        item.get("segment_id")
        for item in manifest.get("segments", [])
        if item.get("planner_query", {}).get("execution_control_transform")
        is not None
    }:
        raise ValueError("frozen suffix execution transform linkage is incomplete")
    return dict(manifest), normalized, controls


def write_frozen_suffix_artifact(
    output_dir: Path, manifest: Mapping[str, Any], arrays: Mapping[str, Any]
) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    validated, normalized, _ = validate_frozen_suffix_artifact(manifest, arrays)
    arrays_path = output_dir / "suffix_controls.npz"
    np.savez_compressed(arrays_path, **normalized)
    with_file = dict(validated)
    with_file["arrays_file_sha256"] = file_sha256(arrays_path)
    (output_dir / "frozen_suffix_artifact.json").write_text(
        json.dumps(with_file, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return with_file


def load_frozen_suffix_artifact(
    output_dir: Path,
) -> tuple[dict, dict[str, np.ndarray], list[dict]]:
    output_dir = Path(output_dir)
    manifest = json.loads(
        (output_dir / "frozen_suffix_artifact.json").read_text(encoding="utf-8")
    )
    arrays_path = output_dir / manifest.get("arrays_file", "suffix_controls.npz")
    if file_sha256(arrays_path) != manifest.get("arrays_file_sha256"):
        raise ValueError("frozen suffix arrays file hash mismatch")
    with np.load(arrays_path, allow_pickle=False) as loaded:
        arrays = {key: loaded[key] for key in loaded.files}
    base = dict(manifest)
    base.pop("arrays_file_sha256", None)
    validated, normalized, controls = validate_frozen_suffix_artifact(base, arrays)
    validated["arrays_file_sha256"] = manifest["arrays_file_sha256"]
    return validated, normalized, controls
