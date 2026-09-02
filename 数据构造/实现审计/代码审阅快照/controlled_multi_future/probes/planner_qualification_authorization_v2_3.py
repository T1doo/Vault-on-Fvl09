"""Single-use authorization validator for V2.3 planner-only jobs.

No authorization is issued by importing or calling this module.  It only
validates a separately signed, time-limited user/senior approval artifact.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from ..canonical_artifact import canonical_hash_json, canonical_jsonable, canonical_write_json
from ..gpu_parallel_policy_v2 import validate_current_gpu_authorization
from ..planner_qualification_integration_v2_3 import (
    IMPLEMENTATION_VERSION,
    RUNNER_SYMBOLS,
    build_manifest_bundle_v2_3,
)
from .runtime_v3_3_authorization_v1 import (
    AuthorizationBindingError,
    AuthorizationExpiredError,
    AuthorizationReplayError,
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
)


AUTH_SCHEMA = "cmf_planner_qualification_authorization_v2_3"
CONSUMPTION_SCHEMA = "cmf_planner_qualification_consumption_v2_3"
QUERY_LIMITS = {"F2_STAGE_A": 3, "F3_STAGE_A": 3, "F3_STAGE_B": 7, "F4_PROGRAM": 30}


def receipt_sha(value: Mapping[str, Any]) -> str:
    payload = canonical_jsonable(value)
    payload.pop("receipt_sha256", None)
    return canonical_hash_json(payload)


def _time(value: Any) -> datetime:
    try:
        result = datetime.fromisoformat(str(value))
    except Exception as exc:
        raise AuthorizationBindingError("V2.3 authorization time is invalid") from exc
    if result.tzinfo is None:
        raise AuthorizationBindingError("V2.3 authorization time lacks timezone")
    return result.astimezone(timezone.utc)


def validate(
    value: Mapping[str, Any],
    *,
    requested_scope: str,
    expected_vault_head: str | None = None,
    expected_source_tree_sha256: str | None = None,
    expected_robotwin_tracked_head: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    result = canonical_jsonable(value)
    if (
        result.get("schema_version") != AUTH_SCHEMA
        or result.get("implementation_version") != IMPLEMENTATION_VERSION
        or result.get("receipt_sha256") != receipt_sha(result)
    ):
        raise AuthorizationBindingError("V2.3 authorization identity/hash mismatch")
    if result.get("approved") is not True or result.get("approved_scopes") != [requested_scope]:
        raise AuthorizationBindingError("V2.3 scope is not separately approved")
    issued, expires = _time(result.get("issued_at")), _time(result.get("expires_at"))
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not 0 < (expires - issued).total_seconds() <= 3600 or not issued <= current < expires:
        raise AuthorizationExpiredError("V2.3 authorization is inactive")
    validate_current_gpu_authorization(result)
    job_kind = result.get("job_kind")
    if job_kind not in RUNNER_SYMBOLS:
        raise AuthorizationBindingError("V2.3 job kind is unsupported")
    bundle = build_manifest_bundle_v2_3()
    manifest_sha = {
        "F2_STAGE_A": bundle["f2_panel_sha256"],
        "F3_STAGE_A": bundle["f3_stage_a_panel_sha256"],
        "F3_STAGE_B": bundle["f3_stage_b_policy_sha256"],
        "F4_PROGRAM": bundle["f4_panel_sha256"],
    }[job_kind]
    forbidden = {"callback", "plan_chain_fn", "target_builder", "raw_pose_generator"}
    if (
        result.get("manifest_bundle_sha256") != bundle["bundle_sha256"]
        or result.get("manifest_sha256") != manifest_sha
        or result.get("runner_symbol") != RUNNER_SYMBOLS[job_kind]
        or forbidden & set(result)
        or result.get("planner_query_limit") != QUERY_LIMITS[job_kind]
        or result.get("scene_limit") != 1
        or result.get("physical_execution_limit") != 0
        or result.get("max_invocations") != 1
        or result.get("automatic_retry") is not False
        or result.get("fallback_allowed") is not False
        or result.get("o_excl_output_required") is not True
        or result.get("source_change_invalidates_authorization") is not True
        or result.get("stage1_authorized") is not False
        or result.get("formal_data") is not False
    ):
        raise AuthorizationBindingError("V2.3 manifest/runner/budget boundary changed")
    for actual, expected, label in (
        (result.get("vault_head"), expected_vault_head, "Vault HEAD"),
        (result.get("active_source_tree_sha256"), expected_source_tree_sha256, "source tree"),
        (result.get("robotwin_tracked_head"), expected_robotwin_tracked_head, "RoboTwin HEAD"),
    ):
        if expected is not None and actual != expected:
            raise AuthorizationBindingError(f"V2.3 {label} changed")
    output = Path(str(result.get("output_path", "")))
    if not output.is_absolute() or not str(output).startswith("/nfs_share/lijunhui/"):
        raise AuthorizationBindingError("V2.3 output path is outside workspace")
    if output.exists() or result.get("output_preexisting") is not False:
        raise AuthorizationBindingError("V2.3 O_EXCL output precondition failed")
    job_spec = canonical_jsonable(result.get("job_spec"))
    payload = dict(job_spec)
    spec_digest = payload.pop("job_spec_sha256", None)
    if spec_digest != canonical_hash_json(payload) or result.get("job_spec_sha256") != spec_digest:
        raise AuthorizationBindingError("V2.3 job spec hash mismatch")
    return result


def load(path: Path, *, requested_scope: str, **kwargs) -> dict[str, Any]:
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


def consume(authorization: Mapping[str, Any], *, ledger_directory: Path) -> dict[str, Any]:
    directory = Path(ledger_directory).resolve()
    if str(directory) != CANONICAL_CONSUMPTION_LEDGER_DIRECTORY:
        raise AuthorizationBindingError("V2.3 consumption directory mismatch")
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
        raise AuthorizationReplayError("V2.3 authorization already consumed") from exc
    return {**value, "path": str(path)}


def validate_consumption(
    consumption: Mapping[str, Any], authorization: Mapping[str, Any]
) -> dict[str, Any]:
    result = canonical_jsonable(consumption)
    if (
        result.get("schema_version") != CONSUMPTION_SCHEMA
        or result.get("consumption_receipt_sha256") != consumption_sha(result)
        or result.get("authorization_id") != authorization.get("authorization_id")
        or result.get("authorization_receipt_sha256") != authorization.get("receipt_sha256")
        or result.get("job_kind") != authorization.get("job_kind")
        or result.get("max_invocations") != 1
    ):
        raise AuthorizationBindingError("V2.3 consumption binding mismatch")
    return result


__all__ = ["IMPLEMENTATION_VERSION", "consume", "load", "validate", "validate_consumption"]
