"""Source/budget/parent-bound authorization for Stage 0 smoke v1.1."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from ..runtime_source_lock_v1 import load_runtime_source_lock
from ..stage0_smoke_budget_v1_1 import (
    F4_INFRA_SCOPE,
    STAGE0_SCOPES,
    SUPPORTED_SCOPES,
    budget_receipt_sha256,
    scope_budget,
)
from ..stage0_smoke_scope_specs_v1_1 import planned_scope_spec
from .runtime_v3_3_authorization_v1 import (
    AuthorizationBindingError,
    AuthorizationExpiredError,
    AuthorizationReplayError,
    AuthorizationScopeError,
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)


AUTHORIZATION_SCHEMA_VERSION = "cmf_stage0_smoke_gpu_authorization_v1_1"
CONSUMPTION_SCHEMA_VERSION = (
    "cmf_stage0_smoke_authorization_consumption_v1_1"
)
DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_stage0_smoke_v1_1"
IMPLEMENTATION_REVISION = (
    "f4_canonical_neutral_provenance_v13_then_12_smoke_v1_1"
)
MAX_VALIDITY_SECONDS = 3600
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
WORKSPACE_ROOT = Path("/nfs_share/lijunhui")
VAULT_ROOT = WORKSPACE_ROOT / "Vault-on-Fvl09"
AUDIT_ROOT = VAULT_ROOT / "数据构造/实现审计"
GROUP = "controlled_multi_future_stage0_smoke_v1_1"
CANONICAL_PARENT_AUTHORIZATION = (
    AUDIT_ROOT / "USER_AUTHORIZATION_STAGE0_SMOKE_V1_1_20260830.json"
)
CANONICAL_STAGE0_MANIFEST = (
    AUDIT_ROOT / "STAGE0_SMOKE_ATTEMPT_MANIFEST_V1.json"
)
CANONICAL_STAGE0_BUDGET = (
    AUDIT_ROOT / "STAGE0_SMOKE_ATTEMPT_BUDGET_V1.json"
)
DATASET_ROOT = (
    WORKSPACE_ROOT
    / "Robotwin2/datasets/controlled_multi_future_stage0_smoke_v1_1"
)
INFRA_NAMESPACE = (
    "prestage0_f4_candidate_hash_infra_v13_stage0_v1_1_"
    "seed20260829_run1"
)
INFRA_AUTHORIZATION_ID = (
    "prestage0-f4-candidate-hash-infra-v13-stage0-v1-1-run1"
)
STAGE0_NAMESPACE_BY_SCOPE = {
    scope: f"stage0_smoke_v1_1_{scope.split('_')[3]}_root_A_seed20260829_run1"
    for scope in STAGE0_SCOPES
}
STAGE0_AUTHORIZATION_ID_BY_SCOPE = {
    scope: f"stage0-smoke-v1-1-{scope.split('_')[3]}-root-A-run1"
    for scope in STAGE0_SCOPES
}


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


def implementation_source_sha256_stage0_v1_1() -> str:
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def current_stage0_source_bindings_v1_1() -> dict[str, str]:
    root = Path(__file__).resolve().parents[1]
    paths = {
        "real_adapter_sha256": root / "real_sapien_adapter_v1_7.py",
        "family_runners_sha256": root / "family_runners_v3_3.py",
        "common_counter_schema_sha256": root
        / "common_scope_counter_schema_v3_4_1.py",
        "f2_preload_entry_gate_sha256": root
        / "f2_preload_entry_evidence_gate_v11.py",
        "f2_release_gates_sha256": root / "f2_release_gates_v10.py",
        "f3_grasp_contract_sha256": root / "f3_grasp_robustness_v10.py",
        "f3_three_context_runner_sha256": root
        / "f3_three_context_diagnostic_runner_v11.py",
        "f4_exact_application_sha256": root
        / "f4_exact_corridor_application_v11.py",
        "f4_candidate_equivalence_sha256": root
        / "f4_candidate_equivalence_v12.py",
        "f4_frozen_neutral_binding_sha256": root
        / "f4_frozen_canonical_neutral_binding_v13.py",
        "f4_corridor_selection_sha256": root
        / "f4_corridor_selection_gate_v13.py",
        "stage0_family_runner_sha256": root
        / "stage0_smoke_family_runner_v1_1.py",
        "stage0_video_capture_sha256": root / "stage0_video_capture_v1.py",
        "stage0_manifest_sha256": root / "stage0_smoke_manifest_v1_1.py",
        "stage0_manifest_builder_sha256": root
        / "probes/build_stage0_smoke_manifest_v1_1.py",
        "stage0_finalizer_sha256": root / "stage0_smoke_finalizer_v1_1.py",
        "stage0_finalizer_entrypoint_sha256": root
        / "probes/stage0_smoke_finalize_v1_1.py",
        "joint_limit_audit_sha256": root / "joint_limit_audit_v3_4_1.py",
        "budget_sha256": root / "stage0_smoke_budget_v1_1.py",
        "scope_specs_sha256": root / "stage0_smoke_scope_specs_v1_1.py",
        "scope_bundle_builder_sha256": root
        / "stage0_smoke_scope_bundle_v1_1.py",
        "scheduler_sha256": root / "stage0_smoke_parallel_scheduler_v1_1.py",
        "scope_runner_sha256": root
        / "probes/stage0_smoke_scope_runner_v1_1.py",
        "runtime_trace_sha256": root / "probes/runtime_trace.py",
        "raw_writer_sha256": root / "raw_writer.py",
        "root_orchestrator_sha256": root / "root_orchestrator_v1_2.py",
        "gpu_guard_sha256": root / "probes/gpu_guard_v2_4.py",
        "gpu_guard_updater_sha256": root / "probes/gpu_guard_v2_1.py",
        "authorization_validator_sha256": root
        / "probes/stage0_smoke_authorization_v1_1.py",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise AuthorizationBindingError(
            f"Stage 0 v1.1 source binding files are missing: {missing}"
        )
    result = {name: sha256_file(path) for name, path in paths.items()}
    result["implementation_source_sha256"] = (
        implementation_source_sha256_stage0_v1_1()
    )
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


def _namespace_for_scope(scope: str) -> str:
    return INFRA_NAMESPACE if scope == F4_INFRA_SCOPE else STAGE0_NAMESPACE_BY_SCOPE[scope]


def _expected_paths(scope: str) -> dict[str, Path]:
    namespace = _namespace_for_scope(scope)
    output = (
        AUDIT_ROOT / "probe_outputs" / namespace
        if scope == F4_INFRA_SCOPE
        else DATASET_ROOT / namespace
    )
    return {
        "request": AUDIT_ROOT / "scope_requests" / GROUP / f"{namespace}.request.json",
        "source_lock": AUDIT_ROOT / "source_locks" / GROUP / f"{namespace}.source_lock.json",
        "authorization": AUDIT_ROOT / "authorizations" / GROUP / f"{namespace}.authorization.json",
        "guard": AUDIT_ROOT / "gpu_guards" / GROUP / f"{namespace}.guard.json",
        "output": output,
    }


def _validate_parent(parent: Mapping[str, Any]) -> None:
    expected = {
        "schema_version": "cmf_stage0_smoke_parent_user_authorization_v1_1",
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "approved": True,
        "authorized_scopes": list(SUPPORTED_SCOPES),
        "stage0_planned_attempt_count": 12,
        "stage0_structure": "4 families x 3 r_pc attempts",
        "stage0_success_required": False,
        "allowed_family_outcomes": ["PASS", "FAILED_WITH_EVIDENCE"],
        "success_and_failure_both_retained": True,
        "stage0_generated_trajectory_mp4_required": True,
        "accepted_roots_4_of_4_precondition_removed": True,
        "f2_f3_pre_stage0_repair_required": False,
        "f4_frozen_canonical_neutral_v13_required_before_stage0": True,
        "allowed_physical_gpu_indices": list(range(8)),
        "family_level_parallelism_authorized": True,
        "one_project_job_per_gpu": True,
        "one_family_root_one_gpu": True,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "stage0_authorized": True,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
        "h_reveal": None,
        "compression_authorized": False,
        "pi05_authorized": False,
        "user_direction_source": (
            "https://chatgpt.com/s/t_6a9443e84dfc8191bc8881ac3ff0b894"
        ),
    }
    mismatches = {
        key: {"expected": wanted, "actual": parent.get(key)}
        for key, wanted in expected.items()
        if parent.get(key) != wanted
    }
    if mismatches:
        raise AuthorizationBindingError(
            f"parent Stage 0 v1.1 contract mismatch: {mismatches}"
        )


def validate_stage0_smoke_authorization_v1_1(
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
        raise AuthorizationScopeError("unsupported Stage 0 v1.1 scope")
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
        "stage0_authorized": True,
        "formal_data": False,
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
        raise AuthorizationScopeError("authorization must bind exactly one v1.1 scope")
    for key in ("authorization_id", "authorized_run_id"):
        if not isinstance(receipt.get(key), str) or SAFE_ID.fullmatch(receipt[key]) is None:
            raise AuthorizationBindingError(f"unsafe authorization {key}")
    expected_id = (
        INFRA_AUTHORIZATION_ID
        if requested_scope == F4_INFRA_SCOPE
        else STAGE0_AUTHORIZATION_ID_BY_SCOPE[requested_scope]
    )
    if receipt.get("authorization_id") != expected_id:
        raise AuthorizationBindingError("authorization ID is not canonical for scope")
    if receipt.get("authorized_run_id") != expected_id + "-run":
        raise AuthorizationBindingError("authorized run ID is not canonical for scope")
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
    budget_publication_path = _workspace_file(
        receipt.get("stage0_budget_publication_path"),
        "Stage 0 attempt budget publication",
    )
    if budget_publication_path != CANONICAL_STAGE0_BUDGET.resolve():
        raise AuthorizationBindingError(
            "Stage 0 attempt budget publication path is not canonical"
        )
    if sha256_file(budget_publication_path) != receipt.get(
        "stage0_budget_publication_file_sha256"
    ):
        raise AuthorizationBindingError(
            "Stage 0 attempt budget publication file SHA mismatch"
        )
    budget_publication = json.loads(
        budget_publication_path.read_text(encoding="utf-8")
    )
    if (
        budget_publication.get("implementation_version")
        != IMPLEMENTATION_VERSION
        or budget_publication.get("budget_receipt_sha256")
        != budget_receipt_sha256()
        or budget_publication.get("approved") is not True
        or budget_publication.get("stage0_authorized") is not True
        or budget_publication.get("stage1_authorized") is not False
        or budget_publication.get("formal_collection_authorized") is not False
        or budget_publication.get("training_authorized") is not False
    ):
        raise AuthorizationBindingError(
            "Stage 0 attempt budget publication content mismatch"
        )
    if receipt.get("planner_query_limit") != budget["planner_query_limit"]:
        raise AuthorizationBindingError("planner limit mismatch")
    if receipt.get("controlled_action_limit") != budget["execution_limit"]:
        raise AuthorizationBindingError("execution limit mismatch")
    if receipt.get("physics_step_limit") != -1:
        raise AuthorizationBindingError("physics-step limit must be -1")
    if receipt.get("timeout_seconds") != budget["timeout_seconds"]:
        raise AuthorizationBindingError("timeout mismatch")
    if receipt.get("stage0_data") is not budget["stage0_data"]:
        raise AuthorizationBindingError("Stage 0 data role mismatch")
    if receipt.get("allowed_physical_gpu_indices") != list(range(8)):
        raise AuthorizationBindingError("Stage 0 v1.1 must allow fresh-idle GPU0-7")
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
    if receipt.get("scene_seed") != spec.get("seed") or (
        expected_seed is not None and receipt.get("scene_seed") != expected_seed
    ):
        raise AuthorizationBindingError("scene seed mismatch")
    source_bindings = current_stage0_source_bindings_v1_1()
    if receipt.get("source_bindings") != source_bindings:
        raise AuthorizationBindingError("authorization source bindings changed")
    if receipt.get("implementation_source_sha256") != source_bindings[
        "implementation_source_sha256"
    ]:
        raise AuthorizationBindingError("implementation source hash mismatch")
    paths = _expected_paths(requested_scope)
    source_lock_path = _workspace_file(
        receipt.get("source_lock_receipt_path"), "source lock"
    )
    if source_lock_path != paths["source_lock"].resolve():
        raise AuthorizationBindingError("source lock path is not canonical")
    source_lock = load_runtime_source_lock(source_lock_path, expected_family=family)
    if source_lock.get("source_lock_receipt_sha256") != receipt.get(
        "source_lock_receipt_sha256"
    ):
        raise AuthorizationBindingError("source lock receipt hash mismatch")
    request_path = _workspace_file(receipt.get("approval_request_path"), "scope request")
    if request_path != paths["request"].resolve():
        raise AuthorizationBindingError("scope request path is not canonical")
    request = _load_hashed_json(
        str(request_path),
        receipt.get("approval_request_file_sha256"),
        "scope_request_sha256",
    )
    if request.get("scope_request_sha256") != receipt.get("approval_request_sha256"):
        raise AuthorizationBindingError("approval request content mismatch")
    parent_path = _workspace_file(
        receipt.get("parent_user_authorization_path"), "parent user authorization"
    )
    if parent_path != CANONICAL_PARENT_AUTHORIZATION.resolve():
        raise AuthorizationBindingError("parent authorization path is not canonical")
    if sha256_file(parent_path) != receipt.get("parent_user_authorization_file_sha256"):
        raise AuthorizationBindingError("parent authorization file SHA mismatch")
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    parent_digest = parent.get("parent_user_authorization_sha256")
    parent_payload = dict(parent)
    parent_payload.pop("parent_user_authorization_sha256", None)
    if not isinstance(parent_digest, str) or canonical_sha256(parent_payload) != parent_digest:
        raise AuthorizationBindingError("parent authorization hash invalid")
    if parent_digest != receipt.get("parent_user_authorization_sha256"):
        raise AuthorizationBindingError("parent authorization content mismatch")
    _validate_parent(parent)
    manifest = None
    if budget["stage0_data"] is True:
        manifest_path = _workspace_file(
            receipt.get("stage0_manifest_path"), "Stage 0 v1.1 manifest"
        )
        if manifest_path != CANONICAL_STAGE0_MANIFEST.resolve():
            raise AuthorizationBindingError("Stage 0 v1.1 manifest path is not canonical")
        if sha256_file(manifest_path) != receipt.get("stage0_manifest_file_sha256"):
            raise AuthorizationBindingError("Stage 0 v1.1 manifest file SHA mismatch")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_payload = dict(manifest)
        manifest_digest = manifest_payload.pop("manifest_sha256", None)
        if not isinstance(manifest_digest, str) or canonical_sha256(
            manifest_payload
        ) != manifest_digest:
            raise AuthorizationBindingError("Stage 0 v1.1 manifest self-hash mismatch")
        if manifest_digest != receipt.get("stage0_manifest_sha256"):
            raise AuthorizationBindingError("Stage 0 v1.1 manifest content mismatch")
        bundle_set_path = _workspace_file(
            receipt.get("bundle_set_receipt_path"), "bundle set receipt"
        )
        if sha256_file(bundle_set_path) != receipt.get(
            "bundle_set_receipt_file_sha256"
        ):
            raise AuthorizationBindingError("bundle set file SHA mismatch")
        bundle_set = json.loads(bundle_set_path.read_text(encoding="utf-8"))
        bundle_payload = dict(bundle_set)
        bundle_digest = bundle_payload.pop("bundle_set_receipt_sha256", None)
        if not isinstance(bundle_digest, str) or canonical_sha256(
            bundle_payload
        ) != bundle_digest:
            raise AuthorizationBindingError("bundle set self-hash mismatch")
        if bundle_digest != receipt.get("bundle_set_receipt_sha256"):
            raise AuthorizationBindingError("authorization bundle set hash mismatch")
        checks = {
            "schema": bundle_set.get("schema_version")
            == "cmf_stage0_smoke_bundle_set_receipt_v1_1",
            "scopes": bundle_set.get("scopes") == list(STAGE0_SCOPES),
            "manifest": bundle_set.get("stage0_manifest_sha256")
            == manifest_digest,
            "manifest_path": bundle_set.get("stage0_manifest_path")
            == str(manifest_path),
            "manifest_file": bundle_set.get("stage0_manifest_file_sha256")
            == receipt.get("stage0_manifest_file_sha256"),
            "source": bundle_set.get("implementation_source_sha256")
            == receipt.get("implementation_source_sha256"),
            "budget": bundle_set.get("budget_receipt_sha256")
            == receipt.get("budget_receipt_sha256"),
            "parent": bundle_set.get("parent_user_authorization_sha256")
            == parent_digest,
            "scope_id": bundle_set.get("authorization_id_by_scope", {}).get(
                requested_scope
            )
            == expected_id,
        }
        if not all(checks.values()):
            raise AuthorizationBindingError(f"bundle set binding mismatch: {checks}")
        sibling_paths = bundle_set.get("authorization_paths")
        if not isinstance(sibling_paths, Mapping) or set(sibling_paths) != set(
            STAGE0_SCOPES
        ):
            raise AuthorizationBindingError("bundle set authorization paths incomplete")
        for sibling_scope, sibling_path_value in sibling_paths.items():
            sibling_path = _workspace_file(
                sibling_path_value, f"bundle sibling {sibling_scope}"
            )
            sibling = json.loads(sibling_path.read_text(encoding="utf-8"))
            if sibling.get("approved_scopes") != [sibling_scope]:
                raise AuthorizationBindingError("bundle sibling scope mismatch")
            if sibling.get("bundle_set_receipt_sha256") != bundle_digest:
                raise AuthorizationBindingError("bundle sibling set hash mismatch")
            if sibling.get("implementation_version") != IMPLEMENTATION_VERSION:
                raise AuthorizationBindingError("bundle sibling implementation mismatch")
            if sibling.get("stage0_manifest_sha256") != manifest_digest:
                raise AuthorizationBindingError("bundle sibling manifest mismatch")
            if sibling.get("budget_receipt_sha256") != budget_receipt_sha256():
                raise AuthorizationBindingError("bundle sibling budget mismatch")
            if sibling.get("receipt_sha256") != authorization_receipt_sha256(
                sibling
            ):
                raise AuthorizationBindingError("bundle sibling self-hash mismatch")
    else:
        if any(
            receipt.get(field) is not None
            for field in (
                "stage0_manifest_path",
                "stage0_manifest_file_sha256",
                "stage0_manifest_sha256",
                "bundle_set_receipt_path",
                "bundle_set_receipt_file_sha256",
                "bundle_set_receipt_sha256",
            )
        ):
            raise AuthorizationBindingError(
                "F4 v13 infrastructure must not bind a Stage 0 manifest"
            )
    expected_spec = planned_scope_spec(
        requested_scope,
        stage0_manifest=manifest if budget["stage0_data"] is True else None,
    )
    if spec != expected_spec:
        raise AuthorizationBindingError(
            "authorization planned spec differs from canonical v1.1 spec"
        )
    request_checks = {
        "scope": request.get("scope") == requested_scope,
        "family": request.get("family") == family,
        "planned_spec": request.get("planned_root_slot_spec") == spec,
        "planned_spec_hash": request.get("planned_root_slot_spec_sha256")
        == receipt.get("planned_root_slot_spec_sha256"),
        "manifest": request.get("stage0_manifest_sha256")
        == receipt.get("stage0_manifest_sha256"),
        "budget": request.get("scope_budget") == budget,
        "budget_publication": request.get("stage0_budget_publication_path")
        == str(CANONICAL_STAGE0_BUDGET)
        and request.get("stage0_budget_publication_file_sha256")
        == receipt.get("stage0_budget_publication_file_sha256"),
        "command": request.get("authorized_command_sha256")
        == receipt.get("authorized_command_sha256"),
        "output": request.get("output_namespace") == receipt.get("output_namespace"),
        "guard": request.get("guard_receipt_path") == receipt.get("guard_receipt_path"),
        "parent": request.get("parent_user_authorization_sha256") == parent_digest,
        "flags": request.get("stage0_data") is budget["stage0_data"]
        and request.get("stage0_authorized") is True
        and request.get("formal_data") is False,
    }
    if not all(request_checks.values()):
        raise AuthorizationBindingError(
            f"scope request/authorization mismatch: {request_checks}"
        )
    for field, canonical in (
        ("consumption_ledger_directory", CANONICAL_CONSUMPTION_LEDGER_DIRECTORY),
        ("gpu_lease_directory", CANONICAL_GPU_LEASE_DIRECTORY),
        ("job_cache_root_directory", CANONICAL_JOB_CACHE_DIRECTORY),
    ):
        if str(_workspace_directory(receipt.get(field), field)) != canonical:
            raise AuthorizationBindingError(f"authorization {field} is not canonical")
    if _workspace_directory(receipt.get("output_namespace"), "output") != paths[
        "output"
    ].resolve():
        raise AuthorizationBindingError("output namespace is not canonical")
    if _workspace_directory(receipt.get("guard_receipt_path"), "guard") != paths[
        "guard"
    ].resolve():
        raise AuthorizationBindingError("guard receipt path is not canonical")
    if expected_output_namespace is not None and paths["output"].resolve() != Path(
        expected_output_namespace
    ).resolve():
        raise AuthorizationBindingError("output namespace differs from Guard argument")
    commit = receipt.get("reviewed_content_commit")
    if not isinstance(commit, str) or HEX40.fullmatch(commit) is None:
        raise AuthorizationBindingError("reviewed content commit is invalid")
    if expected_reviewed_content_commit is not None and commit != expected_reviewed_content_commit:
        raise AuthorizationBindingError("reviewed content commit mismatch")
    if not isinstance(receipt.get("authorized_command_sha256"), str) or HEX64.fullmatch(
        receipt["authorized_command_sha256"]
    ) is None:
        raise AuthorizationBindingError("authorized command hash is invalid")
    return receipt


def load_stage0_smoke_authorization_v1_1(
    path: Path, *, requested_scope: str, **kwargs
) -> dict[str, Any]:
    path = Path(path).resolve()
    expected_path = _expected_paths(requested_scope)["authorization"].resolve()
    if path != expected_path:
        raise AuthorizationBindingError("authorization path is not canonical")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationBindingError("authorization receipt is unreadable") from exc
    return validate_stage0_smoke_authorization_v1_1(
        value, requested_scope=requested_scope, **kwargs
    )


def consumption_receipt_sha256(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("consumption_receipt_sha256", None)
    payload.pop("path", None)
    return canonical_sha256(payload)


def consume_authorization_once_v1_1(
    authorization: Mapping[str, Any], *, ledger_directory: Path
) -> dict[str, Any]:
    ledger = Path(ledger_directory).resolve()
    if str(ledger) != CANONICAL_CONSUMPTION_LEDGER_DIRECTORY:
        raise AuthorizationBindingError("consumption ledger is not canonical")
    ledger.mkdir(parents=True, exist_ok=True)
    path = ledger / f"{authorization['authorization_id']}.json"
    value = {
        "schema_version": CONSUMPTION_SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": authorization["authorization_id"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "approved_scope": authorization["approved_scopes"][0],
        "family": authorization["family"],
        "scene_seed": authorization["scene_seed"],
        "consumed_at": datetime.now(timezone.utc).isoformat(),
        "max_invocations": 1,
    }
    value["consumption_receipt_sha256"] = consumption_receipt_sha256(value)
    data = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise AuthorizationReplayError("authorization was already consumed") from exc
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return {**value, "path": str(path)}


def validate_consumption_receipt_v1_1(
    value: Mapping[str, Any], authorization: Mapping[str, Any]
) -> dict[str, Any]:
    result = dict(value)
    expected = {
        "schema_version": CONSUMPTION_SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": authorization.get("authorization_id"),
        "authorization_receipt_sha256": authorization.get("receipt_sha256"),
        "approved_scope": authorization.get("approved_scopes", [None])[0],
        "family": authorization.get("family"),
        "scene_seed": authorization.get("scene_seed"),
        "max_invocations": 1,
    }
    for key, wanted in expected.items():
        if result.get(key) != wanted:
            raise AuthorizationBindingError(f"consumption receipt mismatch: {key}")
    if result.get("consumption_receipt_sha256") != consumption_receipt_sha256(result):
        raise AuthorizationBindingError("consumption receipt hash mismatch")
    return result


def load_consumption_receipt_v1_1(
    path: Path, authorization: Mapping[str, Any]
) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    result = validate_consumption_receipt_v1_1(value, authorization)
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
            "planned_root_slot_spec_sha256",
            "stage0_manifest_sha256",
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
    "AUTHORIZATION_SCHEMA_VERSION",
    "CANONICAL_PARENT_AUTHORIZATION",
    "CANONICAL_STAGE0_BUDGET",
    "CANONICAL_STAGE0_MANIFEST",
    "CONSUMPTION_SCHEMA_VERSION",
    "DATASET_ROOT",
    "GROUP",
    "IMPLEMENTATION_REVISION",
    "IMPLEMENTATION_VERSION",
    "INFRA_AUTHORIZATION_ID",
    "INFRA_NAMESPACE",
    "STAGE0_AUTHORIZATION_ID_BY_SCOPE",
    "STAGE0_NAMESPACE_BY_SCOPE",
    "authorization_receipt_sha256",
    "authorization_summary",
    "canonical_sha256",
    "consume_authorization_once_v1_1",
    "current_stage0_source_bindings_v1_1",
    "implementation_source_sha256_stage0_v1_1",
    "load_consumption_receipt_v1_1",
    "load_stage0_smoke_authorization_v1_1",
    "sha256_file",
    "validate_consumption_receipt_v1_1",
    "validate_stage0_smoke_authorization_v1_1",
]
