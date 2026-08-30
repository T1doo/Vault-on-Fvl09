"""Immutable bundle builder for the F4 fix and four Stage 0 family jobs."""

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
from .probes.stage0_smoke_authorization_v1 import (
    AUTHORIZATION_SCHEMA_VERSION,
    authorization_receipt_sha256,
    canonical_sha256,
    current_stage0_source_bindings,
    sha256_file,
)
from .runtime_source_lock_v1 import (
    capture_runtime_source_lock,
    write_runtime_source_lock,
)
from .stage0_smoke_budget_v1 import (
    F4_INFRA_SCOPE,
    SCOPE_FAMILIES,
    STAGE0_SCOPES,
    budget_receipt_sha256,
    scope_budget,
)
from .stage0_smoke_scope_specs_v1 import planned_scope_spec
from .stage0_smoke_manifest_v1 import (
    CANONICAL_INFRA_RECEIPT,
    build_stage0_smoke_manifest,
)


VAULT_ROOT = Path("/nfs_share/lijunhui/Vault-on-Fvl09")
AUDIT_ROOT = VAULT_ROOT / "数据构造/实现审计"
PARENT_AUTHORIZATION = (
    AUDIT_ROOT / "USER_AUTHORIZATION_STAGE0_SMOKE_V1_20260830.json"
)
PYTHON_EXECUTABLE = Path("/nfs_share/lijunhui/Robotwin2/env/bin/python")
DATASET_ROOT = Path(
    "/nfs_share/lijunhui/Robotwin2/datasets/controlled_multi_future_stage0_smoke_v1"
)
CANONICAL_STAGE0_MANIFEST = (
    AUDIT_ROOT / "STAGE0_SMOKE_MANIFEST_V1_20260830.json"
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


def _validate_reviewed_publication(commit: str) -> dict[str, Any]:
    head = _git("rev-parse", "HEAD")
    origin = _git("rev-parse", "origin/main")
    status = _git("status", "--porcelain")
    if commit != head or head != origin or status:
        raise ValueError("bundle requires clean published Vault HEAD=origin/main")
    _git("cat-file", "-e", f"{commit}^{{commit}}")
    snapshot = AUDIT_ROOT / "代码审阅快照/controlled_multi_future"
    active_sha = current_stage0_source_bindings()["implementation_source_sha256"]
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
        raise ValueError("Stage 0 parent authorization hash mismatch")
    if value.get("approved") is not True or value.get("stage0_authorized") is not True:
        raise ValueError("Stage 0 parent authorization flags are invalid")
    if value.get("formal_collection_authorized") is not False:
        raise ValueError("Stage 0 parent must not authorize formal collection")
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
    stage0_manifest: Mapping[str, Any] | None,
    bundle_set_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    budget = scope_budget(scope)
    payload = {
        "schema_version": "cmf_stage0_smoke_scope_request_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_stage0_smoke_v1",
        "implementation_strategy": "f4_hash_fix_then_12_smoke_v1",
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
        "allowed_physical_gpu_indices": list(range(8)),
        "scope_budget": budget,
        "budget_receipt_sha256": budget_receipt_sha256(),
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
    namespace_id: str,
    authorization_id: str,
    authorized_run_id: str,
    stage0_manifest: Mapping[str, Any] | None = None,
    stage0_manifest_path: Path | None = None,
    validity_seconds: int = 3600,
    _publication: Mapping[str, Any] | None = None,
    _parent: Mapping[str, Any] | None = None,
    bundle_set_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not 0 < validity_seconds <= 3600:
        raise ValueError("authorization validity must be within one hour")
    publication = dict(
        _publication
        if _publication is not None
        else _validate_reviewed_publication(reviewed_content_commit)
    )
    parent = dict(
        _parent if _parent is not None else load_parent_user_authorization()
    )
    planned = planned_scope_spec(
        scope, stage0_manifest=stage0_manifest
    )
    family = SCOPE_FAMILIES[scope]
    group = "controlled_multi_future_stage0_smoke_v1"
    request_path = AUDIT_ROOT / "scope_requests" / group / f"{namespace_id}.request.json"
    lock_path = AUDIT_ROOT / "source_locks" / group / f"{namespace_id}.source_lock.json"
    auth_path = AUDIT_ROOT / "authorizations" / group / f"{namespace_id}.authorization.json"
    guard_path = AUDIT_ROOT / "gpu_guards" / group / f"{namespace_id}.guard.json"
    output_namespace = (
        AUDIT_ROOT / "probe_outputs" / namespace_id
        if scope == F4_INFRA_SCOPE
        else DATASET_ROOT / namespace_id
    )
    for path in (request_path, lock_path, auth_path, guard_path, output_namespace):
        if path.exists():
            raise FileExistsError(path)
    child_command = (
        str(PYTHON_EXECUTABLE),
        "-m",
        "controlled_multi_future.probes.stage0_smoke_scope_runner",
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
        stage0_manifest=stage0_manifest,
        bundle_set_receipt=bundle_set_receipt,
    )
    source_lock = capture_runtime_source_lock(family=family)
    now = datetime.now(timezone.utc)
    budget = scope_budget(scope)
    source_bindings = current_stage0_source_bindings()
    authorization = {
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_stage0_smoke_v1",
        "implementation_revision": "f4_hash_fix_then_12_smoke_v1",
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
        "allowed_physical_gpu_indices": list(range(8)),
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
        "stage0_data": budget["stage0_data"],
        "stage0_authorized": True,
    }
    _write_new(request_path, request)
    authorization["approval_request_file_sha256"] = sha256_file(request_path)
    write_runtime_source_lock(lock_path, source_lock)
    authorization["receipt_sha256"] = authorization_receipt_sha256(
        authorization
    )
    _write_new(auth_path, authorization)
    return {
        "schema_version": "cmf_stage0_smoke_scope_bundle_v1",
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
        "timeout_seconds": budget["timeout_seconds"],
        "formal_data": False,
        "stage0_data": budget["stage0_data"],
        "stage0_authorized": True,
    }


def _validate_stage0_manifest_for_bundle(
    stage0_manifest: Mapping[str, Any], publication: Mapping[str, Any]
) -> dict[str, Any]:
    manifest = json.loads(
        json.dumps(stage0_manifest, sort_keys=True, allow_nan=False)
    )
    payload = dict(manifest)
    digest = payload.pop("manifest_sha256", None)
    roots = manifest.get("root_specs", {})
    attempts = manifest.get("attempts", [])
    root_hash_checks = {}
    for family, root in roots.items():
        root_payload = dict(root)
        root_digest = root_payload.pop("planned_root_slot_spec_sha256", None)
        root_hash_checks[family] = isinstance(root_digest, str) and hash_json(
            root_payload
        ) == root_digest
    checks = {
        "manifest_self_hash": isinstance(digest, str)
        and hash_json(payload) == digest,
        "implementation_version": manifest.get("implementation_version")
        == "controlled_multi_future_stage0_smoke_v1",
        "stage0_flags": manifest.get("stage0_authorized") is True
        and manifest.get("stage0_data") is True
        and manifest.get("formal_data") is False,
        "exact_four_roots": set(roots) == {"F1", "F2", "F3", "F4"},
        "root_specs_self_hash": len(root_hash_checks) == 4
        and all(root_hash_checks.values()),
        "exact_twelve_attempts": len(attempts) == 12
        and len({item.get("attempt_id") for item in attempts}) == 12,
        "exact_three_per_family": all(
            sum(item.get("family") == family for item in attempts) == 3
            for family in ("F1", "F2", "F3", "F4")
        ),
        "infra_source_matches_publication": manifest.get(
            "f4_infrastructure_source_sha256"
        )
        == publication.get("active_snapshot_source_sha256"),
        "infra_validation_all_pass": bool(
            manifest.get("f4_infrastructure_validation_checks")
        )
        and all(
            value is True
            for value in manifest[
                "f4_infrastructure_validation_checks"
            ].values()
        ),
    }
    result = {"checks": checks, "root_hash_checks": root_hash_checks, "pass": all(checks.values())}
    if not result["pass"]:
        raise ValueError(f"Stage 0 manifest bundle Gate failed: {checks}")
    return result


def build_f4_infrastructure_bundle(
    *, reviewed_content_commit: str, validity_seconds: int = 3600
) -> dict[str, Any]:
    return _build_scope_bundle(
        scope=F4_INFRA_SCOPE,
        reviewed_content_commit=reviewed_content_commit,
        namespace_id="prestage0_f4_candidate_hash_infra_v12_seed20260829_run1",
        authorization_id="prestage0-f4-candidate-hash-infra-v12-run1",
        authorized_run_id="prestage0-f4-candidate-hash-infra-v12-run1",
        stage0_manifest=None,
        validity_seconds=validity_seconds,
    )


def build_stage0_bundle_set(
    *,
    reviewed_content_commit: str,
    stage0_manifest_path: Path = CANONICAL_STAGE0_MANIFEST,
    validity_seconds: int = 3600,
) -> dict[str, Any]:
    publication = _validate_reviewed_publication(reviewed_content_commit)
    parent = load_parent_user_authorization()
    manifest_path = Path(stage0_manifest_path).resolve()
    if manifest_path != CANONICAL_STAGE0_MANIFEST.resolve():
        raise ValueError("Stage 0 manifest path is not canonical")
    if not manifest_path.is_file():
        raise ValueError("canonical Stage 0 manifest is missing")
    stage0_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_manifest = build_stage0_smoke_manifest(CANONICAL_INFRA_RECEIPT)
    if stage0_manifest != expected_manifest:
        raise ValueError(
            "canonical Stage 0 manifest differs from deterministic F4 evidence reconstruction"
        )
    relative_manifest = manifest_path.relative_to(VAULT_ROOT).as_posix()
    _git("cat-file", "-e", f"{reviewed_content_commit}:{relative_manifest}")
    if _git("show", f"{reviewed_content_commit}:{relative_manifest}") != (
        manifest_path.read_text(encoding="utf-8").strip()
    ):
        raise ValueError("published commit Stage 0 manifest bytes differ")
    manifest_gate = _validate_stage0_manifest_for_bundle(
        stage0_manifest, publication
    )
    manifest_sha = str(stage0_manifest["manifest_sha256"])
    group = "controlled_multi_future_stage0_smoke_v1"
    namespace_by_scope = {
        scope: f"stage0_smoke_v1_{SCOPE_FAMILIES[scope]}_root_A_seed20260829_run1"
        for scope in STAGE0_SCOPES
    }
    authorization_id_by_scope = {
        scope: f"stage0-smoke-v1-{SCOPE_FAMILIES[scope]}-root-A-run1"
        for scope in STAGE0_SCOPES
    }
    authorization_paths = {
        scope: str(
            AUDIT_ROOT
            / "authorizations"
            / group
            / f"{namespace_by_scope[scope]}.authorization.json"
        )
        for scope in STAGE0_SCOPES
    }
    set_path = (
        AUDIT_ROOT
        / "authorizations"
        / group
        / f"stage0_bundle_set_{manifest_sha}.json"
    )
    set_receipt = {
        "schema_version": "cmf_stage0_smoke_bundle_set_receipt_v1",
        "path": str(set_path),
        "reviewed_content_commit": reviewed_content_commit,
        "implementation_source_sha256": publication[
            "active_snapshot_source_sha256"
        ],
        "stage0_manifest_sha256": manifest_sha,
        "stage0_manifest_path": str(manifest_path),
        "stage0_manifest_file_sha256": sha256_file(manifest_path),
        "budget_receipt_sha256": budget_receipt_sha256(),
        "parent_user_authorization_sha256": parent[
            "parent_user_authorization_sha256"
        ],
        "scopes": list(STAGE0_SCOPES),
        "namespace_by_scope": namespace_by_scope,
        "authorization_id_by_scope": authorization_id_by_scope,
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
        bundles[scope] = _build_scope_bundle(
            scope=scope,
            reviewed_content_commit=reviewed_content_commit,
            namespace_id=namespace_by_scope[scope],
            authorization_id=authorization_id_by_scope[scope],
            authorized_run_id=authorization_id_by_scope[scope] + "-run",
            stage0_manifest=stage0_manifest,
            stage0_manifest_path=manifest_path,
            validity_seconds=validity_seconds,
            _publication=publication,
            _parent=parent,
            bundle_set_receipt=set_receipt,
        )
    return {
        "schema_version": "cmf_stage0_smoke_bundle_set_v1",
        "reviewed_content_commit": reviewed_content_commit,
        "stage0_manifest_sha256": manifest_sha,
        "manifest_gate": manifest_gate,
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
    "build_f4_infrastructure_bundle",
    "build_stage0_bundle_set",
    "load_parent_user_authorization",
]
