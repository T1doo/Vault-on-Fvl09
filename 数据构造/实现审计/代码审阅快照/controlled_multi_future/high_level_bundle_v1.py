"""CPU publications and one-shot bundle issuer for High-Level V1."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_write_json
from .f2_hierarchical_template_search_v1 import (
    build_f2_hierarchical_template_search_v1,
)
from .f3_asset_grasp_qualification_v2 import (
    build_f3_asset_grasp_qualification_v2,
)
from .f4_hierarchical_template_search_v1 import (
    build_f4_hierarchical_template_search_v1,
)
from .gpu_parallel_policy_v2 import current_gpu_policy_artifact
from .high_level_runtime_specs_v1 import (
    build_f2_runtime_spec_v1,
    build_f3_runtime_spec_v1,
    build_f4_runtime_spec_v1,
    job_budget_v1,
    validate_f2_runtime_spec_v1,
    validate_f3_runtime_spec_v1,
    validate_f4_runtime_spec_v1,
)
from .high_level_template_redesign_v1 import (
    build_high_level_template_redesign_v1,
)
from .probes.gpu_guard_v2_1 import command_sha256
from .probes.high_level_authorization_v1 import (
    AUTH_SCHEMA,
    IMPLEMENTATION_VERSION,
    JOB_KINDS,
    JOB_PURPOSES,
    receipt_sha,
    validate as validate_authorization,
)
from .probes.runtime_v3_3_authorization_v1 import (
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)
from .runtime_source_lock_v1 import (
    capture_runtime_source_lock,
    load_runtime_source_lock,
)


WORKSPACE = Path("/nfs_share/lijunhui")
VAULT = WORKSPACE / "Vault-on-Fvl09"
AUDIT = VAULT / "数据构造/实现审计"
DATASET_GROUP = (
    WORKSPACE
    / "Robotwin2/datasets/controlled_multi_future_high_level_template_redesign_v1"
)
PARENT_PATH = AUDIT / "HIGH_LEVEL_TEMPLATE_REDESIGN_V1_2_7_PARENT_AUTHORIZATION.json"
REGISTRY_PATH = AUDIT / "HIGH_LEVEL_TEMPLATE_REDESIGN_V1_2_7_REGISTRY.json"
F2_PUBLICATION_PATH = AUDIT / "F2_HIERARCHICAL_TEMPLATE_SEARCH_V1.json"
F3_PUBLICATION_PATH = AUDIT / "F3_ASSET_GRASP_QUALIFICATION_V2.json"
F4_PUBLICATION_PATH = AUDIT / "F4_HIERARCHICAL_TEMPLATE_SEARCH_V1.json"
AUTH_DIRECTORY = AUDIT / "authorizations/high_level_template_redesign_v1"
REQUEST_DIRECTORY = AUDIT / "scope_requests/high_level_template_redesign_v1"
SOURCE_DIRECTORY = AUDIT / "source_locks/high_level_template_redesign_v1"
GUARD_DIRECTORY = AUDIT / "gpu_guards/high_level_template_redesign_v1"
PYTHON = Path("/nfs_share/lijunhui/Robotwin2/env/bin/python")
CHILD_MODULE = "controlled_multi_future.probes.high_level_scope_runner_v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_parent_authorization_v1() -> dict[str, Any]:
    parent = build_high_level_template_redesign_v1()
    value = {
        "schema_version": "cmf_high_level_template_redesign_parent_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "approved": True,
        "parent_contract_sha256": parent["parent_contract_sha256"],
        "authorized_scopes": sorted(set(JOB_PURPOSES.values())),
        "authorized_job_kinds": sorted(JOB_KINDS),
        "allowed_physical_gpu_indices": list(range(8)),
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
        "root_sharding_authorized": False,
        "candidate_parallelism_authorized": True,
        "selection_by_completion_speed_forbidden": True,
        "selection_rule": "lowest frozen rank passing every applicable Gate",
        "stage0_reopened": False,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
        "h_reveal_authorized": False,
        "compression_authorized": False,
        "pi05_authorized": False,
        "user_direction_source": (
            "https://chatgpt.com/s/t_6a96cfca88248191af0973460bddd3fd"
        ),
    }
    value["parent_user_authorization_sha256"] = canonical_hash_json(value)
    return value


def build_cpu_registry_v1() -> dict[str, Any]:
    parent_contract = build_high_level_template_redesign_v1()
    f2 = build_f2_hierarchical_template_search_v1()
    f3 = build_f3_asset_grasp_qualification_v2()
    f4 = build_f4_hierarchical_template_search_v1()
    value = {
        "schema_version": "cmf_high_level_template_redesign_registry_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "parent_contract_sha256": parent_contract["parent_contract_sha256"],
        "f1_reference": parent_contract["f1_reference"],
        "f2": {
            "contract_sha256": f2["search_contract_sha256"],
            "candidate_ids": f2["fixed_inside_candidate_order"],
            "candidate_count": len(f2["inside_candidates"]),
            "maximum_physical": f2["maximum_real_inside_executions"],
        },
        "f3": {
            "contract_sha256": f3["qualification_sha256"],
            "selected_asset_model_ids": f3["selected_asset_model_ids"],
            "tuple_ids": f3["fixed_tuple_order"],
            "tuple_count": len(f3["grasp_tuples"]),
            "maximum_physical": f3["maximum_physical_tuples"],
        },
        "f4": {
            "contract_sha256": f4["search_contract_sha256"],
            "candidate_ids": f4["fixed_stage_a_order"],
            "candidate_count": len(f4["stage_a_candidates"]),
        },
        "job_budgets": {
            job_kind: job_budget_v1(purpose)
            for job_kind, purpose in JOB_PURPOSES.items()
        },
        "gpu_policy": current_gpu_policy_artifact(),
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["registry_sha256"] = canonical_hash_json(value)
    return value


def write_cpu_publications_v1() -> dict[str, Any]:
    parent = build_parent_authorization_v1()
    registry = build_cpu_registry_v1()
    publications = {
        PARENT_PATH: parent,
        REGISTRY_PATH: registry,
        F2_PUBLICATION_PATH: build_f2_hierarchical_template_search_v1(),
        F3_PUBLICATION_PATH: build_f3_asset_grasp_qualification_v2(),
        F4_PUBLICATION_PATH: build_f4_hierarchical_template_search_v1(),
    }
    result = {}
    for path, value in publications.items():
        result[path.name] = canonical_write_json(
            path, value, exclusive=True, mode=0o600
        )
    return result


def _validate_spec_for_job(job_kind: str, spec: Mapping[str, Any]):
    if job_kind.startswith("F2_"):
        value = validate_f2_runtime_spec_v1(spec)
    elif job_kind.startswith("F3_"):
        value = validate_f3_runtime_spec_v1(spec)
    elif job_kind.startswith("F4_"):
        value = validate_f4_runtime_spec_v1(spec)
    else:
        raise ValueError("unsupported high-level job kind")
    if value["purpose"] != JOB_PURPOSES[job_kind]:
        raise ValueError("high-level job kind/purpose mismatch")
    return value


def ensure_family_source_lock_v1(family: str) -> tuple[Path, dict[str, Any]]:
    receipt = capture_runtime_source_lock(family=family)
    source_hash = receipt["snapshot"]["implementation_source_sha256"]
    path = SOURCE_DIRECTORY / f"{family.lower()}_{source_hash}.json"
    if path.exists():
        existing = load_runtime_source_lock(path, expected_family=family)
        if existing != receipt:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            path = SOURCE_DIRECTORY / f"{family.lower()}_{source_hash}_{stamp}.json"
            canonical_write_json(path, receipt, exclusive=True, mode=0o600)
        else:
            receipt = existing
    else:
        canonical_write_json(path, receipt, exclusive=True, mode=0o600)
    return path, receipt


def _published_head(reviewed_content_commit: str) -> None:
    if HEX40.fullmatch(reviewed_content_commit) is None:
        raise ValueError("reviewed Vault commit must be a 40-character SHA")
    local = subprocess.run(
        ["git", "-C", str(VAULT), "rev-parse", "HEAD"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()
    remote = subprocess.run(
        ["git", "-C", str(VAULT), "rev-parse", "origin/main"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()
    if reviewed_content_commit != local or local != remote:
        raise ValueError("reviewed commit must equal published local/remote HEAD")


def issue_job_bundle_v1(
    *,
    job_kind: str,
    authorization_id: str,
    planned_root_slot_spec: Mapping[str, Any],
    reviewed_content_commit: str,
    job_inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    _published_head(reviewed_content_commit)
    if job_kind not in JOB_KINDS:
        raise ValueError("unsupported high-level job kind")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]+", authorization_id):
        raise ValueError("authorization ID is not path-safe")
    spec = _validate_spec_for_job(job_kind, planned_root_slot_spec)
    family = spec["family"]
    budget = job_budget_v1(spec["purpose"])
    output = DATASET_GROUP / authorization_id
    auth_path = AUTH_DIRECTORY / f"{authorization_id}.authorization.json"
    request_path = REQUEST_DIRECTORY / f"{authorization_id}.request.json"
    guard_path = GUARD_DIRECTORY / f"{authorization_id}.guard.json"
    if any(path.exists() for path in (output, auth_path, request_path, guard_path)):
        raise FileExistsError("high-level job namespace must be new")
    source_path, source = ensure_family_source_lock_v1(family)
    parent = json.loads(PARENT_PATH.read_text(encoding="utf-8"))
    parent_digest = parent["parent_user_authorization_sha256"]
    command = [
        str(PYTHON),
        "-m",
        CHILD_MODULE,
        "--authorization-receipt",
        str(auth_path.resolve()),
    ]
    command_digest = command_sha256(command)
    inputs = dict(job_inputs or {})
    request = {
        "schema_version": "cmf_high_level_template_scope_request_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": authorization_id,
        "job_kind": job_kind,
        "scope": spec["scope"],
        "family": family,
        "scene_seed": spec["seed"],
        "planned_root_slot_spec_sha256": spec["planned_scope_spec_sha256"],
        "job_inputs_sha256": canonical_hash_json(inputs),
        "output_namespace": str(output.resolve()),
        "guard_receipt_path": str(guard_path.resolve()),
        "authorized_command": command,
        "authorized_command_sha256": command_digest,
        "source_lock_receipt_sha256": source["source_lock_receipt_sha256"],
        "parent_user_authorization_sha256": parent_digest,
        "allowed_physical_gpu_indices": list(range(8)),
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    request["scope_request_sha256"] = canonical_hash_json(request)
    canonical_write_json(request_path, request, exclusive=True, mode=0o600)
    issued = datetime.now(timezone.utc)
    policy = current_gpu_policy_artifact()
    authorization = {
        "schema_version": AUTH_SCHEMA,
        "implementation_version": IMPLEMENTATION_VERSION,
        "approved": True,
        "approved_scopes": [spec["scope"]],
        "authorization_id": authorization_id,
        "authorized_run_id": authorization_id + "-run",
        "job_kind": job_kind,
        "family": family,
        "scene_seed": spec["seed"],
        "planned_root_slot_spec": spec,
        "planned_root_slot_spec_sha256": spec["planned_scope_spec_sha256"],
        "job_inputs": inputs,
        "budget": budget,
        "budget_receipt_sha256": budget["budget_receipt_sha256"],
        "planner_query_limit": budget["planner_query_limit"],
        "controlled_action_limit": budget["controlled_action_limit"],
        "physics_step_limit": budget["physics_step_limit"],
        "timeout_seconds": budget["timeout_seconds"],
        "max_invocations": 1,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage1_authorized": False,
        "issued_at": issued.isoformat(),
        "expires_at": (issued + timedelta(minutes=60)).isoformat(),
        "source_lock_receipt_path": str(source_path.resolve()),
        "source_lock_receipt_sha256": source["source_lock_receipt_sha256"],
        "implementation_source_sha256": source["snapshot"][
            "implementation_source_sha256"
        ],
        "approval_request_path": str(request_path.resolve()),
        "approval_request_file_sha256": _file_sha(request_path),
        "approval_request_sha256": request["scope_request_sha256"],
        "parent_user_authorization_path": str(PARENT_PATH.resolve()),
        "parent_user_authorization_file_sha256": _file_sha(PARENT_PATH),
        "parent_user_authorization_sha256": parent_digest,
        "consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        "gpu_lease_directory": CANONICAL_GPU_LEASE_DIRECTORY,
        "job_cache_root_directory": CANONICAL_JOB_CACHE_DIRECTORY,
        "output_namespace": str(output.resolve()),
        "guard_receipt_path": str(guard_path.resolve()),
        "authorized_command_sha256": command_digest,
        "reviewed_content_commit": reviewed_content_commit,
        **{
            key: policy[key]
            for key in (
                "gpu_policy_version",
                "allowed_physical_gpu_indices",
                "dynamic_fresh_idle_selection",
                "parallel_different_cards_authorized",
                "one_project_job_per_gpu",
                "one_root_one_gpu",
                "root_sharding_authorized",
                "share_busy_gpu_authorized",
                "atomic_guard_recheck_before_launch",
                "automatic_gpu0_fallback",
            )
        },
    }
    authorization["receipt_sha256"] = receipt_sha(authorization)
    canonical_write_json(auth_path, authorization, exclusive=True, mode=0o600)
    validate_authorization(
        authorization,
        requested_scope=spec["scope"],
        expected_output_namespace=str(output.resolve()),
        expected_family=family,
        expected_seed=spec["seed"],
        expected_reviewed_content_commit=reviewed_content_commit,
    )
    return {
        "authorization": authorization,
        "authorization_path": str(auth_path.resolve()),
        "request": request,
        "request_path": str(request_path.resolve()),
        "source_lock": source,
        "source_lock_path": str(source_path.resolve()),
        "guard_path": str(guard_path.resolve()),
        "output_namespace": str(output.resolve()),
        "command": command,
    }


__all__ = [
    "AUDIT",
    "DATASET_GROUP",
    "PARENT_PATH",
    "REGISTRY_PATH",
    "build_cpu_registry_v1",
    "build_parent_authorization_v1",
    "ensure_family_source_lock_v1",
    "issue_job_bundle_v1",
    "write_cpu_publications_v1",
]
