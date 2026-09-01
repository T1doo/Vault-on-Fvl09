"""Canonical single-use authorization for the F2 V3 dynamic/root child."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path

from ..canonical_artifact import (
    canonical_hash_json as hash_json,
    canonical_jsonable,
    canonical_write_json,
)
from ..f2_dynamic_development_scope_v3 import (
    AUTH,
    AUTH_ID,
    BUDGET,
    GUARD,
    IMPLEMENTATION_VERSION,
    MATRIX,
    NAMESPACE,
    OUTPUT,
    PARENT,
    PUBLICATION,
    REQUEST,
    SCOPE,
    SCREENING,
    SOURCE,
    f2_dynamic_development_budget_v3,
    parent_authorization_v3,
    validate_f2_dynamic_development_authorization_v3,
)
from ..f2_dynamic_search_contract_v3 import validate_cpu_static_screening_v3
from ..f2_official_asset_compatibility_matrix_v3 import (
    validate_static_compatibility_matrix_v3,
)
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


AUTH_SCHEMA = "cmf_f2_dynamic_development_authorization_v3"
CONSUMPTION_SCHEMA = "cmf_f2_dynamic_development_consumption_v3"
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


def _workspace_path(value, label):
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


def _self_hash(value, field, label):
    payload = dict(value)
    digest = payload.pop(field, None)
    if not isinstance(digest, str) or hash_json(payload) != digest:
        raise AuthorizationBindingError(f"{label} hash")
    return digest


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
        "family": "F2",
        "scene_seed": 20260829,
        "max_invocations": 1,
        "single_use": True,
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
    if expected_family not in (None, "F2") or expected_seed not in (None, 20260829):
        raise AuthorizationBindingError("family/seed mismatch")
    if result.get("receipt_sha256") != receipt_sha(result):
        raise AuthorizationBindingError("receipt hash")
    issued, expires = _time(result.get("issued_at")), _time(result.get("expires_at"))
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not 0 < (expires - issued).total_seconds() <= 3600 or not issued <= current < expires:
        raise AuthorizationExpiredError("inactive")
    validate_current_gpu_authorization(result)

    budget = f2_dynamic_development_budget_v3()
    if result.get("budget") != budget or result.get("budget_sha256") != hash_json(budget):
        raise AuthorizationBindingError("embedded budget")
    budget_path = _file(result.get("budget_publication_path"), "budget")
    if (
        budget_path != BUDGET.resolve()
        or _fsha(budget_path) != result.get("budget_publication_file_sha256")
        or json.loads(budget_path.read_text(encoding="utf-8")) != budget
    ):
        raise AuthorizationBindingError("budget publication")

    parent_path = _file(result.get("parent_user_authorization_path"), "parent")
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    if (
        parent_path != PARENT.resolve()
        or _fsha(parent_path) != result.get("parent_user_authorization_file_sha256")
        or parent != parent_authorization_v3()
        or parent.get("parent_user_authorization_sha256")
        != result.get("parent_user_authorization_sha256")
    ):
        raise AuthorizationBindingError("parent publication")

    matrix_path = _file(result.get("matrix_publication_path"), "matrix")
    matrix = validate_static_compatibility_matrix_v3(
        json.loads(matrix_path.read_text(encoding="utf-8"))
    )
    if (
        matrix_path != MATRIX.resolve()
        or _fsha(matrix_path) != result.get("matrix_publication_file_sha256")
        or matrix["matrix_sha256"] != result.get("matrix_sha256")
    ):
        raise AuthorizationBindingError("matrix publication")
    screening_path = _file(result.get("screening_publication_path"), "screening")
    screening = validate_cpu_static_screening_v3(
        json.loads(screening_path.read_text(encoding="utf-8"))
    )
    if (
        screening_path != SCREENING.resolve()
        or _fsha(screening_path) != result.get("screening_publication_file_sha256")
        or screening["screening_sha256"] != result.get("screening_sha256")
        or screening["matrix_sha256"] != matrix["matrix_sha256"]
        or screening["dynamic_scope"]["candidate_count"] > 12
    ):
        raise AuthorizationBindingError("screening publication")

    scope_path = _file(result.get("scope_publication_path"), "scope")
    scope_publication = json.loads(scope_path.read_text(encoding="utf-8"))
    scope_digest = _self_hash(
        scope_publication, "scope_publication_sha256", "scope publication"
    )
    if (
        scope_path != PUBLICATION.resolve()
        or _fsha(scope_path) != result.get("scope_publication_file_sha256")
        or scope_digest != result.get("scope_publication_sha256")
        or scope_publication.get("scope") != SCOPE
        or scope_publication.get("matrix_sha256") != matrix["matrix_sha256"]
        or scope_publication.get("screening_sha256") != screening["screening_sha256"]
        or scope_publication.get("budget_receipt_sha256")
        != budget["budget_receipt_sha256"]
    ):
        raise AuthorizationBindingError("scope publication")
    spec = scope_publication.get("planned_scope_spec")
    if not isinstance(spec, dict):
        raise AuthorizationBindingError("planned scope spec")
    spec_digest = _self_hash(spec, "planned_scope_spec_sha256", "planned scope")
    if result.get("planned_scope_spec") != spec or result.get(
        "planned_scope_spec_sha256"
    ) != spec_digest:
        raise AuthorizationBindingError("planned scope binding")

    source_path = _file(result.get("source_lock_receipt_path"), "source")
    source = load_runtime_source_lock(source_path, expected_family="F2")
    if (
        source_path != SOURCE.resolve()
        or source["source_lock_receipt_sha256"]
        != result.get("source_lock_receipt_sha256")
        or source["snapshot"]["implementation_source_sha256"]
        != result.get("implementation_source_sha256")
    ):
        raise AuthorizationBindingError("source")

    request_path = _file(result.get("approval_request_path"), "request")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request_digest = _self_hash(request, "scope_request_sha256", "request")
    if (
        request_path != REQUEST.resolve()
        or _fsha(request_path) != result.get("approval_request_file_sha256")
        or request_digest != result.get("approval_request_sha256")
        or request.get("authorized_command_sha256")
        != result.get("authorized_command_sha256")
        or request.get("output_namespace") != result.get("output_namespace")
        or request.get("matrix_sha256") != matrix["matrix_sha256"]
        or request.get("screening_sha256") != screening["screening_sha256"]
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
        if str(_workspace_path(result.get(key), key)) != expected:
            raise AuthorizationBindingError(f"path {key}")
    if expected_output_namespace is not None and Path(
        expected_output_namespace
    ).resolve() != OUTPUT.resolve():
        raise AuthorizationBindingError("output")
    commit = result.get("reviewed_content_commit")
    if not isinstance(commit, str) or not HEX40.fullmatch(commit):
        raise AuthorizationBindingError("commit")
    if expected_reviewed_content_commit is not None and commit != expected_reviewed_content_commit:
        raise AuthorizationBindingError("commit changed")
    command_sha = result.get("authorized_command_sha256")
    if not isinstance(command_sha, str) or not HEX64.fullmatch(command_sha):
        raise AuthorizationBindingError("command")

    # Reuse the execution-layer budget/flags validator after canonical binding.
    validate_f2_dynamic_development_authorization_v3(
        result,
        matrix_sha256=matrix["matrix_sha256"],
        screening_sha256=screening["screening_sha256"],
    )
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
        "family": "F2",
        "scene_seed": 20260829,
        "matrix_sha256": authorization["matrix_sha256"],
        "screening_sha256": authorization["screening_sha256"],
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
        "family": "F2",
        "scene_seed": 20260829,
        "matrix_sha256": authorization.get("matrix_sha256"),
        "screening_sha256": authorization.get("screening_sha256"),
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
            "matrix_sha256",
            "screening_sha256",
            "planned_scope_spec_sha256",
            "implementation_source_sha256",
            "source_lock_receipt_sha256",
            "budget_sha256",
            "parent_user_authorization_sha256",
            "reviewed_content_commit",
            "output_namespace",
            "timeout_seconds",
            "allowed_physical_gpu_indices",
        )
    }


__all__ = [
    "consume",
    "load",
    "load_consumption",
    "receipt_sha",
    "summary",
    "validate",
    "validate_consumption",
]
