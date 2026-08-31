"""Fail-closed one-shot authorization for the F2 Stage-0 slot replacement."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from ..current_hasher import hash_json
from ..gpu_parallel_policy_v2 import validate_current_gpu_authorization
from ..runtime_source_lock_v1 import load_runtime_source_lock
from ..stage0_f2_replacement_manifest_v1_2 import (
    CANONICAL_OUTPUT as CANONICAL_REPLACEMENT_MANIFEST,
    IMPLEMENTATION_VERSION,
    OUTPUT_NAMESPACE,
    SCOPE,
    build_stage0_f2_replacement_manifest_v1_2,
    f2_replacement_budget_v1_2,
    validate_stage0_f2_replacement_manifest_v1_2,
)
from .gpu_guard_v2_1 import command_sha256
from .runtime_v3_3_authorization_v1 import (
    AuthorizationBindingError,
    AuthorizationExpiredError,
    AuthorizationReplayError,
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)


AUTHORIZATION_SCHEMA_VERSION = "cmf_stage0_f2_replacement_authorization_v1_2"
CONSUMPTION_SCHEMA_VERSION = (
    "cmf_stage0_f2_replacement_authorization_consumption_v1_2"
)
WORKSPACE_ROOT = Path("/nfs_share/lijunhui")
AUDIT_ROOT = WORKSPACE_ROOT / "Vault-on-Fvl09/数据构造/实现审计"
GROUP = "controlled_multi_future_stage0_smoke_v1_2"
PARENT_AUTHORIZATION = (
    AUDIT_ROOT / "USER_AUTHORIZATION_STAGE0_F2_REPLACEMENT_V1_2_20260831.json"
)
BUDGET_PUBLICATION = AUDIT_ROOT / "STAGE0_F2_REPLACEMENT_BUDGET_V1_2.json"
NAMESPACE = "stage0_smoke_v1_2_F2_root_A_scene_layout_replacement_run2"
AUTHORIZATION_ID = "stage0-smoke-v1-2-F2-root-A-layout-replacement-run2"
REQUEST_PATH = AUDIT_ROOT / "scope_requests" / GROUP / f"{NAMESPACE}.request.json"
SOURCE_LOCK_PATH = AUDIT_ROOT / "source_locks" / GROUP / f"{NAMESPACE}.source_lock.json"
AUTHORIZATION_PATH = AUDIT_ROOT / "authorizations" / GROUP / f"{NAMESPACE}.authorization.json"
GUARD_PATH = AUDIT_ROOT / "gpu_guards" / GROUP / f"{NAMESPACE}.guard.json"
MAX_VALIDITY_SECONDS = 3600
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def authorization_receipt_sha256(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("receipt_sha256", None)
    return hash_json(payload)


def _parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise AuthorizationBindingError(f"{label} is missing")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise AuthorizationBindingError(f"{label} is invalid") from exc
    if parsed.tzinfo is None:
        raise AuthorizationBindingError(f"{label} lacks timezone")
    return parsed.astimezone(timezone.utc)


def _workspace_file(value: Any, label: str) -> Path:
    if not isinstance(value, str):
        raise AuthorizationBindingError(f"{label} path is missing")
    path = Path(value).resolve()
    if not str(path).startswith(str(WORKSPACE_ROOT) + "/") or not path.is_file():
        raise AuthorizationBindingError(f"{label} path is invalid")
    return path


def _workspace_directory(value: Any, label: str) -> Path:
    if not isinstance(value, str):
        raise AuthorizationBindingError(f"{label} directory is missing")
    path = Path(value).resolve()
    if not str(path).startswith(str(WORKSPACE_ROOT) + "/"):
        raise AuthorizationBindingError(f"{label} directory is invalid")
    return path


def validate_stage0_f2_replacement_authorization_v1_2(
    value: Mapping[str, Any],
    *,
    requested_scope: str,
    now: datetime | None = None,
    expected_output_namespace: str | None = None,
    expected_family: str | None = None,
    expected_seed: int | None = None,
    expected_reviewed_content_commit: str | None = None,
) -> dict[str, Any]:
    if requested_scope != SCOPE:
        raise AuthorizationBindingError("unsupported F2 replacement scope")
    receipt = json.loads(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    )
    fixed = {
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "approved": True,
        "approved_scopes": [SCOPE],
        "authorization_id": AUTHORIZATION_ID,
        "authorized_run_id": AUTHORIZATION_ID + "-run",
        "family": "F2",
        "scene_seed": 20260829,
        "max_invocations": 1,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
        "stage1_authorized": False,
    }
    for key, expected in fixed.items():
        if receipt.get(key) != expected:
            raise AuthorizationBindingError(f"authorization field changed: {key}")
    if expected_family is not None and expected_family != "F2":
        raise AuthorizationBindingError("authorization family mismatch")
    if expected_seed is not None and expected_seed != 20260829:
        raise AuthorizationBindingError("authorization seed mismatch")
    if receipt.get("receipt_sha256") != authorization_receipt_sha256(receipt):
        raise AuthorizationBindingError("authorization receipt hash mismatch")
    issued = _parse_time(receipt.get("issued_at"), "issued_at")
    expires = _parse_time(receipt.get("expires_at"), "expires_at")
    if not 0 < (expires - issued).total_seconds() <= MAX_VALIDITY_SECONDS:
        raise AuthorizationExpiredError("authorization validity exceeds one hour")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if current < issued or current >= expires:
        raise AuthorizationExpiredError("authorization is expired or not active")
    validate_current_gpu_authorization(receipt)
    budget = f2_replacement_budget_v1_2()
    for key, expected in (
        ("budget_receipt_sha256", budget["budget_receipt_sha256"]),
        ("planner_query_limit", budget["planner_query_limit"]),
        ("controlled_action_limit", budget["execution_limit"]),
        ("physics_step_limit", -1),
        ("timeout_seconds", budget["timeout_seconds"]),
    ):
        if receipt.get(key) != expected:
            raise AuthorizationBindingError(f"authorization budget mismatch: {key}")
    budget_path = _workspace_file(
        receipt.get("budget_publication_path"), "budget publication"
    )
    if budget_path != BUDGET_PUBLICATION.resolve() or _sha256_file(
        budget_path
    ) != receipt.get("budget_publication_file_sha256"):
        raise AuthorizationBindingError("budget publication binding mismatch")
    if json.loads(budget_path.read_text(encoding="utf-8")) != budget:
        raise AuthorizationBindingError("budget publication content changed")
    manifest_path = _workspace_file(
        receipt.get("replacement_manifest_path"), "replacement manifest"
    )
    if manifest_path != CANONICAL_REPLACEMENT_MANIFEST.resolve() or _sha256_file(
        manifest_path
    ) != receipt.get("replacement_manifest_file_sha256"):
        raise AuthorizationBindingError("replacement manifest file binding mismatch")
    manifest = validate_stage0_f2_replacement_manifest_v1_2(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )
    if receipt.get("replacement_manifest_sha256") != manifest["manifest_sha256"]:
        raise AuthorizationBindingError("replacement manifest content mismatch")
    spec = receipt.get("planned_root_slot_spec")
    if spec != manifest["replacement_root_spec"] or receipt.get(
        "planned_root_slot_spec_sha256"
    ) != manifest["replacement_root_spec_sha256"]:
        raise AuthorizationBindingError("planned replacement spec mismatch")
    parent_path = _workspace_file(
        receipt.get("parent_user_authorization_path"), "parent authorization"
    )
    if parent_path != PARENT_AUTHORIZATION.resolve() or _sha256_file(
        parent_path
    ) != receipt.get("parent_user_authorization_file_sha256"):
        raise AuthorizationBindingError("parent authorization file mismatch")
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    parent_payload = dict(parent)
    parent_digest = parent_payload.pop("parent_user_authorization_sha256", None)
    if not isinstance(parent_digest, str) or hash_json(parent_payload) != parent_digest:
        raise AuthorizationBindingError("parent authorization self-hash mismatch")
    parent_expected = {
        "approved": True,
        "authorized_scope": SCOPE,
        "allowed_physical_gpu_indices": list(range(8)),
        "attempts": 3,
        "automatic_retry": False,
        "stage0_authorized": True,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
    }
    if any(parent.get(key) != expected for key, expected in parent_expected.items()):
        raise AuthorizationBindingError("parent authorization contract mismatch")
    if receipt.get("parent_user_authorization_sha256") != parent_digest:
        raise AuthorizationBindingError("parent authorization content mismatch")
    source_lock_path = _workspace_file(
        receipt.get("source_lock_receipt_path"), "source lock"
    )
    if source_lock_path != SOURCE_LOCK_PATH.resolve():
        raise AuthorizationBindingError("source lock path is noncanonical")
    source_lock = load_runtime_source_lock(source_lock_path, expected_family="F2")
    if source_lock.get("source_lock_receipt_sha256") != receipt.get(
        "source_lock_receipt_sha256"
    ):
        raise AuthorizationBindingError("source lock digest mismatch")
    live_source = source_lock["snapshot"]["implementation_source_sha256"]
    if receipt.get("implementation_source_sha256") != live_source:
        raise AuthorizationBindingError("implementation source binding mismatch")
    request_path = _workspace_file(receipt.get("approval_request_path"), "request")
    if request_path != REQUEST_PATH.resolve() or _sha256_file(
        request_path
    ) != receipt.get("approval_request_file_sha256"):
        raise AuthorizationBindingError("approval request file mismatch")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request_payload = dict(request)
    request_digest = request_payload.pop("scope_request_sha256", None)
    if not isinstance(request_digest, str) or hash_json(request_payload) != request_digest:
        raise AuthorizationBindingError("scope request self-hash mismatch")
    if request_digest != receipt.get("approval_request_sha256"):
        raise AuthorizationBindingError("scope request content mismatch")
    request_checks = {
        "scope": request.get("scope") == SCOPE,
        "spec": request.get("planned_root_slot_spec") == spec,
        "manifest": request.get("replacement_manifest_sha256")
        == manifest["manifest_sha256"],
        "command": request.get("authorized_command_sha256")
        == receipt.get("authorized_command_sha256"),
        "output": request.get("output_namespace")
        == receipt.get("output_namespace"),
    }
    if not all(request_checks.values()):
        raise AuthorizationBindingError(f"request/authorization mismatch: {request_checks}")
    expected_paths = {
        "consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        "gpu_lease_directory": CANONICAL_GPU_LEASE_DIRECTORY,
        "job_cache_root_directory": CANONICAL_JOB_CACHE_DIRECTORY,
        "output_namespace": str(OUTPUT_NAMESPACE.resolve()),
        "guard_receipt_path": str(GUARD_PATH.resolve()),
    }
    for key, expected in expected_paths.items():
        actual = str(_workspace_directory(receipt.get(key), key))
        if actual != expected:
            raise AuthorizationBindingError(f"authorization path mismatch: {key}")
    if expected_output_namespace is not None and Path(
        expected_output_namespace
    ).resolve() != OUTPUT_NAMESPACE.resolve():
        raise AuthorizationBindingError("Guard output namespace mismatch")
    if not isinstance(receipt.get("reviewed_content_commit"), str) or HEX40.fullmatch(
        receipt["reviewed_content_commit"]
    ) is None:
        raise AuthorizationBindingError("reviewed content commit is invalid")
    if (
        expected_reviewed_content_commit is not None
        and receipt["reviewed_content_commit"]
        != expected_reviewed_content_commit
    ):
        raise AuthorizationBindingError("reviewed content commit mismatch")
    if not isinstance(receipt.get("authorized_command_sha256"), str) or HEX64.fullmatch(
        receipt["authorized_command_sha256"]
    ) is None:
        raise AuthorizationBindingError("authorized command SHA is invalid")
    return receipt


def load_stage0_f2_replacement_authorization_v1_2(
    path: Path, *, requested_scope: str, **kwargs
) -> dict[str, Any]:
    path = Path(path).resolve()
    if path != AUTHORIZATION_PATH.resolve():
        raise AuthorizationBindingError("authorization path is noncanonical")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationBindingError("authorization is unreadable") from exc
    return validate_stage0_f2_replacement_authorization_v1_2(
        value, requested_scope=requested_scope, **kwargs
    )


def consumption_receipt_sha256(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("consumption_receipt_sha256", None)
    payload.pop("path", None)
    return hash_json(payload)


def consume_stage0_f2_replacement_authorization_once_v1_2(
    authorization: Mapping[str, Any], *, ledger_directory: Path
) -> dict[str, Any]:
    ledger = Path(ledger_directory).resolve()
    if str(ledger) != CANONICAL_CONSUMPTION_LEDGER_DIRECTORY:
        raise AuthorizationBindingError("consumption ledger is noncanonical")
    ledger.mkdir(parents=True, exist_ok=True)
    path = ledger / f"{authorization['authorization_id']}.json"
    value = {
        "schema_version": CONSUMPTION_SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": authorization["authorization_id"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "approved_scope": SCOPE,
        "family": "F2",
        "scene_seed": 20260829,
        "consumed_at": datetime.now(timezone.utc).isoformat(),
        "max_invocations": 1,
    }
    value["consumption_receipt_sha256"] = consumption_receipt_sha256(value)
    data = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise AuthorizationReplayError("authorization was already consumed") from exc
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return {**value, "path": str(path)}


def validate_stage0_f2_replacement_consumption_v1_2(
    value: Mapping[str, Any], authorization: Mapping[str, Any]
) -> dict[str, Any]:
    result = dict(value)
    expected = {
        "schema_version": CONSUMPTION_SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": authorization.get("authorization_id"),
        "authorization_receipt_sha256": authorization.get("receipt_sha256"),
        "approved_scope": SCOPE,
        "family": "F2",
        "scene_seed": 20260829,
        "max_invocations": 1,
    }
    if any(result.get(key) != wanted for key, wanted in expected.items()):
        raise AuthorizationBindingError("consumption receipt binding mismatch")
    if result.get("consumption_receipt_sha256") != consumption_receipt_sha256(
        result
    ):
        raise AuthorizationBindingError("consumption receipt hash mismatch")
    return result


def load_stage0_f2_replacement_consumption_v1_2(
    path: Path, authorization: Mapping[str, Any]
) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    result = validate_stage0_f2_replacement_consumption_v1_2(
        value, authorization
    )
    result["path"] = str(Path(path).resolve())
    return result


def authorization_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "authorization_id",
        "receipt_sha256",
        "approved_scopes",
        "family",
        "scene_seed",
        "planned_root_slot_spec_sha256",
        "replacement_manifest_sha256",
        "implementation_source_sha256",
        "budget_receipt_sha256",
        "parent_user_authorization_sha256",
        "reviewed_content_commit",
        "output_namespace",
        "timeout_seconds",
        "allowed_physical_gpu_indices",
    )
    return {key: value.get(key) for key in keys}


__all__ = [
    "AUTHORIZATION_ID",
    "AUTHORIZATION_PATH",
    "AUTHORIZATION_SCHEMA_VERSION",
    "BUDGET_PUBLICATION",
    "GUARD_PATH",
    "PARENT_AUTHORIZATION",
    "REQUEST_PATH",
    "SOURCE_LOCK_PATH",
    "authorization_receipt_sha256",
    "authorization_summary",
    "consume_stage0_f2_replacement_authorization_once_v1_2",
    "load_stage0_f2_replacement_authorization_v1_2",
    "load_stage0_f2_replacement_consumption_v1_2",
    "validate_stage0_f2_replacement_authorization_v1_2",
    "validate_stage0_f2_replacement_consumption_v1_2",
]
