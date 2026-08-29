"""One-shot, fully bound runtime-v3_1 GPU authorization validation.

This module validates user-provided approvals and atomically consumes them.  It
never manufactures an ``approved=true`` receipt.  Importing it is CPU-only and
has no SAPIEN/CUDA/GPU side effects.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from ..current_hasher import hash_json
from ..runtime_v3_1_budget_v1_1 import (
    SUPPORTED_SCOPES,
    budget_receipt_sha256,
    scope_budget,
    validate_scope_budget,
)


AUTHORIZATION_SCHEMA_VERSION = "cmf_runtime_v3_1_gpu_authorization_v1_1"
CONSUMPTION_SCHEMA_VERSION = "cmf_runtime_v3_1_authorization_consumption_v1_1"
DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_1"
IMPLEMENTATION_REVISION = "runtime_v3_1_cpu_hardening_v5"
ALLOWED_UUID_POLICY = "fresh_idle_exact_uuid_selected_by_atomic_guard"
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


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def implementation_source_sha256_v5() -> str:
    source_root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(source_root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def current_source_bindings() -> dict:
    root = Path(__file__).resolve().parents[1]
    paths = {
        "a0_orchestrator_sha256": root / "a0_orchestrator_v1_2.py",
        "a0_activity_monitor_sha256": root / "a0_activity_monitor_v2.py",
        "real_adapter_sha256": root / "real_sapien_adapter_v1_2.py",
        "gpu_guard_sha256": root / "probes" / "gpu_guard_v2_1.py",
    }
    result = {key: _sha256_file(path) for key, path in paths.items()}
    result["implementation_source_sha256"] = implementation_source_sha256_v5()
    result["budget_receipt_sha256"] = budget_receipt_sha256()
    return result


def authorization_receipt_sha256(payload_without_hash: Mapping[str, Any]) -> str:
    value = dict(payload_without_hash)
    value.pop("receipt_sha256", None)
    return _canonical_sha256(value)


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


def _expected_common_limits(scope: str) -> tuple[int, int, int]:
    budget = scope_budget(scope)
    if scope == "A0_current_anchor_smoke":
        return budget["planner_query_limit"], budget["controlled_action_limit"], budget["timeout_seconds"]
    if scope in ("F1_three_branch_nonformal_probe", "real_sapien_root_integration_nonformal_probe"):
        return 3 * budget["planner_query_limit_per_branch"], 3, 3 * budget["timeout_seconds_per_branch"]
    if scope == "F2_beside_nonformal_probe":
        return budget["planner_query_limit_total"], budget["execution_limit"], budget["timeout_seconds"]
    if scope == "F3_release_diagnosis_nonformal_probe":
        return 2 * budget["planner_query_limit_per_run"], 2, 2 * budget["timeout_seconds_per_run"]
    if scope == "F4_common_carry_nonformal_probe":
        return 2 * budget["planner_query_limit_per_route"], 2, 2 * budget["timeout_seconds_per_route"]
    raise AuthorizationScopeError(f"unsupported scope {scope}")


def validate_authorization_v1_1(
    value: Mapping[str, Any],
    *,
    requested_scope: str,
    now: datetime | None = None,
    expected_family: str | None = None,
    expected_seed: int | None = None,
    expected_output_namespace: str | None = None,
    expected_content_commit: str | None = None,
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
    scopes = receipt.get("approved_scopes")
    if scopes != [requested_scope]:
        raise AuthorizationScopeError("authorization must approve exactly the requested scope")
    issued = _parse_time(receipt.get("issued_at"), "issued_at")
    expires = _parse_time(receipt.get("expires_at"), "expires_at")
    now_value = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if expires <= issued or now_value < issued or now_value >= expires:
        raise AuthorizationExpiredError("authorization is not within its one-shot validity interval")
    if not isinstance(receipt.get("content_commit"), str) or HEX40.fullmatch(receipt["content_commit"]) is None:
        raise AuthorizationBindingError("authorization content_commit must be a full Git SHA")
    if expected_content_commit is not None and receipt["content_commit"] != expected_content_commit:
        raise AuthorizationBindingError("authorization content commit mismatch")
    bindings = current_source_bindings()
    for key, expected in bindings.items():
        if receipt.get(key) != expected:
            raise AuthorizationBindingError(f"authorization source/budget binding mismatch: {key}")
    planned = receipt.get("planned_root_slot_spec")
    if not isinstance(planned, Mapping):
        raise AuthorizationBindingError("authorization lacks planned_root_slot_spec")
    if receipt.get("planned_root_slot_spec_sha256") != hash_json(planned):
        raise AuthorizationBindingError("authorization planned spec hash mismatch")
    family = receipt.get("family")
    seed = receipt.get("scene_seed")
    if planned.get("family") != family or planned.get("seed") != seed:
        raise AuthorizationBindingError("authorization family/seed differ from planned spec")
    canonical_budget = scope_budget(requested_scope)
    if canonical_budget["family"] != family:
        raise AuthorizationBindingError("authorization family does not match scope budget")
    validate_scope_budget(requested_scope, receipt.get("scope_budget"))
    if receipt.get("scope_budget_sha256") != canonical_budget["scope_budget_sha256"]:
        raise AuthorizationBindingError("authorization scope budget hash mismatch")
    expected_planner, expected_controlled, expected_timeout = _expected_common_limits(requested_scope)
    if (
        receipt.get("planner_query_limit") != expected_planner
        or receipt.get("controlled_action_limit") != expected_controlled
        or receipt.get("timeout_seconds") != expected_timeout
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
    if (
        output_path is None
        or not output_path.is_absolute()
        or ".." in output_path.parts
        or not str(output_path).startswith("/nfs_share/lijunhui/")
    ):
        raise AuthorizationBindingError("authorization output namespace must be an absolute workspace path")
    if expected_output_namespace is not None and output != expected_output_namespace:
        raise AuthorizationBindingError("authorization output namespace mismatch")
    if expected_family is not None and family != expected_family:
        raise AuthorizationBindingError("authorization family mismatch")
    if expected_seed is not None and seed != expected_seed:
        raise AuthorizationBindingError("authorization seed mismatch")
    if not isinstance(receipt.get("authorized_command_sha256"), str) or HEX64.fullmatch(
        receipt["authorized_command_sha256"]
    ) is None:
        raise AuthorizationBindingError("authorization command contract hash is missing")
    expected_hash = receipt.get("receipt_sha256")
    if not isinstance(expected_hash, str) or HEX64.fullmatch(expected_hash) is None:
        raise AuthorizationBindingError("authorization receipt SHA-256 is missing")
    if authorization_receipt_sha256(receipt) != expected_hash:
        raise AuthorizationBindingError("authorization receipt SHA-256 mismatch")
    return receipt


def load_authorization_v1_1(path: Path, **kwargs) -> dict:
    path = Path(path)
    if not path.is_file():
        raise AuthorizationBindingError("runtime-v3_1 requires an explicit v1_1 authorization receipt")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationBindingError("authorization receipt is unreadable") from exc
    return validate_authorization_v1_1(value, **kwargs)


def authorization_summary(value: Mapping[str, Any]) -> dict:
    return {
        "authorization_id": value["authorization_id"],
        "authorized_run_id": value["authorized_run_id"],
        "authorization_receipt_sha256": value["receipt_sha256"],
        "approved_scope": value["approved_scopes"][0],
        "family": value["family"],
        "scene_seed": value["scene_seed"],
        "planned_root_slot_spec_sha256": value["planned_root_slot_spec_sha256"],
        "implementation_source_sha256": value["implementation_source_sha256"],
        "budget_receipt_sha256": value["budget_receipt_sha256"],
        "timeout_seconds": value["timeout_seconds"],
        "output_namespace": value["output_namespace"],
        "stage0_authorized": False,
        "formal_data": False,
        "stage0_data": False,
    }


def consume_authorization_once(
    value: Mapping[str, Any],
    *,
    ledger_directory: Path,
    now: datetime | None = None,
) -> dict:
    """Atomically consume an already validated authorization exactly once."""

    authorization_id = value.get("authorization_id")
    if not isinstance(authorization_id, str) or SAFE_ID.fullmatch(authorization_id) is None:
        raise AuthorizationBindingError("cannot consume unsafe authorization_id")
    ledger_directory = Path(ledger_directory)
    try:
        ledger_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as exc:
        raise AuthorizationBindingError("cannot create authorization consumption ledger") from exc
    path = ledger_directory / f"{authorization_id}.json"
    consumed_at = (now or datetime.now(timezone.utc)).astimezone().isoformat()
    payload = {
        "schema_version": CONSUMPTION_SCHEMA_VERSION,
        "authorization_id": authorization_id,
        "authorization_receipt_sha256": value["receipt_sha256"],
        "authorized_run_id": value["authorized_run_id"],
        "output_namespace": value["output_namespace"],
        "consumed_at": consumed_at,
        "max_invocations": 1,
    }
    payload["consumption_receipt_sha256"] = _canonical_sha256(payload)
    data = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(path, flags, 0o600)
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
    except BaseException:
        os.close(fd)
        raise
    else:
        os.close(fd)
    payload["path"] = str(path)
    return payload


def validate_consumption_receipt(value: Mapping[str, Any], authorization: Mapping[str, Any]) -> dict:
    if not isinstance(value, Mapping) or value.get("schema_version") != CONSUMPTION_SCHEMA_VERSION:
        raise AuthorizationBindingError("invalid authorization consumption receipt schema")
    receipt = dict(value)
    expected_hash = receipt.pop("consumption_receipt_sha256", None)
    receipt.pop("path", None)
    if not isinstance(expected_hash, str) or _canonical_sha256(receipt) != expected_hash:
        raise AuthorizationBindingError("authorization consumption receipt hash mismatch")
    required = {
        "authorization_id": authorization["authorization_id"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "authorized_run_id": authorization["authorized_run_id"],
        "output_namespace": authorization["output_namespace"],
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
