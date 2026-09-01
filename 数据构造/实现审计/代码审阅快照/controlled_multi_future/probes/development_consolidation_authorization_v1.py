"""Generic single-use authorization for the consolidation qualification jobs."""

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
from ..f2_exact_replay_v1 import validate_f2_exact_replay_spec_v1
from ..f3_grasp_qualification_v1 import validate_f3_grasp_candidate_spec_v1
from ..f4_template_qualification_v1 import validate_f4_template_candidate_spec_v1
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


IMPLEMENTATION_VERSION = "controlled_multi_future_development_consolidation_v1"
AUTH_SCHEMA = "cmf_development_consolidation_authorization_v1"
CONSUMPTION_SCHEMA = "cmf_development_consolidation_consumption_v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
JOB_KINDS = frozenset(
    {
        "F2_EXACT_REPLAY",
        "F3_PLANNER_SCREEN",
        "F3_PHYSICAL_CANDIDATE",
        "F3_THREE_SCENE_CONFIRMATION",
        "F3_FULL_ROOT",
        "F4_TEMPLATE_CANDIDATE",
        "F4_A_ONLY",
        "F4_FULL_ROOT",
    }
)


def job_budget_v1(job_kind: str) -> dict[str, Any]:
    values = {
        "F2_EXACT_REPLAY": (768, 3, 13, 21600),
        "F3_PLANNER_SCREEN": (8, 0, 1, 7200),
        "F3_PHYSICAL_CANDIDATE": (32, 1, 1, 7200),
        "F3_THREE_SCENE_CONFIRMATION": (96, 3, 3, 21600),
        "F3_FULL_ROOT": (192, 3, 8, 28800),
        "F4_TEMPLATE_CANDIDATE": (96, 1, 4, 14400),
        "F4_A_ONLY": (64, 1, 1, 14400),
        "F4_FULL_ROOT": (320, 3, 8, 28800),
    }
    if job_kind not in values:
        raise ValueError("unsupported consolidation job kind")
    planner, controlled, scenes, timeout = values[job_kind]
    value = {
        "schema_version": "cmf_development_consolidation_job_budget_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "job_kind": job_kind,
        "planner_query_limit": planner,
        "controlled_action_limit": controlled,
        "fresh_scene_limit": scenes,
        "physics_step_limit": -1,
        "timeout_seconds": timeout,
        "recovery_attempts": 0,
        "maximum_invocations": 1,
        "allowed_physical_gpu_indices": list(range(8)),
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
        "root_sharding_authorized": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["budget_receipt_sha256"] = canonical_hash_json(value)
    return value


def _validate_job_spec(job_kind: str, value: Mapping[str, Any]) -> dict[str, Any]:
    if job_kind == "F2_EXACT_REPLAY":
        return validate_f2_exact_replay_spec_v1(value)
    if job_kind.startswith("F3_"):
        result = validate_f3_grasp_candidate_spec_v1(value)
        expected_purpose = {
            "F3_PLANNER_SCREEN": "planner_screen",
            "F3_PHYSICAL_CANDIDATE": "physical",
            "F3_THREE_SCENE_CONFIRMATION": "three_scene_confirmation",
            "F3_FULL_ROOT": "full_root",
        }[job_kind]
        if result["purpose"] != expected_purpose:
            raise AuthorizationBindingError("F3 job kind/purpose mismatch")
        return result
    result = validate_f4_template_candidate_spec_v1(value)
    return result


def _validate_job_inputs(
    job_kind: str, value: Any, spec: Mapping[str, Any]
) -> dict[str, Any]:
    inputs = canonical_jsonable(value)
    if not isinstance(inputs, dict):
        raise AuthorizationBindingError("consolidation job inputs must be a mapping")
    source_required = job_kind in {
        "F3_PHYSICAL_CANDIDATE",
        "F3_THREE_SCENE_CONFIRMATION",
        "F3_FULL_ROOT",
        "F4_A_ONLY",
        "F4_FULL_ROOT",
    }
    if not source_required:
        if inputs:
            raise AuthorizationBindingError("consolidation base job cannot carry inputs")
        return inputs
    required = {
        "source_receipt_path",
        "source_receipt_file_sha256",
        "source_receipt_sha256",
        "selected_candidate_id",
    }
    if job_kind == "F4_A_ONLY":
        required.add("planner_only_output_dir")
    if set(inputs) != required:
        raise AuthorizationBindingError("consolidation job input fields changed")
    source_path = _path(
        inputs["source_receipt_path"], "source job receipt", file_required=True
    )
    source_value = json.loads(source_path.read_text(encoding="utf-8"))
    if (
        _file_sha(source_path) != inputs["source_receipt_file_sha256"]
        or source_value.get("receipt_sha256") != inputs["source_receipt_sha256"]
    ):
        raise AuthorizationBindingError("consolidation source job receipt changed")
    selected = (
        spec.get("selected_grasp_candidate", {}).get("candidate_id")
        if spec.get("family") == "F3"
        else spec.get("selected_layout_candidate_id")
    )
    if inputs["selected_candidate_id"] != selected:
        raise AuthorizationBindingError("consolidation source candidate mismatch")
    if job_kind == "F4_A_ONLY":
        planner_dir = _path(inputs["planner_only_output_dir"], "planner-only output")
        if not (planner_dir / "receipt.json").is_file() or not (
            planner_dir / "prefix_artifact/canonical_prefix_artifact.json"
        ).is_file():
            raise AuthorizationBindingError("F4 A-only planner source is incomplete")
    return inputs


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
        raise AuthorizationBindingError("consolidation authorization schema mismatch")
    if result.get("implementation_version") != IMPLEMENTATION_VERSION:
        raise AuthorizationBindingError("consolidation implementation mismatch")
    scopes = result.get("approved_scopes")
    if scopes != [requested_scope] or result.get("approved") is not True:
        raise AuthorizationBindingError("consolidation scope is not approved exactly once")
    job_kind = result.get("job_kind")
    if job_kind not in JOB_KINDS:
        raise AuthorizationBindingError("consolidation job kind is unsupported")
    if result.get("receipt_sha256") != receipt_sha(result):
        raise AuthorizationBindingError("consolidation authorization hash mismatch")
    issued = _time(result.get("issued_at"))
    expires = _time(result.get("expires_at"))
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not 0 < (expires - issued).total_seconds() <= 3600 or not issued <= current < expires:
        raise AuthorizationExpiredError("consolidation authorization is inactive")
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
        raise AuthorizationBindingError("consolidation safety boundary changed")
    spec = _validate_job_spec(job_kind, result.get("planned_root_slot_spec", {}))
    _validate_job_inputs(job_kind, result.get("job_inputs", {}), spec)
    if (
        result.get("planned_root_slot_spec_sha256")
        != spec["planned_scope_spec_sha256"]
        or result.get("family") != spec["family"]
        or result.get("scene_seed") != spec["seed"]
        or result.get("approved_scopes") != [spec["scope"]]
    ):
        raise AuthorizationBindingError("consolidation planned spec binding mismatch")
    if expected_family is not None and result["family"] != expected_family:
        raise AuthorizationBindingError("consolidation family mismatch")
    if expected_seed is not None and result["scene_seed"] != expected_seed:
        raise AuthorizationBindingError("consolidation seed mismatch")
    budget = job_budget_v1(job_kind)
    for key, expected in (
        ("budget", budget),
        ("budget_receipt_sha256", budget["budget_receipt_sha256"]),
        ("planner_query_limit", budget["planner_query_limit"]),
        ("controlled_action_limit", budget["controlled_action_limit"]),
        ("physics_step_limit", budget["physics_step_limit"]),
        ("timeout_seconds", budget["timeout_seconds"]),
    ):
        if result.get(key) != expected:
            raise AuthorizationBindingError(f"consolidation budget mismatch: {key}")
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
        raise AuthorizationBindingError("consolidation source lock mismatch")
    request_path = _path(
        result.get("approval_request_path"), "approval request", file_required=True
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
        raise AuthorizationBindingError("consolidation approval request mismatch")
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
        or result["approved_scopes"][0] not in parent.get("authorized_scopes", [])
    ):
        raise AuthorizationBindingError("consolidation parent authorization mismatch")
    expected_paths = {
        "consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        "gpu_lease_directory": CANONICAL_GPU_LEASE_DIRECTORY,
        "job_cache_root_directory": CANONICAL_JOB_CACHE_DIRECTORY,
    }
    for key, expected in expected_paths.items():
        if str(_path(result.get(key), key)) != expected:
            raise AuthorizationBindingError(f"consolidation path mismatch: {key}")
    output = _path(result.get("output_namespace"), "output namespace")
    guard = _path(result.get("guard_receipt_path"), "guard receipt")
    if expected_output_namespace is not None and output != Path(
        expected_output_namespace
    ).resolve():
        raise AuthorizationBindingError("consolidation output namespace mismatch")
    if guard.parent.name != "development_pipeline_consolidation_v1":
        raise AuthorizationBindingError("consolidation guard directory mismatch")
    command_sha = result.get("authorized_command_sha256")
    if not isinstance(command_sha, str) or HEX64.fullmatch(command_sha) is None:
        raise AuthorizationBindingError("consolidation command hash is invalid")
    commit = result.get("reviewed_content_commit")
    if not isinstance(commit, str) or HEX40.fullmatch(commit) is None:
        raise AuthorizationBindingError("consolidation reviewed commit is invalid")
    if expected_reviewed_content_commit is not None and commit != expected_reviewed_content_commit:
        raise AuthorizationBindingError("consolidation reviewed commit changed")
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
        raise AuthorizationBindingError("consolidation consumption ledger mismatch")
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
        raise AuthorizationReplayError("consolidation authorization already consumed") from exc
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
        raise AuthorizationBindingError("consolidation consumption binding mismatch")
    if result.get("consumption_receipt_sha256") != consumption_sha(result):
        raise AuthorizationBindingError("consolidation consumption hash mismatch")
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
    "consume",
    "job_budget_v1",
    "load",
    "load_consumption",
    "receipt_sha",
    "validate",
    "validate_consumption",
]
