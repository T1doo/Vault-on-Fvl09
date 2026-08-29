"""CPU-only builder for one immutable runtime-v3_3 scope authorization bundle."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Sequence

from .pre_stage0_authorization_v3 import (
    build_scope_request,
    issue_authorization_from_scope_request,
    load_parent_user_authorization,
)
from .probes.runtime_v3_3_authorization_v1 import (
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_REVISION_LEDGER_DIRECTORY,
    current_source_bindings_v3_3,
)
from .runtime_source_lock_v1 import capture_runtime_source_lock, write_runtime_source_lock
from .runtime_v3_3_budget_v1 import ROOT_SCOPES, SCOPE_FAMILIES, scope_budget
from .runtime_v3_3_scope_specs_v1 import planned_scope_spec


VAULT_ROOT = Path("/nfs_share/lijunhui/Vault-on-Fvl09")
AUDIT_ROOT = VAULT_ROOT / "数据构造/实现审计"
PARENT_AUTHORIZATION = (
    AUDIT_ROOT
    / "USER_AUTHORIZATION_RUNTIME_V3_3_PRE_STAGE0_WORK_GPU0_7_20260829.json"
)
PYTHON_EXECUTABLE = Path("/nfs_share/lijunhui/Robotwin2/env/bin/python")


def _write_new(path: Path, value) -> None:
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as handle:
        os.fchmod(fd, 0o600)
        handle.write(data)
        handle.flush()
        os.fsync(fd)


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(VAULT_ROOT), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
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


def _validate_reviewed_publication(reviewed_content_commit: str) -> dict:
    head = _git("rev-parse", "HEAD")
    origin = _git("rev-parse", "origin/main")
    status = _git("status", "--porcelain")
    if reviewed_content_commit != head or head != origin or status:
        raise ValueError(
            "reviewed content commit must equal clean published Vault HEAD and origin/main"
        )
    _git("cat-file", "-e", f"{reviewed_content_commit}^{{commit}}")
    snapshot = AUDIT_ROOT / "代码审阅快照/controlled_multi_future"
    if not snapshot.is_dir():
        raise ValueError("byte-equal controlled_multi_future review snapshot is missing")
    snapshot_sha = _python_tree_sha256(snapshot)
    active_sha = current_source_bindings_v3_3()["implementation_source_sha256"]
    if snapshot_sha != active_sha:
        raise ValueError("published review snapshot differs from active implementation source")
    return {
        "reviewed_content_commit": reviewed_content_commit,
        "origin_main": origin,
        "vault_worktree_clean": True,
        "active_snapshot_source_sha256": active_sha,
    }


def build_scope_bundle(
    *,
    scope: str,
    reviewed_content_commit: str,
    namespace_id: str,
    authorization_id: str,
    authorized_run_id: str,
    revision_index: int | None = None,
    validity_seconds: int = 3600,
) -> dict:
    publication = _validate_reviewed_publication(reviewed_content_commit)
    family = SCOPE_FAMILIES[scope]
    if scope in ROOT_SCOPES and revision_index not in (1, 2):
        raise ValueError("root scope bundle requires revision_index 1 or 2")
    if scope not in ROOT_SCOPES and revision_index is not None:
        raise ValueError("non-root scope bundle cannot consume a revision")
    parent = load_parent_user_authorization(PARENT_AUTHORIZATION)
    group = "runtime_v3_3_v1_1_gpu0_7"
    request_path = AUDIT_ROOT / "scope_requests" / group / f"{namespace_id}.request.json"
    lock_path = AUDIT_ROOT / "source_locks" / group / f"{namespace_id}.source_lock.json"
    auth_path = AUDIT_ROOT / "authorizations" / group / f"{namespace_id}.authorization.json"
    guard_path = AUDIT_ROOT / "gpu_guards" / group / f"{namespace_id}.guard.json"
    output_namespace = AUDIT_ROOT / "probe_outputs" / namespace_id
    for path in (
        request_path,
        lock_path,
        auth_path,
        guard_path,
        output_namespace,
    ):
        if path.exists():
            raise FileExistsError(path)
    child_command: Sequence[str] = (
        str(PYTHON_EXECUTABLE),
        "-m",
        "controlled_multi_future.probes.runtime_v3_3_scope_runner",
        "--authorization-receipt",
        str(auth_path),
    )
    planned = planned_scope_spec(scope, revision_index=revision_index)
    request = build_scope_request(
        parent_user_authorization=parent,
        scope=scope,
        family=family,
        scene_seed=int(planned["seed"]),
        planned_root_slot_spec=planned,
        reviewed_content_commit=reviewed_content_commit,
        authorization_receipt_path=str(auth_path),
        source_lock_receipt_path=str(lock_path),
        consumption_ledger_directory=CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        revision_ledger_directory=(
            CANONICAL_REVISION_LEDGER_DIRECTORY if scope in ROOT_SCOPES else None
        ),
        family_revision_index=revision_index,
        guard_receipt_path=str(guard_path),
        output_namespace=str(output_namespace),
        exact_child_command=child_command,
        allowed_physical_gpu_indices=list(range(8)),
        reviewed_publication=publication,
    )
    source_lock = capture_runtime_source_lock(family=family)
    _write_new(request_path, request)
    write_runtime_source_lock(lock_path, source_lock)
    authorization = issue_authorization_from_scope_request(
        scope_request_path=request_path,
        parent_user_authorization_path=PARENT_AUTHORIZATION,
        source_lock_receipt=source_lock,
        authorization_id=authorization_id,
        authorized_run_id=authorized_run_id,
        validity_seconds=validity_seconds,
    )
    _write_new(auth_path, authorization)
    return {
        "schema_version": "cmf_runtime_v3_3_scope_bundle_v1",
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
        "physical_gpu_indices": list(range(8)),
        "timeout_seconds": scope_budget(scope)["timeout_seconds"],
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
    }
