"""Static publications and one-shot bundle issuer for consolidation V1."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_write_json
from .f2_exact_replay_v1 import (
    SCOPE as F2_SCOPE,
    build_f2_exact_replay_spec_v1,
    build_f2_exact_replay_v1,
    validate_f2_exact_replay_spec_v1,
)
from .f3_grasp_qualification_v1 import (
    SCOPE as F3_SCOPE,
    build_f3_grasp_qualification_v1,
    validate_f3_grasp_candidate_spec_v1,
)
from .f4_template_qualification_v1 import (
    SCOPE as F4_SCOPE,
    build_f4_template_qualification_v1,
    validate_f4_template_candidate_spec_v1,
)
from .gpu_parallel_policy_v2 import current_gpu_policy_artifact
from .probes.development_consolidation_authorization_v1 import (
    AUTH_SCHEMA,
    IMPLEMENTATION_VERSION,
    job_budget_v1,
    receipt_sha,
)
from .probes.gpu_guard_v2_1 import command_sha256
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
AUDIT = WORKSPACE / "Vault-on-Fvl09/数据构造/实现审计"
DATASET_GROUP = (
    WORKSPACE
    / "Robotwin2/datasets/controlled_multi_future_development_consolidation_v1"
)
PARENT_PATH = AUDIT / "DEVELOPMENT_PIPELINE_CONSOLIDATION_V1_PARENT_AUTHORIZATION.json"
REGISTRY_PATH = AUDIT / "DEVELOPMENT_PIPELINE_CONSOLIDATION_V1_REGISTRY.json"
F2_PUBLICATION_PATH = AUDIT / "F2_EXACT_REPLAY_V1_SCOPE.json"
F3_PUBLICATION_PATH = AUDIT / "F3_GRASP_QUALIFICATION_V1.json"
F4_PUBLICATION_PATH = AUDIT / "F4_TEMPLATE_QUALIFICATION_V1.json"
AUTH_DIRECTORY = AUDIT / "authorizations/development_pipeline_consolidation_v1"
REQUEST_DIRECTORY = AUDIT / "scope_requests/development_pipeline_consolidation_v1"
SOURCE_DIRECTORY = AUDIT / "source_locks/development_pipeline_consolidation_v1"
GUARD_DIRECTORY = AUDIT / "gpu_guards/development_pipeline_consolidation_v1"
PYTHON = Path("/nfs_share/lijunhui/Robotwin2/env/bin/python")
CHILD_MODULE = (
    "controlled_multi_future.probes.development_consolidation_scope_runner_v1"
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_parent_authorization_v1() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_development_pipeline_consolidation_parent_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "approved": True,
        "authorized_scopes": [F2_SCOPE, F3_SCOPE, F4_SCOPE],
        "authorized_job_kinds": [
            "F2_EXACT_REPLAY",
            "F3_PLANNER_SCREEN",
            "F3_PHYSICAL_CANDIDATE",
            "F3_THREE_SCENE_CONFIRMATION",
            "F3_FULL_ROOT",
            "F4_TEMPLATE_CANDIDATE",
            "F4_A_ONLY",
            "F4_FULL_ROOT",
        ],
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
            "/home/lijunhui/.codex/attachments/"
            "1398376c-11fc-42fd-b549-60066eea76da/pasted-text-1.txt"
        ),
    }
    value["parent_user_authorization_sha256"] = canonical_hash_json(value)
    return value


def build_cpu_registry_v1(
    matrix: Mapping[str, Any], screening: Mapping[str, Any]
) -> dict[str, Any]:
    f2 = build_f2_exact_replay_v1(matrix, screening)
    f3 = build_f3_grasp_qualification_v1()
    f4 = build_f4_template_qualification_v1()
    value = {
        "schema_version": "cmf_development_pipeline_consolidation_registry_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "canonical_serialization_module": "controlled_multi_future/canonical_artifact.py",
        "f1_regression": {
            "frozen_contract_canonical_sha256": (
                "60d303df5392b139eac29ed189e287e77988c08b6ee7554e1e4b1941451a78e7"
            ),
            "template_redesign": False,
            "existing_development_roots": 5,
            "existing_development_trajectories": 15,
        },
        "f2": f2,
        "f3": f3,
        "f4": f4,
        "job_budgets": {
            kind: job_budget_v1(kind)
            for kind in (
                "F2_EXACT_REPLAY",
                "F3_PLANNER_SCREEN",
                "F3_PHYSICAL_CANDIDATE",
                "F3_THREE_SCENE_CONFIRMATION",
                "F3_FULL_ROOT",
                "F4_TEMPLATE_CANDIDATE",
                "F4_A_ONLY",
                "F4_FULL_ROOT",
            )
        },
        "gpu_policy": current_gpu_policy_artifact(),
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["registry_sha256"] = canonical_hash_json(value)
    return value


def write_cpu_publications_v1(
    matrix: Mapping[str, Any], screening: Mapping[str, Any]
) -> dict[str, Any]:
    parent = build_parent_authorization_v1()
    registry = build_cpu_registry_v1(matrix, screening)
    publications = {
        PARENT_PATH: parent,
        REGISTRY_PATH: registry,
        F2_PUBLICATION_PATH: {
            "schema_version": "cmf_f2_exact_replay_publication_v1",
            "planned_root_slot_spec": build_f2_exact_replay_spec_v1(
                matrix, screening
            ),
            "parent_user_authorization_sha256": parent[
                "parent_user_authorization_sha256"
            ],
        },
        F3_PUBLICATION_PATH: {
            "schema_version": "cmf_f3_grasp_qualification_publication_v1",
            "qualification": registry["f3"],
            "parent_user_authorization_sha256": parent[
                "parent_user_authorization_sha256"
            ],
        },
        F4_PUBLICATION_PATH: {
            "schema_version": "cmf_f4_template_qualification_publication_v1",
            "qualification": registry["f4"],
            "parent_user_authorization_sha256": parent[
                "parent_user_authorization_sha256"
            ],
        },
    }
    result = {}
    for path, value in publications.items():
        if path not in (PARENT_PATH, REGISTRY_PATH):
            value["publication_sha256"] = canonical_hash_json(value)
        result[path.name] = canonical_write_json(
            path, value, exclusive=True, mode=0o600
        )
    return result


def _validate_spec_for_job(job_kind: str, spec: Mapping[str, Any]) -> dict[str, Any]:
    if job_kind == "F2_EXACT_REPLAY":
        return validate_f2_exact_replay_spec_v1(spec)
    if job_kind.startswith("F3_"):
        return validate_f3_grasp_candidate_spec_v1(spec)
    return validate_f4_template_candidate_spec_v1(spec)


def ensure_family_source_lock_v1(family: str) -> tuple[Path, dict[str, Any]]:
    receipt = capture_runtime_source_lock(family=family)
    source_hash = receipt["snapshot"]["implementation_source_sha256"]
    path = SOURCE_DIRECTORY / f"{family.lower()}_{source_hash}.json"
    if path.exists():
        existing = load_runtime_source_lock(path, expected_family=family)
        if existing != receipt:
            # captured_at is expected to differ.  Reuse only when the immutable
            # snapshot and receipt already match exactly; otherwise make a new
            # timestamp-qualified source-lock path.
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            path = SOURCE_DIRECTORY / f"{family.lower()}_{source_hash}_{stamp}.json"
            canonical_write_json(path, receipt, exclusive=True, mode=0o600)
        else:
            receipt = existing
    else:
        canonical_write_json(path, receipt, exclusive=True, mode=0o600)
    return path, receipt


def issue_job_bundle_v1(
    *,
    job_kind: str,
    authorization_id: str,
    planned_root_slot_spec: Mapping[str, Any],
    reviewed_content_commit: str,
    job_inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if HEX40.fullmatch(reviewed_content_commit) is None:
        raise ValueError("reviewed Vault commit must be a 40-character SHA")
    local_head = subprocess.run(
        ["git", "-C", str(AUDIT.parents[1]), "rev-parse", "HEAD"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()
    remote_head = subprocess.run(
        ["git", "-C", str(AUDIT.parents[1]), "rev-parse", "origin/main"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()
    if reviewed_content_commit != local_head or local_head != remote_head:
        raise ValueError(
            "reviewed Vault commit must equal clean published local HEAD and origin/main"
        )
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]+", authorization_id):
        raise ValueError("authorization ID is not path-safe")
    spec = _validate_spec_for_job(job_kind, planned_root_slot_spec)
    family = spec["family"]
    budget = job_budget_v1(job_kind)
    output = DATASET_GROUP / authorization_id
    auth_path = AUTH_DIRECTORY / f"{authorization_id}.authorization.json"
    request_path = REQUEST_DIRECTORY / f"{authorization_id}.request.json"
    guard_path = GUARD_DIRECTORY / f"{authorization_id}.guard.json"
    if any(path.exists() for path in (output, auth_path, request_path, guard_path)):
        raise FileExistsError("consolidation job namespace must be new")
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
        "schema_version": "cmf_development_consolidation_scope_request_v1",
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
