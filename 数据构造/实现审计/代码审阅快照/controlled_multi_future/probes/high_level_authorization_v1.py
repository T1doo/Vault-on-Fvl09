"""Single-use authorization validator for High-Level Template Redesign V1."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from ..canonical_artifact import (
    canonical_hash_json,
    canonical_jsonable,
    canonical_write_json,
)
from ..gpu_parallel_policy_v2 import validate_current_gpu_authorization
from ..high_level_runtime_specs_v1 import (
    job_budget_v1,
    validate_f2_runtime_spec_v1,
    validate_f3_runtime_spec_v1,
    validate_f4_runtime_spec_v1,
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


IMPLEMENTATION_VERSION = "controlled_multi_future_high_level_template_redesign_v1_2_5"
AUTH_SCHEMA = "cmf_high_level_template_redesign_authorization_v1"
CONSUMPTION_SCHEMA = "cmf_high_level_template_redesign_consumption_v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
JOB_PURPOSES = {
    "F2_STAGE_A_PLANNER": "f2_stage_a_planner",
    "F2_INSIDE_PHYSICAL": "f2_inside_physical",
    "F3_LEVEL1_PLANNER": "f3_level1_planner",
    "F3_LEVEL2_PHYSICAL": "f3_level2_physical",
    "F4_STAGE_A_PLANNER": "f4_stage_a_planner",
    "F4_STAGE_B_PLANNER": "f4_stage_b_planner",
}
JOB_KINDS = frozenset(JOB_PURPOSES)


def _path(value: Any, label: str, *, file_required: bool = False) -> Path:
    path = Path(value).resolve() if isinstance(value, str) else Path("/")
    if not str(path).startswith("/nfs_share/lijunhui/"):
        raise AuthorizationBindingError(f"{label} is outside workspace")
    if file_required and not path.is_file():
        raise AuthorizationBindingError(f"{label} is not a file")
    return path


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _time(value: Any) -> datetime:
    try:
        result = datetime.fromisoformat(value)
    except Exception as exc:
        raise AuthorizationBindingError("authorization time is invalid") from exc
    if result.tzinfo is None:
        raise AuthorizationBindingError("authorization time lacks timezone")
    return result.astimezone(timezone.utc)


def receipt_sha(value: Mapping[str, Any]) -> str:
    payload = canonical_jsonable(value)
    payload.pop("receipt_sha256", None)
    return canonical_hash_json(payload)


def _validate_job_spec(job_kind: str, value: Mapping[str, Any]) -> dict[str, Any]:
    if job_kind.startswith("F2_"):
        spec = validate_f2_runtime_spec_v1(value)
    elif job_kind.startswith("F3_"):
        spec = validate_f3_runtime_spec_v1(value)
    elif job_kind.startswith("F4_"):
        spec = validate_f4_runtime_spec_v1(value)
    else:
        raise AuthorizationBindingError("unsupported high-level job kind")
    if spec["purpose"] != JOB_PURPOSES[job_kind]:
        raise AuthorizationBindingError("high-level job kind/purpose mismatch")
    return spec


def _validate_selection_source(
    job_kind: str, inputs: Mapping[str, Any], spec: Mapping[str, Any]
) -> dict[str, Any]:
    required = {
        "selection_receipt_path",
        "selection_receipt_file_sha256",
        "selection_receipt_sha256",
        "selected_candidate_id",
    }
    if set(inputs) != required:
        raise AuthorizationBindingError("physical selection input fields changed")
    path = _path(
        inputs["selection_receipt_path"],
        "selection receipt",
        file_required=True,
    )
    source = json.loads(path.read_text(encoding="utf-8"))
    if (
        _file_sha(path) != inputs["selection_receipt_file_sha256"]
        or source.get("receipt_sha256") != inputs["selection_receipt_sha256"]
    ):
        raise AuthorizationBindingError("physical selection receipt changed")
    if job_kind == "F2_INSIDE_PHYSICAL":
        expected_schema = "cmf_f2_hierarchical_inside_planner_terminal_v1"
        selected_ids = source.get("physical_candidate_ids", [])
        candidate_id = spec["candidate"]["candidate_id"]
    elif job_kind == "F3_LEVEL2_PHYSICAL":
        expected_schema = "cmf_f3_asset_grasp_level1_terminal_v2"
        selected_ids = source.get("level2_tuple_ids", [])
        candidate_id = spec["f3_asset_grasp_tuple_v2"]["tuple_id"]
    else:
        raise AuthorizationBindingError("job does not accept selection source")
    if source.get("schema_version") != expected_schema:
        raise AuthorizationBindingError("selection receipt schema mismatch")
    if (
        inputs["selected_candidate_id"] != candidate_id
        or candidate_id not in selected_ids
    ):
        raise AuthorizationBindingError("candidate is not selected for physical audit")
    return canonical_jsonable(inputs)


def _validate_job_inputs(
    job_kind: str, value: Any, spec: Mapping[str, Any]
) -> dict[str, Any]:
    inputs = canonical_jsonable(value)
    if not isinstance(inputs, dict):
        raise AuthorizationBindingError("high-level job inputs must be a mapping")
    if job_kind in {
        "F2_STAGE_A_PLANNER",
        "F3_LEVEL1_PLANNER",
        "F4_STAGE_A_PLANNER",
    }:
        if inputs:
            raise AuthorizationBindingError("planner candidate job cannot carry inputs")
        return inputs
    if job_kind == "F4_STAGE_B_PLANNER":
        required = {
            "stage_a_selection_receipt_path",
            "stage_a_selection_receipt_file_sha256",
            "stage_a_selection_receipt_sha256",
            "selected_source_grasp_candidate_id",
            "stage_b_candidate_id",
        }
        if set(inputs) != required:
            raise AuthorizationBindingError(
                "F4 Stage-B selection input fields changed"
            )
        path = _path(
            inputs["stage_a_selection_receipt_path"],
            "F4 Stage-A selection receipt",
            file_required=True,
        )
        source = json.loads(path.read_text(encoding="utf-8"))
        embedded = spec.get("f4_stage_a_terminal_v1")
        if (
            _file_sha(path)
            != inputs["stage_a_selection_receipt_file_sha256"]
            or source.get("receipt_sha256")
            != inputs["stage_a_selection_receipt_sha256"]
            or source.get("schema_version")
            not in {
                "cmf_f4_hierarchical_stage_a_terminal_v1",
                "cmf_f4_hierarchical_stage_a_sequential_terminal_v1",
            }
            or canonical_jsonable(source) != canonical_jsonable(embedded)
            or source.get("stage_b_authorized_by_result") is not True
            or source.get("selected_source_grasp", {}).get("candidate_id")
            != inputs["selected_source_grasp_candidate_id"]
            or spec.get("f4_source_grasp_candidate_v1", {}).get(
                "candidate_id"
            )
            != inputs["selected_source_grasp_candidate_id"]
            or spec.get("f4_stage_b_candidate_v1", {}).get("candidate_id")
            != inputs["stage_b_candidate_id"]
        ):
            raise AuthorizationBindingError(
                "F4 Stage-B selection receipt or candidate binding changed"
            )
        return inputs
    return _validate_selection_source(job_kind, inputs, spec)


def validate(
    value: Mapping[str, Any],
    *,
    requested_scope: str,
    now: datetime | None = None,
    expected_output_namespace: str | None = None,
    expected_family: str | None = None,
    expected_seed: int | None = None,
    expected_reviewed_content_commit: str | None = None,
) -> dict[str, Any]:
    result = canonical_jsonable(value)
    if result.get("schema_version") != AUTH_SCHEMA:
        raise AuthorizationBindingError("high-level authorization schema mismatch")
    if result.get("implementation_version") != IMPLEMENTATION_VERSION:
        raise AuthorizationBindingError("high-level implementation mismatch")
    if result.get("approved") is not True or result.get("approved_scopes") != [
        requested_scope
    ]:
        raise AuthorizationBindingError("high-level scope is not approved exactly once")
    job_kind = result.get("job_kind")
    if job_kind not in JOB_KINDS:
        raise AuthorizationBindingError("high-level job kind is unsupported")
    if result.get("receipt_sha256") != receipt_sha(result):
        raise AuthorizationBindingError("high-level authorization hash mismatch")
    issued = _time(result.get("issued_at"))
    expires = _time(result.get("expires_at"))
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not 0 < (expires - issued).total_seconds() <= 3600 or not issued <= current < expires:
        raise AuthorizationExpiredError("high-level authorization is inactive")
    validate_current_gpu_authorization(result)
    if (
        result.get("max_invocations") != 1
        or result.get("automatic_retry") is not False
        or result.get("recovery_attempts") != 0
        or result.get("formal_data") is not False
        or result.get("stage0_data") is not False
        or result.get("stage0_authorized") is not False
        or result.get("stage1_authorized") is not False
    ):
        raise AuthorizationBindingError("high-level safety boundary changed")
    spec = _validate_job_spec(job_kind, result.get("planned_root_slot_spec", {}))
    _validate_job_inputs(job_kind, result.get("job_inputs", {}), spec)
    if (
        result.get("planned_root_slot_spec_sha256")
        != spec["planned_scope_spec_sha256"]
        or result.get("family") != spec["family"]
        or result.get("scene_seed") != spec["seed"]
        or result.get("approved_scopes") != [spec["scope"]]
    ):
        raise AuthorizationBindingError("high-level planned spec binding mismatch")
    if expected_family is not None and result["family"] != expected_family:
        raise AuthorizationBindingError("high-level family mismatch")
    if expected_seed is not None and result["scene_seed"] != expected_seed:
        raise AuthorizationBindingError("high-level seed mismatch")
    budget = job_budget_v1(spec["purpose"])
    for key, expected in (
        ("budget", budget),
        ("budget_receipt_sha256", budget["budget_receipt_sha256"]),
        ("planner_query_limit", budget["planner_query_limit"]),
        ("controlled_action_limit", budget["controlled_action_limit"]),
        ("physics_step_limit", budget["physics_step_limit"]),
        ("timeout_seconds", budget["timeout_seconds"]),
    ):
        if result.get(key) != expected:
            raise AuthorizationBindingError(f"high-level budget mismatch: {key}")
    source_path = _path(
        result.get("source_lock_receipt_path"), "source lock", file_required=True
    )
    source = load_runtime_source_lock(source_path, expected_family=result["family"])
    if (
        source["source_lock_receipt_sha256"]
        != result.get("source_lock_receipt_sha256")
        or source["snapshot"]["implementation_source_sha256"]
        != result.get("implementation_source_sha256")
    ):
        raise AuthorizationBindingError("high-level source lock mismatch")
    request_path = _path(
        result.get("approval_request_path"),
        "approval request",
        file_required=True,
    )
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request_payload = dict(request)
    request_digest = request_payload.pop("scope_request_sha256", None)
    if (
        request_digest != canonical_hash_json(request_payload)
        or request_digest != result.get("approval_request_sha256")
        or _file_sha(request_path) != result.get("approval_request_file_sha256")
        or request.get("authorization_id") != result.get("authorization_id")
        or request.get("authorized_command_sha256")
        != result.get("authorized_command_sha256")
        or request.get("output_namespace") != result.get("output_namespace")
        or request.get("planned_root_slot_spec_sha256")
        != result.get("planned_root_slot_spec_sha256")
    ):
        raise AuthorizationBindingError("high-level approval request mismatch")
    parent_path = _path(
        result.get("parent_user_authorization_path"),
        "parent authorization",
        file_required=True,
    )
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    parent_payload = dict(parent)
    parent_digest = parent_payload.pop("parent_user_authorization_sha256", None)
    if (
        parent_digest != canonical_hash_json(parent_payload)
        or parent_digest != result.get("parent_user_authorization_sha256")
        or _file_sha(parent_path) != result.get("parent_user_authorization_file_sha256")
        or job_kind not in parent.get("authorized_job_kinds", [])
        or result["approved_scopes"][0] not in parent.get("authorized_scopes", [])
    ):
        raise AuthorizationBindingError("high-level parent authorization mismatch")
    expected_paths = {
        "consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        "gpu_lease_directory": CANONICAL_GPU_LEASE_DIRECTORY,
        "job_cache_root_directory": CANONICAL_JOB_CACHE_DIRECTORY,
    }
    for key, expected in expected_paths.items():
        if str(_path(result.get(key), key)) != expected:
            raise AuthorizationBindingError(f"high-level path mismatch: {key}")
    output = _path(result.get("output_namespace"), "output namespace")
    guard = _path(result.get("guard_receipt_path"), "guard receipt")
    if expected_output_namespace is not None and output != Path(
        expected_output_namespace
    ).resolve():
        raise AuthorizationBindingError("high-level output namespace mismatch")
    if guard.parent.name != "high_level_template_redesign_v1":
        raise AuthorizationBindingError("high-level guard directory mismatch")
    if not isinstance(result.get("authorized_command_sha256"), str) or HEX64.fullmatch(
        result["authorized_command_sha256"]
    ) is None:
        raise AuthorizationBindingError("high-level command hash is invalid")
    commit = result.get("reviewed_content_commit")
    if not isinstance(commit, str) or HEX40.fullmatch(commit) is None:
        raise AuthorizationBindingError("high-level reviewed commit is invalid")
    if (
        expected_reviewed_content_commit is not None
        and commit != expected_reviewed_content_commit
    ):
        raise AuthorizationBindingError("high-level reviewed commit changed")
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
    ledger = Path(ledger_directory).resolve()
    if str(ledger) != CANONICAL_CONSUMPTION_LEDGER_DIRECTORY:
        raise AuthorizationBindingError("high-level consumption ledger mismatch")
    ledger.mkdir(parents=True, exist_ok=True)
    path = ledger / f"{authorization['authorization_id']}.json"
    value = {
        "schema_version": CONSUMPTION_SCHEMA,
        "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": authorization["authorization_id"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "approved_scope": authorization["approved_scopes"][0],
        "job_kind": authorization["job_kind"],
        "family": authorization["family"],
        "scene_seed": authorization["scene_seed"],
        "consumed_at": datetime.now(timezone.utc).isoformat(),
        "max_invocations": 1,
    }
    value["consumption_receipt_sha256"] = consumption_sha(value)
    try:
        canonical_write_json(path, value, exclusive=True, mode=0o600)
    except FileExistsError as exc:
        raise AuthorizationReplayError("high-level authorization already consumed") from exc
    return {**value, "path": str(path)}


def validate_consumption(
    value: Mapping[str, Any], authorization: Mapping[str, Any]
) -> dict[str, Any]:
    result = canonical_jsonable(value)
    expected = {
        "schema_version": CONSUMPTION_SCHEMA,
        "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": authorization.get("authorization_id"),
        "authorization_receipt_sha256": authorization.get("receipt_sha256"),
        "approved_scope": authorization.get("approved_scopes", [None])[0],
        "job_kind": authorization.get("job_kind"),
        "family": authorization.get("family"),
        "scene_seed": authorization.get("scene_seed"),
        "max_invocations": 1,
    }
    if any(result.get(key) != item for key, item in expected.items()):
        raise AuthorizationBindingError("high-level consumption binding mismatch")
    if result.get("consumption_receipt_sha256") != consumption_sha(result):
        raise AuthorizationBindingError("high-level consumption hash mismatch")
    return result


def load_consumption(
    path: Path, authorization: Mapping[str, Any]
) -> dict[str, Any]:
    result = validate_consumption(
        json.loads(Path(path).read_text(encoding="utf-8")), authorization
    )
    result["path"] = str(Path(path).resolve())
    return result


__all__ = [
    "AUTH_SCHEMA",
    "IMPLEMENTATION_VERSION",
    "JOB_KINDS",
    "JOB_PURPOSES",
    "consume",
    "load",
    "load_consumption",
    "receipt_sha",
    "validate",
    "validate_consumption",
]
