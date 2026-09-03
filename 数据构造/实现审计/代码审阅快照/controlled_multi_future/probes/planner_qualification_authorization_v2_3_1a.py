"""Guard-compatible authorization for V2.3.1a/b smoke-wave jobs."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from ..canonical_artifact import (
    canonical_hash_json,
    canonical_jsonable,
    canonical_write_json,
)
from ..gpu_parallel_policy_v2 import validate_current_gpu_authorization
from ..planner_qualification_scene_bridges_v2_3_1 import RUNNER_SYMBOLS
from ..planner_qualification_scene_bridges_v2_3_1a import (
    prepare_exact_job_bridge_envelope_v2_3_1a,
    validate_exact_job_bridge_envelope_v2_3_1a,
)
from ..planner_qualification_integration_v2_3_1a import (
    build_manifest_bundle_v2_3_1a,
)
from ..planner_wiring_smoke_v2_3_1a import (
    build_updated_planner_wiring_smoke_v1_proposal_v2,
    validate_wave_approval_v2,
)
from ..runtime_source_lock_v1 import load_runtime_source_lock
from .gpu_guard_v2_1 import command_sha256
from .runtime_v3_3_authorization_v1 import (
    AuthorizationBindingError,
    AuthorizationExpiredError,
    AuthorizationReplayError,
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)


LEGACY_IMPLEMENTATION_VERSION = "controlled_multi_future_pre_smoke_hotfix_v2_3_1a"
IMPLEMENTATION_VERSION = "controlled_multi_future_pre_smoke_hotfix_v2_3_1b"
SUPPORTED_IMPLEMENTATION_VERSIONS = (
    LEGACY_IMPLEMENTATION_VERSION,
    IMPLEMENTATION_VERSION,
)
LEGACY_AUTH_SCHEMA = "cmf_planner_qualification_authorization_v2_3_1a"
AUTH_SCHEMA = "cmf_planner_qualification_authorization_v2_3_1b"
LEGACY_CONSUMPTION_SCHEMA = "cmf_planner_qualification_consumption_v2_3_1a"
CONSUMPTION_SCHEMA = "cmf_planner_qualification_consumption_v2_3_1b"
SCOPE = "PLANNER_WIRING_SMOKE_V1"
GUARD_PURPOSE = "planner_wiring_smoke_v1"
QUERY_LIMITS = {
    "F2_STAGE_A": 3,
    "F3_STAGE_A": 3,
    "F3_STAGE_B": 7,
    "F4_PROGRAM": 42,
}
FAMILIES = {
    "F2_STAGE_A": "F2",
    "F3_STAGE_A": "F3",
    "F3_STAGE_B": "F3",
    "F4_PROGRAM": "F4",
}


def _path(value: Any, label: str, *, file_required=False) -> Path:
    path = Path(str(value)).resolve()
    if not str(path).startswith("/nfs_share/lijunhui/"):
        raise AuthorizationBindingError(f"{label} is outside workspace")
    if file_required and not path.is_file():
        raise AuthorizationBindingError(f"{label} is not a file")
    return path


def receipt_sha(value: Mapping[str, Any]) -> str:
    payload = canonical_jsonable(value)
    payload.pop("receipt_sha256", None)
    return canonical_hash_json(payload)


def _time(value: Any) -> datetime:
    try:
        result = datetime.fromisoformat(str(value))
    except Exception as exc:
        raise AuthorizationBindingError("V2.3.1a authorization time invalid") from exc
    if result.tzinfo is None:
        raise AuthorizationBindingError("V2.3.1a authorization time lacks timezone")
    return result.astimezone(timezone.utc)


def _validate_guard_receipt_state(
    guard: Path,
    *,
    result: Mapping[str, Any],
    mode: str,
) -> None:
    try:
        receipt = canonical_jsonable(
            json.loads(guard.read_text(encoding="utf-8"))
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationBindingError(
            "V2.3.1b Guard receipt is unreadable"
        ) from exc
    if mode == "preclaimed":
        expected = {
            "schema_version": "cmf_gpu_guard_v2_4_1",
            "purpose": GUARD_PURPOSE,
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "status": "starting",
        }
        if receipt != expected:
            raise AuthorizationBindingError(
                "V2.3.1b preclaimed Guard receipt is not the exact starting claim"
            )
        return
    if mode != "active":
        raise AuthorizationBindingError("V2.3.1b Guard receipt mode is invalid")
    sealed = dict(receipt)
    digest = sealed.pop("guard_receipt_sha256", None)
    binding = receipt.get("binding")
    if (
        digest != canonical_hash_json(sealed)
        or receipt.get("schema_version") != "cmf_gpu_guard_v2_4_1"
        or receipt.get("purpose") != GUARD_PURPOSE
        or receipt.get("status") not in {"precheck_passed", "running"}
        or not isinstance(binding, Mapping)
        or binding.get("authorization_id") != result.get("authorization_id")
        or binding.get("authorization_receipt_sha256")
        != result.get("receipt_sha256")
        or binding.get("output_namespace") != result.get("output_namespace")
        or binding.get("command_sha256")
        != result.get("authorized_command_sha256")
    ):
        raise AuthorizationBindingError(
            "V2.3.1b active Guard receipt binding mismatch"
        )


def validate(
    value: Mapping[str, Any],
    *,
    requested_scope: str,
    expected_output_namespace: str | None = None,
    expected_family: str | None = None,
    expected_seed: int | None = None,
    expected_reviewed_content_commit: str | None = None,
    allow_completed_paths: bool = False,
    allow_preclaimed_guard_receipt: bool = False,
    allow_active_guard_receipt: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    result = canonical_jsonable(value)
    identity = (
        result.get("schema_version"),
        result.get("implementation_version"),
    )
    if (
        identity
        not in {
            (LEGACY_AUTH_SCHEMA, LEGACY_IMPLEMENTATION_VERSION),
            (AUTH_SCHEMA, IMPLEMENTATION_VERSION),
        }
        or result.get("receipt_sha256") != receipt_sha(result)
        or result.get("approved") is not True
        or result.get("approved_scopes") != [requested_scope]
        or requested_scope != SCOPE
    ):
        raise AuthorizationBindingError("V2.3.1a authorization identity mismatch")
    issued, expires = _time(result.get("issued_at")), _time(result.get("expires_at"))
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not 0 < (expires - issued).total_seconds() <= 3600:
        raise AuthorizationExpiredError("V2.3.1a lifetime is invalid")
    if sum(
        bool(item)
        for item in (
            allow_completed_paths,
            allow_preclaimed_guard_receipt,
            allow_active_guard_receipt,
        )
    ) > 1:
        raise AuthorizationBindingError(
            "V2.3.1b Guard/path validation modes are mutually exclusive"
        )
    if not allow_completed_paths and not issued <= current < expires:
        raise AuthorizationExpiredError("V2.3.1a authorization inactive")
    validate_current_gpu_authorization(result)
    kind = result.get("job_kind")
    if kind not in RUNNER_SYMBOLS:
        raise AuthorizationBindingError("V2.3.1a unsupported job kind")
    family = FAMILIES[kind]
    job = canonical_jsonable(result.get("job_spec"))
    job_payload = dict(job)
    job_sha = job_payload.pop("job_spec_sha256", None)
    budget = canonical_jsonable(result.get("budget"))
    budget_payload = dict(budget)
    budget_sha = budget_payload.pop("budget_receipt_sha256", None)
    contract = canonical_jsonable(result.get("activation_contract"))
    contract_payload = dict(contract)
    contract_sha = contract_payload.pop("contract_sha256", None)
    if (
        job_sha != canonical_hash_json(job_payload)
        or result.get("job_spec_sha256") != job_sha
        or contract_sha != canonical_hash_json(contract_payload)
        or result.get("activation_contract_sha256") != contract_sha
        or budget_sha != canonical_hash_json(budget_payload)
        or result.get("budget_receipt_sha256") != budget_sha
        or result.get("runner_symbol") != RUNNER_SYMBOLS[kind]
        or result.get("family") != family
        or result.get("wave_id") != job.get("wave_id")
        or result.get("slot") != job.get("slot")
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
        or result.get("guard_purpose") != GUARD_PURPOSE
        or result.get("planner_reset_nonce") != job.get("planner_reset_nonce")
        or result.get("motiongen_reset_seed_argument") is not True
        or result.get("reset_receipt_bound_to_authorization") is not True
        or result.get("numeric_rng_seed_application_proven") is not False
        or result.get("bitwise_determinism_claimed") is not False
    ):
        raise AuthorizationBindingError("V2.3.1a job/budget binding mismatch")
    validate_exact_job_bridge_envelope_v2_3_1a(
        job.get("bridge_envelope"), authorization=result
    )
    approval = validate_wave_approval_v2(
        result["wave_approval"], activation_contract=contract
    )
    if (
        result.get("parent_user_authorization_sha256")
        != approval["wave_approval_sha256"]
        or result.get("wave_id") != approval["wave_id"]
    ):
        raise AuthorizationBindingError("V2.3.1a wave approval mismatch")
    proposal = build_updated_planner_wiring_smoke_v1_proposal_v2()
    slots = [item for item in proposal["ordered_job_slots"] if item["slot"] == job.get("slot")]
    if len(slots) != 1:
        raise AuthorizationBindingError("V2.3.1a job slot is outside proposal")
    slot = slots[0]
    bundle = build_manifest_bundle_v2_3_1a()
    entry = job.get("manifest_entry")
    entry_key = "job_sha256" if kind == "F4_PROGRAM" else "entry_sha256"
    if kind == "F2_STAGE_A":
        candidates = bundle["manifests"]["F2"]["ordered_recipes"]
        expected_context = {
            "certificate": bundle["manifests"]["F2"]["certificate"],
            "bindings_by_arm": bundle["manifests"]["F2"]["bindings_by_arm"],
        }
        expected_manifest_sha = bundle["f2_panel_sha256"]
    elif kind in {"F3_STAGE_A", "F3_STAGE_B"}:
        candidates = bundle["manifests"]["F3_STAGE_A"]["ordered_recipes"]
        expected_context = {}
        expected_manifest_sha = (
            bundle["f3_stage_a_panel_sha256"]
            if kind == "F3_STAGE_A"
            else bundle["f3_stage_b_policy_sha256"]
        )
    else:
        candidates = bundle["manifests"]["F4"]["ordered_jobs"]
        expected_job = next(
            item
            for item in candidates
            if item["job_sha256"] == slot["entry_sha256"]
        )
        expected_candidate = next(
            item
            for item in bundle["manifests"]["F4"]["candidates"]
            if item["candidate_sha256"] == expected_job["candidate_sha256"]
        )
        expected_context = {
            "source_candidate": bundle["manifests"]["F4"]["source_candidate"],
            "candidate": expected_candidate,
        }
        expected_manifest_sha = bundle["f4_panel_sha256"]
    matches = [
        item
        for item in candidates
        if item.get(entry_key) == slot["entry_sha256"]
    ]
    if (
        len(matches) != 1
        or canonical_jsonable(entry) != matches[0]
        or job.get("manifest_context") != expected_context
        or job.get("manifest_sha256") != expected_manifest_sha
        or job.get("manifest_bundle_sha256") != bundle["bundle_sha256"]
        or job.get("planner_query_limit") != slot["max_queries"]
        or kind != slot["job_kind"]
    ):
        raise AuthorizationBindingError("V2.3.1a manifest/slot binding mismatch")
    rebuilt_bridge = prepare_exact_job_bridge_envelope_v2_3_1a(
        job_kind=kind,
        job_id=job["job_id"],
        manifest_entry=entry,
        manifest_context=job["manifest_context"],
        manifest_sha256=job["manifest_sha256"],
        planner_reset_nonce=job["planner_reset_nonce"],
        dependency_registry=job.get("dependency_registry"),
    )
    if rebuilt_bridge != job.get("bridge_envelope"):
        raise AuthorizationBindingError("V2.3.1a bridge envelope rebuild mismatch")
    envelope = canonical_jsonable(result.get("job_envelope"))
    envelope_payload = dict(envelope)
    envelope_sha = envelope_payload.pop("job_envelope_sha256", None)
    if (
        envelope_sha != canonical_hash_json(envelope_payload)
        or result.get("job_envelope_sha256") != envelope_sha
        or envelope.get("job_spec_sha256") != job_sha
        or envelope.get("bridge_envelope_sha256")
        != job["bridge_envelope"]["bridge_envelope_sha256"]
        or envelope.get("output_namespace") != result.get("output_namespace")
        or envelope.get("guard_receipt_path") != result.get("guard_receipt_path")
        or envelope.get("authorized_command_sha256")
        != result.get("authorized_command_sha256")
        or result.get("approval_request_sha256") != envelope_sha
    ):
        raise AuthorizationBindingError("V2.3.1a job envelope mismatch")
    source_path = _path(
        result.get("source_lock_receipt_path"), "source lock", file_required=True
    )
    source = load_runtime_source_lock(source_path, expected_family=family)
    if (
        source["source_lock_receipt_sha256"]
        != result.get("source_lock_receipt_sha256")
        or source["snapshot"]["implementation_source_sha256"]
        != result.get("implementation_source_sha256")
        or source["snapshot"]["official_repo_commit"]
        != result.get("robotwin_tracked_head")
    ):
        raise AuthorizationBindingError("V2.3.1a source lock changed")
    for key, expected in (
        ("consumption_ledger_directory", CANONICAL_CONSUMPTION_LEDGER_DIRECTORY),
        ("gpu_lease_directory", CANONICAL_GPU_LEASE_DIRECTORY),
        ("job_cache_root_directory", CANONICAL_JOB_CACHE_DIRECTORY),
    ):
        if str(_path(result.get(key), key)) != expected:
            raise AuthorizationBindingError(f"V2.3.1a {key} mismatch")
    _path(result.get("wave_ledger_directory"), "wave ledger")
    output = _path(result.get("output_namespace"), "output namespace")
    guard = _path(result.get("guard_receipt_path"), "guard receipt")
    auth_path = _path(result.get("authorization_receipt_path"), "authorization receipt")
    command = result.get("authorized_command")
    if (
        result.get("authorized_command_sha256") != command_sha256(command)
        or command
        != [
            "/nfs_share/lijunhui/Robotwin2/env/bin/python",
            "-m",
            "controlled_multi_future.probes.planner_qualification_scope_runner_v2_3_1a",
            "--authorization-receipt",
            str(auth_path),
        ]
        or (not allow_completed_paths and output.exists())
    ):
        raise AuthorizationBindingError("V2.3.1a command/O_EXCL mismatch")
    if not allow_completed_paths:
        if allow_preclaimed_guard_receipt:
            if not guard.is_file():
                raise AuthorizationBindingError(
                    "V2.3.1b preclaimed Guard receipt is missing"
                )
            _validate_guard_receipt_state(
                guard, result=result, mode="preclaimed"
            )
        elif allow_active_guard_receipt:
            if not guard.is_file():
                raise AuthorizationBindingError(
                    "V2.3.1b active Guard receipt is missing"
                )
            _validate_guard_receipt_state(guard, result=result, mode="active")
        elif guard.exists():
            raise AuthorizationBindingError(
                "V2.3.1a command/O_EXCL mismatch"
            )
    if expected_output_namespace is not None and output != Path(expected_output_namespace).resolve():
        raise AuthorizationBindingError("V2.3.1a output namespace changed")
    if expected_family is not None and family != expected_family:
        raise AuthorizationBindingError("V2.3.1a family changed")
    if expected_seed is not None and result["scene_seed"] != expected_seed:
        raise AuthorizationBindingError("V2.3.1a scene seed changed")
    if expected_reviewed_content_commit is not None and result.get("reviewed_content_commit") != expected_reviewed_content_commit:
        raise AuthorizationBindingError("V2.3.1a reviewed commit changed")
    if result.get("reviewed_content_commit") != contract.get("vault_head"):
        raise AuthorizationBindingError("V2.3.1a source-freeze commit mismatch")
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
        raise AuthorizationBindingError("V2.3.1a ledger mismatch")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{authorization['authorization_id']}.json"
    implementation = authorization.get("implementation_version")
    if implementation not in SUPPORTED_IMPLEMENTATION_VERSIONS:
        raise AuthorizationBindingError(
            "V2.3.1a/b authorization implementation mismatch"
        )
    value = {
        "schema_version": (
            LEGACY_CONSUMPTION_SCHEMA
            if implementation == LEGACY_IMPLEMENTATION_VERSION
            else CONSUMPTION_SCHEMA
        ),
        "implementation_version": implementation,
        "authorization_id": authorization["authorization_id"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "wave_id": authorization["wave_id"],
        "slot": authorization["slot"],
        "job_kind": authorization["job_kind"],
        "consumed_at": datetime.now(timezone.utc).isoformat(),
        "max_invocations": 1,
    }
    value["consumption_receipt_sha256"] = consumption_sha(value)
    try:
        canonical_write_json(path, value, exclusive=True, mode=0o600)
    except FileExistsError as exc:
        raise AuthorizationReplayError("V2.3.1a authorization replay") from exc
    return {**value, "path": str(path)}


def validate_consumption(consumption, authorization):
    value = canonical_jsonable(consumption)
    implementation = authorization.get("implementation_version")
    expected_schema = (
        LEGACY_CONSUMPTION_SCHEMA
        if implementation == LEGACY_IMPLEMENTATION_VERSION
        else CONSUMPTION_SCHEMA
    )
    if (
        implementation not in SUPPORTED_IMPLEMENTATION_VERSIONS
        or value.get("schema_version") != expected_schema
        or value.get("implementation_version") != implementation
        or value.get("consumption_receipt_sha256") != consumption_sha(value)
        or value.get("authorization_id") != authorization.get("authorization_id")
        or value.get("authorization_receipt_sha256")
        != authorization.get("receipt_sha256")
        or value.get("wave_id") != authorization.get("wave_id")
        or value.get("slot") != authorization.get("slot")
        or value.get("job_kind") != authorization.get("job_kind")
    ):
        raise AuthorizationBindingError("V2.3.1a consumption mismatch")
    return value


__all__ = [
    "AUTH_SCHEMA",
    "GUARD_PURPOSE",
    "IMPLEMENTATION_VERSION",
    "SCOPE",
    "consume",
    "load",
    "receipt_sha",
    "validate",
    "validate_consumption",
]
