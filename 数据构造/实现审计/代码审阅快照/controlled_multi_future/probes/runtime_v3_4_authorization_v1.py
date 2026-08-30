"""Request/source/budget-bound one-shot authorization for runtime-v3_4."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from ..runtime_source_lock_v1 import load_runtime_source_lock
from ..runtime_v3_4_budget_v1 import (
    SUPPORTED_SCOPES,
    budget_receipt_sha256,
    scope_budget,
)
from .runtime_v3_3_authorization_v1 import (
    AuthorizationBindingError,
    AuthorizationExpiredError,
    AuthorizationReplayError,
    AuthorizationScopeError,
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)


AUTHORIZATION_SCHEMA_VERSION = "cmf_runtime_v3_4_gpu_authorization_v1"
CONSUMPTION_SCHEMA_VERSION = "cmf_runtime_v3_4_authorization_consumption_v1"
DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_4"
IMPLEMENTATION_REVISION = "diagnosis_first_multi_gpu_convergence_v1"
MAX_VALIDITY_SECONDS = 3600
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
WORKSPACE_ROOT = Path("/nfs_share/lijunhui")


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


def implementation_source_sha256_v3_4() -> str:
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def current_source_bindings_v3_4() -> dict[str, str]:
    root = Path(__file__).resolve().parents[1]
    paths = {
        "real_adapter_sha256": root / "real_sapien_adapter_v1_4.py",
        "family_runners_sha256": root / "family_runners_v3_3.py",
        "f2_release_gates_sha256": root / "f2_release_gates_v10.py",
        "f3_grasp_contract_sha256": root / "f3_grasp_robustness_v10.py",
        "f3_three_context_gate_sha256": root / "f3_grasp_three_context_gate_v10.py",
        "f4_corridor_contract_sha256": root / "f4_carry_corridor_v10.py",
        "f4_corridor_selection_sha256": root / "f4_corridor_selection_gate_v10.py",
        "f4_corridor_A_gate_sha256": root / "f4_corridor_a_gate_v10.py",
        "f4_BC_AB_gate_sha256": root / "f4_bc_ab_gate_v10.py",
        "single_program_gate_sha256": root / "single_program_strict_prefix_gate_v1.py",
        "budget_sha256": root / "runtime_v3_4_budget_v1.py",
        "scope_specs_sha256": root / "runtime_v3_4_scope_specs_v1.py",
        "scope_bundle_builder_sha256": root / "runtime_v3_4_scope_bundle_v1.py",
        "scheduler_sha256": root / "runtime_v3_4_multi_gpu_scheduler_v1.py",
        "scope_runner_sha256": root / "probes/runtime_v3_4_scope_runner.py",
        "runtime_trace_sha256": root / "probes/runtime_trace.py",
        "raw_writer_sha256": root / "raw_writer.py",
        "root_orchestrator_sha256": root / "root_orchestrator_v1_2.py",
        "gpu_guard_sha256": root / "probes/gpu_guard_v2_4.py",
        "authorization_validator_sha256": root
        / "probes/runtime_v3_4_authorization_v1.py",
    }
    result = {name: sha256_file(path) for name, path in paths.items()}
    result["implementation_source_sha256"] = implementation_source_sha256_v3_4()
    result["budget_receipt_sha256"] = budget_receipt_sha256()
    return result


def authorization_receipt_sha256(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("receipt_sha256", None)
    return canonical_sha256(payload)


def _workspace_file(path_value: Any, label: str) -> Path:
    if not isinstance(path_value, str):
        raise AuthorizationBindingError(f"{label} path is missing")
    path = Path(path_value).resolve()
    if not str(path).startswith(str(WORKSPACE_ROOT) + "/") or not path.is_file():
        raise AuthorizationBindingError(f"{label} path is invalid")
    return path


def _workspace_directory(path_value: Any, label: str) -> Path:
    if not isinstance(path_value, str):
        raise AuthorizationBindingError(f"{label} directory is missing")
    path = Path(path_value).resolve()
    if not str(path).startswith(str(WORKSPACE_ROOT) + "/"):
        raise AuthorizationBindingError(f"{label} directory is outside workspace")
    return path


def _parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise AuthorizationBindingError(f"{label} must be ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise AuthorizationBindingError(f"{label} is invalid") from exc
    if parsed.tzinfo is None:
        raise AuthorizationBindingError(f"{label} lacks timezone")
    return parsed.astimezone(timezone.utc)


def _load_hashed_json(path_value: Any, file_sha: Any, content_sha_field: str) -> dict:
    path = _workspace_file(path_value, content_sha_field)
    if sha256_file(path) != file_sha:
        raise AuthorizationBindingError(f"{content_sha_field} file SHA mismatch")
    value = json.loads(path.read_text(encoding="utf-8"))
    expected = value.get(content_sha_field)
    payload = dict(value)
    payload.pop(content_sha_field, None)
    if not isinstance(expected, str) or canonical_sha256(payload) != expected:
        raise AuthorizationBindingError(f"{content_sha_field} content hash mismatch")
    return value


def validate_authorization_v3_4(
    value: Mapping[str, Any],
    *,
    requested_scope: str,
    now: datetime | None = None,
    expected_family: str | None = None,
    expected_seed: int | None = None,
    expected_output_namespace: str | None = None,
    expected_reviewed_content_commit: str | None = None,
) -> dict[str, Any]:
    if requested_scope not in SUPPORTED_SCOPES:
        raise AuthorizationScopeError("unsupported runtime-v3_4 scope")
    if not isinstance(value, Mapping):
        raise AuthorizationBindingError("authorization must be mapping")
    receipt = json.loads(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    )
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
        "automatic_retry": False,
        "recovery_attempts": 0,
    }
    for key, expected in fixed.items():
        if receipt.get(key) != expected:
            raise AuthorizationBindingError(f"authorization rejected field {key}")
    if receipt.get("receipt_sha256") != authorization_receipt_sha256(receipt):
        raise AuthorizationBindingError("authorization receipt hash mismatch")
    if receipt.get("approved_scopes") != [requested_scope]:
        raise AuthorizationScopeError("authorization must bind exactly one scope")
    for key in ("authorization_id", "authorized_run_id"):
        if not isinstance(receipt.get(key), str) or SAFE_ID.fullmatch(receipt[key]) is None:
            raise AuthorizationBindingError(f"unsafe authorization {key}")
    issued = _parse_time(receipt.get("issued_at"), "issued_at")
    expires = _parse_time(receipt.get("expires_at"), "expires_at")
    if not 0 < (expires - issued).total_seconds() <= MAX_VALIDITY_SECONDS:
        raise AuthorizationExpiredError("authorization validity exceeds one hour")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if current < issued or current >= expires:
        raise AuthorizationExpiredError("authorization is expired or not active")
    budget = scope_budget(requested_scope)
    if receipt.get("scope_budget") != budget:
        raise AuthorizationBindingError("authorization scope budget mismatch")
    if receipt.get("budget_receipt_sha256") != budget_receipt_sha256():
        raise AuthorizationBindingError("authorization budget hash mismatch")
    if receipt.get("planner_query_limit") != budget["planner_query_limit"]:
        raise AuthorizationBindingError("planner limit mismatch")
    if receipt.get("controlled_action_limit") != budget["execution_limit"]:
        raise AuthorizationBindingError("execution limit mismatch")
    if receipt.get("physics_step_limit") != -1:
        raise AuthorizationBindingError("physics-step limit must be -1 for bounded action scope")
    if receipt.get("timeout_seconds") != budget["timeout_seconds"]:
        raise AuthorizationBindingError("timeout mismatch")
    if receipt.get("allowed_physical_gpu_indices") != list(range(8)):
        raise AuthorizationBindingError("runtime-v3_4 must authorize GPU0–7 eligibility")
    family = budget["family"]
    if receipt.get("family") != family or (
        expected_family is not None and family != expected_family
    ):
        raise AuthorizationBindingError("authorization family mismatch")
    spec = receipt.get("planned_root_slot_spec")
    if not isinstance(spec, Mapping) or canonical_sha256(spec) != receipt.get(
        "planned_root_slot_spec_sha256"
    ):
        raise AuthorizationBindingError("planned spec hash mismatch")
    if spec.get("scope") != requested_scope or spec.get("family") != family:
        raise AuthorizationBindingError("planned spec scope/family mismatch")
    if receipt.get("scene_seed") != spec.get("seed") or (
        expected_seed is not None and receipt.get("scene_seed") != expected_seed
    ):
        raise AuthorizationBindingError("scene seed mismatch")
    source_bindings = current_source_bindings_v3_4()
    if receipt.get("source_bindings") != source_bindings:
        raise AuthorizationBindingError("authorization source bindings changed")
    if receipt.get("implementation_source_sha256") != source_bindings[
        "implementation_source_sha256"
    ]:
        raise AuthorizationBindingError("implementation source hash mismatch")
    source_lock_path = _workspace_file(
        receipt.get("source_lock_receipt_path"), "source lock"
    )
    source_lock = load_runtime_source_lock(source_lock_path, expected_family=family)
    if source_lock.get("source_lock_receipt_sha256") != receipt.get(
        "source_lock_receipt_sha256"
    ):
        raise AuthorizationBindingError("source lock receipt hash mismatch")
    request = _load_hashed_json(
        receipt.get("approval_request_path"),
        receipt.get("approval_request_file_sha256"),
        "scope_request_sha256",
    )
    if request.get("scope_request_sha256") != receipt.get("approval_request_sha256"):
        raise AuthorizationBindingError("approval request content mismatch")
    parent_path = _workspace_file(
        receipt.get("parent_user_authorization_path"), "parent user authorization"
    )
    if sha256_file(parent_path) != receipt.get("parent_user_authorization_file_sha256"):
        raise AuthorizationBindingError("parent authorization file SHA mismatch")
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    if parent.get("parent_user_authorization_sha256") != receipt.get(
        "parent_user_authorization_sha256"
    ):
        raise AuthorizationBindingError("parent authorization content mismatch")
    if canonical_sha256(
        {k: v for k, v in parent.items() if k != "parent_user_authorization_sha256"}
    ) != parent.get("parent_user_authorization_sha256"):
        raise AuthorizationBindingError("parent authorization hash invalid")
    for field, canonical in (
        ("consumption_ledger_directory", CANONICAL_CONSUMPTION_LEDGER_DIRECTORY),
        ("gpu_lease_directory", CANONICAL_GPU_LEASE_DIRECTORY),
        ("job_cache_root_directory", CANONICAL_JOB_CACHE_DIRECTORY),
    ):
        if str(_workspace_directory(receipt.get(field), field)) != canonical:
            raise AuthorizationBindingError(f"authorization {field} is not canonical")
    for field in ("output_namespace", "guard_receipt_path"):
        resolved = _workspace_directory(receipt.get(field), field)
        if field == "output_namespace" and expected_output_namespace is not None:
            if str(resolved) != str(Path(expected_output_namespace).resolve()):
                raise AuthorizationBindingError("output namespace mismatch")
    commit = receipt.get("reviewed_content_commit")
    if not isinstance(commit, str) or HEX40.fullmatch(commit) is None:
        raise AuthorizationBindingError("reviewed content commit is invalid")
    if expected_reviewed_content_commit is not None and commit != expected_reviewed_content_commit:
        raise AuthorizationBindingError("reviewed content commit mismatch")
    if not isinstance(receipt.get("authorized_command_sha256"), str):
        raise AuthorizationBindingError("authorized command hash is missing")
    return receipt


def load_authorization_v3_4(
    path: Path, *, requested_scope: str, **kwargs
) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationBindingError("authorization receipt is unreadable") from exc
    return validate_authorization_v3_4(
        value, requested_scope=requested_scope, **kwargs
    )


def consumption_receipt_sha256(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("consumption_receipt_sha256", None)
    payload.pop("path", None)
    return canonical_sha256(payload)


def consume_authorization_once(
    authorization: Mapping[str, Any], *, ledger_directory: Path
) -> dict[str, Any]:
    ledger = Path(ledger_directory).resolve()
    if str(ledger) != CANONICAL_CONSUMPTION_LEDGER_DIRECTORY:
        raise AuthorizationBindingError("consumption ledger is not canonical")
    ledger.mkdir(parents=True, exist_ok=True)
    path = ledger / f"{authorization['authorization_id']}.json"
    value = {
        "schema_version": CONSUMPTION_SCHEMA_VERSION,
        "authorization_id": authorization["authorization_id"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "approved_scope": authorization["approved_scopes"][0],
        "family": authorization["family"],
        "scene_seed": authorization["scene_seed"],
        "consumed_at": datetime.now(timezone.utc).isoformat(),
        "max_invocations": 1,
    }
    value["consumption_receipt_sha256"] = consumption_receipt_sha256(value)
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise AuthorizationReplayError("authorization was already consumed") from exc
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return {**value, "path": str(path)}


def validate_consumption_receipt(
    value: Mapping[str, Any], authorization: Mapping[str, Any]
) -> dict[str, Any]:
    result = dict(value)
    if result.get("schema_version") != CONSUMPTION_SCHEMA_VERSION:
        raise AuthorizationBindingError("consumption schema mismatch")
    if result.get("authorization_id") != authorization.get("authorization_id"):
        raise AuthorizationBindingError("consumption authorization ID mismatch")
    if result.get("authorization_receipt_sha256") != authorization.get("receipt_sha256"):
        raise AuthorizationBindingError("consumption authorization hash mismatch")
    if result.get("approved_scope") != authorization.get("approved_scopes", [None])[0]:
        raise AuthorizationBindingError("consumption scope mismatch")
    if result.get("consumption_receipt_sha256") != consumption_receipt_sha256(result):
        raise AuthorizationBindingError("consumption receipt hash mismatch")
    return result


def load_consumption_receipt(
    path: Path, authorization: Mapping[str, Any]
) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    result = validate_consumption_receipt(value, authorization)
    result["path"] = str(Path(path).resolve())
    return result


def authorization_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value.get(key)
        for key in (
            "authorization_id",
            "receipt_sha256",
            "approved_scopes",
            "family",
            "scene_seed",
            "implementation_source_sha256",
            "budget_receipt_sha256",
            "reviewed_content_commit",
            "output_namespace",
            "timeout_seconds",
            "allowed_physical_gpu_indices",
        )
    }


__all__ = [
    "AUTHORIZATION_SCHEMA_VERSION",
    "authorization_receipt_sha256",
    "authorization_summary",
    "consume_authorization_once",
    "current_source_bindings_v3_4",
    "implementation_source_sha256_v3_4",
    "load_authorization_v3_4",
    "load_consumption_receipt",
    "validate_authorization_v3_4",
    "validate_consumption_receipt",
]
