"""Request-bound one-shot authorization for complete pre-Stage-0 scopes."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from ..current_hasher import hash_json
from ..runtime_source_lock_v1 import load_runtime_source_lock
from ..runtime_v3_2_budget_v1 import (
    SUPPORTED_SCOPES,
    authorization_common_limits,
    budget_receipt_sha256,
    scope_budget,
    validate_scope_budget,
)


AUTHORIZATION_SCHEMA_VERSION = "cmf_runtime_v3_2_gpu_authorization_v1"
CONSUMPTION_SCHEMA_VERSION = "cmf_runtime_v3_2_authorization_consumption_v1"
DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_2"
IMPLEMENTATION_REVISION = "runtime_v3_2_common_hardening_v1"
ALLOWED_UUID_POLICY = "fresh_idle_exact_uuid_selected_by_atomic_guard"
MAX_AUTHORIZATION_VALIDITY_SECONDS = 3600
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")


class AuthorizationError(PermissionError):
    failure_status = "failed_authorization_binding"


class AuthorizationReplayError(AuthorizationError):
    failure_status = "failed_authorization_replay"


class AuthorizationExpiredError(AuthorizationError):
    failure_status = "failed_authorization_expired"


class AuthorizationScopeError(AuthorizationError):
    failure_status = "failed_authorization_scope"


class AuthorizationBindingError(AuthorizationError):
    failure_status = "failed_authorization_binding"


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def implementation_source_sha256_v3_2() -> str:
    source_root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(source_root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def current_source_bindings_v3_2() -> dict:
    root = Path(__file__).resolve().parents[1]
    paths = {
        "root_orchestrator_sha256": root / "root_orchestrator_v1_1.py",
        "real_adapter_sha256": root / "real_sapien_adapter_v1_2.py",
        "planner_dtype_sha256": root / "planner_dtype_v3_2.py",
        "gpu_guard_sha256": root / "probes/gpu_guard_v2_3.py",
        "authorization_validator_sha256": root / "probes/runtime_v3_2_authorization_v1.py",
        "complete_family_scope_sha256": root / "probes/runtime_v3_2_complete_family_scope.py",
        "budget_module_sha256": root / "runtime_v3_2_budget_v1.py",
        "runtime_source_lock_module_sha256": root / "runtime_source_lock_v1.py",
    }
    result = {key: sha256_file(path) for key, path in paths.items()}
    result["implementation_source_sha256"] = implementation_source_sha256_v3_2()
    result["budget_receipt_sha256"] = budget_receipt_sha256()
    return result


def authorization_receipt_sha256(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("receipt_sha256", None)
    return canonical_sha256(payload)


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise AuthorizationBindingError(f"authorization {field} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise AuthorizationBindingError(f"authorization {field} is invalid") from exc
    if parsed.tzinfo is None:
        raise AuthorizationBindingError(f"authorization {field} must include timezone")
    return parsed.astimezone(timezone.utc)


def _load_scope_request(receipt: Mapping[str, Any]) -> dict:
    path_value = receipt.get("approval_request_path")
    if not isinstance(path_value, str):
        raise AuthorizationBindingError("authorization lacks approval_request_path")
    path = Path(path_value)
    if not path.is_absolute() or not str(path).startswith("/nfs_share/lijunhui/") or not path.is_file():
        raise AuthorizationBindingError("authorization approval request path is invalid")
    if sha256_file(path) != receipt.get("approval_request_file_sha256"):
        raise AuthorizationBindingError("authorization approval request file SHA mismatch")
    try:
        request = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationBindingError("authorization approval request is unreadable") from exc
    request_hash = request.get("scope_request_sha256")
    request_without_hash = dict(request)
    request_without_hash.pop("scope_request_sha256", None)
    if not isinstance(request_hash, str) or canonical_sha256(request_without_hash) != request_hash:
        raise AuthorizationBindingError("scope request content hash mismatch")
    if request_hash != receipt.get("approval_request_sha256"):
        raise AuthorizationBindingError("authorization approval request hash mismatch")
    if request.get("schema_version") != receipt.get("approval_request_schema_version"):
        raise AuthorizationBindingError("authorization approval request schema mismatch")
    return request


def validate_authorization_v3_2(
    value: Mapping[str, Any],
    *,
    requested_scope: str,
    now: datetime | None = None,
    expected_family: str | None = None,
    expected_seed: int | None = None,
    expected_output_namespace: str | None = None,
    expected_reviewed_content_commit: str | None = None,
) -> dict:
    if requested_scope not in SUPPORTED_SCOPES:
        raise AuthorizationScopeError(f"unsupported requested scope {requested_scope}")
    if not isinstance(value, Mapping):
        raise AuthorizationBindingError("authorization receipt must be a mapping")
    receipt = json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))
    fixed = {
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_revision": IMPLEMENTATION_REVISION,
        "approved": True,
        "stage0_authorized": False,
        "formal_data": False,
        "stage0_data": False,
        "max_invocations": 1,
    }
    for key, expected in fixed.items():
        if receipt.get(key) != expected:
            raise AuthorizationBindingError(f"authorization rejected field {key}")
    for key in ("authorization_id", "authorized_run_id"):
        if not isinstance(receipt.get(key), str) or SAFE_ID.fullmatch(receipt[key]) is None:
            raise AuthorizationBindingError(f"authorization {key} is unsafe")
    if receipt.get("approved_scopes") != [requested_scope]:
        raise AuthorizationScopeError("authorization must approve exactly the requested scope")

    issued = _parse_time(receipt.get("issued_at"), "issued_at")
    expires = _parse_time(receipt.get("expires_at"), "expires_at")
    validity = (expires - issued).total_seconds()
    if not 0 < validity <= MAX_AUTHORIZATION_VALIDITY_SECONDS:
        raise AuthorizationExpiredError("authorization validity must be at most one hour")
    now_value = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if now_value < issued or now_value >= expires:
        raise AuthorizationExpiredError("authorization is outside its one-shot validity interval")

    reviewed_commit = receipt.get("reviewed_content_commit")
    if not isinstance(reviewed_commit, str) or HEX40.fullmatch(reviewed_commit) is None:
        raise AuthorizationBindingError("reviewed_content_commit must be a full Git SHA")
    if expected_reviewed_content_commit is not None and reviewed_commit != expected_reviewed_content_commit:
        raise AuthorizationBindingError("reviewed content commit mismatch")
    for key in (
        "parent_user_authorization_sha256",
        "approval_request_sha256",
        "approval_request_file_sha256",
        "source_lock_receipt_sha256",
    ):
        if not isinstance(receipt.get(key), str) or HEX64.fullmatch(receipt[key]) is None:
            raise AuthorizationBindingError(f"authorization {key} is missing")

    request = _load_scope_request(receipt)
    if request.get("parent_user_authorization_sha256") != receipt["parent_user_authorization_sha256"]:
        raise AuthorizationBindingError("scope request parent authorization mismatch")
    if request.get("reviewed_content_commit") != reviewed_commit:
        raise AuthorizationBindingError("scope request reviewed commit mismatch")
    if request.get("scope") != requested_scope:
        raise AuthorizationScopeError("scope request and authorization scope differ")

    bindings = current_source_bindings_v3_2()
    for key, expected in bindings.items():
        if receipt.get(key) != expected:
            raise AuthorizationBindingError(f"authorization source/budget binding mismatch: {key}")
    source_lock_path = receipt.get("source_lock_receipt_path")
    if not isinstance(source_lock_path, str):
        raise AuthorizationBindingError("authorization lacks source lock path")
    family = receipt.get("family")
    source_lock = load_runtime_source_lock(Path(source_lock_path), expected_family=family)
    if source_lock.get("source_lock_receipt_sha256") != receipt["source_lock_receipt_sha256"]:
        raise AuthorizationBindingError("authorization source lock hash mismatch")
    if source_lock["snapshot"].get("implementation_source_sha256") != receipt["implementation_source_sha256"]:
        raise AuthorizationBindingError("source lock implementation hash mismatch")

    planned = receipt.get("planned_root_slot_spec")
    if not isinstance(planned, Mapping) or receipt.get("planned_root_slot_spec_sha256") != hash_json(planned):
        raise AuthorizationBindingError("authorization planned spec/hash is invalid")
    seed = receipt.get("scene_seed")
    if planned.get("family") != family or planned.get("seed") != seed:
        raise AuthorizationBindingError("authorization family/seed differ from planned spec")
    canonical_budget = scope_budget(requested_scope)
    if canonical_budget["family"] != family:
        raise AuthorizationBindingError("authorization family does not match scope budget")
    validate_scope_budget(requested_scope, receipt.get("scope_budget"))
    if receipt.get("scope_budget_sha256") != canonical_budget["scope_budget_sha256"]:
        raise AuthorizationBindingError("authorization scope budget hash mismatch")
    planner, controlled, physics, timeout = authorization_common_limits(requested_scope)
    if (
        receipt.get("planner_query_limit") != planner
        or receipt.get("controlled_action_limit") != controlled
        or receipt.get("physics_step_limit") != physics
        or receipt.get("timeout_seconds") != timeout
    ):
        raise AuthorizationBindingError("authorization common limits differ from scope budget")
    if requested_scope == "A0_current_anchor_smoke" and receipt.get("scene_pattern") != canonical_budget["scene_pattern"]:
        raise AuthorizationBindingError("authorization A0 scene pattern mismatch")

    indices = receipt.get("allowed_physical_gpu_indices")
    if (
        not isinstance(indices, list)
        or not indices
        or len(set(indices)) != len(indices)
        or any(not isinstance(index, int) or index not in range(8) for index in indices)
    ):
        raise AuthorizationBindingError("authorization GPU index policy is invalid")
    if receipt.get("allowed_gpu_uuid_policy") != ALLOWED_UUID_POLICY:
        raise AuthorizationBindingError("authorization GPU UUID policy mismatch")
    output = receipt.get("output_namespace")
    output_path = Path(output) if isinstance(output, str) else None
    if output_path is None or not output_path.is_absolute() or not str(output_path).startswith("/nfs_share/lijunhui/"):
        raise AuthorizationBindingError("authorization output namespace is invalid")
    if expected_output_namespace is not None and output != expected_output_namespace:
        raise AuthorizationBindingError("authorization output namespace mismatch")
    if expected_family is not None and family != expected_family:
        raise AuthorizationBindingError("authorization family mismatch")
    if expected_seed is not None and seed != expected_seed:
        raise AuthorizationBindingError("authorization seed mismatch")
    if not isinstance(receipt.get("authorized_command_sha256"), str) or HEX64.fullmatch(receipt["authorized_command_sha256"]) is None:
        raise AuthorizationBindingError("authorization command hash is missing")
    expected_hash = receipt.get("receipt_sha256")
    if not isinstance(expected_hash, str) or HEX64.fullmatch(expected_hash) is None:
        raise AuthorizationBindingError("authorization receipt hash is missing")
    if authorization_receipt_sha256(receipt) != expected_hash:
        raise AuthorizationBindingError("authorization receipt hash mismatch")
    return receipt


def load_authorization_v3_2(path: Path, **kwargs) -> dict:
    path = Path(path)
    if not path.is_file():
        raise AuthorizationBindingError("runtime-v3_2 requires an explicit v1 authorization receipt")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationBindingError("authorization receipt is unreadable") from exc
    return validate_authorization_v3_2(value, **kwargs)


def authorization_summary(value: Mapping[str, Any]) -> dict:
    return {
        "authorization_id": value["authorization_id"],
        "authorized_run_id": value["authorized_run_id"],
        "authorization_receipt_sha256": value["receipt_sha256"],
        "approved_scope": value["approved_scopes"][0],
        "family": value["family"],
        "scene_seed": value["scene_seed"],
        "planned_root_slot_spec_sha256": value["planned_root_slot_spec_sha256"],
        "parent_user_authorization_sha256": value["parent_user_authorization_sha256"],
        "approval_request_sha256": value["approval_request_sha256"],
        "source_lock_receipt_sha256": value["source_lock_receipt_sha256"],
        "implementation_source_sha256": value["implementation_source_sha256"],
        "budget_receipt_sha256": value["budget_receipt_sha256"],
        "timeout_seconds": value["timeout_seconds"],
        "output_namespace": value["output_namespace"],
        "stage0_authorized": False,
        "formal_data": False,
        "stage0_data": False,
    }


def consume_authorization_once(
    value: Mapping[str, Any], *, ledger_directory: Path, now: datetime | None = None
) -> dict:
    authorization_id = value.get("authorization_id")
    if not isinstance(authorization_id, str) or SAFE_ID.fullmatch(authorization_id) is None:
        raise AuthorizationBindingError("cannot consume unsafe authorization_id")
    ledger_directory = Path(ledger_directory)
    ledger_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = ledger_directory / f"{authorization_id}.json"
    payload = {
        "schema_version": CONSUMPTION_SCHEMA_VERSION,
        "authorization_id": authorization_id,
        "authorization_receipt_sha256": value["receipt_sha256"],
        "authorized_run_id": value["authorized_run_id"],
        "output_namespace": value["output_namespace"],
        "source_lock_receipt_sha256": value["source_lock_receipt_sha256"],
        "consumed_at": (now or datetime.now(timezone.utc)).astimezone().isoformat(),
        "max_invocations": 1,
    }
    payload["consumption_receipt_sha256"] = canonical_sha256(payload)
    data = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise AuthorizationReplayError("authorization has already been consumed") from exc
    except OSError as exc:
        raise AuthorizationBindingError("cannot atomically create consumption receipt") from exc
    try:
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise OSError("short write while sealing consumption receipt")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    payload["path"] = str(path)
    return payload


def validate_consumption_receipt(value: Mapping[str, Any], authorization: Mapping[str, Any]) -> dict:
    if not isinstance(value, Mapping) or value.get("schema_version") != CONSUMPTION_SCHEMA_VERSION:
        raise AuthorizationBindingError("invalid authorization consumption receipt schema")
    receipt = dict(value)
    expected_hash = receipt.pop("consumption_receipt_sha256", None)
    receipt.pop("path", None)
    if not isinstance(expected_hash, str) or canonical_sha256(receipt) != expected_hash:
        raise AuthorizationBindingError("authorization consumption receipt hash mismatch")
    required = {
        "authorization_id": authorization["authorization_id"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "authorized_run_id": authorization["authorized_run_id"],
        "output_namespace": authorization["output_namespace"],
        "source_lock_receipt_sha256": authorization["source_lock_receipt_sha256"],
        "max_invocations": 1,
    }
    for key, expected in required.items():
        if receipt.get(key) != expected:
            raise AuthorizationBindingError(f"authorization consumption binding mismatch: {key}")
    return dict(value)


def load_consumption_receipt(path: Path, authorization: Mapping[str, Any]) -> dict:
    path = Path(path)
    if not path.is_file():
        raise AuthorizationBindingError("authorization consumption receipt is missing")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationBindingError("authorization consumption receipt is unreadable") from exc
    value["path"] = str(path)
    return validate_consumption_receipt(value, authorization)
