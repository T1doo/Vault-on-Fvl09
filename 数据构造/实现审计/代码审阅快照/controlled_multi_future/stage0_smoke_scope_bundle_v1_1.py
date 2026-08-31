"""Immutable v13 infrastructure and Stage 0 v1.1 bundle builders."""

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
from .probes.stage0_smoke_authorization_v1_1 import (
    AUTHORIZATION_SCHEMA_VERSION,
    AUDIT_ROOT,
    CANONICAL_PARENT_AUTHORIZATION,
    CANONICAL_STAGE0_BUDGET,
    CANONICAL_STAGE0_MANIFEST,
    DATASET_ROOT,
    DESIGN_VERSION,
    GROUP,
    IMPLEMENTATION_REVISION,
    IMPLEMENTATION_VERSION,
    INFRA_AUTHORIZATION_ID,
    INFRA_NAMESPACE,
    STAGE0_AUTHORIZATION_ID_BY_SCOPE,
    STAGE0_NAMESPACE_BY_SCOPE,
    VAULT_ROOT,
    authorization_receipt_sha256,
    canonical_sha256,
    current_stage0_source_bindings_v1_1,
    sha256_file,
)
from .runtime_source_lock_v1 import (
    capture_runtime_source_lock,
    write_runtime_source_lock,
)
from .stage0_smoke_budget_v1_1 import (
    F4_INFRA_SCOPE,
    SCOPE_FAMILIES,
    STAGE0_SCOPES,
    budget_receipt_sha256,
    scope_budget,
)
from .stage0_smoke_manifest_v1_1 import (
    CANONICAL_INFRA_RECEIPT,
    build_stage0_smoke_manifest_v1_1,
    validate_stage0_smoke_manifest_structure,
)
from .stage0_smoke_scope_specs_v1_1 import planned_scope_spec


PYTHON_EXECUTABLE = Path("/nfs_share/lijunhui/Robotwin2/env/bin/python")
CANONICAL_STAGE0_BUDGET_MD = (
    AUDIT_ROOT / "STAGE0_SMOKE_ATTEMPT_BUDGET_V1.md"
)
CANONICAL_STAGE0_MANIFEST_MD = (
    AUDIT_ROOT / "STAGE0_SMOKE_ATTEMPT_MANIFEST_V1.md"
)


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


def _require_published_file(commit: str, path: Path) -> None:
    path = Path(path).resolve()
    relative = path.relative_to(VAULT_ROOT).as_posix()
    _git("cat-file", "-e", f"{commit}:{relative}")
    current = path.read_bytes()
    committed = subprocess.run(
        ["git", "-C", str(VAULT_ROOT), "show", f"{commit}:{relative}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    if committed != current:
        raise ValueError(f"published commit bytes differ for {path}")


def _validate_budget_publication(commit: str) -> dict[str, Any]:
    if not CANONICAL_STAGE0_BUDGET.is_file() or not CANONICAL_STAGE0_BUDGET_MD.is_file():
        raise ValueError("canonical Stage 0 attempt budget JSON/Markdown is missing")
    value = json.loads(CANONICAL_STAGE0_BUDGET.read_text(encoding="utf-8"))
    checks = {
        "schema": value.get("schema_version")
        in (
            "cmf_stage0_smoke_budget_v1_1",
            "cmf_stage0_smoke_attempt_budget_publication_v1",
        ),
        "implementation": value.get("implementation_version")
        == IMPLEMENTATION_VERSION,
        "budget": value.get("budget_receipt_sha256")
        == budget_receipt_sha256(),
        "approved": value.get("approved") is True,
        "stage0_authorized": value.get("stage0_authorized") is True,
        "stage1_false": value.get("stage1_authorized") is False,
        "formal_false": value.get("formal_collection_authorized") is False,
        "training_false": value.get("training_authorized") is False,
    }
    if not all(checks.values()):
        raise ValueError(f"canonical Stage 0 attempt budget is invalid: {checks}")
    _require_published_file(commit, CANONICAL_STAGE0_BUDGET)
    _require_published_file(commit, CANONICAL_STAGE0_BUDGET_MD)
    return {
        "path": str(CANONICAL_STAGE0_BUDGET),
        "file_sha256": sha256_file(CANONICAL_STAGE0_BUDGET),
        "markdown_path": str(CANONICAL_STAGE0_BUDGET_MD),
        "markdown_file_sha256": sha256_file(CANONICAL_STAGE0_BUDGET_MD),
        "budget_receipt_sha256": budget_receipt_sha256(),
    }


def _validate_reviewed_publication(commit: str) -> dict[str, Any]:
    head = _git("rev-parse", "HEAD")
    origin = _git("rev-parse", "origin/main")
    status = _git("status", "--porcelain")
    if commit != head or head != origin or status:
        raise ValueError("bundle requires clean published Vault HEAD=origin/main")
    _git("cat-file", "-e", f"{commit}^{{commit}}")
    snapshot = AUDIT_ROOT / "代码审阅快照/controlled_multi_future"
    bindings = current_stage0_source_bindings_v1_1()
    active_sha = bindings["implementation_source_sha256"]
    if _python_tree_sha256(snapshot) != active_sha:
        raise ValueError("published Vault snapshot differs from active v1.1 source")
    budget_publication = _validate_budget_publication(commit)
    return {
        "reviewed_content_commit": commit,
        "origin_main": origin,
        "vault_worktree_clean": True,
        "active_snapshot_source_sha256": active_sha,
        "source_bindings": bindings,
        "budget_publication": budget_publication,
    }


def load_parent_user_authorization(
    path: Path = CANONICAL_PARENT_AUTHORIZATION,
) -> dict[str, Any]:
    path = Path(path).resolve()
    if path != CANONICAL_PARENT_AUTHORIZATION.resolve():
        raise ValueError("Stage 0 v1.1 parent path is not canonical")
    value = json.loads(path.read_text(encoding="utf-8"))
    digest = value.get("parent_user_authorization_sha256")
    payload = dict(value)
    payload.pop("parent_user_authorization_sha256", None)
    if not isinstance(digest, str) or canonical_sha256(payload) != digest:
        raise ValueError("Stage 0 v1.1 parent authorization hash mismatch")
    if value.get("approved") is not True or value.get("stage0_authorized") is not True:
        raise ValueError("Stage 0 v1.1 parent authorization flags are invalid")
    if value.get("formal_collection_authorized") is not False:
        raise ValueError("Stage 0 v1.1 parent must not authorize formal collection")
    return value


def _namespace_for_scope(scope: str) -> str:
    return INFRA_NAMESPACE if scope == F4_INFRA_SCOPE else STAGE0_NAMESPACE_BY_SCOPE[scope]


def _paths_for_scope(scope: str) -> dict[str, Path]:
    namespace = _namespace_for_scope(scope)
    return {
        "request": AUDIT_ROOT / "scope_requests" / GROUP / f"{namespace}.request.json",
        "source_lock": AUDIT_ROOT / "source_locks" / GROUP / f"{namespace}.source_lock.json",
        "authorization": AUDIT_ROOT / "authorizations" / GROUP / f"{namespace}.authorization.json",
        "guard": AUDIT_ROOT / "gpu_guards" / GROUP / f"{namespace}.guard.json",
        "output": (
            AUDIT_ROOT / "probe_outputs" / namespace
            if scope == F4_INFRA_SCOPE
            else DATASET_ROOT / namespace
        ),
    }


def _build_request(
    *,
    parent: Mapping[str, Any],
    scope: str,
    planned: Mapping[str, Any],
    reviewed_content_commit: str,
    paths: Mapping[str, Path],
    child_command: Sequence[str],
    publication: Mapping[str, Any],
    stage0_manifest: Mapping[str, Any] | None,
    bundle_set_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    budget = scope_budget(scope)
    payload = {
        "schema_version": "cmf_stage0_smoke_scope_request_v1_1",
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_revision": IMPLEMENTATION_REVISION,
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
        "authorization_receipt_path": str(paths["authorization"]),
        "source_lock_receipt_path": str(paths["source_lock"]),
        "guard_receipt_path": str(paths["guard"]),
        "output_namespace": str(paths["output"]),
        "consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        "exact_child_command": list(child_command),
        "authorized_command_sha256": command_sha256(child_command),
        "allowed_physical_gpu_indices": list(range(8)),
        "scope_budget": budget,
        "budget_receipt_sha256": budget_receipt_sha256(),
        "stage0_budget_publication_path": str(CANONICAL_STAGE0_BUDGET),
        "stage0_budget_publication_file_sha256": sha256_file(
            CANONICAL_STAGE0_BUDGET
        ),
        "stage0_manifest_sha256": None
        if stage0_manifest is None
        else stage0_manifest["manifest_sha256"],
        "bundle_set_receipt_sha256": None
        if bundle_set_receipt is None
        else bundle_set_receipt["bundle_set_receipt_sha256"],
        "formal_data": False,
        "stage0_data": budget["stage0_data"],
        "stage0_authorized": True,
        "automatic_retry": False,
        "recovery_attempts": 0,
    }
    payload["scope_request_sha256"] = canonical_sha256(payload)
    return payload


def _build_scope_bundle(
    *,
    scope: str,
    reviewed_content_commit: str,
    authorization_id: str,
    authorized_run_id: str,
    stage0_manifest: Mapping[str, Any] | None = None,
    stage0_manifest_path: Path | None = None,
    validity_seconds: int = 3600,
    publication: Mapping[str, Any] | None = None,
    parent: Mapping[str, Any] | None = None,
    bundle_set_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not 0 < validity_seconds <= 3600:
        raise ValueError("authorization validity must be within one hour")
    publication = dict(
        publication
        if publication is not None
        else _validate_reviewed_publication(reviewed_content_commit)
    )
    parent = dict(parent if parent is not None else load_parent_user_authorization())
    planned = planned_scope_spec(scope, stage0_manifest=stage0_manifest)
    family = SCOPE_FAMILIES[scope]
    paths = _paths_for_scope(scope)
    for path in paths.values():
        if path.exists():
            raise FileExistsError(path)
    child_command = (
        str(PYTHON_EXECUTABLE),
        "-m",
        "controlled_multi_future.probes.stage0_smoke_scope_runner_v1_1",
        "--authorization-receipt",
        str(paths["authorization"]),
    )
    request = _build_request(
        parent=parent,
        scope=scope,
        planned=planned,
        reviewed_content_commit=reviewed_content_commit,
        paths=paths,
        child_command=child_command,
        publication=publication,
        stage0_manifest=stage0_manifest,
        bundle_set_receipt=bundle_set_receipt,
    )
    source_lock = capture_runtime_source_lock(family=family)
    now = datetime.now(timezone.utc)
    budget = scope_budget(scope)
    source_bindings = current_stage0_source_bindings_v1_1()
    authorization = {
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_revision": IMPLEMENTATION_REVISION,
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
        "stage0_manifest_sha256": None
        if stage0_manifest is None
        else stage0_manifest["manifest_sha256"],
        "stage0_manifest_path": None
        if stage0_manifest_path is None
        else str(Path(stage0_manifest_path).resolve()),
        "stage0_manifest_file_sha256": None
        if stage0_manifest_path is None
        else sha256_file(Path(stage0_manifest_path)),
        "bundle_set_receipt_path": None
        if bundle_set_receipt is None
        else bundle_set_receipt["path"],
        "bundle_set_receipt_file_sha256": None
        if bundle_set_receipt is None
        else sha256_file(Path(bundle_set_receipt["path"])),
        "bundle_set_receipt_sha256": None
        if bundle_set_receipt is None
        else bundle_set_receipt["bundle_set_receipt_sha256"],
        "parent_user_authorization_path": str(CANONICAL_PARENT_AUTHORIZATION),
        "parent_user_authorization_file_sha256": sha256_file(
            CANONICAL_PARENT_AUTHORIZATION
        ),
        "parent_user_authorization_sha256": parent[
            "parent_user_authorization_sha256"
        ],
        "approval_request_path": str(paths["request"]),
        "approval_request_file_sha256": None,
        "approval_request_sha256": request["scope_request_sha256"],
        "source_lock_receipt_path": str(paths["source_lock"]),
        "source_lock_receipt_sha256": source_lock[
            "source_lock_receipt_sha256"
        ],
        "source_bindings": source_bindings,
        "implementation_source_sha256": source_bindings[
            "implementation_source_sha256"
        ],
        "budget_receipt_sha256": budget_receipt_sha256(),
        "stage0_budget_publication_path": str(CANONICAL_STAGE0_BUDGET),
        "stage0_budget_publication_file_sha256": sha256_file(
            CANONICAL_STAGE0_BUDGET
        ),
        "scope_budget": budget,
        "planner_query_limit": budget["planner_query_limit"],
        "controlled_action_limit": budget["execution_limit"],
        "physics_step_limit": -1,
        "timeout_seconds": budget["timeout_seconds"],
        "allowed_physical_gpu_indices": list(range(8)),
        "output_namespace": str(paths["output"]),
        "guard_receipt_path": str(paths["guard"]),
        "consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        "gpu_lease_directory": CANONICAL_GPU_LEASE_DIRECTORY,
        "job_cache_root_directory": CANONICAL_JOB_CACHE_DIRECTORY,
        "authorized_command_sha256": command_sha256(child_command),
        "reviewed_content_commit": reviewed_content_commit,
        "max_invocations": 1,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": budget["stage0_data"],
        "stage0_authorized": True,
    }
    _write_new(paths["request"], request)
    authorization["approval_request_file_sha256"] = sha256_file(paths["request"])
    write_runtime_source_lock(paths["source_lock"], source_lock)
    authorization["receipt_sha256"] = authorization_receipt_sha256(authorization)
    _write_new(paths["authorization"], authorization)
    return {
        "schema_version": "cmf_stage0_smoke_scope_bundle_v1_1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": scope,
        "family": family,
        "namespace_id": _namespace_for_scope(scope),
        "reviewed_content_commit": reviewed_content_commit,
        "request_path": str(paths["request"]),
        "request_sha256": request["scope_request_sha256"],
        "source_lock_path": str(paths["source_lock"]),
        "source_lock_sha256": source_lock["source_lock_receipt_sha256"],
        "authorization_path": str(paths["authorization"]),
        "authorization_sha256": authorization["receipt_sha256"],
        "guard_path": str(paths["guard"]),
        "output_namespace": str(paths["output"]),
        "child_command": list(child_command),
        "physical_gpu_indices": list(range(8)),
        "timeout_seconds": budget["timeout_seconds"],
        "formal_data": False,
        "stage0_data": budget["stage0_data"],
        "stage0_authorized": True,
    }


def build_f4_infrastructure_bundle_v1_1(
    *, reviewed_content_commit: str, validity_seconds: int = 3600
) -> dict[str, Any]:
    return _build_scope_bundle(
        scope=F4_INFRA_SCOPE,
        reviewed_content_commit=reviewed_content_commit,
        authorization_id=INFRA_AUTHORIZATION_ID,
        authorized_run_id=INFRA_AUTHORIZATION_ID + "-run",
        validity_seconds=validity_seconds,
    )


def build_stage0_bundle_set_v1_1(
    *,
    reviewed_content_commit: str,
    stage0_manifest_path: Path = CANONICAL_STAGE0_MANIFEST,
    validity_seconds: int = 3600,
) -> dict[str, Any]:
    publication = _validate_reviewed_publication(reviewed_content_commit)
    parent = load_parent_user_authorization()
    manifest_path = Path(stage0_manifest_path).resolve()
    if manifest_path != CANONICAL_STAGE0_MANIFEST.resolve():
        raise ValueError("Stage 0 v1.1 manifest path is not canonical")
    if not manifest_path.is_file() or not CANONICAL_STAGE0_MANIFEST_MD.is_file():
        raise ValueError("canonical Stage 0 attempt manifest JSON/Markdown is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_manifest = build_stage0_smoke_manifest_v1_1(
        CANONICAL_INFRA_RECEIPT
    )
    if manifest != expected_manifest:
        raise ValueError("canonical v1.1 manifest differs from v13 reconstruction")
    gate = validate_stage0_smoke_manifest_structure(manifest)
    if gate["pass"] is not True:
        raise ValueError(f"Stage 0 v1.1 manifest Gate failed: {gate['checks']}")
    _require_published_file(reviewed_content_commit, manifest_path)
    _require_published_file(reviewed_content_commit, CANONICAL_STAGE0_MANIFEST_MD)
    manifest_sha = str(manifest["manifest_sha256"])
    set_path = (
        AUDIT_ROOT
        / "authorizations"
        / GROUP
        / f"stage0_v1_1_bundle_set_{manifest_sha}.json"
    )
    authorization_paths = {
        scope: str(_paths_for_scope(scope)["authorization"])
        for scope in STAGE0_SCOPES
    }
    set_receipt = {
        "schema_version": "cmf_stage0_smoke_bundle_set_receipt_v1_1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "path": str(set_path),
        "reviewed_content_commit": reviewed_content_commit,
        "implementation_source_sha256": publication[
            "active_snapshot_source_sha256"
        ],
        "stage0_manifest_sha256": manifest_sha,
        "stage0_manifest_path": str(manifest_path),
        "stage0_manifest_file_sha256": sha256_file(manifest_path),
        "stage0_manifest_markdown_path": str(CANONICAL_STAGE0_MANIFEST_MD),
        "stage0_manifest_markdown_file_sha256": sha256_file(
            CANONICAL_STAGE0_MANIFEST_MD
        ),
        "budget_receipt_sha256": budget_receipt_sha256(),
        "stage0_budget_publication_path": str(CANONICAL_STAGE0_BUDGET),
        "stage0_budget_publication_file_sha256": sha256_file(
            CANONICAL_STAGE0_BUDGET
        ),
        "parent_user_authorization_sha256": parent[
            "parent_user_authorization_sha256"
        ],
        "scopes": list(STAGE0_SCOPES),
        "namespace_by_scope": dict(STAGE0_NAMESPACE_BY_SCOPE),
        "authorization_id_by_scope": dict(STAGE0_AUTHORIZATION_ID_BY_SCOPE),
        "authorization_paths": authorization_paths,
        "bundle_count": 4,
        "scope_max_invocations": 1,
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
    }
    set_receipt["bundle_set_receipt_sha256"] = canonical_sha256(set_receipt)
    _write_new(set_path, set_receipt)
    bundles = {}
    for scope in STAGE0_SCOPES:
        auth_id = STAGE0_AUTHORIZATION_ID_BY_SCOPE[scope]
        bundles[scope] = _build_scope_bundle(
            scope=scope,
            reviewed_content_commit=reviewed_content_commit,
            authorization_id=auth_id,
            authorized_run_id=auth_id + "-run",
            stage0_manifest=manifest,
            stage0_manifest_path=manifest_path,
            validity_seconds=validity_seconds,
            publication=publication,
            parent=parent,
            bundle_set_receipt=set_receipt,
        )
    return {
        "schema_version": "cmf_stage0_smoke_bundle_set_v1_1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "reviewed_content_commit": reviewed_content_commit,
        "stage0_manifest_sha256": manifest_sha,
        "manifest_gate": gate,
        "bundle_set_receipt": set_receipt,
        "bundle_count": 4,
        "bundles": bundles,
        "allowed_physical_gpu_indices": list(range(8)),
        "family_level_parallelism_authorized": True,
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
    }


__all__ = [
    "CANONICAL_STAGE0_BUDGET_MD",
    "CANONICAL_STAGE0_MANIFEST_MD",
    "build_f4_infrastructure_bundle_v1_1",
    "build_stage0_bundle_set_v1_1",
    "load_parent_user_authorization",
]
