"""Guard-compatible authorization for V2.3.1 planner wiring jobs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ..canonical_artifact import canonical_hash_json, canonical_jsonable, canonical_write_json
from ..gpu_parallel_policy_v2 import validate_current_gpu_authorization
from ..planner_qualification_scene_bridges_v2_3_1 import RUNNER_SYMBOLS
from ..planner_wiring_smoke_v2_3_1 import validate_wave_approval_v1
from ..probes.gpu_guard_v2_1 import command_sha256
from ..runtime_source_lock_v1 import load_runtime_source_lock
from .runtime_v3_3_authorization_v1 import (
    AuthorizationBindingError,
    AuthorizationExpiredError,
    AuthorizationReplayError,
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)


IMPLEMENTATION_VERSION = "controlled_multi_future_smoke_activation_bridge_v2_3_1"
AUTH_SCHEMA = "cmf_planner_qualification_authorization_v2_3_1"
CONSUMPTION_SCHEMA = "cmf_planner_qualification_consumption_v2_3_1"
QUERY_LIMITS = {"F2_STAGE_A": 3, "F3_STAGE_A": 3, "F3_STAGE_B": 7, "F4_PROGRAM": 42}
FAMILIES = {"F2_STAGE_A": "F2", "F3_STAGE_A": "F3", "F3_STAGE_B": "F3", "F4_PROGRAM": "F4"}


def _path(value: Any, label: str, *, file_required=False) -> Path:
    path = Path(str(value)).resolve()
    if not str(path).startswith("/nfs_share/lijunhui/"):
        raise AuthorizationBindingError(f"{label} is outside workspace")
    if file_required and not path.is_file():
        raise AuthorizationBindingError(f"{label} is not a file")
    return path


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def receipt_sha(value: Mapping[str, Any]) -> str:
    payload = canonical_jsonable(value)
    payload.pop("receipt_sha256", None)
    return canonical_hash_json(payload)


def _time(value: Any) -> datetime:
    try:
        result = datetime.fromisoformat(str(value))
    except Exception as exc:
        raise AuthorizationBindingError("V2.3.1 authorization time invalid") from exc
    if result.tzinfo is None:
        raise AuthorizationBindingError("V2.3.1 authorization time lacks timezone")
    return result.astimezone(timezone.utc)


def validate(
    value: Mapping[str, Any],
    *,
    requested_scope: str,
    expected_output_namespace: str | None = None,
    expected_family: str | None = None,
    expected_seed: int | None = None,
    expected_reviewed_content_commit: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    result = canonical_jsonable(value)
    if (
        result.get("schema_version") != AUTH_SCHEMA
        or result.get("implementation_version") != IMPLEMENTATION_VERSION
        or result.get("receipt_sha256") != receipt_sha(result)
    ):
        raise AuthorizationBindingError("V2.3.1 authorization identity/hash mismatch")
    if result.get("approved") is not True or result.get("approved_scopes") != [requested_scope]:
        raise AuthorizationBindingError("V2.3.1 scope not approved exactly")
    issued, expires = _time(result.get("issued_at")), _time(result.get("expires_at"))
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not 0 < (expires - issued).total_seconds() <= 3600 or not issued <= current < expires:
        raise AuthorizationExpiredError("V2.3.1 authorization inactive")
    validate_current_gpu_authorization(result)
    kind = result.get("job_kind")
    if kind not in RUNNER_SYMBOLS:
        raise AuthorizationBindingError("V2.3.1 unsupported job kind")
    family = FAMILIES[kind]
    job = canonical_jsonable(result.get("job_spec"))
    job_payload = dict(job)
    job_sha = job_payload.pop("job_spec_sha256", None)
    budget = canonical_jsonable(result.get("budget"))
    budget_payload = dict(budget)
    budget_sha = budget_payload.pop("budget_receipt_sha256", None)
    activation = canonical_jsonable(result.get("activation_contract"))
    activation_payload = dict(activation)
    activation_sha = activation_payload.pop("contract_sha256", None)
    if (
        job_sha != canonical_hash_json(job_payload)
        or result.get("job_spec_sha256") != job_sha
        or activation_sha != canonical_hash_json(activation_payload)
        or result.get("activation_contract_sha256") != activation_sha
        or budget_sha != canonical_hash_json(budget_payload)
        or result.get("budget_receipt_sha256") != budget_sha
        or result.get("runner_symbol") != RUNNER_SYMBOLS[kind]
        or result.get("family") != family
        or result.get("scene_seed") != job.get("scene_seed")
        or result.get("planned_root_slot_spec_sha256") != job_sha
        or result.get("planner_query_limit") != QUERY_LIMITS[kind]
        or budget.get("planner_query_limit") != QUERY_LIMITS[kind]
        or result.get("controlled_action_limit") != 0
        or result.get("physics_step_limit") != 5000
        or result.get("timeout_seconds") != budget.get("timeout_seconds")
        or result.get("max_invocations") != 1
        or result.get("automatic_retry") is not False
        or result.get("fallback_allowed") is not False
        or result.get("physical_execution_limit") != 0
        or result.get("stage1_authorized") is not False
        or result.get("formal_data") is not False
    ):
        raise AuthorizationBindingError("V2.3.1 job/budget/semantic binding mismatch")
    approval = validate_wave_approval_v1(
        result["wave_approval"], activation_contract=activation
    )
    envelope = canonical_jsonable(result.get("job_envelope"))
    envelope_payload = dict(envelope)
    envelope_sha = envelope_payload.pop("job_envelope_sha256", None)
    if (
        envelope_sha != canonical_hash_json(envelope_payload)
        or result.get("job_envelope_sha256") != envelope_sha
        or envelope.get("job_spec_sha256") != job_sha
        or envelope.get("output_namespace") != result.get("output_namespace")
        or envelope.get("guard_receipt_path") != result.get("guard_receipt_path")
        or envelope.get("authorized_command_sha256")
        != result.get("authorized_command_sha256")
        or result.get("parent_user_authorization_sha256")
        != approval["wave_approval_sha256"]
        or result.get("approval_request_sha256") != result.get("job_envelope_sha256")
    ):
        raise AuthorizationBindingError("V2.3.1 wave/envelope binding mismatch")
    source_path = _path(result.get("source_lock_receipt_path"), "source lock", file_required=True)
    source = load_runtime_source_lock(source_path, expected_family=family)
    if (
        source["source_lock_receipt_sha256"] != result.get("source_lock_receipt_sha256")
        or source["snapshot"]["implementation_source_sha256"]
        != result.get("implementation_source_sha256")
        or source["snapshot"]["official_repo_commit"] != result.get("robotwin_tracked_head")
    ):
        raise AuthorizationBindingError("V2.3.1 source lock changed")
    for key, expected in (
        ("consumption_ledger_directory", CANONICAL_CONSUMPTION_LEDGER_DIRECTORY),
        ("gpu_lease_directory", CANONICAL_GPU_LEASE_DIRECTORY),
        ("job_cache_root_directory", CANONICAL_JOB_CACHE_DIRECTORY),
    ):
        if str(_path(result.get(key), key)) != expected:
            raise AuthorizationBindingError(f"V2.3.1 {key} mismatch")
    output = _path(result.get("output_namespace"), "output namespace")
    guard = _path(result.get("guard_receipt_path"), "guard receipt")
    auth_path = _path(result.get("authorization_receipt_path"), "authorization receipt")
    command = result.get("authorized_command")
    if (
        result.get("authorized_command_sha256") != command_sha256(command)
        or command != [
            "/nfs_share/lijunhui/Robotwin2/env/bin/python",
            "-m",
            "controlled_multi_future.probes.planner_qualification_scope_runner_v2_3",
            "--authorization-receipt",
            str(auth_path),
        ]
        or output.exists()
        or guard.exists()
    ):
        raise AuthorizationBindingError("V2.3.1 command/O_EXCL paths mismatch")
    if expected_output_namespace is not None and output != Path(expected_output_namespace).resolve():
        raise AuthorizationBindingError("V2.3.1 output namespace changed")
    if expected_family is not None and family != expected_family:
        raise AuthorizationBindingError("V2.3.1 family changed")
    if expected_seed is not None and result["scene_seed"] != expected_seed:
        raise AuthorizationBindingError("V2.3.1 scene seed changed")
    if expected_reviewed_content_commit is not None and result.get("reviewed_content_commit") != expected_reviewed_content_commit:
        raise AuthorizationBindingError("V2.3.1 reviewed commit changed")
    if result.get("reviewed_content_commit") != activation.get("vault_head"):
        raise AuthorizationBindingError("V2.3.1 authorization not bound to activation freeze")
    return result


def load(path: Path, *, requested_scope: str, **kwargs):
    return validate(
        json.loads(Path(path).read_text(encoding="utf-8")),
        requested_scope=requested_scope,
        **kwargs,
    )


def consumption_sha(value: Mapping[str, Any]) -> str:
    payload = canonical_jsonable(value)
    payload.pop("consumption_receipt_sha256", None)
    payload.pop("path", None)
    return canonical_hash_json(payload)


def consume(authorization: Mapping[str, Any], *, ledger_directory: Path):
    directory = Path(ledger_directory).resolve()
    if str(directory) != CANONICAL_CONSUMPTION_LEDGER_DIRECTORY:
        raise AuthorizationBindingError("V2.3.1 ledger mismatch")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{authorization['authorization_id']}.json"
    value = {
        "schema_version": CONSUMPTION_SCHEMA,
        "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": authorization["authorization_id"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "job_kind": authorization["job_kind"],
        "consumed_at": datetime.now(timezone.utc).isoformat(),
        "max_invocations": 1,
    }
    value["consumption_receipt_sha256"] = consumption_sha(value)
    try:
        canonical_write_json(path, value, exclusive=True, mode=0o600)
    except FileExistsError as exc:
        raise AuthorizationReplayError("V2.3.1 authorization already consumed") from exc
    return {**value, "path": str(path)}


def validate_consumption(consumption, authorization):
    value = canonical_jsonable(consumption)
    if (
        value.get("schema_version") != CONSUMPTION_SCHEMA
        or value.get("consumption_receipt_sha256") != consumption_sha(value)
        or value.get("authorization_id") != authorization.get("authorization_id")
        or value.get("authorization_receipt_sha256") != authorization.get("receipt_sha256")
        or value.get("job_kind") != authorization.get("job_kind")
    ):
        raise AuthorizationBindingError("V2.3.1 consumption mismatch")
    return value


__all__ = ["IMPLEMENTATION_VERSION", "consume", "load", "receipt_sha", "validate", "validate_consumption"]
