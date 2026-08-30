"""CPU-only immutable scope bundle builder for runtime-v3_4_1."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from .current_hasher import hash_json
from .probes.gpu_guard_v2_1 import command_sha256
from .probes.runtime_v3_3_authorization_v1 import (
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)
from .probes.runtime_v3_4_1_authorization_v1 import (
    AUTHORIZATION_SCHEMA_VERSION,
    authorization_receipt_sha256,
    canonical_sha256,
    current_source_bindings_v3_4_1,
    sha256_file,
)
from .runtime_source_lock_v1 import (
    capture_runtime_source_lock,
    write_runtime_source_lock,
)
from .runtime_v3_4_1_budget_v1 import SCOPE_FAMILIES, budget_receipt_sha256, scope_budget
from .runtime_v3_4_1_scope_specs_v1 import planned_scope_spec


VAULT_ROOT = Path("/nfs_share/lijunhui/Vault-on-Fvl09")
AUDIT_ROOT = VAULT_ROOT / "数据构造/实现审计"
PARENT_AUTHORIZATION = (
    AUDIT_ROOT / "USER_AUTHORIZATION_RUNTIME_V3_4_1_ONE_SHOT_POSTMORTEM_20260830.json"
)
PYTHON_EXECUTABLE = Path("/nfs_share/lijunhui/Robotwin2/env/bin/python")


def _write_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(VAULT_ROOT), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def _python_tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _validate_reviewed_publication(commit: str) -> dict[str, Any]:
    head = _git("rev-parse", "HEAD")
    origin = _git("rev-parse", "origin/main")
    status = _git("status", "--porcelain")
    if commit != head or head != origin or status:
        raise ValueError("bundle requires clean published Vault HEAD=origin/main")
    _git("cat-file", "-e", f"{commit}^{{commit}}")
    snapshot = AUDIT_ROOT / "代码审阅快照/controlled_multi_future"
    active_sha = current_source_bindings_v3_4_1()["implementation_source_sha256"]
    if _python_tree_sha256(snapshot) != active_sha:
        raise ValueError("published Vault snapshot differs from active source")
    return {
        "reviewed_content_commit": commit,
        "origin_main": origin,
        "vault_worktree_clean": True,
        "active_snapshot_source_sha256": active_sha,
    }


def load_parent_user_authorization(path: Path = PARENT_AUTHORIZATION) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    digest = value.get("parent_user_authorization_sha256")
    payload = dict(value)
    payload.pop("parent_user_authorization_sha256", None)
    if not isinstance(digest, str) or canonical_sha256(payload) != digest:
        raise ValueError("runtime-v3_4_1 parent authorization hash mismatch")
    if value.get("approved") is not True or value.get("stage0_authorized") is not False:
        raise ValueError("runtime-v3_4_1 parent authorization flags are invalid")
    return value


def _build_request(
    *,
    parent: Mapping[str, Any],
    scope: str,
    planned: Mapping[str, Any],
    reviewed_content_commit: str,
    authorization_path: Path,
    source_lock_path: Path,
    guard_path: Path,
    output_namespace: Path,
    child_command: Sequence[str],
    publication: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema_version": "cmf_runtime_v3_4_1_scope_request_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_4_1",
        "implementation_strategy": "one_shot_postmortem_hardening",
        "scope": scope,
        "family": SCOPE_FAMILIES[scope],
        "scene_seed": planned["seed"],
        "planned_root_slot_spec": dict(planned),
        "planned_root_slot_spec_sha256": canonical_sha256(planned),
        "parent_user_authorization_sha256": parent[
            "parent_user_authorization_sha256"
        ],
        "reviewed_content_commit": reviewed_content_commit,
        "reviewed_publication": dict(publication),
        "authorization_receipt_path": str(authorization_path),
        "source_lock_receipt_path": str(source_lock_path),
        "guard_receipt_path": str(guard_path),
        "output_namespace": str(output_namespace),
        "consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        "exact_child_command": list(child_command),
        "authorized_command_sha256": command_sha256(child_command),
        "allowed_physical_gpu_indices": [0],
        "scope_budget": scope_budget(scope),
        "budget_receipt_sha256": budget_receipt_sha256(),
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "automatic_retry": False,
        "recovery_attempts": 0,
    }
    payload["scope_request_sha256"] = canonical_sha256(payload)
    return payload


def build_scope_bundle(
    *,
    scope: str,
    reviewed_content_commit: str,
    namespace_id: str,
    authorization_id: str,
    authorized_run_id: str,
    prerequisite_receipts: Mapping[str, Any] | None = None,
    validity_seconds: int = 3600,
) -> dict[str, Any]:
    if not 0 < validity_seconds <= 3600:
        raise ValueError("authorization validity must be within one hour")
    publication = _validate_reviewed_publication(reviewed_content_commit)
    parent = load_parent_user_authorization()
    planned = planned_scope_spec(
        scope, prerequisite_receipts=prerequisite_receipts
    )
    family = SCOPE_FAMILIES[scope]
    group = "runtime_v3_4_1_one_shot_postmortem_v1"
    request_path = AUDIT_ROOT / "scope_requests" / group / f"{namespace_id}.request.json"
    lock_path = AUDIT_ROOT / "source_locks" / group / f"{namespace_id}.source_lock.json"
    auth_path = AUDIT_ROOT / "authorizations" / group / f"{namespace_id}.authorization.json"
    guard_path = AUDIT_ROOT / "gpu_guards" / group / f"{namespace_id}.guard.json"
    output_namespace = AUDIT_ROOT / "probe_outputs" / namespace_id
    for path in (request_path, lock_path, auth_path, guard_path, output_namespace):
        if path.exists():
            raise FileExistsError(path)
    child_command = (
        str(PYTHON_EXECUTABLE),
        "-m",
        "controlled_multi_future.probes.runtime_v3_4_1_scope_runner",
        "--authorization-receipt",
        str(auth_path),
    )
    request = _build_request(
        parent=parent,
        scope=scope,
        planned=planned,
        reviewed_content_commit=reviewed_content_commit,
        authorization_path=auth_path,
        source_lock_path=lock_path,
        guard_path=guard_path,
        output_namespace=output_namespace,
        child_command=child_command,
        publication=publication,
    )
    source_lock = capture_runtime_source_lock(family=family)
    now = datetime.now(timezone.utc)
    budget = scope_budget(scope)
    source_bindings = current_source_bindings_v3_4_1()
    authorization = {
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_4_1",
        "implementation_revision": "one_shot_postmortem_hardening_v1",
        "authorization_id": authorization_id,
        "authorized_run_id": authorized_run_id,
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=validity_seconds)).isoformat(),
        "approved": True,
        "approved_scopes": [scope],
        "family": family,
        "scene_seed": planned["seed"],
        "planned_root_slot_spec": planned,
        "planned_root_slot_spec_sha256": canonical_sha256(planned),
        "parent_user_authorization_path": str(PARENT_AUTHORIZATION),
        "parent_user_authorization_file_sha256": sha256_file(PARENT_AUTHORIZATION),
        "parent_user_authorization_sha256": parent[
            "parent_user_authorization_sha256"
        ],
        "approval_request_path": str(request_path),
        "approval_request_file_sha256": None,
        "approval_request_sha256": request["scope_request_sha256"],
        "source_lock_receipt_path": str(lock_path),
        "source_lock_receipt_sha256": source_lock[
            "source_lock_receipt_sha256"
        ],
        "source_bindings": source_bindings,
        "implementation_source_sha256": source_bindings[
            "implementation_source_sha256"
        ],
        "budget_receipt_sha256": budget_receipt_sha256(),
        "scope_budget": budget,
        "planner_query_limit": budget["planner_query_limit"],
        "controlled_action_limit": budget["execution_limit"],
        "physics_step_limit": -1,
        "timeout_seconds": budget["timeout_seconds"],
        "allowed_physical_gpu_indices": [0],
        "output_namespace": str(output_namespace),
        "guard_receipt_path": str(guard_path),
        "consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        "gpu_lease_directory": CANONICAL_GPU_LEASE_DIRECTORY,
        "job_cache_root_directory": CANONICAL_JOB_CACHE_DIRECTORY,
        "authorized_command_sha256": command_sha256(child_command),
        "reviewed_content_commit": reviewed_content_commit,
        "max_invocations": 1,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
    }
    _write_new(request_path, request)
    authorization["approval_request_file_sha256"] = sha256_file(request_path)
    write_runtime_source_lock(lock_path, source_lock)
    authorization["receipt_sha256"] = authorization_receipt_sha256(
        authorization
    )
    _write_new(auth_path, authorization)
    return {
        "schema_version": "cmf_runtime_v3_4_1_scope_bundle_v1",
        "scope": scope,
        "family": family,
        "namespace_id": namespace_id,
        "reviewed_content_commit": reviewed_content_commit,
        "reviewed_publication": publication,
        "request_path": str(request_path),
        "request_sha256": request["scope_request_sha256"],
        "source_lock_path": str(lock_path),
        "source_lock_sha256": source_lock["source_lock_receipt_sha256"],
        "authorization_path": str(auth_path),
        "authorization_sha256": authorization["receipt_sha256"],
        "guard_path": str(guard_path),
        "output_namespace": str(output_namespace),
        "child_command": list(child_command),
        "physical_gpu_indices": [0],
        "timeout_seconds": budget["timeout_seconds"],
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
    }


__all__ = ["build_scope_bundle", "load_parent_user_authorization"]
