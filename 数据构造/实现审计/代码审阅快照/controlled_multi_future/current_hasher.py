"""Deterministic hashes for model-visible current context and audit-only layout."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

import numpy as np


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def hash_array(array) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode("ascii"))
    digest.update(_json_bytes(list(value.shape)))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def hash_json(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def build_current_hashes(
    *,
    head_rgb,
    wrist_rgb: Mapping[str, Any],
    robot_state,
    object_role_layout: Mapping[str, Any],
    scene_seed: int,
    generator_version: str,
) -> dict:
    components = {
        "head_rgb_sha256": hash_array(head_rgb),
        "wrist_rgb_sha256": {name: hash_array(wrist_rgb[name]) for name in sorted(wrist_rgb)},
        "robot_state_sha256": hash_array(robot_state),
        "object_role_layout_sha256": hash_json(object_role_layout),
        "scene_spec_sha256": hash_json({"scene_seed": int(scene_seed), "generator_version": generator_version}),
    }
    return {"components": components, "aggregate_sha256": hash_json(components)}


def require_same_current(reference: Mapping[str, Any], candidate: Mapping[str, Any]) -> None:
    if reference.get("aggregate_sha256") != candidate.get("aggregate_sha256"):
        raise ValueError("fresh reconstruction failed same-current aggregate hash")
