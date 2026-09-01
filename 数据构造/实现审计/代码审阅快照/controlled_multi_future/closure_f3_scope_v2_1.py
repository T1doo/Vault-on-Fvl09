"""Fresh one-shot scope for the interface-fixed F3CommonGraspPrefixV2_1."""

from __future__ import annotations

from pathlib import Path

from .canonical_artifact import canonical_hash_json
from .canonical_artifact import canonical_hash_json as hash_json
from .f3_common_grasp_prefix_v2 import PROGRAM_IDS, build_f3_common_grasp_prefix_v2
from .f3_common_grasp_prefix_v2_1 import IMPLEMENTATION_VERSION


ROOT = Path("/nfs_share/lijunhui")
AUDIT = ROOT / "Vault-on-Fvl09/数据构造/实现审计"
GROUP = "controlled_multi_future_post_stage0_f3_v2_1"
SCOPE = "F3CommonGraspPrefixV2_1_three_scene_prefix_only"
SEED = 20260829
NAMESPACE = "closure_v1_f3_common_grasp_prefix_v2_1_seed20260829_run4"
AUTH_ID = "closure-v1-f3-common-grasp-prefix-v2-1-run4"
OUTPUT = ROOT / "Robotwin2/datasets" / GROUP / NAMESPACE
PARENT = AUDIT / "USER_AUTHORIZATION_F3_V2_1_INTERFACE_FIXED_DIAGNOSTIC_20260831.json"
BUDGET = AUDIT / "POST_STAGE0_F3_V2_1_BUDGET.json"
PUBLICATION = AUDIT / "POST_STAGE0_F3_V2_1_SCOPE.json"
EVIDENCE = AUDIT / "POST_STAGE0_CLOSURE_V1_F3_RESULT.json"
REQUEST = AUDIT / "scope_requests" / GROUP / f"{NAMESPACE}.request.json"
SOURCE = AUDIT / "source_locks" / GROUP / f"{NAMESPACE}.source_lock.json"
AUTH = AUDIT / "authorizations" / GROUP / f"{NAMESPACE}.authorization.json"
GUARD = AUDIT / "gpu_guards" / GROUP / f"{NAMESPACE}.guard.json"


def _sha(value):
    return canonical_hash_json(value)


def budget():
    value = {
        "schema_version": "cmf_post_stage0_f3_v2_1_budget",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "family": "F3",
        "planner_query_limit": 16,
        "execution_limit": 3,
        "fresh_scene_limit": 3,
        "suffix_planner_limit": 0,
        "suffix_execution_limit": 0,
        "release_execution_limit": 0,
        "physics_step_limit": -1,
        "timeout_seconds": 7200,
        "allowed_physical_gpu_indices": list(range(8)),
        "automatic_retry": False,
        "recovery_attempts": 0,
        "maximum_scope_invocations": 1,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage1_authorized": False,
    }
    value["budget_receipt_sha256"] = _sha(value)
    return value


def spec():
    value = {
        "schema_version": "cmf_post_stage0_f3_v2_1_spec",
        "slot_id": "post-stage0-F3CommonGraspPrefixV2_1",
        "scope": SCOPE,
        "family": "F3",
        "arm": "left",
        "seed": SEED,
        "generator": "controlled_multi_future_post_stage0_closure_f3_v2_1_adapter",
        "origin": "post_stage0_f3_v2_1_interface_fix",
        "f3_common_grasp_prefix_v2": build_f3_common_grasp_prefix_v2(),
        "interface_fix_only": True,
        "canonical_program_ids": list(PROGRAM_IDS),
        "diagnostic_scene_count": 3,
        "attempts_per_scene": 1,
        "same_canonical_prefix_artifact": True,
        "prefix_only": True,
        "suffix_allowed": False,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage1_authorized": False,
        "budget_receipt_sha256": budget()["budget_receipt_sha256"],
        "stop_condition": "first terminal physical/infrastructure/cleanup failure or 3/3 pass",
    }
    value["planned_scope_spec_sha256"] = _sha(value)
    return value


def parent():
    value = {
        "schema_version": "cmf_post_stage0_f3_v2_1_parent_authorization",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "approved": True,
        "authorized_scopes": [SCOPE],
        "allowed_physical_gpu_indices": list(range(8)),
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
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
        "schema_version": "cmf_post_stage0_f3_v2_1_publication",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "planned_scope_spec": spec(),
        "budget": budget(),
        "source_failure_result_payload_sha256": (
            "a92469b5a379a3821f76fc17ca54310005f9201a96c03b6030205415025244ae"
        ),
        "stage0_seal_unchanged": True,
    }
    value["scope_publication_sha256"] = _sha(value)
    return value


__all__ = [
    "AUTH",
    "AUTH_ID",
    "BUDGET",
    "EVIDENCE",
    "GROUP",
    "GUARD",
    "NAMESPACE",
    "OUTPUT",
    "PARENT",
    "PUBLICATION",
    "REQUEST",
    "SCOPE",
    "SEED",
    "SOURCE",
    "budget",
    "parent",
    "publication",
    "spec",
]
