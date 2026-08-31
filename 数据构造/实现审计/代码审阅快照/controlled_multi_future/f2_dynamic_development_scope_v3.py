"""Scope and authorization contract for bounded F2 dynamic audit + one root."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


SCOPE = "F2_asset_redesign_dynamic_12_then_one_root_v3"
NAMESPACE = "post_stage0_f2_asset_redesign_dynamic_v3_run1"
AUTHORIZATION_SCHEMA = "cmf_f2_dynamic_development_authorization_v3"
IMPLEMENTATION_VERSION = "controlled_multi_future_f2_asset_redesign_dynamic_v3"
ROOT = Path("/nfs_share/lijunhui")
AUDIT = ROOT / "Vault-on-Fvl09/数据构造/实现审计"
GROUP = "controlled_multi_future_post_stage0_f2_asset_redesign_v3"
AUTH_ID = "post-stage0-f2-asset-redesign-v3-run1"
OUTPUT = ROOT / "Robotwin2/datasets" / GROUP / NAMESPACE
PARENT = AUDIT / "USER_AUTHORIZATION_F2_ASSET_REDESIGN_V3_20260831.json"
BUDGET = AUDIT / "POST_STAGE0_F2_ASSET_REDESIGN_V3_BUDGET.json"
PUBLICATION = AUDIT / "POST_STAGE0_F2_ASSET_REDESIGN_V3_SCOPE.json"
MATRIX = AUDIT / "F2_OFFICIAL_ASSET_COMPATIBILITY_MATRIX_V3.json"
SCREENING = AUDIT / "F2_CPU_STATIC_SCREENING_V3.json"
REQUEST = AUDIT / "scope_requests" / GROUP / f"{NAMESPACE}.request.json"
SOURCE = AUDIT / "source_locks" / GROUP / f"{NAMESPACE}.source_lock.json"
AUTH = AUDIT / "authorizations" / GROUP / f"{NAMESPACE}.authorization.json"
GUARD = AUDIT / "gpu_guards" / GROUP / f"{NAMESPACE}.guard.json"


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))


def _hash_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def f2_dynamic_development_budget_v3() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_f2_dynamic_development_budget_v3",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "maximum_dynamic_candidates": 12,
        "maximum_passive_on_scenes": 12,
        "maximum_planner_only_roots": 12,
        "maximum_development_execution_roots": 1,
        "maximum_prefix_reference_executions": 13,
        "maximum_suffix_execution_attempts": 3,
        "maximum_planner_queries_total": 768,
        "maximum_recovery_attempts": 0,
        "maximum_wall_time_seconds": 21600,
        "single_use": True,
        "automatic_retry": False,
        "fallback_beyond_candidate_12": False,
        "allowed_physical_gpu_indices": list(range(8)),
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
        "root_sharding_authorized": False,
        "development_mp4_required_per_generated_trajectory": True,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["budget_receipt_sha256"] = _hash_json(value)
    return value


def parent_authorization_v3() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_f2_asset_redesign_parent_authorization_v3",
        "approved": True,
        "authorized_scopes": [SCOPE],
        "allowed_physical_gpu_indices": list(range(8)),
        "single_use": True,
        "automatic_retry": False,
        "stage0_reopened": False,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
        "user_direction_source": "https://chatgpt.com/s/t_6a95674546fc81918e8287f959e8e46c",
    }
    value["parent_user_authorization_sha256"] = _hash_json(value)
    return value


def validate_f2_dynamic_development_authorization_v3(
    value: Mapping[str, Any], *, matrix_sha256: str, screening_sha256: str
) -> dict[str, Any]:
    result = _copy(value)
    digest = result.pop("authorization_sha256", None)
    if not isinstance(digest, str) or _hash_json(result) != digest:
        raise ValueError("F2 dynamic development authorization hash mismatch")
    budget = f2_dynamic_development_budget_v3()
    checks = {
        "schema": result.get("schema_version") == AUTHORIZATION_SCHEMA,
        "scope": result.get("scope") == SCOPE,
        "namespace": result.get("output_namespace") == NAMESPACE,
        "matrix": result.get("matrix_sha256") == matrix_sha256,
        "screening": result.get("screening_sha256") == screening_sha256,
        "budget": result.get("budget") == budget
        and result.get("budget_sha256") == _hash_json(budget),
        "approved": result.get("approved") is True,
        "source_lock": isinstance(result.get("source_lock_receipt_sha256"), str)
        and len(result["source_lock_receipt_sha256"]) == 64
        and isinstance(result.get("implementation_source_sha256"), str)
        and len(result["implementation_source_sha256"]) == 64,
        "gpu_policy": result.get("allowed_physical_gpu_indices") == list(range(8))
        and result.get("single_use") is True
        and result.get("automatic_retry") is False
        and result.get("one_root_one_gpu") is True,
        "not_stage0_formal": result.get("formal_data") is False
        and result.get("stage0_data") is False
        and result.get("stage1_authorized") is False,
    }
    if not all(checks.values()):
        raise ValueError(f"F2 dynamic development authorization failed: {checks}")
    return {**result, "authorization_sha256": digest}


def planned_f2_asset_bound_root_spec_v3(binding: Mapping[str, Any], *, slot_id: str) -> dict[str, Any]:
    value = {
        "schema_version": "cmf_f2_asset_bound_planned_root_spec_v3",
        "slot_id": slot_id,
        "family": "F2",
        "seed": 20260829,
        "generator": "controlled_multi_future_f2_asset_redesign_v3",
        "program_ids": ["F2-inside", "F2-on", "F2-beside"],
        "f2_asset_layout_binding_v3": _copy(binding),
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["planned_root_slot_spec_sha256"] = _hash_json(value)
    return value


__all__ = [
    "NAMESPACE",
    "SCOPE",
    "f2_dynamic_development_budget_v3",
    "parent_authorization_v3",
    "planned_f2_asset_bound_root_spec_v3",
    "validate_f2_dynamic_development_authorization_v3",
]
