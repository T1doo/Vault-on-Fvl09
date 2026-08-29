"""Raw-first pilot writer with the frozen 26-D/250 Hz/N+1 contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .current_hasher import hash_json
from .schemas import validate_primary_stream


PRIMARY_STREAM_NAME = "controller_effective_setpoint_v1"
PRIMARY_FREQUENCY_HZ = 250
PRIMARY_ACTION_DIM = 26
ACTION_LAYOUT_VERSION = "controller_effective_setpoint_v1_layout_v2_1"
RAW_SCHEMA_VERSION = "cmf_raw_attempt_v2_1_1"
TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS = 1e-9
ACTION_LAYOUT_DIMENSIONS = tuple(
    [f"left_joint_{index}_position_target" for index in range(6)]
    + [f"right_joint_{index}_position_target" for index in range(6)]
    + [f"left_joint_{index}_velocity_target" for index in range(6)]
    + [f"right_joint_{index}_velocity_target" for index in range(6)]
    + ["left_gripper_normalized_target", "right_gripper_normalized_target"]
)
STREAM_SOURCE_STATUSES = frozenset({"measured", "commanded", "derived", "mixed", "unavailable"})
PLANNER_AUDIT_FIELDS = (
    "planner_goal_available",
    "planner_query_id",
    "planner_goal_active",
    "planner_goal_source",
    "planner_goal_start_step",
    "planner_goal_end_step",
)
REQUIRED_STREAM_METADATA = (
    "controller_effective_setpoint",
    "requested_command",
    "planner_goal_eef_pose",
    "realized_qpos",
    "realized_qvel",
    "realized_eef",
    "gripper_command",
    "action_interval_start_timestamps",
    "action_interval_end_timestamps",
    "state_timestamps",
    "component_masks",
)
REAL_RUNTIME_REQUIRED_AUDIT_FIELDS = (
    "object_pose",
    "object_linear_velocity",
    "object_linear_velocity_measured",
    "object_angular_velocity",
    "object_angular_velocity_measured",
    "object_component_linear_velocity",
    "object_component_linear_velocity_measured",
    "object_component_angular_velocity",
    "object_component_angular_velocity_measured",
    "object_component_velocity_provenance_json",
    "eef_linear_velocity",
    "eef_angular_velocity",
    "gripper_drive_target_readback",
    "left_gripper_joint_drive_target",
    "right_gripper_joint_drive_target",
    "left_gripper_joint_drive_velocity_target",
    "right_gripper_joint_drive_velocity_target",
    "realized_left_gripper_joint_qpos",
    "realized_right_gripper_joint_qpos",
    "selected_gripper_contact",
    "selected_gripper_contact_count",
    "selected_gripper_contact_impulse",
    "selected_contact_actor_name",
    "contact_count",
    "contact_pairs_json",
    *PLANNER_AUDIT_FIELDS,
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
    role_prefix = "role_object_pose__"
    roles = sorted(
        field[len(role_prefix) :]
        for field in arrays
        if field.startswith(role_prefix)
    )
    role_suffixes = (
        "pose",
        "linear_velocity",
        "angular_velocity",
        "linear_velocity_measured",
        "angular_velocity_measured",
        "component_linear_velocity",
        "component_angular_velocity",
        "component_linear_velocity_measured",
        "component_angular_velocity_measured",
        "component_velocity_provenance_json",
    )
    for role in roles:
        role_missing = [
            f"role_object_{suffix}__{role}"
            for suffix in role_suffixes
            if f"role_object_{suffix}__{role}" not in arrays
        ]
        if role_missing:
            raise ValueError(
                f"audit role {role} has incomplete pose/velocity bundle: {role_missing}"
            )
    if np.asarray(arrays.get("object_pose")).shape != (action_count + 1, 7):
        raise ValueError("audit object_pose must have shape [N+1,7]")
    if np.asarray(arrays.get("contact_count")).shape != (action_count + 1,):
        raise ValueError("audit contact_count must have shape [N+1]")
    for field in ("realized_left_gripper_joint_qpos", "realized_right_gripper_joint_qpos", "gripper_drive_target_readback"):
        values = np.asarray(arrays.get(field))
        if values.ndim != 2 or values.shape[0] != action_count + 1 or values.shape[1] < 1:
            raise ValueError(f"audit {field} must have shape [N+1,D] with D>=1")
    for field in PLANNER_AUDIT_FIELDS:
        values = np.asarray(arrays.get(field))
        if values.shape != (action_count, 2):
            raise ValueError(f"audit {field} must have shape [N,2]")
    for field, values in arrays.items():
        expected_rows = action_count if field in PLANNER_AUDIT_FIELDS else action_count + 1
        if values.ndim == 0 or values.shape[0] != expected_rows:
            raise ValueError(
                f"audit field {field} must have {expected_rows} rows"
            )
        item = metadata.get(field)
        if not isinstance(item, Mapping) or item.get("status") not in STREAM_SOURCE_STATUSES:
            raise ValueError(f"audit field_metadata missing valid status for {field}")
        source = item.get("source")
        if not isinstance(source, str) or not source or "placeholder" in source.lower():
            raise ValueError(f"audit field {field} must name a non-placeholder source")


def validate_real_runtime_audit_fields(
    audit_streams: Mapping[str, Any], provenance: Mapping[str, Any]
) -> None:
    expected_schema = "cmf_runtime_trace_pose_consistent_velocity_v2"
    if provenance.get("synthetic") is False and provenance.get(
        "trace_schema_version"
    ) != expected_schema:
        raise ValueError("real runtime provenance lacks the exact trace schema")
    if provenance.get("trace_schema_version") != expected_schema:
        return
    arrays = {
        key: value for key, value in audit_streams.items() if key != "field_metadata"
    }
    missing = [
        field for field in REAL_RUNTIME_REQUIRED_AUDIT_FIELDS if field not in arrays
    ]
    if missing:
        raise ValueError(f"real runtime audit streams missing required fields: {missing}")
    expected_roles = provenance.get("trace_role_names")
    if (
        not isinstance(expected_roles, list)
        or not expected_roles
        or any(not isinstance(role, str) or not role for role in expected_roles)
        or len(set(expected_roles)) != len(expected_roles)
    ):
        raise ValueError("real runtime provenance lacks exact trace_role_names")
    role_marker = "role_object_"
    actual_roles = {
        field.rsplit("__", 1)[1]
        for field in arrays
        if field.startswith(role_marker) and "__" in field
    }
    if actual_roles != set(expected_roles):
        raise ValueError(
            "real runtime audit role bundle differs from trace_role_names"
        )
    state_count = int(np.asarray(arrays["object_pose"]).shape[0])
    shaped_suffixes = {
        "pose": (state_count, 7),
        "linear_velocity": (state_count, 3),
        "angular_velocity": (state_count, 3),
        "component_linear_velocity": (state_count, 3),
        "component_angular_velocity": (state_count, 3),
        "linear_velocity_measured": (state_count,),
        "angular_velocity_measured": (state_count,),
        "component_linear_velocity_measured": (state_count,),
        "component_angular_velocity_measured": (state_count,),
        "component_velocity_provenance_json": (state_count,),
    }
    for role in expected_roles:
        for suffix, expected_shape in shaped_suffixes.items():
            field = f"role_object_{suffix}__{role}"
            if field not in arrays:
                raise ValueError(
                    f"real runtime audit role {role} missing required field {field}"
                )
            if np.asarray(arrays[field]).shape != expected_shape:
                raise ValueError(
                    f"real runtime audit role field {field} must have shape {expected_shape}"
                )


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{label} must be a lowercase SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a lowercase SHA-256 hex digest") from exc
    if value.lower() != value:
        raise ValueError(f"{label} must be lowercase")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_simulator_timing(provenance: Mapping[str, Any]) -> dict:
    timing = provenance.get("simulator_timing")
    if not isinstance(timing, Mapping):
        raise ValueError("provenance must include simulator_timing")
    required = (
        "simulator_timestep_seconds",
        "control_steps_per_action",
        "effective_action_interval_seconds",
        "scene_timestep_source",
    )
    missing = [key for key in required if key not in timing]
    if missing:
        raise ValueError(f"simulator_timing missing {missing}")
    timestep = float(timing["simulator_timestep_seconds"])
    control_steps = timing["control_steps_per_action"]
    effective = float(timing["effective_action_interval_seconds"])
    source = timing["scene_timestep_source"]
    if not isinstance(control_steps, int) or control_steps <= 0:
        raise ValueError("control_steps_per_action must be a positive integer")
    if not isinstance(source, str) or not source:
        raise ValueError("scene_timestep_source must be non-empty")
    if not np.isclose(
        effective,
        timestep * control_steps,
        rtol=0.0,
        atol=TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS,
    ):
        raise ValueError("effective action interval must equal simulator timestep times control steps")
    if not np.isclose(
        effective,
        1.0 / PRIMARY_FREQUENCY_HZ,
        rtol=0.0,
        atol=TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS,
    ):
        raise ValueError("effective action interval must match the frozen 250 Hz stream")
    if (
        not np.isclose(
            timestep,
            1.0 / PRIMARY_FREQUENCY_HZ,
            rtol=0.0,
            atol=TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS,
        )
        or control_steps != 1
    ):
        raise ValueError("current raw-v2_1_1 requires a real 0.004 s scene timestep and one scene.step per action")
    return {
        "simulator_timestep_seconds": timestep,
        "control_steps_per_action": control_steps,
        "effective_action_interval_seconds": effective,
        "scene_timestep_source": source,
    }


def validate_planner_goal_audit(streams: Mapping[str, Any], audit_streams: Mapping[str, Any], provenance: Mapping[str, Any]) -> None:
    goals = np.asarray(streams["planner_goal_eef_pose"], dtype=np.float64)
    n = goals.shape[0]
    available = np.asarray(audit_streams["planner_goal_available"], dtype=bool)
    active = np.asarray(audit_streams["planner_goal_active"], dtype=bool)
    query_ids = np.asarray(audit_streams["planner_query_id"], dtype=np.int64)
    sources = np.asarray(audit_streams["planner_goal_source"]).astype(str)
    starts = np.asarray(audit_streams["planner_goal_start_step"], dtype=np.int64)
    ends = np.asarray(audit_streams["planner_goal_end_step"], dtype=np.int64)
    if not np.array_equal(available, active):
        raise ValueError("planner_goal_available must mean active on the current action interval")
    table = provenance.get("planner_queries")
    if not isinstance(table, list):
        raise ValueError("provenance must include planner_queries list")
    indexed = {}
    for item in table:
        if not isinstance(item, Mapping):
            raise ValueError("planner query table entries must be mappings")
        query_id = item.get("query_id")
        arm = item.get("arm")
        if not isinstance(query_id, int) or query_id <= 0 or arm not in ("left", "right"):
            raise ValueError("planner query table requires positive query_id and left/right arm")
        key = (query_id, arm)
        if key in indexed:
            raise ValueError("planner query IDs must be unique per arm")
        indexed[key] = item
    for step in range(n):
        for arm_index, arm in enumerate(("left", "right")):
            goal = goals[step, arm_index * 7:(arm_index + 1) * 7]
            if not active[step, arm_index]:
                if not np.all(np.isnan(goal)):
                    raise ValueError("inactive planner goal must be encoded as NaN")
                if query_ids[step, arm_index] != -1 or starts[step, arm_index] != -1 or ends[step, arm_index] != -1:
                    raise ValueError("inactive planner audit IDs/intervals must be -1")
                if sources[step, arm_index] != "":
                    raise ValueError("inactive planner goal source must be empty")
                continue
            if not np.all(np.isfinite(goal)):
                raise ValueError("active planner goal must be finite")
            query_id = int(query_ids[step, arm_index])
            key = (query_id, arm)
            if key not in indexed:
                raise ValueError("active planner goal has no matching query-table entry")
            item = indexed[key]
            start = int(starts[step, arm_index])
            end = int(ends[step, arm_index])
            if not (0 <= start <= step < end <= n):
                raise ValueError("planner goal active step lies outside its valid interval")
            if item.get("start_step") != start or item.get("end_step") != end:
                raise ValueError("planner goal interval disagrees with query table")
            if item.get("source") != sources[step, arm_index]:
                raise ValueError("planner goal source disagrees with query table")
            if not np.allclose(goal, np.asarray(item.get("goal_eef_pose"), dtype=np.float64).reshape(7), rtol=0.0, atol=0.0):
                raise ValueError("planner goal pose disagrees with query table")


def validate_raw_streams(streams: Mapping[str, Any]) -> None:
    actions = np.asarray(streams["controller_effective_setpoint"])
    states = np.asarray(streams["realized_qpos"])
    validate_primary_stream(actions, states, frequency_hz=PRIMARY_FREQUENCY_HZ, action_dim=PRIMARY_ACTION_DIM)
    n = actions.shape[0]
    for key in (
        "requested_command", "planner_goal_eef_pose", "gripper_command",
        "action_interval_start_timestamps", "action_interval_end_timestamps", "component_masks",
    ):
        if np.asarray(streams[key]).shape[0] != n:
            raise ValueError(f"{key} must have N rows")
    for key in ("realized_qvel", "realized_eef"):
        if np.asarray(streams[key]).shape[0] != n + 1:
            raise ValueError(f"{key} must have N+1 rows")
    if np.asarray(streams["requested_command"]).shape != (n, PRIMARY_ACTION_DIM):
        raise ValueError("requested_command must have shape [N,26]")
    if np.asarray(streams["planner_goal_eef_pose"]).shape != (n, 14):
        raise ValueError("planner_goal_eef_pose must have shape [N,14] for dual-arm EEF goals")
    if np.asarray(streams["gripper_command"]).shape != (n, 2):
        raise ValueError("gripper_command must have shape [N,2]")
    if np.asarray(streams["component_masks"]).shape != (n, PRIMARY_ACTION_DIM):
        raise ValueError("component_masks must have shape [N,26]")
    state_timestamps = np.asarray(streams["state_timestamps"], dtype=np.float64)
    action_starts = np.asarray(streams["action_interval_start_timestamps"], dtype=np.float64)
    action_ends = np.asarray(streams["action_interval_end_timestamps"], dtype=np.float64)
    if state_timestamps.shape != (n + 1,):
        raise ValueError("state_timestamps must have shape [N+1]")
    if action_starts.shape != (n,) or action_ends.shape != (n,):
        raise ValueError("action interval timestamps must each have shape [N]")
    if not all(np.all(np.isfinite(values)) for values in (state_timestamps, action_starts, action_ends)):
        raise ValueError("state/action timestamps must be finite")
    if n and not np.allclose(np.diff(state_timestamps), 1.0 / PRIMARY_FREQUENCY_HZ, rtol=0.0, atol=1e-9):
        raise ValueError("state_timestamps must follow the frozen 250 Hz cadence")
    if not np.allclose(action_starts, state_timestamps[:-1], rtol=0.0, atol=1e-12):
        raise ValueError("action starts must equal state_timestamps[:-1]")
    if not np.allclose(action_ends, state_timestamps[1:], rtol=0.0, atol=1e-12):
        raise ValueError("action ends must equal state_timestamps[1:]")
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


def verify_raw_artifact_integrity(output_dir: Path) -> dict:
    manifest_path = output_dir / "manifest.json"
    raw_path = output_dir / "raw_streams.npz"
    sidecar_path = output_dir / "manifest.sha256.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    manifest_payload = dict(manifest)
    manifest_payload.pop("manifest_payload_sha256", None)
    manifest_payload.pop("manifest_sha256", None)
    checks = {
        "raw_streams_npz_sha256": _sha256_file(raw_path) == manifest.get("raw_streams_npz_sha256"),
        "manifest_file_sha256": _sha256_file(manifest_path) == sidecar.get("manifest_file_sha256"),
        "manifest_payload_sha256": manifest.get("manifest_payload_sha256") == sidecar.get("manifest_payload_sha256"),
        "manifest_payload_recomputed": hash_json(manifest_payload) == manifest.get("manifest_payload_sha256"),
    }
    trace_relative = manifest.get("provenance", {}).get("trace_source_relative_path")
    if trace_relative is not None:
        trace_path = output_dir / trace_relative
        checks["trace_source_sha256"] = trace_path.is_file() and _sha256_file(trace_path) == manifest.get("trace_source_sha256")
    return {"pass": all(checks.values()), "checks": checks, "manifest": manifest, "integrity_sidecar": sidecar}


def write_raw_attempt(output_dir: Path, streams: Mapping[str, Any], audit_streams: Mapping[str, Any], provenance: Mapping[str, Any]) -> dict:
    validate_raw_streams(streams)
    action_count = int(np.asarray(streams["controller_effective_setpoint"]).shape[0])
    validate_audit_streams(audit_streams, action_count)
    validate_real_runtime_audit_fields(audit_streams, provenance)
    timing = validate_simulator_timing(provenance)
    validate_planner_goal_audit(streams, audit_streams, provenance)
    trace_source_sha256 = _require_sha256(provenance.get("trace_source_sha256"), "trace_source_sha256")
    output_dir.mkdir(parents=True, exist_ok=False)
    arrays = {f"stream__{key}": np.asarray(value) for key, value in streams.items() if key != "field_metadata"}
    arrays.update({f"audit__{key}": np.asarray(value) for key, value in audit_streams.items() if key != "field_metadata"})
    raw_path = output_dir / "raw_streams.npz"
    np.savez_compressed(raw_path, **arrays)
    raw_streams_npz_sha256 = _sha256_file(raw_path)
    manifest = {
        "schema_version": RAW_SCHEMA_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "primary_action_stream": PRIMARY_STREAM_NAME,
        "frequency_hz": PRIMARY_FREQUENCY_HZ,
        "action_dim": PRIMARY_ACTION_DIM,
        "action_layout_version": ACTION_LAYOUT_VERSION,
        "action_layout_dimensions": list(ACTION_LAYOUT_DIMENSIONS),
        "timestamp_semantics": "state[k] -- action[k] on [start,end) --> state[k+1]",
        "stream_field_metadata": dict(streams["field_metadata"]),
        "audit_field_metadata": dict(audit_streams["field_metadata"]),
        "action_count": int(np.asarray(streams["controller_effective_setpoint"]).shape[0]),
        "state_count": int(np.asarray(streams["realized_qpos"]).shape[0]),
        "simulator_timing": timing,
        "raw_streams_npz_sha256": raw_streams_npz_sha256,
        "trace_source_sha256": trace_source_sha256,
        "provenance": dict(provenance),
    }
    manifest["manifest_payload_sha256"] = hash_json(manifest)
    manifest["manifest_sha256"] = manifest["manifest_payload_sha256"]
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # A file cannot contain its own final hash without a self-reference paradox.
    # Store the actual manifest-file digest in a sidecar and copy it into the
    # returned receipt descriptor.
    manifest_file_sha256 = _sha256_file(manifest_path)
    sidecar = {
        "schema_version": "cmf_raw_manifest_integrity_v1",
        "manifest_file": "manifest.json",
        "manifest_file_sha256": manifest_file_sha256,
        "manifest_payload_sha256": manifest["manifest_payload_sha256"],
        "raw_streams_file": "raw_streams.npz",
        "raw_streams_npz_sha256": raw_streams_npz_sha256,
        "trace_source_sha256": trace_source_sha256,
    }
    sidecar_path = output_dir / "manifest.sha256.json"
    sidecar_path.write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result = dict(manifest)
    result["manifest_file_sha256"] = manifest_file_sha256
    result["manifest_integrity_sidecar"] = "manifest.sha256.json"
    result["manifest_integrity_sidecar_sha256"] = _sha256_file(sidecar_path)
    integrity = verify_raw_artifact_integrity(output_dir)
    if not integrity["pass"]:
        raise RuntimeError(f"raw artifact integrity self-check failed: {integrity['checks']}")
    return result
