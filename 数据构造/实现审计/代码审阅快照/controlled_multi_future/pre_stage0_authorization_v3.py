"""Builders for parent authorization, frozen scope requests, and child receipts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from .current_hasher import hash_json
from .probes.gpu_guard_v2_1 import command_sha256
from .probes.runtime_v3_3_authorization_v1 import (
    ALLOWED_UUID_POLICY,
    AUTHORIZATION_SCHEMA_VERSION,
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
    CANONICAL_REVISION_LEDGER_DIRECTORY,
    authorization_receipt_sha256,
    canonical_sha256,
    current_source_bindings_v3_3,
    sha256_file,
)
from .runtime_source_lock_v1 import validate_runtime_source_lock
from .runtime_v3_3_budget_v1 import (
    ROOT_SCOPES,
    authorization_common_limits,
    scope_budget,
)


PARENT_SCHEMA_VERSION = "cmf_pre_stage0_user_authorization_v3_3_v1_1"
SCOPE_REQUEST_SCHEMA_VERSION = "cmf_pre_stage0_gpu_scope_request_v3_1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
WORKSPACE_PREFIX = "/nfs_share/lijunhui/"


def _workspace_path(value: str, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or not str(path).startswith(WORKSPACE_PREFIX):
        raise ValueError(f"{label} must be an absolute workspace path")
    return path


def validate_parent_user_authorization(value: Mapping[str, Any]) -> dict:
    if not isinstance(value, Mapping) or value.get("schema_version") != PARENT_SCHEMA_VERSION:
        raise ValueError("parent user authorization schema mismatch")
    if value.get("approved") is not True:
        raise ValueError("parent user authorization is not approved")
    for key in (
        "formal_stage0_authorized",
        "stage1_authorized",
        "formal_collection_authorized",
        "training_authorized",
    ):
        if value.get(key) is not False:
            raise ValueError(f"parent user authorization must keep {key}=false")
    fixed = {
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_3",
        "formal_data": False,
        "stage0_data": False,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "maximum_new_implementation_revisions_per_family": 2,
        "maximum_full_root_execution_per_revision": 1,
        "allowed_physical_gpu_indices": list(range(8)),
        "parallel_independent_jobs": True,
    }
    for key, expected in fixed.items():
        if value.get(key) != expected:
            raise ValueError(f"parent user authorization rejected field {key}")
    payload = dict(value)
    expected = payload.pop("parent_user_authorization_sha256", None)
    if not isinstance(expected, str) or canonical_sha256(payload) != expected:
        raise ValueError("parent user authorization content hash mismatch")
    markdown_path = _workspace_path(value["authorization_markdown_path"], "authorization_markdown_path")
    if not markdown_path.is_file() or sha256_file(markdown_path) != value.get("authorization_markdown_sha256"):
        raise ValueError("parent user authorization Markdown hash mismatch")
    return dict(value)


def load_parent_user_authorization(path: Path) -> dict:
    path = Path(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    return validate_parent_user_authorization(value)


def build_scope_request(
    *,
    parent_user_authorization: Mapping[str, Any],
    scope: str,
    family: str,
    scene_seed: int,
    planned_root_slot_spec: Mapping[str, Any],
    reviewed_content_commit: str,
    authorization_receipt_path: str,
    source_lock_receipt_path: str,
    consumption_ledger_directory: str,
    revision_ledger_directory: str | None,
    family_revision_index: int | None,
    guard_receipt_path: str,
    output_namespace: str,
    exact_child_command: Sequence[str],
    allowed_physical_gpu_indices: Sequence[int] = tuple(range(8)),
    reviewed_publication: Mapping[str, Any] | None = None,
) -> dict:
    parent = validate_parent_user_authorization(parent_user_authorization)
    if HEX40.fullmatch(reviewed_content_commit) is None:
        raise ValueError("reviewed_content_commit must be a full Git SHA")
    if not isinstance(reviewed_publication, Mapping):
        raise ValueError("scope request requires a reviewed publication receipt")
    publication = json.loads(
        json.dumps(
            reviewed_publication,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
    )
    if (
        publication.get("reviewed_content_commit") != reviewed_content_commit
        or publication.get("origin_main") != reviewed_content_commit
        or publication.get("vault_worktree_clean") is not True
        or publication.get("active_snapshot_source_sha256")
        != current_source_bindings_v3_3()["implementation_source_sha256"]
    ):
        raise ValueError("scope request reviewed publication binding is invalid")
    for label, value in (
        ("authorization_receipt_path", authorization_receipt_path),
        ("source_lock_receipt_path", source_lock_receipt_path),
        ("consumption_ledger_directory", consumption_ledger_directory),
        ("guard_receipt_path", guard_receipt_path),
        ("output_namespace", output_namespace),
    ):
        _workspace_path(value, label)
    if consumption_ledger_directory != CANONICAL_CONSUMPTION_LEDGER_DIRECTORY:
        raise ValueError("scope request consumption ledger is not canonical")
    if scope in ROOT_SCOPES:
        if family_revision_index not in (1, 2):
            raise ValueError("root scope family_revision_index must be 1 or 2")
        if not isinstance(revision_ledger_directory, str):
            raise ValueError("root scope requires revision_ledger_directory")
        _workspace_path(revision_ledger_directory, "revision_ledger_directory")
        if revision_ledger_directory != CANONICAL_REVISION_LEDGER_DIRECTORY:
            raise ValueError("scope request revision ledger is not canonical")
    elif family_revision_index is not None or revision_ledger_directory is not None:
        raise ValueError("non-root scopes cannot consume a family revision slot")
    indices = list(allowed_physical_gpu_indices)
    if indices != list(range(8)):
        raise ValueError(
            "runtime-v3_3 scope requests must allow exactly physical GPU0-7; "
            "the atomic Guard selects one independently fresh-idle card"
        )
    budget = scope_budget(scope)
    if budget["family"] != family:
        raise ValueError("scope request family differs from budget")
    planned = json.loads(json.dumps(planned_root_slot_spec, ensure_ascii=False, sort_keys=True, allow_nan=False))
    if planned.get("family") != family or planned.get("seed") != scene_seed:
        raise ValueError("scope request planned spec family/seed mismatch")
    if scope in ROOT_SCOPES and planned.get("implementation_revision_index") != family_revision_index:
        raise ValueError("planned spec revision index differs from root scope")
    if scope in ROOT_SCOPES and not isinstance(
        planned.get("implementation_revision"), str
    ):
        raise ValueError("planned root spec lacks implementation_revision")
    planner, controlled, physics, timeout = authorization_common_limits(scope)
    request = {
        "schema_version": SCOPE_REQUEST_SCHEMA_VERSION,
        "status": "approved_by_parent_user_authorization_pending_one_shot_issue",
        "parent_user_authorization_sha256": parent["parent_user_authorization_sha256"],
        "scope": scope,
        "family": family,
        "scene_seed": int(scene_seed),
        "reviewed_content_commit": reviewed_content_commit,
        "reviewed_publication": publication,
        "source_bindings": current_source_bindings_v3_3(),
        "planned_root_slot_spec": planned,
        "planned_root_slot_spec_sha256": hash_json(planned),
        "scope_budget": budget,
        "scope_budget_sha256": budget["scope_budget_sha256"],
        "planner_query_limit": planner,
        "controlled_action_limit": controlled,
        "physics_step_limit": physics,
        "timeout_seconds": timeout,
        "max_invocations": 1,
        "automatic_retry": False,
        "allowed_physical_gpu_indices": indices,
        "allowed_gpu_uuid_policy": ALLOWED_UUID_POLICY,
        "authorization_receipt_path": authorization_receipt_path,
        "source_lock_receipt_path": source_lock_receipt_path,
        "consumption_ledger_directory": consumption_ledger_directory,
        "gpu_lease_directory": CANONICAL_GPU_LEASE_DIRECTORY,
        "job_cache_root_directory": CANONICAL_JOB_CACHE_DIRECTORY,
        "revision_ledger_directory": revision_ledger_directory,
        "family_revision_index": family_revision_index,
        "maximum_new_implementation_revisions_per_family": parent[
            "maximum_new_implementation_revisions_per_family"
        ],
        "maximum_full_root_execution_per_revision": parent[
            "maximum_full_root_execution_per_revision"
        ],
        "guard_receipt_path": guard_receipt_path,
        "output_namespace": output_namespace,
        "exact_child_command": list(exact_child_command),
        "exact_child_command_sha256": command_sha256(exact_child_command),
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
    }
    request["scope_request_sha256"] = canonical_sha256(request)
    return request


def validate_scope_request(value: Mapping[str, Any], parent: Mapping[str, Any]) -> dict:
    parent = validate_parent_user_authorization(parent)
    if not isinstance(value, Mapping) or value.get("schema_version") != SCOPE_REQUEST_SCHEMA_VERSION:
        raise ValueError("scope request schema mismatch")
    request = json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))
    expected = request.pop("scope_request_sha256", None)
    if not isinstance(expected, str) or canonical_sha256(request) != expected:
        raise ValueError("scope request content hash mismatch")
    if value.get("parent_user_authorization_sha256") != parent["parent_user_authorization_sha256"]:
        raise ValueError("scope request parent authorization mismatch")
    budget = scope_budget(value["scope"])
    if value.get("scope_budget") != budget or value.get("scope_budget_sha256") != budget["scope_budget_sha256"]:
        raise ValueError("scope request budget mismatch")
    if value.get("source_bindings") != current_source_bindings_v3_3():
        raise ValueError("scope request source bindings no longer match active source")
    publication = value.get("reviewed_publication")
    if (
        not isinstance(publication, Mapping)
        or publication.get("reviewed_content_commit")
        != value.get("reviewed_content_commit")
        or publication.get("origin_main") != value.get("reviewed_content_commit")
        or publication.get("vault_worktree_clean") is not True
        or publication.get("active_snapshot_source_sha256")
        != value.get("source_bindings", {}).get("implementation_source_sha256")
    ):
        raise ValueError("scope request reviewed publication binding is invalid")
    if value.get("exact_child_command_sha256") != command_sha256(value.get("exact_child_command", [])):
        raise ValueError("scope request command hash mismatch")
    if value.get("consumption_ledger_directory") != CANONICAL_CONSUMPTION_LEDGER_DIRECTORY:
        raise ValueError("scope request consumption ledger is not canonical")
    if value.get("gpu_lease_directory") != CANONICAL_GPU_LEASE_DIRECTORY:
        raise ValueError("scope request GPU lease directory is not canonical")
    if value.get("job_cache_root_directory") != CANONICAL_JOB_CACHE_DIRECTORY:
        raise ValueError("scope request job cache root is not canonical")
    scope = value.get("scope")
    if scope in ROOT_SCOPES:
        if value.get("family_revision_index") not in (1, 2):
            raise ValueError("root scope request revision index is invalid")
        revision_dir = value.get("revision_ledger_directory")
        if not isinstance(revision_dir, str):
            raise ValueError("root scope request revision ledger is missing")
        _workspace_path(revision_dir, "revision_ledger_directory")
        if revision_dir != CANONICAL_REVISION_LEDGER_DIRECTORY:
            raise ValueError("scope request revision ledger is not canonical")
        if value.get("planned_root_slot_spec", {}).get(
            "implementation_revision_index"
        ) != value.get("family_revision_index"):
            raise ValueError("root scope request planned revision mismatch")
    elif (
        value.get("family_revision_index") is not None
        or value.get("revision_ledger_directory") is not None
    ):
        raise ValueError("non-root scope request cannot reserve a revision")
    if value.get("maximum_new_implementation_revisions_per_family") != parent[
        "maximum_new_implementation_revisions_per_family"
    ]:
        raise ValueError("scope request family revision limit mismatch")
    if value.get("maximum_full_root_execution_per_revision") != parent[
        "maximum_full_root_execution_per_revision"
    ]:
        raise ValueError("scope request root-per-revision limit mismatch")
    return dict(value)


def issue_authorization_from_scope_request(
    *,
    scope_request_path: Path,
    parent_user_authorization_path: Path,
    source_lock_receipt: Mapping[str, Any],
    authorization_id: str,
    authorized_run_id: str,
    issued_at: datetime | None = None,
    validity_seconds: int = 3600,
) -> dict:
    if not 0 < validity_seconds <= 3600:
        raise ValueError("authorization validity must be at most one hour")
    parent = load_parent_user_authorization(parent_user_authorization_path)
    scope_request_path = Path(scope_request_path)
    request = validate_scope_request(
        json.loads(scope_request_path.read_text(encoding="utf-8")),
        parent,
    )
    source_lock = validate_runtime_source_lock(
        source_lock_receipt,
        expected_family=request["family"],
    )
    if source_lock["snapshot"]["implementation_source_sha256"] != request["source_bindings"]["implementation_source_sha256"]:
        raise ValueError("source lock and reviewed request implementation hashes differ")
    issued = (issued_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    expires = issued + timedelta(seconds=validity_seconds)
    authorization = {
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "authorization_id": authorization_id,
        "authorized_run_id": authorized_run_id,
        "issued_at": issued.isoformat(),
        "expires_at": expires.isoformat(),
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_3",
        "implementation_revision": "runtime_v3_3_strict_prefix_common_v1",
        "reviewed_content_commit": request["reviewed_content_commit"],
        "reviewed_publication": request.get("reviewed_publication"),
        **request["source_bindings"],
        "parent_user_authorization_sha256": parent["parent_user_authorization_sha256"],
        "approval_request_schema_version": request["schema_version"],
        "approval_request_path": str(scope_request_path.resolve()),
        "approval_request_sha256": request["scope_request_sha256"],
        "approval_request_file_sha256": sha256_file(scope_request_path),
        "source_lock_receipt_path": request["source_lock_receipt_path"],
        "guard_receipt_path": request["guard_receipt_path"],
        "consumption_ledger_directory": request[
            "consumption_ledger_directory"
        ],
        "gpu_lease_directory": request["gpu_lease_directory"],
        "job_cache_root_directory": request["job_cache_root_directory"],
        "source_lock_receipt_sha256": source_lock["source_lock_receipt_sha256"],
        "approved": True,
        "approved_scopes": [request["scope"]],
        "family": request["family"],
        "scene_seed": request["scene_seed"],
        "planned_root_slot_spec": request["planned_root_slot_spec"],
        "planned_root_slot_spec_sha256": request["planned_root_slot_spec_sha256"],
        "planner_query_limit": request["planner_query_limit"],
        "controlled_action_limit": request["controlled_action_limit"],
        "physics_step_limit": request["physics_step_limit"],
        "timeout_seconds": request["timeout_seconds"],
        "max_invocations": 1,
        "scope_budget": request["scope_budget"],
        "scope_budget_sha256": request["scope_budget_sha256"],
        "revision_ledger_directory": request["revision_ledger_directory"],
        "family_revision_index": request["family_revision_index"],
        "maximum_new_implementation_revisions_per_family": request[
            "maximum_new_implementation_revisions_per_family"
        ],
        "maximum_full_root_execution_per_revision": request[
            "maximum_full_root_execution_per_revision"
        ],
        "allowed_physical_gpu_indices": request["allowed_physical_gpu_indices"],
        "allowed_gpu_uuid_policy": request["allowed_gpu_uuid_policy"],
        "output_namespace": request["output_namespace"],
        "authorized_command_sha256": request["exact_child_command_sha256"],
        "stage0_authorized": False,
        "formal_data": False,
        "stage0_data": False,
    }
    if "scene_pattern" in request:
        authorization["scene_pattern"] = request["scene_pattern"]
    authorization["receipt_sha256"] = authorization_receipt_sha256(authorization)
    return authorization
