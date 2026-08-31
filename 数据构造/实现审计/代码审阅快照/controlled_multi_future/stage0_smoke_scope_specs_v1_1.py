"""Deterministic v13 infrastructure and v1.1 Stage 0 scope specs."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .current_hasher import hash_json
from .f4_right_workspace_layout_v4 import LAYOUT as F4_LAYOUT
from .stage0_smoke_budget_v1_1 import (
    F4_INFRA_SCOPE,
    SCOPE_FAMILIES,
    scope_budget,
)
from .stage0_smoke_manifest_v1_1 import (
    SCENE_SEED,
    validate_stage0_smoke_manifest_structure,
)


SCHEMA_VERSION = "cmf_stage0_smoke_scope_spec_v1_1"
GENERATOR_VERSION = "controlled_multi_future_stage0_smoke_v1_1_adapter_v1_7"


def planned_scope_spec(
    scope: str,
    *,
    stage0_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if scope not in SCOPE_FAMILIES:
        raise ValueError(f"unsupported Stage 0 v1.1 scope {scope}")
    family = SCOPE_FAMILIES[scope]
    if scope == F4_INFRA_SCOPE:
        if stage0_manifest is not None:
            raise ValueError("F4 v13 infrastructure scope precedes Stage 0 manifest")
        scene_layout = json.loads(
            json.dumps(F4_LAYOUT, sort_keys=True, allow_nan=False)
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "slot_id": "prestage0-F4-candidate-hash-infra-v13-stage0-v1_1",
            "family": "F4",
            "scope": scope,
            "seed": SCENE_SEED,
            "arm": "right",
            "generator": GENERATOR_VERSION,
            "origin": "authorized_frozen_canonical_neutral_v13_fix",
            "predecessor_implementation_version": (
                "controlled_multi_future_stage0_smoke_v1"
            ),
            "predecessor_scope": "F4_candidate_hash_infra_v12",
            "scene_layout": scene_layout,
            "scene_layout_sha256": hash_json(scene_layout),
            "budget_sha256": scope_budget(scope)["scope_budget_sha256"],
            "automatic_retry": False,
            "recovery_attempts": 0,
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": True,
            "required_success": (
                "v13 hash infrastructure pass and candidate planner query > 0; "
                "corridor physical pass optional"
            ),
            "stop_condition": "terminal receipt or cleanup/source/GPU uncertainty",
        }
    if not isinstance(stage0_manifest, Mapping):
        raise ValueError("Stage 0 v1.1 scope requires its frozen manifest")
    manifest = json.loads(
        json.dumps(stage0_manifest, sort_keys=True, allow_nan=False)
    )
    manifest_gate = validate_stage0_smoke_manifest_structure(manifest)
    if manifest_gate["pass"] is not True:
        raise ValueError(
            f"Stage 0 v1.1 manifest structure failed: {manifest_gate['checks']}"
        )
    if manifest.get("stage0_authorized") is not True:
        raise ValueError("Stage 0 v1.1 manifest is not authorized")
    root_spec = manifest.get("root_specs", {}).get(family)
    if not isinstance(root_spec, Mapping) or root_spec.get("scope") != scope:
        raise ValueError("Stage 0 v1.1 manifest lacks the requested root spec")
    result = json.loads(json.dumps(root_spec, sort_keys=True, allow_nan=False))
    result["stage0_manifest_sha256"] = manifest["manifest_sha256"]
    result["stage0_manifest_attempt_count"] = manifest["planned_attempt_count"]
    return result


__all__ = ["GENERATOR_VERSION", "planned_scope_spec"]
