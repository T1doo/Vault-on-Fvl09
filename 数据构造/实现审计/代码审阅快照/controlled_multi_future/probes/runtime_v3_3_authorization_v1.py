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
from ..runtime_v3_3_budget_v1 import (
    ROOT_SCOPES,
    SUPPORTED_SCOPES,
    authorization_common_limits,
    budget_receipt_sha256,
    scope_budget,
    validate_scope_budget,
)


AUTHORIZATION_SCHEMA_VERSION = "cmf_runtime_v3_3_gpu_authorization_v1"
CONSUMPTION_SCHEMA_VERSION = "cmf_runtime_v3_3_authorization_consumption_v1"
DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_3"
IMPLEMENTATION_REVISION = "runtime_v3_3_strict_prefix_common_v1"
ALLOWED_UUID_POLICY = "fresh_idle_exact_uuid_selected_by_atomic_guard"
MAX_AUTHORIZATION_VALIDITY_SECONDS = 3600
CANONICAL_CONSUMPTION_LEDGER_DIRECTORY = (
    "/nfs_share/lijunhui/Robotwin2/runtime_v3_3_authorization_ledger/authorizations"
)
CANONICAL_REVISION_LEDGER_DIRECTORY = (
    "/nfs_share/lijunhui/Robotwin2/runtime_v3_3_authorization_ledger/family_revisions"
)
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


def implementation_source_sha256_v3_3() -> str:
    source_root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(source_root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def current_source_bindings_v3_3() -> dict:
    root = Path(__file__).resolve().parents[1]
    paths = {
        "root_orchestrator_sha256": root / "root_orchestrator_v1_2.py",
        "real_adapter_sha256": root / "real_sapien_adapter_v1_3.py",
        "canonical_prefix_artifact_sha256": root / "canonical_prefix_artifact_v1.py",
        "canonical_prefix_replay_sha256": root / "canonical_prefix_replay_v1.py",
        "frozen_suffix_artifact_sha256": root / "frozen_suffix_artifact_v1.py",
        "family_runners_sha256": root / "family_runners_v3_3.py",
        "project_cube_grasp_pose_sha256": root / "project_cube_grasp_pose_v1.py",
        "canonical_prefix_smoke_sha256": root / "canonical_prefix_smoke_v1.py",
        "f4_cube_grasp_ik_audit_sha256": root / "f4_cube_grasp_ik_audit_v1.py",
        "f4_staged_block_gate_sha256": root / "f4_staged_block_gate_v1.py",
        "scope_specs_sha256": root / "runtime_v3_3_scope_specs_v1.py",
        "scope_bundle_builder_sha256": root / "runtime_v3_3_scope_bundle_v1.py",
        "gpu_guard_sha256": root / "probes/gpu_guard_v2_4.py",
        "authorization_validator_sha256": root / "probes/runtime_v3_3_authorization_v1.py",
        "scope_runner_sha256": root / "probes/runtime_v3_3_scope_runner.py",
        "budget_module_sha256": root / "runtime_v3_3_budget_v1.py",
        "runtime_source_lock_module_sha256": root / "runtime_source_lock_v1.py",
    }
    result = {key: sha256_file(path) for key, path in paths.items()}
    result["implementation_source_sha256"] = implementation_source_sha256_v3_3()
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


def validate_authorization_v3_3(
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

    request_receipt_bindings = {
        "family": "family",
        "scene_seed": "scene_seed",
        "planned_root_slot_spec": "planned_root_slot_spec",
        "planned_root_slot_spec_sha256": "planned_root_slot_spec_sha256",
        "scope_budget": "scope_budget",
        "scope_budget_sha256": "scope_budget_sha256",
        "planner_query_limit": "planner_query_limit",
        "controlled_action_limit": "controlled_action_limit",
        "physics_step_limit": "physics_step_limit",
        "timeout_seconds": "timeout_seconds",
        "allowed_physical_gpu_indices": "allowed_physical_gpu_indices",
        "allowed_gpu_uuid_policy": "allowed_gpu_uuid_policy",
        "output_namespace": "output_namespace",
        "exact_child_command_sha256": "authorized_command_sha256",
        "source_lock_receipt_path": "source_lock_receipt_path",
        "consumption_ledger_directory": "consumption_ledger_directory",
        "revision_ledger_directory": "revision_ledger_directory",
        "family_revision_index": "family_revision_index",
        "maximum_new_implementation_revisions_per_family": "maximum_new_implementation_revisions_per_family",
        "maximum_full_root_execution_per_revision": "maximum_full_root_execution_per_revision",
    }
    for request_key, receipt_key in request_receipt_bindings.items():
        if request.get(request_key) != receipt.get(receipt_key):
            raise AuthorizationBindingError(
                f"scope request/authorization mismatch: {request_key}"
            )
    if receipt.get("consumption_ledger_directory") != CANONICAL_CONSUMPTION_LEDGER_DIRECTORY:
        raise AuthorizationBindingError("authorization consumption ledger is not canonical")

    bindings = current_source_bindings_v3_3()
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
    if requested_scope in ROOT_SCOPES:
        revision_index = receipt.get("family_revision_index")
        if revision_index not in (1, 2):
            raise AuthorizationBindingError("root authorization revision index must be 1 or 2")
        if planned.get("implementation_revision_index") != revision_index:
            raise AuthorizationBindingError("root authorization/planned revision mismatch")
        revision_label = planned.get("implementation_revision")
        if not isinstance(revision_label, str) or SAFE_ID.fullmatch(revision_label) is None:
            raise AuthorizationBindingError("root planned implementation revision label is invalid")
        revision_directory = receipt.get("revision_ledger_directory")
        if (
            not isinstance(revision_directory, str)
            or not Path(revision_directory).is_absolute()
            or not revision_directory.startswith("/nfs_share/lijunhui/")
        ):
            raise AuthorizationBindingError("root authorization revision ledger is invalid")
        if revision_directory != CANONICAL_REVISION_LEDGER_DIRECTORY:
            raise AuthorizationBindingError("root authorization revision ledger is not canonical")
        if receipt.get("maximum_new_implementation_revisions_per_family") != 2:
            raise AuthorizationBindingError("root authorization revision limit mismatch")
        if receipt.get("maximum_full_root_execution_per_revision") != 1:
            raise AuthorizationBindingError("root authorization root-per-revision limit mismatch")
    elif (
        receipt.get("family_revision_index") is not None
        or receipt.get("revision_ledger_directory") is not None
    ):
        raise AuthorizationBindingError("non-root authorization cannot consume a revision slot")
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
    indices = receipt.get("allowed_physical_gpu_indices")
    if indices != [0]:
        raise AuthorizationBindingError("runtime-v3_3 is restricted to physical GPU0")
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


def load_authorization_v3_3(path: Path, **kwargs) -> dict:
    path = Path(path)
    if not path.is_file():
        raise AuthorizationBindingError("runtime-v3_3 requires an explicit v1 authorization receipt")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationBindingError("authorization receipt is unreadable") from exc
    return validate_authorization_v3_3(value, **kwargs)


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
        "family_revision_index": value.get("family_revision_index"),
        "revision_ledger_directory": value.get("revision_ledger_directory"),
        "consumption_ledger_directory": value["consumption_ledger_directory"],
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
    if str(ledger_directory) != CANONICAL_CONSUMPTION_LEDGER_DIRECTORY:
        raise AuthorizationBindingError("authorization consumption ledger is not canonical")
    ledger_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = ledger_directory / f"{authorization_id}.json"
    revision_payload = None
    revision_path = None
    approved_scope = value["approved_scopes"][0]
    if approved_scope in ROOT_SCOPES:
        revision_directory = Path(value["revision_ledger_directory"])
        revision_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        revision_path = revision_directory / (
            f"{value['family']}-revision-{value['family_revision_index']}.json"
        )
        revision_payload = {
            "schema_version": "cmf_runtime_v3_3_family_revision_consumption_v1",
            "family": value["family"],
            "family_revision_index": value["family_revision_index"],
            "authorization_id": authorization_id,
            "authorization_receipt_sha256": value["receipt_sha256"],
            "authorized_run_id": value["authorized_run_id"],
            "planned_root_slot_spec_sha256": value[
                "planned_root_slot_spec_sha256"
            ],
            "root_slot_id": value["planned_root_slot_spec"]["slot_id"],
            "scene_seed": value["scene_seed"],
            "implementation_revision": value["planned_root_slot_spec"][
                "implementation_revision"
            ],
            "implementation_source_sha256": value[
                "implementation_source_sha256"
            ],
            "root_identity_sha256": canonical_sha256(
                {
                    "family": value["family"],
                    "root_slot_id": value["planned_root_slot_spec"]["slot_id"],
                    "scene_seed": value["scene_seed"],
                }
            ),
            "maximum_full_root_execution_per_revision": 1,
            "consumed_at": (now or datetime.now(timezone.utc)).astimezone().isoformat(),
        }
        revision_payload["revision_consumption_receipt_sha256"] = canonical_sha256(
            revision_payload
        )
    payload = {
        "schema_version": CONSUMPTION_SCHEMA_VERSION,
        "authorization_id": authorization_id,
        "authorization_receipt_sha256": value["receipt_sha256"],
        "authorized_run_id": value["authorized_run_id"],
        "output_namespace": value["output_namespace"],
        "source_lock_receipt_sha256": value["source_lock_receipt_sha256"],
        "consumed_at": (now or datetime.now(timezone.utc)).astimezone().isoformat(),
        "max_invocations": 1,
        "approved_scope": approved_scope,
        "family_revision_index": value.get("family_revision_index"),
        "revision_consumption_receipt_sha256": None
        if revision_payload is None
        else revision_payload["revision_consumption_receipt_sha256"],
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
    if revision_payload is not None:
        if value["family_revision_index"] == 2:
            previous_path = Path(value["revision_ledger_directory"]) / (
                f"{value['family']}-revision-1.json"
            )
            if not previous_path.is_file():
                raise AuthorizationBindingError(
                    "family revision 2 requires a consumed revision 1"
                )
            try:
                previous = json.loads(previous_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise AuthorizationBindingError(
                    "family revision 1 receipt is unreadable"
                ) from exc
            previous_hash = previous.pop(
                "revision_consumption_receipt_sha256", None
            )
            if (
                not isinstance(previous_hash, str)
                or canonical_sha256(previous) != previous_hash
            ):
                raise AuthorizationBindingError(
                    "family revision 1 receipt hash mismatch"
                )
            for key in ("family", "root_slot_id", "scene_seed", "root_identity_sha256"):
                if previous.get(key) != revision_payload[key]:
                    raise AuthorizationBindingError(
                        f"family revision 2 changed frozen root identity: {key}"
                    )
            if (
                previous.get("implementation_source_sha256")
                == revision_payload["implementation_source_sha256"]
            ):
                raise AuthorizationBindingError(
                    "family revision 2 must bind a different implementation source hash"
                )
            if previous.get("implementation_revision") == revision_payload[
                "implementation_revision"
            ]:
                raise AuthorizationBindingError(
                    "family revision 2 must use a new implementation revision label"
                )
        revision_data = (
            json.dumps(revision_payload, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        ).encode("utf-8")
        try:
            revision_fd = os.open(
                revision_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
        except FileExistsError as exc:
            raise AuthorizationReplayError(
                "family revision already consumed its one full-root slot"
            ) from exc
        except OSError as exc:
            raise AuthorizationBindingError(
                "cannot atomically create family revision receipt"
            ) from exc
        try:
            offset = 0
            while offset < len(revision_data):
                written = os.write(revision_fd, revision_data[offset:])
                if written <= 0:
                    raise OSError("short write while sealing revision receipt")
                offset += written
            os.fsync(revision_fd)
        finally:
            os.close(revision_fd)
        payload["revision_consumption_path"] = str(revision_path)
    return payload


def validate_consumption_receipt(value: Mapping[str, Any], authorization: Mapping[str, Any]) -> dict:
    if not isinstance(value, Mapping) or value.get("schema_version") != CONSUMPTION_SCHEMA_VERSION:
        raise AuthorizationBindingError("invalid authorization consumption receipt schema")
    receipt = dict(value)
    expected_hash = receipt.pop("consumption_receipt_sha256", None)
    receipt.pop("path", None)
    receipt.pop("revision_consumption_path", None)
    if not isinstance(expected_hash, str) or canonical_sha256(receipt) != expected_hash:
        raise AuthorizationBindingError("authorization consumption receipt hash mismatch")
    required = {
        "authorization_id": authorization["authorization_id"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "authorized_run_id": authorization["authorized_run_id"],
        "output_namespace": authorization["output_namespace"],
        "source_lock_receipt_sha256": authorization["source_lock_receipt_sha256"],
        "max_invocations": 1,
        "approved_scope": authorization["approved_scopes"][0],
        "family_revision_index": authorization.get("family_revision_index"),
    }
    for key, expected in required.items():
        if receipt.get(key) != expected:
            raise AuthorizationBindingError(f"authorization consumption binding mismatch: {key}")
    expected_revision_hash = None
    if authorization["approved_scopes"][0] in ROOT_SCOPES:
        revision_path = value.get("revision_consumption_path")
        if not isinstance(revision_path, str) or not Path(revision_path).is_file():
            raise AuthorizationBindingError("family revision consumption receipt is missing")
        try:
            revision = json.loads(Path(revision_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AuthorizationBindingError("family revision receipt is unreadable") from exc
        revision_hash = revision.pop("revision_consumption_receipt_sha256", None)
        if not isinstance(revision_hash, str) or canonical_sha256(revision) != revision_hash:
            raise AuthorizationBindingError("family revision receipt hash mismatch")
        revision_required = {
            "schema_version": "cmf_runtime_v3_3_family_revision_consumption_v1",
            "family": authorization["family"],
            "family_revision_index": authorization["family_revision_index"],
            "authorization_id": authorization["authorization_id"],
            "authorization_receipt_sha256": authorization["receipt_sha256"],
            "authorized_run_id": authorization["authorized_run_id"],
            "planned_root_slot_spec_sha256": authorization[
                "planned_root_slot_spec_sha256"
            ],
            "root_slot_id": authorization["planned_root_slot_spec"]["slot_id"],
            "scene_seed": authorization["scene_seed"],
            "implementation_revision": authorization["planned_root_slot_spec"][
                "implementation_revision"
            ],
            "implementation_source_sha256": authorization[
                "implementation_source_sha256"
            ],
            "root_identity_sha256": canonical_sha256(
                {
                    "family": authorization["family"],
                    "root_slot_id": authorization["planned_root_slot_spec"][
                        "slot_id"
                    ],
                    "scene_seed": authorization["scene_seed"],
                }
            ),
            "maximum_full_root_execution_per_revision": 1,
        }
        for key, expected in revision_required.items():
            if revision.get(key) != expected:
                raise AuthorizationBindingError(
                    f"family revision consumption binding mismatch: {key}"
                )
        expected_revision_hash = revision_hash
    if receipt.get("revision_consumption_receipt_sha256") != expected_revision_hash:
        raise AuthorizationBindingError("authorization revision consumption hash mismatch")
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
    if authorization["approved_scopes"][0] in ROOT_SCOPES:
        value["revision_consumption_path"] = str(
            Path(authorization["revision_ledger_directory"])
            / f"{authorization['family']}-revision-{authorization['family_revision_index']}.json"
        )
    return validate_consumption_receipt(value, authorization)
