"""Fail-closed authorization binding for the F3 V2_1 one-shot."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path

from ..closure_f3_scope_v2_1 import *
from ..canonical_artifact import (
    canonical_hash_json as hash_json,
    canonical_jsonable,
    canonical_write_json,
)
from ..f3_common_grasp_prefix_v2_1 import IMPLEMENTATION_VERSION
from ..gpu_parallel_policy_v2 import validate_current_gpu_authorization
from ..runtime_source_lock_v1 import load_runtime_source_lock
from .runtime_v3_3_authorization_v1 import (
    AuthorizationBindingError,
    AuthorizationExpiredError,
    AuthorizationReplayError,
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)


AUTH_SCHEMA = "cmf_post_stage0_f3_v2_1_authorization"
CONSUMPTION_SCHEMA = "cmf_post_stage0_f3_v2_1_consumption"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _fsha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def receipt_sha(value):
    payload = dict(value)
    payload.pop("receipt_sha256", None)
    return hash_json(payload)


def _file(value, label):
    path = Path(value).resolve() if isinstance(value, str) else Path("/")
    if not str(path).startswith("/nfs_share/lijunhui/") or not path.is_file():
        raise AuthorizationBindingError(f"{label} invalid")
    return path


def _path(value, label):
    path = Path(value).resolve() if isinstance(value, str) else Path("/")
    if not str(path).startswith("/nfs_share/lijunhui/"):
        raise AuthorizationBindingError(f"{label} invalid")
    return path


def _time(value):
    try:
        result = datetime.fromisoformat(value)
    except Exception as exc:
        raise AuthorizationBindingError("time invalid") from exc
    if result.tzinfo is None:
        raise AuthorizationBindingError("time timezone missing")
    return result.astimezone(timezone.utc)


def validate(
    value,
    *,
    requested_scope,
    now=None,
    expected_output_namespace=None,
    expected_family=None,
    expected_seed=None,
    expected_reviewed_content_commit=None,
):
    if requested_scope != SCOPE:
        raise AuthorizationBindingError("scope mismatch")
    result = canonical_jsonable(value)
    fixed = {
        "schema_version": AUTH_SCHEMA,
        "implementation_version": IMPLEMENTATION_VERSION,
        "approved": True,
        "approved_scopes": [SCOPE],
        "authorization_id": AUTH_ID,
        "authorized_run_id": AUTH_ID + "-run",
        "family": "F3",
        "scene_seed": SEED,
        "max_invocations": 1,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage1_authorized": False,
    }
    for key, expected in fixed.items():
        if result.get(key) != expected:
            raise AuthorizationBindingError(f"field changed {key}")
    if expected_family not in (None, "F3") or expected_seed not in (None, SEED):
        raise AuthorizationBindingError("family/seed mismatch")
    if result.get("receipt_sha256") != receipt_sha(result):
        raise AuthorizationBindingError("receipt hash")
    issued, expires = _time(result.get("issued_at")), _time(result.get("expires_at"))
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not 0 < (expires - issued).total_seconds() <= 3600 or not issued <= current < expires:
        raise AuthorizationExpiredError("inactive")
    validate_current_gpu_authorization(result)
    frozen_budget = budget()
    for key, expected in (
        ("budget_receipt_sha256", frozen_budget["budget_receipt_sha256"]),
        ("planner_query_limit", frozen_budget["planner_query_limit"]),
        ("controlled_action_limit", frozen_budget["execution_limit"]),
        ("physics_step_limit", -1),
        ("timeout_seconds", frozen_budget["timeout_seconds"]),
    ):
        if result.get(key) != expected:
            raise AuthorizationBindingError(f"budget {key}")
    for field, path, expected in (
        ("budget_publication_path", BUDGET, budget()),
        ("scope_publication_path", PUBLICATION, publication()),
        ("parent_user_authorization_path", PARENT, parent()),
    ):
        actual = _file(result.get(field), field)
        sha_field = field.replace("_path", "_file_sha256")
        if actual != path.resolve() or _fsha(actual) != result.get(sha_field):
            raise AuthorizationBindingError(f"publication {field}")
        if json.loads(actual.read_text(encoding="utf-8")) != expected:
            raise AuthorizationBindingError(f"publication content {field}")
    if result.get("planned_root_slot_spec") != spec():
        raise AuthorizationBindingError("spec")
    if result.get("planned_root_slot_spec_sha256") != spec()["planned_scope_spec_sha256"]:
        raise AuthorizationBindingError("spec hash")
    evidence = _file(result.get("source_evidence_path"), "evidence")
    if (
        evidence != EVIDENCE.resolve()
        or _fsha(evidence) != result.get("source_evidence_file_sha256")
        or json.loads(evidence.read_text(encoding="utf-8")).get("result_payload_sha256")
        != "a92469b5a379a3821f76fc17ca54310005f9201a96c03b6030205415025244ae"
    ):
        raise AuthorizationBindingError("evidence")
    source_path = _file(result.get("source_lock_receipt_path"), "source")
    source = load_runtime_source_lock(source_path, expected_family="F3")
    if (
        source_path != SOURCE.resolve()
        or source["source_lock_receipt_sha256"] != result.get("source_lock_receipt_sha256")
        or source["snapshot"]["implementation_source_sha256"]
        != result.get("implementation_source_sha256")
    ):
        raise AuthorizationBindingError("source")
    request_path = _file(result.get("approval_request_path"), "request")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    payload = dict(request)
    digest = payload.pop("scope_request_sha256", None)
    if (
        request_path != REQUEST.resolve()
        or _fsha(request_path) != result.get("approval_request_file_sha256")
        or hash_json(payload) != digest
        or digest != result.get("approval_request_sha256")
        or request.get("authorized_command_sha256") != result.get("authorized_command_sha256")
        or request.get("output_namespace") != result.get("output_namespace")
    ):
        raise AuthorizationBindingError("request")
    expected_paths = {
        "consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        "gpu_lease_directory": CANONICAL_GPU_LEASE_DIRECTORY,
        "job_cache_root_directory": CANONICAL_JOB_CACHE_DIRECTORY,
        "output_namespace": str(OUTPUT.resolve()),
        "guard_receipt_path": str(GUARD.resolve()),
    }
    for key, expected in expected_paths.items():
        if str(_path(result.get(key), key)) != expected:
            raise AuthorizationBindingError(f"path {key}")
    if expected_output_namespace is not None and Path(expected_output_namespace).resolve() != OUTPUT.resolve():
        raise AuthorizationBindingError("output")
    commit = result.get("reviewed_content_commit")
    if not isinstance(commit, str) or not HEX40.fullmatch(commit):
        raise AuthorizationBindingError("commit")
    if expected_reviewed_content_commit is not None and commit != expected_reviewed_content_commit:
        raise AuthorizationBindingError("commit changed")
    if not isinstance(result.get("authorized_command_sha256"), str) or not HEX64.fullmatch(
        result["authorized_command_sha256"]
    ):
        raise AuthorizationBindingError("command")
    return result


def load(path, *, requested_scope, **kwargs):
    actual = Path(path).resolve()
    if actual != AUTH.resolve():
        raise AuthorizationBindingError("authorization path")
    return validate(
        json.loads(actual.read_text(encoding="utf-8")),
        requested_scope=requested_scope,
        **kwargs,
    )


def consumption_sha(value):
    payload = dict(value)
    payload.pop("consumption_receipt_sha256", None)
    payload.pop("path", None)
    return hash_json(payload)


def consume(authorization, *, ledger_directory):
    ledger = Path(ledger_directory).resolve()
    if str(ledger) != CANONICAL_CONSUMPTION_LEDGER_DIRECTORY:
        raise AuthorizationBindingError("ledger")
    ledger.mkdir(parents=True, exist_ok=True)
    path = ledger / f"{AUTH_ID}.json"
    value = {
        "schema_version": CONSUMPTION_SCHEMA,
        "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": AUTH_ID,
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "approved_scope": SCOPE,
        "family": "F3",
        "scene_seed": SEED,
        "consumed_at": datetime.now(timezone.utc).isoformat(),
        "max_invocations": 1,
    }
    value["consumption_receipt_sha256"] = consumption_sha(value)
    try:
        canonical_write_json(path, value, exclusive=True, mode=0o600)
    except FileExistsError as exc:
        raise AuthorizationReplayError("consumed") from exc
    return {**value, "path": str(path)}


def validate_consumption(value, authorization):
    result = dict(value)
    expected = {
        "schema_version": CONSUMPTION_SCHEMA,
        "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": AUTH_ID,
        "authorization_receipt_sha256": authorization.get("receipt_sha256"),
        "approved_scope": SCOPE,
        "family": "F3",
        "scene_seed": SEED,
        "max_invocations": 1,
    }
    if any(result.get(key) != item for key, item in expected.items()):
        raise AuthorizationBindingError("consumption")
    if result.get("consumption_receipt_sha256") != consumption_sha(result):
        raise AuthorizationBindingError("consumption hash")
    return result


def load_consumption(path, authorization):
    result = validate_consumption(
        json.loads(Path(path).read_text(encoding="utf-8")), authorization
    )
    result["path"] = str(Path(path).resolve())
    return result


def summary(value):
    return {
        key: value.get(key)
        for key in (
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
    }


__all__ = [
    "AUTH_SCHEMA",
    "consume",
    "load",
    "load_consumption",
    "receipt_sha",
    "summary",
    "validate",
    "validate_consumption",
]
