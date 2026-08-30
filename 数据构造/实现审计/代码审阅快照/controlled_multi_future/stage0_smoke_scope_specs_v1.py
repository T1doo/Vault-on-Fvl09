"""Deterministic scope specs for the F4 hash check and Stage 0 roots."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .stage0_smoke_budget_v1 import F4_INFRA_SCOPE, SCOPE_FAMILIES, scope_budget
from .stage0_smoke_manifest_v1 import SCENE_SEED


SCHEMA_VERSION = "cmf_stage0_smoke_scope_spec_v1"


def planned_scope_spec(
    scope: str,
    *,
    stage0_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    family = SCOPE_FAMILIES[scope]
    if scope == F4_INFRA_SCOPE:
        if stage0_manifest is not None:
            raise ValueError("F4 infrastructure scope precedes Stage 0 manifest")
        return {
            "schema_version": SCHEMA_VERSION,
            "slot_id": "prestage0-F4-candidate-hash-infra-v12",
            "family": "F4",
            "scope": scope,
            "seed": SCENE_SEED,
            "arm": "right",
            "generator": "controlled_multi_future_stage0_smoke_v1_adapter_v1_6",
            "origin": "authorized_lightweight_f4_hash_infrastructure_fix",
            "budget_sha256": scope_budget(scope)["scope_budget_sha256"],
            "automatic_retry": False,
            "recovery_attempts": 0,
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": True,
            "required_success": "hash_infrastructure_pass; corridor physical pass optional",
            "stop_condition": "terminal receipt or cleanup/source/GPU uncertainty",
        }
    if not isinstance(stage0_manifest, Mapping):
        raise ValueError("Stage 0 scope requires its frozen manifest")
    manifest = json.loads(
        json.dumps(stage0_manifest, sort_keys=True, allow_nan=False)
    )
    if manifest.get("stage0_authorized") is not True:
        raise ValueError("Stage 0 manifest is not authorized")
    root_spec = manifest.get("root_specs", {}).get(family)
    if not isinstance(root_spec, Mapping) or root_spec.get("scope") != scope:
        raise ValueError("Stage 0 manifest lacks the requested root spec")
    result = json.loads(json.dumps(root_spec, sort_keys=True, allow_nan=False))
    result["stage0_manifest_sha256"] = manifest["manifest_sha256"]
    result["stage0_manifest_attempt_count"] = manifest["planned_attempt_count"]
    return result


__all__ = ["planned_scope_spec"]
