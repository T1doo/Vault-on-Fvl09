"""Fail-closed one-shot authorization for the post-Stage-0 F3 diagnostic."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from ..current_hasher import hash_json
from ..f3_contact_preserving_prefix_v11 import IMPLEMENTATION_VERSION
from ..gpu_parallel_policy_v2 import validate_current_gpu_authorization
from ..post_stage0_f3_scope_v1 import (
    AUTHORIZATION_ID,
    AUTHORIZATION_PATH,
    BUDGET_PUBLICATION,
    GUARD_PATH,
    IMPACT_REVIEW,
    OUTPUT_NAMESPACE,
    PARENT_AUTHORIZATION,
    REQUEST_PATH,
    SCENE_SEED,
    SCOPE,
    SCOPE_PUBLICATION,
    SOURCE_LOCK_PATH,
    post_stage0_f3_budget_v1,
    post_stage0_f3_parent_authorization_v1,
    post_stage0_f3_planned_spec_v1,
    post_stage0_f3_scope_publication_v1,
)
from ..runtime_source_lock_v1 import load_runtime_source_lock
from .runtime_v3_3_authorization_v1 import (
    AuthorizationBindingError,
    AuthorizationExpiredError,
    AuthorizationReplayError,
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)


AUTHORIZATION_SCHEMA_VERSION = "cmf_post_stage0_f3_authorization_v1"
CONSUMPTION_SCHEMA_VERSION = "cmf_post_stage0_f3_authorization_consumption_v1"
WORKSPACE_ROOT = Path("/nfs_share/lijunhui")
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
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise AuthorizationBindingError(f"{label} is invalid") from exc
    if result.tzinfo is None:
        raise AuthorizationBindingError(f"{label} lacks timezone")
    return result.astimezone(timezone.utc)


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


def validate_post_stage0_f3_authorization_v1(
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
        raise AuthorizationBindingError("unsupported post-Stage-0 F3 scope")
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
        "family": "F3",
        "scene_seed": SCENE_SEED,
        "max_invocations": 1,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage0_reopened": False,
        "stage1_authorized": False,
    }
    for key, expected in fixed.items():
        if receipt.get(key) != expected:
            raise AuthorizationBindingError(f"authorization field changed: {key}")
    if expected_family is not None and expected_family != "F3":
        raise AuthorizationBindingError("authorization family mismatch")
    if expected_seed is not None and expected_seed != SCENE_SEED:
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

    budget = post_stage0_f3_budget_v1()
    for key, expected in (
        ("budget_receipt_sha256", budget["budget_receipt_sha256"]),
        ("planner_query_limit", budget["planner_query_limit"]),
        ("controlled_action_limit", budget["execution_limit"]),
        ("physics_step_limit", budget["physics_step_limit"]),
        ("timeout_seconds", budget["timeout_seconds"]),
    ):
        if receipt.get(key) != expected:
            raise AuthorizationBindingError(f"authorization budget mismatch: {key}")
    bindings = (
        ("budget_publication_path", BUDGET_PUBLICATION, budget),
        (
            "scope_publication_path",
            SCOPE_PUBLICATION,
            post_stage0_f3_scope_publication_v1(),
        ),
        (
            "parent_user_authorization_path",
            PARENT_AUTHORIZATION,
            post_stage0_f3_parent_authorization_v1(),
        ),
    )
    for field, expected_path, expected_value in bindings:
        path = _workspace_file(receipt.get(field), field)
        sha_field = field.replace("_path", "_file_sha256")
        if path != expected_path.resolve() or _sha256_file(path) != receipt.get(sha_field):
            raise AuthorizationBindingError(f"publication binding mismatch: {field}")
        if json.loads(path.read_text(encoding="utf-8")) != expected_value:
            raise AuthorizationBindingError(f"publication content changed: {field}")
    parent = post_stage0_f3_parent_authorization_v1()
    if receipt.get("parent_user_authorization_sha256") != parent[
        "parent_user_authorization_sha256"
    ]:
        raise AuthorizationBindingError("parent authorization hash mismatch")
    scope_publication = post_stage0_f3_scope_publication_v1()
    if receipt.get("scope_publication_sha256") != scope_publication[
        "scope_publication_sha256"
    ]:
        raise AuthorizationBindingError("scope publication hash mismatch")
    planned = post_stage0_f3_planned_spec_v1()
    if receipt.get("planned_root_slot_spec") != planned or receipt.get(
        "planned_root_slot_spec_sha256"
    ) != planned["planned_scope_spec_sha256"]:
        raise AuthorizationBindingError("planned F3 diagnostic spec mismatch")
    impact = _workspace_file(receipt.get("impact_review_path"), "impact review")
    if impact != IMPACT_REVIEW.resolve() or _sha256_file(impact) != receipt.get(
        "impact_review_file_sha256"
    ):
        raise AuthorizationBindingError("impact review file binding mismatch")
    impact_value = json.loads(impact.read_text(encoding="utf-8"))
    if impact_value.get("review_payload_sha256") != receipt.get(
        "impact_review_payload_sha256"
    ):
        raise AuthorizationBindingError("impact review payload mismatch")
    source_path = _workspace_file(
        receipt.get("source_lock_receipt_path"), "source lock"
    )
    if source_path != SOURCE_LOCK_PATH.resolve():
        raise AuthorizationBindingError("source lock path is noncanonical")
    source_lock = load_runtime_source_lock(source_path, expected_family="F3")
    if source_lock.get("source_lock_receipt_sha256") != receipt.get(
        "source_lock_receipt_sha256"
    ):
        raise AuthorizationBindingError("source lock hash mismatch")
    if source_lock["snapshot"]["implementation_source_sha256"] != receipt.get(
        "implementation_source_sha256"
    ):
        raise AuthorizationBindingError("implementation source mismatch")
    request_path = _workspace_file(receipt.get("approval_request_path"), "request")
    if request_path != REQUEST_PATH.resolve() or _sha256_file(request_path) != receipt.get(
        "approval_request_file_sha256"
    ):
        raise AuthorizationBindingError("scope request binding mismatch")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request_payload = dict(request)
    request_sha = request_payload.pop("scope_request_sha256", None)
    if not isinstance(request_sha, str) or hash_json(request_payload) != request_sha:
        raise AuthorizationBindingError("scope request self-hash mismatch")
    request_checks = {
        "scope": request.get("scope") == SCOPE,
        "planned": request.get("planned_root_slot_spec") == planned,
        "source": request.get("implementation_source_sha256")
        == receipt.get("implementation_source_sha256"),
        "command": request.get("authorized_command_sha256")
        == receipt.get("authorized_command_sha256"),
        "output": request.get("output_namespace") == receipt.get("output_namespace"),
    }
    if not all(request_checks.values()) or request_sha != receipt.get(
        "approval_request_sha256"
    ):
        raise AuthorizationBindingError(f"request mismatch: {request_checks}")
    expected_paths = {
        "consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        "gpu_lease_directory": CANONICAL_GPU_LEASE_DIRECTORY,
        "job_cache_root_directory": CANONICAL_JOB_CACHE_DIRECTORY,
        "output_namespace": str(OUTPUT_NAMESPACE.resolve()),
        "guard_receipt_path": str(GUARD_PATH.resolve()),
    }
    for key, expected in expected_paths.items():
        if str(_workspace_directory(receipt.get(key), key)) != expected:
            raise AuthorizationBindingError(f"authorization path mismatch: {key}")
    if expected_output_namespace is not None and Path(
        expected_output_namespace
    ).resolve() != OUTPUT_NAMESPACE.resolve():
        raise AuthorizationBindingError("Guard output namespace mismatch")
    commit = receipt.get("reviewed_content_commit")
    if not isinstance(commit, str) or HEX40.fullmatch(commit) is None:
        raise AuthorizationBindingError("reviewed content commit is invalid")
    if expected_reviewed_content_commit is not None and commit != expected_reviewed_content_commit:
        raise AuthorizationBindingError("reviewed content commit mismatch")
    command_sha = receipt.get("authorized_command_sha256")
    if not isinstance(command_sha, str) or HEX64.fullmatch(command_sha) is None:
        raise AuthorizationBindingError("authorized command SHA is invalid")
    if receipt.get("uncommitted_source_bound_by_source_lock") is not True:
        raise AuthorizationBindingError("uncommitted source-lock disclosure missing")
    return receipt


def load_post_stage0_f3_authorization_v1(
    path: Path, *, requested_scope: str, **kwargs
) -> dict[str, Any]:
    path = Path(path).resolve()
    if path != AUTHORIZATION_PATH.resolve():
        raise AuthorizationBindingError("authorization path is noncanonical")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationBindingError("authorization is unreadable") from exc
    return validate_post_stage0_f3_authorization_v1(
        value, requested_scope=requested_scope, **kwargs
    )


def consumption_receipt_sha256(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("consumption_receipt_sha256", None)
    payload.pop("path", None)
    return hash_json(payload)


def consume_post_stage0_f3_authorization_once_v1(
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
        "family": "F3",
        "scene_seed": SCENE_SEED,
        "consumed_at": datetime.now(timezone.utc).isoformat(),
        "max_invocations": 1,
    }
    value["consumption_receipt_sha256"] = consumption_receipt_sha256(value)
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise AuthorizationReplayError("authorization was already consumed") from exc
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return {**value, "path": str(path)}


def validate_post_stage0_f3_consumption_v1(
    value: Mapping[str, Any], authorization: Mapping[str, Any]
) -> dict[str, Any]:
    result = dict(value)
    expected = {
        "schema_version": CONSUMPTION_SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": authorization.get("authorization_id"),
        "authorization_receipt_sha256": authorization.get("receipt_sha256"),
        "approved_scope": SCOPE,
        "family": "F3",
        "scene_seed": SCENE_SEED,
        "max_invocations": 1,
    }
    if any(result.get(key) != wanted for key, wanted in expected.items()):
        raise AuthorizationBindingError("consumption receipt binding mismatch")
    if result.get("consumption_receipt_sha256") != consumption_receipt_sha256(result):
        raise AuthorizationBindingError("consumption receipt hash mismatch")
    return result


def load_post_stage0_f3_consumption_v1(
    path: Path, authorization: Mapping[str, Any]
) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    result = validate_post_stage0_f3_consumption_v1(value, authorization)
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
    "AUTHORIZATION_SCHEMA_VERSION",
    "authorization_receipt_sha256",
    "authorization_summary",
    "consume_post_stage0_f3_authorization_once_v1",
    "load_post_stage0_f3_authorization_v1",
    "load_post_stage0_f3_consumption_v1",
    "validate_post_stage0_f3_authorization_v1",
    "validate_post_stage0_f3_consumption_v1",
]
