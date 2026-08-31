"""Fail-closed authorization for the F4 post-Stage-0 planner-only audit."""

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
from ..post_stage0_f4_scope_v1 import (
    AUTHORIZATION_ID, AUTHORIZATION_PATH, BUDGET_PUBLICATION, GUARD_PATH,
    IMPACT_REVIEW, OUTPUT_NAMESPACE, PARENT_AUTHORIZATION, REQUEST_PATH,
    SCENE_SEED, SCOPE, SCOPE_PUBLICATION, SOURCE_LOCK_PATH,
    post_stage0_f4_budget_v1, post_stage0_f4_parent_authorization_v1,
    post_stage0_f4_planned_spec_v1, post_stage0_f4_scope_publication_v1,
)
from ..real_sapien_adapter_post_stage0_f4_v1 import IMPLEMENTATION_VERSION
from ..runtime_source_lock_v1 import load_runtime_source_lock
from .runtime_v3_3_authorization_v1 import (
    AuthorizationBindingError, AuthorizationExpiredError, AuthorizationReplayError,
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY, CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)


AUTHORIZATION_SCHEMA_VERSION = "cmf_post_stage0_f4_authorization_v1"
CONSUMPTION_SCHEMA_VERSION = "cmf_post_stage0_f4_authorization_consumption_v1"
WORKSPACE_ROOT = Path("/nfs_share/lijunhui")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def authorization_receipt_sha256(value: Mapping[str, Any]) -> str:
    payload = dict(value); payload.pop("receipt_sha256", None); return hash_json(payload)


def _time(value, label):
    try: result = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc: raise AuthorizationBindingError(f"{label} invalid") from exc
    if result.tzinfo is None: raise AuthorizationBindingError(f"{label} lacks timezone")
    return result.astimezone(timezone.utc)


def _file(value, label):
    path = Path(value).resolve() if isinstance(value, str) else Path("/")
    if not str(path).startswith(str(WORKSPACE_ROOT) + "/") or not path.is_file():
        raise AuthorizationBindingError(f"{label} path invalid")
    return path


def _workspace_path(value, label):
    path = Path(value).resolve() if isinstance(value, str) else Path("/")
    if not str(path).startswith(str(WORKSPACE_ROOT) + "/"):
        raise AuthorizationBindingError(f"{label} path invalid")
    return path


def validate_post_stage0_f4_authorization_v1(value: Mapping[str, Any], *, requested_scope: str,
    now: datetime | None = None, expected_output_namespace: str | None = None,
    expected_family: str | None = None, expected_seed: int | None = None,
    expected_reviewed_content_commit: str | None = None) -> dict[str, Any]:
    if requested_scope != SCOPE: raise AuthorizationBindingError("unsupported F4 scope")
    receipt = json.loads(json.dumps(value, sort_keys=True, allow_nan=False))
    fixed = {"schema_version": AUTHORIZATION_SCHEMA_VERSION, "implementation_version": IMPLEMENTATION_VERSION,
        "approved": True, "approved_scopes": [SCOPE], "authorization_id": AUTHORIZATION_ID,
        "authorized_run_id": AUTHORIZATION_ID + "-run", "family": "F4", "scene_seed": SCENE_SEED,
        "max_invocations": 1, "automatic_retry": False, "recovery_attempts": 0, "formal_data": False,
        "stage0_data": False, "stage0_authorized": False, "stage0_reopened": False, "stage1_authorized": False}
    for key, expected in fixed.items():
        if receipt.get(key) != expected: raise AuthorizationBindingError(f"authorization changed: {key}")
    if expected_family is not None and expected_family != "F4": raise AuthorizationBindingError("family mismatch")
    if expected_seed is not None and expected_seed != SCENE_SEED: raise AuthorizationBindingError("seed mismatch")
    if receipt.get("receipt_sha256") != authorization_receipt_sha256(receipt): raise AuthorizationBindingError("receipt hash mismatch")
    issued, expires = _time(receipt.get("issued_at"), "issued"), _time(receipt.get("expires_at"), "expires")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not 0 < (expires-issued).total_seconds() <= 3600 or not issued <= current < expires: raise AuthorizationExpiredError("authorization inactive")
    validate_current_gpu_authorization(receipt)
    budget = post_stage0_f4_budget_v1()
    for key, expected in (("budget_receipt_sha256", budget["budget_receipt_sha256"]),
        ("planner_query_limit", budget["planner_query_limit"]),
        ("controlled_action_limit", budget["canonical_prefix_reference_execution_limit"]),
        ("physics_step_limit", budget["physics_step_limit"]), ("timeout_seconds", budget["timeout_seconds"])):
        if receipt.get(key) != expected: raise AuthorizationBindingError(f"budget mismatch: {key}")
    publications = (("budget_publication_path", BUDGET_PUBLICATION, budget),
        ("scope_publication_path", SCOPE_PUBLICATION, post_stage0_f4_scope_publication_v1()),
        ("parent_user_authorization_path", PARENT_AUTHORIZATION, post_stage0_f4_parent_authorization_v1()))
    for field, expected_path, expected_value in publications:
        path = _file(receipt.get(field), field); sha_field = field.replace("_path", "_file_sha256")
        if path != expected_path.resolve() or _file_sha(path) != receipt.get(sha_field) or json.loads(path.read_text()) != expected_value:
            raise AuthorizationBindingError(f"publication mismatch: {field}")
    planned = post_stage0_f4_planned_spec_v1()
    if receipt.get("planned_root_slot_spec") != planned or receipt.get("planned_root_slot_spec_sha256") != planned["planned_scope_spec_sha256"]:
        raise AuthorizationBindingError("planned spec mismatch")
    impact = _file(receipt.get("impact_review_path"), "impact")
    if impact != IMPACT_REVIEW.resolve() or _file_sha(impact) != receipt.get("impact_review_file_sha256") or json.loads(impact.read_text()).get("review_payload_sha256") != receipt.get("impact_review_payload_sha256"):
        raise AuthorizationBindingError("impact review mismatch")
    source_path = _file(receipt.get("source_lock_receipt_path"), "source lock")
    if source_path != SOURCE_LOCK_PATH.resolve(): raise AuthorizationBindingError("source path mismatch")
    source = load_runtime_source_lock(source_path, expected_family="F4")
    if source["source_lock_receipt_sha256"] != receipt.get("source_lock_receipt_sha256") or source["snapshot"]["implementation_source_sha256"] != receipt.get("implementation_source_sha256"):
        raise AuthorizationBindingError("source lock mismatch")
    request_path = _file(receipt.get("approval_request_path"), "request")
    if request_path != REQUEST_PATH.resolve() or _file_sha(request_path) != receipt.get("approval_request_file_sha256"):
        raise AuthorizationBindingError("request file mismatch")
    request = json.loads(request_path.read_text()); payload = dict(request); digest = payload.pop("scope_request_sha256", None)
    if hash_json(payload) != digest or digest != receipt.get("approval_request_sha256") or request.get("planned_root_slot_spec") != planned or request.get("authorized_command_sha256") != receipt.get("authorized_command_sha256") or request.get("output_namespace") != receipt.get("output_namespace"):
        raise AuthorizationBindingError("request mismatch")
    expected_paths = {"consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        "gpu_lease_directory": CANONICAL_GPU_LEASE_DIRECTORY, "job_cache_root_directory": CANONICAL_JOB_CACHE_DIRECTORY,
        "output_namespace": str(OUTPUT_NAMESPACE.resolve()), "guard_receipt_path": str(GUARD_PATH.resolve())}
    for key, expected in expected_paths.items():
        if str(_workspace_path(receipt.get(key), key)) != expected: raise AuthorizationBindingError(f"path mismatch: {key}")
    if expected_output_namespace is not None and Path(expected_output_namespace).resolve() != OUTPUT_NAMESPACE.resolve(): raise AuthorizationBindingError("output mismatch")
    commit = receipt.get("reviewed_content_commit")
    if not isinstance(commit, str) or not HEX40.fullmatch(commit) or (expected_reviewed_content_commit is not None and commit != expected_reviewed_content_commit): raise AuthorizationBindingError("commit mismatch")
    if not isinstance(receipt.get("authorized_command_sha256"), str) or not HEX64.fullmatch(receipt["authorized_command_sha256"]): raise AuthorizationBindingError("command hash invalid")
    if receipt.get("uncommitted_source_bound_by_source_lock") is not True: raise AuthorizationBindingError("source-lock disclosure missing")
    return receipt


def load_post_stage0_f4_authorization_v1(path: Path, *, requested_scope: str, **kwargs):
    path = Path(path).resolve()
    if path != AUTHORIZATION_PATH.resolve(): raise AuthorizationBindingError("authorization path noncanonical")
    return validate_post_stage0_f4_authorization_v1(json.loads(path.read_text()), requested_scope=requested_scope, **kwargs)


def consumption_receipt_sha256(value):
    payload = dict(value); payload.pop("consumption_receipt_sha256", None); payload.pop("path", None); return hash_json(payload)


def consume_post_stage0_f4_authorization_once_v1(authorization, *, ledger_directory: Path):
    ledger = Path(ledger_directory).resolve()
    if str(ledger) != CANONICAL_CONSUMPTION_LEDGER_DIRECTORY: raise AuthorizationBindingError("ledger noncanonical")
    ledger.mkdir(parents=True, exist_ok=True); path = ledger / f"{AUTHORIZATION_ID}.json"
    value = {"schema_version": CONSUMPTION_SCHEMA_VERSION, "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": AUTHORIZATION_ID, "authorization_receipt_sha256": authorization["receipt_sha256"],
        "approved_scope": SCOPE, "family": "F4", "scene_seed": SCENE_SEED,
        "consumed_at": datetime.now(timezone.utc).isoformat(), "max_invocations": 1}
    value["consumption_receipt_sha256"] = consumption_receipt_sha256(value)
    try: fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc: raise AuthorizationReplayError("authorization consumed") from exc
    with os.fdopen(fd, "wb") as handle: handle.write((json.dumps(value, indent=2, sort_keys=True)+"\n").encode()); handle.flush(); os.fsync(handle.fileno())
    return {**value, "path": str(path)}


def validate_post_stage0_f4_consumption_v1(value, authorization):
    result = dict(value); expected = {"schema_version": CONSUMPTION_SCHEMA_VERSION, "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": AUTHORIZATION_ID, "authorization_receipt_sha256": authorization.get("receipt_sha256"),
        "approved_scope": SCOPE, "family": "F4", "scene_seed": SCENE_SEED, "max_invocations": 1}
    if any(result.get(k) != v for k,v in expected.items()) or result.get("consumption_receipt_sha256") != consumption_receipt_sha256(result): raise AuthorizationBindingError("consumption mismatch")
    return result


def load_post_stage0_f4_consumption_v1(path, authorization):
    result = validate_post_stage0_f4_consumption_v1(json.loads(Path(path).read_text()), authorization); result["path"] = str(Path(path).resolve()); return result


def authorization_summary(value):
    return {key:value.get(key) for key in ("authorization_id","receipt_sha256","approved_scopes","family","scene_seed","planned_root_slot_spec_sha256","implementation_source_sha256","budget_receipt_sha256","parent_user_authorization_sha256","reviewed_content_commit","output_namespace","timeout_seconds","allowed_physical_gpu_indices")}
