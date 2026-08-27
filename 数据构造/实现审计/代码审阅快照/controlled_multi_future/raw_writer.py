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


def pack_effective_setpoint(left_position, left_velocity, left_gripper, right_position, right_velocity, right_gripper):
    row = np.concatenate((
        np.asarray(left_position, dtype=np.float64).reshape(6),
        np.asarray(left_velocity, dtype=np.float64).reshape(6),
        np.asarray([left_gripper], dtype=np.float64),
        np.asarray(right_position, dtype=np.float64).reshape(6),
        np.asarray(right_velocity, dtype=np.float64).reshape(6),
        np.asarray([right_gripper], dtype=np.float64),
    ))
    if row.shape != (26,):
        raise ValueError("effective setpoint must be exactly 26-D")
    return row


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


def write_raw_attempt(output_dir: Path, streams: Mapping[str, Any], audit_streams: Mapping[str, Any], provenance: Mapping[str, Any]) -> dict:
    validate_raw_streams(streams)
    output_dir.mkdir(parents=True, exist_ok=False)
    arrays = {f"stream__{key}": np.asarray(value) for key, value in streams.items()}
    arrays.update({f"audit__{key}": np.asarray(value) for key, value in audit_streams.items()})
    np.savez_compressed(output_dir / "raw_streams.npz", **arrays)
    manifest = {
        "schema_version": "cmf_raw_attempt_v1",
        "formal_data": False,
        "stage0_data": False,
        "primary_action_stream": PRIMARY_STREAM_NAME,
        "frequency_hz": PRIMARY_FREQUENCY_HZ,
        "action_dim": PRIMARY_ACTION_DIM,
        "action_count": int(np.asarray(streams["controller_effective_setpoint"]).shape[0]),
        "state_count": int(np.asarray(streams["realized_qpos"]).shape[0]),
        "provenance": dict(provenance),
    }
    manifest["manifest_sha256"] = hash_json(manifest)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
