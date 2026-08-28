"""Raw-first pilot writer with the frozen 26-D/250 Hz/N+1 contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .current_hasher import hash_json
from .schemas import validate_primary_stream


PRIMARY_STREAM_NAME = "controller_effective_setpoint_v1"
PRIMARY_FREQUENCY_HZ = 250
PRIMARY_ACTION_DIM = 26
ACTION_LAYOUT_VERSION = "controller_effective_setpoint_v1_layout_v2"
ACTION_LAYOUT_DIMENSIONS = tuple(
    [f"left_joint_{index}_position_target" for index in range(6)]
    + [f"right_joint_{index}_position_target" for index in range(6)]
    + [f"left_joint_{index}_velocity_target" for index in range(6)]
    + [f"right_joint_{index}_velocity_target" for index in range(6)]
    + ["left_gripper_normalized_target", "right_gripper_normalized_target"]
)
STREAM_SOURCE_STATUSES = frozenset({"measured", "commanded", "derived", "mixed", "unavailable"})
REQUIRED_STREAM_METADATA = (
    "controller_effective_setpoint",
    "requested_command",
    "planner_target",
    "realized_qpos",
    "realized_qvel",
    "realized_eef",
    "gripper_command",
    "timestamps",
    "component_masks",
)


def pack_effective_setpoint(left_position, left_velocity, left_gripper, right_position, right_velocity, right_gripper):
    row = np.concatenate((
        np.asarray(left_position, dtype=np.float64).reshape(6),
        np.asarray(right_position, dtype=np.float64).reshape(6),
        np.asarray(left_velocity, dtype=np.float64).reshape(6),
        np.asarray(right_velocity, dtype=np.float64).reshape(6),
        np.asarray([left_gripper], dtype=np.float64),
        np.asarray([right_gripper], dtype=np.float64),
    ))
    if row.shape != (26,):
        raise ValueError("effective setpoint must be exactly 26-D")
    return row


def _validate_field_metadata(metadata: Mapping[str, Any]) -> None:
    if not isinstance(metadata, Mapping):
        raise ValueError("streams must include machine-readable field_metadata")
    for field in REQUIRED_STREAM_METADATA:
        item = metadata.get(field)
        if not isinstance(item, Mapping):
            raise ValueError(f"field_metadata missing {field}")
        if item.get("status") not in STREAM_SOURCE_STATUSES:
            raise ValueError(f"{field} has unsupported source status")
        source = item.get("source")
        if not isinstance(source, str) or not source or "placeholder" in source.lower():
            raise ValueError(f"{field} must name a non-placeholder source")


def validate_audit_streams(audit_streams: Mapping[str, Any], action_count: int) -> None:
    metadata = audit_streams.get("field_metadata")
    if not isinstance(metadata, Mapping):
        raise ValueError("audit_streams must include machine-readable field_metadata")
    arrays = {key: np.asarray(value) for key, value in audit_streams.items() if key != "field_metadata"}
    if np.asarray(arrays.get("object_pose")).shape != (action_count + 1, 7):
        raise ValueError("audit object_pose must have shape [N+1,7]")
    if np.asarray(arrays.get("contact_count")).shape != (action_count + 1,):
        raise ValueError("audit contact_count must have shape [N+1]")
    for field, values in arrays.items():
        if values.ndim == 0 or values.shape[0] not in (action_count, action_count + 1):
            raise ValueError(f"audit field {field} must have N or N+1 rows")
        item = metadata.get(field)
        if not isinstance(item, Mapping) or item.get("status") not in STREAM_SOURCE_STATUSES:
            raise ValueError(f"audit field_metadata missing valid status for {field}")
        source = item.get("source")
        if not isinstance(source, str) or not source or "placeholder" in source.lower():
            raise ValueError(f"audit field {field} must name a non-placeholder source")


def validate_raw_streams(streams: Mapping[str, Any]) -> None:
    actions = np.asarray(streams["controller_effective_setpoint"])
    states = np.asarray(streams["realized_qpos"])
    validate_primary_stream(actions, states, frequency_hz=PRIMARY_FREQUENCY_HZ, action_dim=PRIMARY_ACTION_DIM)
    n = actions.shape[0]
    for key in ("requested_command", "planner_target", "gripper_command", "timestamps", "component_masks"):
        if np.asarray(streams[key]).shape[0] != n:
            raise ValueError(f"{key} must have N rows")
    for key in ("realized_qvel", "realized_eef"):
        if np.asarray(streams[key]).shape[0] != n + 1:
            raise ValueError(f"{key} must have N+1 rows")
    if np.asarray(streams["requested_command"]).shape != (n, PRIMARY_ACTION_DIM):
        raise ValueError("requested_command must have shape [N,26]")
    if np.asarray(streams["planner_target"]).shape != (n, 14):
        raise ValueError("planner_target must have shape [N,14] for dual-arm EEF targets")
    if np.asarray(streams["gripper_command"]).shape != (n, 2):
        raise ValueError("gripper_command must have shape [N,2]")
    if np.asarray(streams["component_masks"]).shape != (n, PRIMARY_ACTION_DIM):
        raise ValueError("component_masks must have shape [N,26]")
    if np.asarray(streams["timestamps"]).shape != (n,):
        raise ValueError("timestamps must have shape [N]")
    timestamps = np.asarray(streams["timestamps"], dtype=np.float64)
    if not np.all(np.isfinite(timestamps)):
        raise ValueError("timestamps must be finite")
    if n > 1 and not np.allclose(np.diff(timestamps), 1.0 / PRIMARY_FREQUENCY_HZ, rtol=0.0, atol=1e-9):
        raise ValueError("timestamps must follow the frozen 250 Hz cadence")
    if np.asarray(streams["component_masks"]).dtype != np.dtype(bool):
        raise ValueError("component_masks must be boolean")
    for field in ("controller_effective_setpoint", "requested_command", "realized_qpos", "realized_qvel", "realized_eef", "gripper_command"):
        if not np.all(np.isfinite(np.asarray(streams[field], dtype=np.float64))):
            raise ValueError(f"{field} must be finite")
    if np.asarray(streams["realized_qvel"]).shape != states.shape:
        raise ValueError("realized_qpos and realized_qvel must have matching dual-arm shapes")
    if np.asarray(streams["realized_eef"]).shape != (n + 1, 14):
        raise ValueError("realized_eef must have shape [N+1,14]")
    if np.shares_memory(actions, np.asarray(streams["requested_command"])):
        raise ValueError("effective and requested streams must not alias the same memory")
    _validate_field_metadata(streams.get("field_metadata"))
    for field, item in streams["field_metadata"].items():
        if item.get("status") == "unavailable" and field in streams:
            values = np.asarray(streams[field], dtype=np.float64)
            if values.size and not np.all(np.isnan(values)):
                raise ValueError(f"unavailable field {field} must be encoded as NaN")


def write_raw_attempt(output_dir: Path, streams: Mapping[str, Any], audit_streams: Mapping[str, Any], provenance: Mapping[str, Any]) -> dict:
    validate_raw_streams(streams)
    action_count = int(np.asarray(streams["controller_effective_setpoint"]).shape[0])
    validate_audit_streams(audit_streams, action_count)
    output_dir.mkdir(parents=True, exist_ok=False)
    arrays = {f"stream__{key}": np.asarray(value) for key, value in streams.items() if key != "field_metadata"}
    arrays.update({f"audit__{key}": np.asarray(value) for key, value in audit_streams.items() if key != "field_metadata"})
    np.savez_compressed(output_dir / "raw_streams.npz", **arrays)
    manifest = {
        "schema_version": "cmf_raw_attempt_v2",
        "formal_data": False,
        "stage0_data": False,
        "primary_action_stream": PRIMARY_STREAM_NAME,
        "frequency_hz": PRIMARY_FREQUENCY_HZ,
        "action_dim": PRIMARY_ACTION_DIM,
        "action_layout_version": ACTION_LAYOUT_VERSION,
        "action_layout_dimensions": list(ACTION_LAYOUT_DIMENSIONS),
        "stream_field_metadata": dict(streams["field_metadata"]),
        "audit_field_metadata": dict(audit_streams["field_metadata"]),
        "action_count": int(np.asarray(streams["controller_effective_setpoint"]).shape[0]),
        "state_count": int(np.asarray(streams["realized_qpos"]).shape[0]),
        "provenance": dict(provenance),
    }
    manifest["manifest_sha256"] = hash_json(manifest)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
