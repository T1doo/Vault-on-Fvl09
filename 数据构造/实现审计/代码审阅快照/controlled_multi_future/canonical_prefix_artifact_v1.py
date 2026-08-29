"""Immutable canonical-prefix artifact for runtime-v3_3.

The semantic prefix is represented by exact 26-D effective-setpoint bytes.
Any post-prefix settling window is recorded separately and is never included
in ``prefix_step_count`` or ``prefix_action_sha256``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .current_hasher import hash_json
from .raw_writer import ACTION_LAYOUT_VERSION, PRIMARY_ACTION_DIM, PRIMARY_FREQUENCY_HZ


SCHEMA_VERSION = "cmf_canonical_prefix_artifact_v1"
ARRAY_SCHEMA_VERSION = "cmf_canonical_prefix_arrays_v1"
PREFIX_END_TOLERANCE_VERSION = "cmf_prefix_end_tolerance_v1_provisional"
FORBIDDEN_PREFIX_KEYS = frozenset(
    {
        "target_role",
        "program_id",
        "branch_id",
        "intent_id",
        "selected_candidate_id",
        "candidate_id",
    }
)
ARRAY_FIELDS = (
    "effective_setpoint_actions",
    "requested_commands",
    "component_masks",
    "action_interval_start_timestamps",
    "action_interval_end_timestamps",
)


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def array_sha256(value: Any) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def prefix_action_sha256(value: Any) -> str:
    array = np.ascontiguousarray(np.asarray(value, dtype=np.float64))
    if array.ndim != 2 or array.shape[1] != PRIMARY_ACTION_DIM:
        raise ValueError("canonical prefix actions must have shape [N,26]")
    return array_sha256(array)


def _reject_forbidden_keys(value: Any, *, path: str = "prefix_contract") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in FORBIDDEN_PREFIX_KEYS:
                raise ValueError(f"canonical prefix contract exposes forbidden key {path}.{key}")
            _reject_forbidden_keys(item, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_forbidden_keys(item, path=f"{path}[{index}]")


def _normalized_arrays(arrays: Mapping[str, Any]) -> dict[str, np.ndarray]:
    if not isinstance(arrays, Mapping) or set(arrays) != set(ARRAY_FIELDS):
        raise ValueError(f"canonical prefix arrays must contain exactly {ARRAY_FIELDS}")
    actions = np.ascontiguousarray(np.asarray(arrays["effective_setpoint_actions"], dtype=np.float64))
    requested = np.ascontiguousarray(np.asarray(arrays["requested_commands"], dtype=np.float64))
    masks = np.ascontiguousarray(np.asarray(arrays["component_masks"], dtype=bool))
    starts = np.ascontiguousarray(np.asarray(arrays["action_interval_start_timestamps"], dtype=np.float64))
    ends = np.ascontiguousarray(np.asarray(arrays["action_interval_end_timestamps"], dtype=np.float64))
    if actions.ndim != 2 or actions.shape[1] != PRIMARY_ACTION_DIM or actions.shape[0] < 1:
        raise ValueError("canonical prefix effective actions must have nonempty shape [N,26]")
    n = actions.shape[0]
    if requested.shape != actions.shape or masks.shape != actions.shape:
        raise ValueError("requested commands and component masks must match canonical actions")
    if starts.shape != (n,) or ends.shape != (n,):
        raise ValueError("canonical prefix action timestamps must have shape [N]")
    if not np.all(np.isfinite(actions)) or not np.all(np.isfinite(requested)):
        raise ValueError("canonical prefix commands must be finite")
    if not np.all(np.isfinite(starts)) or not np.all(np.isfinite(ends)):
        raise ValueError("canonical prefix timestamps must be finite")
    dt = 1.0 / PRIMARY_FREQUENCY_HZ
    if not np.allclose(ends - starts, dt, rtol=0.0, atol=1e-9):
        raise ValueError("canonical prefix action intervals must be 250 Hz")
    if n > 1 and not np.allclose(starts[1:], ends[:-1], rtol=0.0, atol=1e-9):
        raise ValueError("canonical prefix action intervals must be contiguous")
    if not np.isclose(starts[0], 0.0, rtol=0.0, atol=1e-9):
        raise ValueError("canonical prefix local timestamps must start at zero")
    return {
        "effective_setpoint_actions": actions,
        "requested_commands": requested,
        "component_masks": masks,
        "action_interval_start_timestamps": starts,
        "action_interval_end_timestamps": ends,
    }


def build_canonical_prefix_artifact(
    *,
    root_slot_id: str,
    family: str,
    reference_current_sha256: str,
    reference_anchor: Mapping[str, Any],
    prefix_contract: Mapping[str, Any],
    planner_seed: int,
    planner_query_receipts: list[Mapping[str, Any]],
    planner_source_hash: str,
    arrays: Mapping[str, Any],
    semantic_prefix_end_anchor: Mapping[str, Any],
    acceptance_prefix_end_anchor: Mapping[str, Any],
    settling_step_count: int,
    settling_policy: Mapping[str, Any],
    prefix_physical_acceptance: Mapping[str, Any],
    reference_trace_source: Mapping[str, Any],
    reference_event_boundaries: Mapping[str, int] | None = None,
) -> tuple[dict, dict[str, np.ndarray]]:
    if not isinstance(root_slot_id, str) or not root_slot_id:
        raise ValueError("root_slot_id must be nonempty")
    if family not in ("F1", "F2", "F3", "F4"):
        raise ValueError("unsupported canonical-prefix family")
    if not isinstance(reference_current_sha256, str) or len(reference_current_sha256) != 64:
        raise ValueError("reference current hash is invalid")
    if not isinstance(planner_source_hash, str) or len(planner_source_hash) != 64:
        raise ValueError("planner source hash is invalid")
    if not isinstance(settling_step_count, int) or settling_step_count < 0:
        raise ValueError("settling_step_count must be nonnegative")
    _reject_forbidden_keys(prefix_contract)
    if (
        not isinstance(prefix_physical_acceptance, Mapping)
        or prefix_physical_acceptance.get("pass") is not True
    ):
        raise ValueError("canonical prefix physical-acceptance Gate did not pass")
    trace_sha256 = reference_trace_source.get("sha256") if isinstance(
        reference_trace_source, Mapping
    ) else None
    if not isinstance(trace_sha256, str) or len(trace_sha256) != 64:
        raise ValueError("canonical prefix reference trace SHA-256 is missing")
    normalized = _normalized_arrays(arrays)
    n = normalized["effective_setpoint_actions"].shape[0]
    boundaries = dict(reference_event_boundaries or {})
    if not all(
        isinstance(name, str)
        and name
        and isinstance(index, int)
        and 0 <= index <= n
        for name, index in boundaries.items()
    ):
        raise ValueError("canonical prefix event boundaries are invalid")
    array_hashes = {key: array_sha256(value) for key, value in normalized.items()}
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "array_schema_version": ARRAY_SCHEMA_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_3",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "root_slot_id": root_slot_id,
        "family": family,
        "reference_current_sha256": reference_current_sha256,
        "reference_anchor_sha256": reference_anchor.get("anchor_sha256"),
        "reference_anchor": json.loads(json.dumps(reference_anchor, sort_keys=True)),
        "prefix_contract": json.loads(json.dumps(prefix_contract, sort_keys=True)),
        "prefix_contract_sha256": hash_json(prefix_contract),
        "planner_seed": int(planner_seed),
        "planner_query_receipts": json.loads(json.dumps(planner_query_receipts, sort_keys=True)),
        "planner_source_hash": planner_source_hash,
        "action_layout_version": ACTION_LAYOUT_VERSION,
        "action_frequency_hz": PRIMARY_FREQUENCY_HZ,
        "action_dim": PRIMARY_ACTION_DIM,
        "prefix_step_count": int(n),
        "semantic_prefix_step_count": int(n),
        "prefix_action_sha256": prefix_action_sha256(normalized["effective_setpoint_actions"]),
        "array_hashes": array_hashes,
        "semantic_prefix_end_anchor": json.loads(json.dumps(semantic_prefix_end_anchor, sort_keys=True)),
        "semantic_prefix_end_anchor_sha256": semantic_prefix_end_anchor.get("anchor_sha256"),
        "acceptance_prefix_end_anchor": json.loads(json.dumps(acceptance_prefix_end_anchor, sort_keys=True)),
        "acceptance_prefix_end_anchor_sha256": acceptance_prefix_end_anchor.get("anchor_sha256"),
        "prefix_end_tolerance_version": PREFIX_END_TOLERANCE_VERSION,
        "settling_step_count_excluded_from_semantic_prefix": settling_step_count,
        "settling_policy": json.loads(json.dumps(settling_policy, sort_keys=True)),
        "prefix_physical_acceptance": json.loads(
            json.dumps(prefix_physical_acceptance, sort_keys=True)
        ),
        "reference_trace_source": json.loads(
            json.dumps(reference_trace_source, sort_keys=True)
        ),
        "settling_is_part_of_semantic_prefix": False,
        "reference_event_boundaries": boundaries,
        "prefix_arrays_file": "prefix_arrays.npz",
    }
    manifest["artifact_sha256"] = canonical_json_sha256(manifest)
    return manifest, normalized


def validate_canonical_prefix_artifact(
    manifest: Mapping[str, Any], arrays: Mapping[str, Any]
) -> tuple[dict, dict[str, np.ndarray]]:
    if not isinstance(manifest, Mapping) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("canonical prefix artifact schema mismatch")
    value = json.loads(json.dumps(manifest, ensure_ascii=False, sort_keys=True, allow_nan=False))
    expected_artifact_hash = value.pop("artifact_sha256", None)
    value.pop("prefix_arrays_npz_sha256", None)
    if not isinstance(expected_artifact_hash, str) or canonical_json_sha256(value) != expected_artifact_hash:
        raise ValueError("canonical prefix artifact hash mismatch")
    if manifest.get("formal_data") is not False or manifest.get("stage0_data") is not False:
        raise ValueError("canonical prefix artifact must remain nonformal")
    if manifest.get("stage0_authorized") is not False:
        raise ValueError("canonical prefix artifact cannot authorize Stage 0")
    if manifest.get("action_layout_version") != ACTION_LAYOUT_VERSION:
        raise ValueError("canonical prefix action layout mismatch")
    if manifest.get("action_frequency_hz") != PRIMARY_FREQUENCY_HZ:
        raise ValueError("canonical prefix frequency mismatch")
    if manifest.get("settling_is_part_of_semantic_prefix") is not False:
        raise ValueError("settling must not extend semantic P")
    if manifest.get("prefix_physical_acceptance", {}).get("pass") is not True:
        raise ValueError("canonical prefix physical-acceptance Gate is absent or failed")
    reference_trace_sha = manifest.get("reference_trace_source", {}).get("sha256")
    if not isinstance(reference_trace_sha, str) or len(reference_trace_sha) != 64:
        raise ValueError("canonical prefix reference trace SHA-256 is invalid")
    _reject_forbidden_keys(manifest.get("prefix_contract", {}))
    normalized = _normalized_arrays(arrays)
    if manifest.get("prefix_step_count") != normalized["effective_setpoint_actions"].shape[0]:
        raise ValueError("canonical prefix step count mismatch")
    if manifest.get("semantic_prefix_step_count") != manifest.get("prefix_step_count"):
        raise ValueError("semantic prefix step count mismatch")
    if manifest.get("prefix_action_sha256") != prefix_action_sha256(
        normalized["effective_setpoint_actions"]
    ):
        raise ValueError("canonical prefix action hash mismatch")
    expected_array_hashes = {key: array_sha256(value) for key, value in normalized.items()}
    if manifest.get("array_hashes") != expected_array_hashes:
        raise ValueError("canonical prefix array hash mismatch")
    return dict(manifest), normalized


def write_canonical_prefix_artifact(
    output_dir: Path, manifest: Mapping[str, Any], arrays: Mapping[str, Any]
) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    validated, normalized = validate_canonical_prefix_artifact(manifest, arrays)
    arrays_path = output_dir / "prefix_arrays.npz"
    np.savez_compressed(arrays_path, **normalized)
    with_file = dict(validated)
    with_file["prefix_arrays_npz_sha256"] = file_sha256(arrays_path)
    manifest_path = output_dir / "canonical_prefix_artifact.json"
    manifest_path.write_text(
        json.dumps(with_file, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return with_file


def load_canonical_prefix_artifact(output_dir: Path) -> tuple[dict, dict[str, np.ndarray]]:
    output_dir = Path(output_dir)
    manifest = json.loads((output_dir / "canonical_prefix_artifact.json").read_text(encoding="utf-8"))
    arrays_path = output_dir / manifest.get("prefix_arrays_file", "prefix_arrays.npz")
    if file_sha256(arrays_path) != manifest.get("prefix_arrays_npz_sha256"):
        raise ValueError("canonical prefix arrays file hash mismatch")
    with np.load(arrays_path, allow_pickle=False) as loaded:
        arrays = {key: loaded[key] for key in loaded.files}
    base = dict(manifest)
    base.pop("prefix_arrays_npz_sha256", None)
    validated, normalized = validate_canonical_prefix_artifact(base, arrays)
    validated["prefix_arrays_npz_sha256"] = manifest["prefix_arrays_npz_sha256"]
    return validated, normalized
