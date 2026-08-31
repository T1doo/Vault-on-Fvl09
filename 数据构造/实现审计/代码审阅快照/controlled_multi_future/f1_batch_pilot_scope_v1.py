"""Bounded GPU scope for the five-root F1 development batch pilot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .current_hasher import hash_json
from .f1_batch_generation_pilot_v1 import (
    IMPLEMENTATION_VERSION,
    build_f1_batch_pilot_plan_v1,
)


ROOT = Path("/nfs_share/lijunhui")
AUDIT = ROOT / "Vault-on-Fvl09/数据构造/实现审计"
GROUP = "controlled_multi_future_post_stage0_f1_batch_pilot_v1"
SCOPE = "F1_five_root_development_batch_pilot_v1"
NAMESPACE = "post_stage0_f1_batch_pilot_v1_run3"
AUTH_ID = "post-stage0-f1-batch-pilot-v1-run3"
OUTPUT = ROOT / "Robotwin2/datasets" / GROUP / NAMESPACE
PARENT = AUDIT / "USER_AUTHORIZATION_F1_BATCH_PILOT_V1_20260831.json"
BUDGET = AUDIT / "POST_STAGE0_F1_BATCH_PILOT_V1_BUDGET.json"
PUBLICATION = AUDIT / "POST_STAGE0_F1_BATCH_PILOT_V1_SCOPE.json"
EVIDENCE = AUDIT / "POST_STAGE0_CLOSURE_V1_REPORT.json"
REQUEST = AUDIT / "scope_requests" / GROUP / f"{NAMESPACE}.request.json"
SOURCE = AUDIT / "source_locks" / GROUP / f"{NAMESPACE}.source_lock.json"
AUTH = AUDIT / "authorizations" / GROUP / f"{NAMESPACE}.authorization.json"
GUARD = AUDIT / "gpu_guards" / GROUP / f"{NAMESPACE}.guard.json"


def _sha(value):
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def budget():
    value = {
        "schema_version": "cmf_f1_batch_pilot_scope_budget_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "family": "F1",
        "primary_root_limit": 5,
        "ordered_reserve_activation_limit": 5,
        "total_root_attempt_limit": 10,
        "trajectory_execution_limit": 30,
        "planner_query_limit": 320,
        "fresh_scene_limit": 160,
        "recovery_attempt_limit": 0,
        "timeout_seconds": 28800,
        "allowed_physical_gpu_indices": list(range(8)),
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
        "root_sharding_authorized": False,
        "automatic_retry": False,
        "maximum_scope_invocations": 1,
        "development_raw_required": True,
        "development_mp4_required": True,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage1_authorized": False,
    }
    value["budget_receipt_sha256"] = _sha(value)
    return value


def spec():
    plan = build_f1_batch_pilot_plan_v1()
    value = {
        "schema_version": "cmf_f1_batch_pilot_scope_spec_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "family": "F1",
        "plan": plan,
        "plan_sha256": plan["plan_sha256"],
        "root_execution_order": "all five primary slots in rank order, then activated reserves in activation order",
        "reserve_activation_rule": plan["reserve_activation_rule"],
        "stop_condition": "five accepted development roots or ordered reserve exhaustion",
        "each_root_at_most_once": True,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "development_raw_required": True,
        "development_mp4_required": True,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage1_authorized": False,
        "budget_receipt_sha256": budget()["budget_receipt_sha256"],
    }
    value["planned_scope_spec_sha256"] = _sha(value)
    return value


def parent():
    value = {
        "schema_version": "cmf_post_stage0_f1_batch_pilot_parent_authorization_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "approved": True,
        "authorized_scopes": [SCOPE],
        "allowed_physical_gpu_indices": list(range(8)),
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
        "root_sharding_authorized": False,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "stage0_reopened": False,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
        "h_reveal": None,
        "compression_authorized": False,
        "pi05_authorized": False,
        "user_direction_source": "https://chatgpt.com/s/t_6a95674546fc81918e8287f959e8e46c",
    }
    value["parent_user_authorization_sha256"] = hash_json(value)
    return value


def publication():
    value = {
        "schema_version": "cmf_post_stage0_f1_batch_pilot_publication_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "planned_scope_spec": spec(),
        "budget": budget(),
        "stage0_seal_unchanged": True,
    }
    value["scope_publication_sha256"] = _sha(value)
    return value


__all__ = [name for name in tuple(globals()) if name.isupper()] + [
    "budget",
    "parent",
    "publication",
    "spec",
]
