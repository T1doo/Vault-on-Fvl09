"""Authorization-bound atomic GPU guard for runtime-v3_1 hardening v5.

Importing this module performs no GPU query.  The CLI is intentionally dormant
until a user supplies a valid one-shot v1_1 authorization receipt.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
from typing import Any, Mapping, Sequence

from .gpu_guard import (
    ALLOWED_PHYSICAL_GPU_INDICES,
    build_child_environment,
    classify_terminal_status,
    is_idle,
    pids_in_process_group,
    snapshot,
    verify_post_release,
)
from .runtime_v3_1_authorization_v1_1 import (
    AuthorizationError,
    AuthorizationBindingError,
    authorization_summary,
    consume_authorization_once,
    load_authorization_v1_1,
    load_consumption_receipt,
    validate_consumption_receipt,
)


GUARD_SCHEMA_VERSION = "cmf_gpu_guard_v2_1"
PRECHECK_MAX_AGE_SECONDS = 60.0


class GuardAuthorizationMismatch(PermissionError):
    failure_status = "failed_guard_authorization_mismatch"


class GuardBudgetMismatch(PermissionError):
    failure_status = "failed_guard_budget_mismatch"


def _require_workspace_path(path: Path, label: str) -> Path:
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts or not str(path).startswith("/nfs_share/lijunhui/"):
        raise GuardAuthorizationMismatch(f"{label} must be an absolute /nfs_share/lijunhui workspace path")
    return path


def command_sha256(command: Sequence[str]) -> str:
    return hashlib.sha256(
        json.dumps(list(command), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.tmp.", dir=str(path.parent)
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def build_guard_binding(
    authorization: Mapping[str, Any],
    consumption: Mapping[str, Any],
    *,
    physical_index: int,
    expected_uuid: str,
    timeout_seconds: int,
    output_namespace: str,
    command: Sequence[str],
    guard_pid: int,
) -> dict:
    if timeout_seconds != authorization["timeout_seconds"]:
        raise GuardBudgetMismatch("guard timeout differs from authorization budget")
    if output_namespace != authorization["output_namespace"]:
        raise GuardAuthorizationMismatch("guard output namespace differs from authorization")
    if physical_index not in authorization["allowed_physical_gpu_indices"]:
        raise GuardAuthorizationMismatch("guard physical GPU index is outside authorization")
    if not isinstance(expected_uuid, str) or not expected_uuid.startswith("GPU-"):
        raise GuardAuthorizationMismatch("guard requires an explicit GPU UUID")
    validate_consumption_receipt(consumption, authorization)
    actual_command_sha256 = command_sha256(command)
    if actual_command_sha256 != authorization["authorized_command_sha256"]:
        raise GuardAuthorizationMismatch("guard child command differs from authorization")
    return {
        "authorization_id": authorization["authorization_id"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "authorized_run_id": authorization["authorized_run_id"],
        "approved_scope": authorization["approved_scopes"][0],
        "family": authorization["family"],
        "scene_seed": authorization["scene_seed"],
        "planned_root_slot_spec_sha256": authorization["planned_root_slot_spec_sha256"],
        "implementation_source_sha256": authorization["implementation_source_sha256"],
        "budget_receipt_sha256": authorization["budget_receipt_sha256"],
        "timeout_seconds": timeout_seconds,
        "output_namespace": output_namespace,
        "physical_gpu_index": physical_index,
        "expected_gpu_uuid": expected_uuid,
        "command_sha256": actual_command_sha256,
        "consumption_receipt_sha256": consumption["consumption_receipt_sha256"],
        "guard_pid": int(guard_pid),
    }


def validate_guard_binding(
    guard: Mapping[str, Any],
    authorization: Mapping[str, Any],
    consumption: Mapping[str, Any],
    *,
    physical_index: int,
    expected_uuid: str,
    child_parent_pid: int,
    now: datetime | None = None,
) -> dict:
    if guard.get("schema_version") != GUARD_SCHEMA_VERSION:
        raise GuardAuthorizationMismatch("guard schema mismatch")
    if guard.get("status") not in ("precheck_passed", "running"):
        raise GuardAuthorizationMismatch("guard has no launchable precheck status")
    binding = guard.get("binding")
    if not isinstance(binding, Mapping):
        raise GuardAuthorizationMismatch("guard binding is missing")
    expected = {
        "authorization_id": authorization["authorization_id"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "authorized_run_id": authorization["authorized_run_id"],
        "approved_scope": authorization["approved_scopes"][0],
        "family": authorization["family"],
        "scene_seed": authorization["scene_seed"],
        "planned_root_slot_spec_sha256": authorization["planned_root_slot_spec_sha256"],
        "implementation_source_sha256": authorization["implementation_source_sha256"],
        "budget_receipt_sha256": authorization["budget_receipt_sha256"],
        "timeout_seconds": authorization["timeout_seconds"],
        "output_namespace": authorization["output_namespace"],
        "physical_gpu_index": physical_index,
        "expected_gpu_uuid": expected_uuid,
        "consumption_receipt_sha256": consumption["consumption_receipt_sha256"],
        "guard_pid": child_parent_pid,
    }
    for key, value in expected.items():
        if binding.get(key) != value:
            error = GuardBudgetMismatch if key in ("budget_receipt_sha256", "timeout_seconds") else GuardAuthorizationMismatch
            raise error(f"guard binding mismatch: {key}")
    if binding.get("command_sha256") != authorization["authorized_command_sha256"]:
        raise GuardAuthorizationMismatch("guard command hash mismatch")
    precheck = guard.get("precheck")
    if not isinstance(precheck, Mapping):
        raise GuardAuthorizationMismatch("guard precheck is missing")
    try:
        captured = datetime.fromisoformat(precheck["captured_at"])
        if captured.tzinfo is None:
            raise ValueError
        age = ((now or datetime.now(timezone.utc)).astimezone(timezone.utc) - captured.astimezone(timezone.utc)).total_seconds()
    except (KeyError, TypeError, ValueError) as exc:
        raise GuardAuthorizationMismatch("guard precheck timestamp is invalid") from exc
    if not 0.0 <= age <= PRECHECK_MAX_AGE_SECONDS:
        raise GuardAuthorizationMismatch("guard precheck is stale")
    if (
        precheck.get("uuid") != expected_uuid
        or precheck.get("physical_index") != physical_index
        or int(precheck.get("memory_used_mib", 10**9)) > 100
        or int(precheck.get("utilization_percent", 100)) > 1
        or precheck.get("pstate") != "P8"
        or precheck.get("compute_processes")
    ):
        raise GuardAuthorizationMismatch("guard precheck does not prove a matching fresh-idle GPU")
    validate_consumption_receipt(consumption, authorization)
    return {"binding": dict(binding), "precheck": dict(precheck), "precheck_age_seconds": age}


def require_atomic_gpu_guard_v2_1(
    authorization: Mapping[str, Any],
    consumption: Mapping[str, Any],
    *,
    expected_uuid: str,
    physical_index: int,
) -> dict:
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    auth_path = os.environ.get("CMF_RUNTIME_AUTHORIZATION_RECEIPT")
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    index_value = os.environ.get("CMF_GPU_GUARD_PHYSICAL_INDEX")
    if not guard_path or not auth_path or not consumption_path or index_value != str(physical_index):
        raise GuardAuthorizationMismatch("child was not launched by bound GPU guard v2_1")
    if not Path(guard_path).is_file():
        raise GuardAuthorizationMismatch("bound guard receipt is missing")
    try:
        environment_authorization = json.loads(Path(auth_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GuardAuthorizationMismatch("bound authorization file is unreadable") from exc
    if environment_authorization.get("receipt_sha256") != authorization.get("receipt_sha256"):
        raise GuardAuthorizationMismatch("bound authorization file differs from validated authorization")
    if Path(consumption_path).resolve() != Path(consumption.get("path", consumption_path)).resolve():
        raise GuardAuthorizationMismatch("consumption environment path is inconsistent")
    guard = json.loads(Path(guard_path).read_text(encoding="utf-8"))
    result = validate_guard_binding(
        guard,
        authorization,
        consumption,
        physical_index=physical_index,
        expected_uuid=expected_uuid,
        child_parent_pid=os.getppid(),
    )
    return {"path": guard_path, **result}


def update_child_receipt_v2_1(
    output_dir: Path,
    guard_path: Path,
    guard_binding: Mapping[str, Any],
    post: Mapping[str, Any],
    orphan_pids: Sequence[int],
    post_release: Mapping[str, Any],
    post_error: Mapping[str, Any] | None = None,
    additional_cleanup_audit: Mapping[str, Any] | None = None,
) -> bool:
    child_path = Path(output_dir) / "receipt.json"
    if not child_path.is_file():
        return False
    payload = json.loads(child_path.read_text(encoding="utf-8"))
    child_payload_digest = payload.get("child_payload_sha256")
    if (
        payload.get("implementation_version")
        == "controlled_multi_future_stage0_smoke_v1"
        and (
            not isinstance(child_payload_digest, str)
            or payload.get("schema_version")
            != "cmf_stage0_smoke_guarded_scope_receipt_v1"
        )
    ):
        raise GuardAuthorizationMismatch(
            "Stage 0 child lacks its mandatory pre-Guard payload seal"
        )
    if child_payload_digest is not None:
        child_payload = dict(payload)
        child_payload.pop("child_payload_sha256", None)
        recomputed = hashlib.sha256(
            json.dumps(
                child_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        if recomputed != child_payload_digest:
            raise GuardAuthorizationMismatch(
                "child payload hash changed before Guard sealing"
            )
    payload["gpu_guard_binding"] = dict(guard_binding)
    payload["gpu_postcheck"] = dict(post)
    payload["gpu_postcheck_error"] = dict(post_error) if isinstance(post_error, Mapping) else None
    payload["gpu_postcheck_release"] = dict(post_release)
    scene_orphans = int(payload.get("orphan_process_count") or 0)
    payload["scene_orphan_process_count"] = scene_orphans
    payload["guard_process_group_orphan_count"] = len(orphan_pids)
    payload["orphan_process_count"] = scene_orphans + len(orphan_pids)
    payload["task_owned_orphan_pids"] = list(orphan_pids)
    payload["guard_receipt"] = str(guard_path)
    payload["guard_additional_cleanup_audit"] = (
        dict(additional_cleanup_audit)
        if isinstance(additional_cleanup_audit, Mapping)
        else None
    )
    additional_cleanup_pass = bool(
        additional_cleanup_audit is None
        or additional_cleanup_audit.get("pass") is True
    )
    if (
        payload["orphan_process_count"]
        or post_error is not None
        or post_release.get("verified") is not True
        or (payload.get("scene_created") and not payload.get("scene_cleanup_succeeded"))
        or not additional_cleanup_pass
    ):
        payload["status"] = "failed_cleanup_uncertain"
    write_json(child_path, payload)
    return True


def _peek_scope(path: Path) -> str:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        scopes = value.get("approved_scopes")
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationBindingError("cannot read authorization before guard launch") from exc
    if not isinstance(scopes, list) or len(scopes) != 1:
        raise AuthorizationBindingError("authorization must contain one approved scope")
    return scopes[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    parser.add_argument("--consumption-ledger-dir", type=Path, required=True)
    parser.add_argument("--physical-index", type=int, choices=ALLOWED_PHYSICAL_GPU_INDICES, required=True)
    parser.add_argument("--expected-uuid", required=True)
    parser.add_argument("--timeout-seconds", type=int, required=True)
    parser.add_argument("--guard-receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("a child command is required after --")
    for path, label in (
        (args.authorization_receipt, "authorization receipt"),
        (args.consumption_ledger_dir, "consumption ledger"),
        (args.guard_receipt, "guard receipt"),
        (args.output_dir, "output namespace"),
    ):
        _require_workspace_path(path, label)
    if args.guard_receipt.exists() or args.output_dir.exists():
        raise FileExistsError("guard receipt and output namespace must be new and immutable")
    started = time.time()
    guard = {
        "schema_version": GUARD_SCHEMA_VERSION,
        "purpose": "nonformal_feasibility",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "status": "starting",
    }
    try:
        scope = _peek_scope(args.authorization_receipt)
        authorization = load_authorization_v1_1(
            args.authorization_receipt,
            requested_scope=scope,
            expected_output_namespace=str(args.output_dir),
        )
        if args.timeout_seconds != authorization["timeout_seconds"]:
            raise GuardBudgetMismatch("guard timeout does not match authorization")
        if args.physical_index not in authorization["allowed_physical_gpu_indices"]:
            raise GuardAuthorizationMismatch("physical index is not authorized")
        if command_sha256(command) != authorization["authorized_command_sha256"]:
            raise GuardAuthorizationMismatch("child command differs from authorization")
    except (AuthorizationError, GuardAuthorizationMismatch, GuardBudgetMismatch) as exc:
        guard.update(
            {
                "status": getattr(exc, "failure_status", "failed_guard_authorization_mismatch"),
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "elapsed_seconds": time.time() - started,
            }
        )
        write_json(args.guard_receipt, guard)
        return 96
    try:
        pre = snapshot(args.physical_index, args.expected_uuid)
    except BaseException as exc:
        guard.update({"status": "failed_gpu_precheck", "error": {"type": type(exc).__name__, "message": str(exc)}})
        write_json(args.guard_receipt, guard)
        return 95
    guard["precheck"] = pre
    if not is_idle(pre):
        guard.update({"status": "blocked_precheck_not_idle", "elapsed_seconds": time.time() - started})
        write_json(args.guard_receipt, guard)
        return 42

    # Consumption happens after fresh-idle admission but before child launch.
    try:
        consumption = consume_authorization_once(
            authorization,
            ledger_directory=args.consumption_ledger_dir,
        )
        binding = build_guard_binding(
            authorization,
            consumption,
            physical_index=args.physical_index,
            expected_uuid=args.expected_uuid,
            timeout_seconds=args.timeout_seconds,
            output_namespace=str(args.output_dir),
            command=command,
            guard_pid=os.getpid(),
        )
    except (AuthorizationError, GuardAuthorizationMismatch, GuardBudgetMismatch) as exc:
        guard.update(
            {
                "status": getattr(exc, "failure_status", "failed_guard_authorization_mismatch"),
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "elapsed_seconds": time.time() - started,
            }
        )
        write_json(args.guard_receipt, guard)
        return 97
    guard.update({"binding": binding, "consumption_receipt": consumption["path"], "status": "precheck_passed"})
    write_json(args.guard_receipt, guard)

    stdout_path = args.guard_receipt.with_suffix(".stdout.log")
    stderr_path = args.guard_receipt.with_suffix(".stderr.log")
    environment = build_child_environment(os.environ, args.expected_uuid)
    environment.update(
        {
            "CMF_GPU_GUARD_RECEIPT": str(args.guard_receipt.resolve()),
            "CMF_GPU_GUARD_PHYSICAL_INDEX": str(args.physical_index),
            "CMF_RUNTIME_AUTHORIZATION_RECEIPT": str(args.authorization_receipt.resolve()),
            "CMF_AUTHORIZATION_CONSUMPTION_RECEIPT": str(Path(consumption["path"]).resolve()),
        }
    )
    child = None
    child_exit = None
    timed_out = False
    orphan_pids: list[int] = []
    launch_error = None
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            child = subprocess.Popen(command, env=environment, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                child_exit = child.wait(timeout=args.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child_exit = child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child_exit = child.wait(timeout=15)
    except BaseException as exc:
        launch_error = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if child is not None:
            orphan_pids = pids_in_process_group(child.pid)
            if orphan_pids:
                os.killpg(child.pid, signal.SIGKILL)
                time.sleep(1)
                orphan_pids = pids_in_process_group(child.pid)

    time.sleep(1)
    post_error = None
    try:
        post = snapshot(args.physical_index, args.expected_uuid)
        post_release = verify_post_release(pre, post)
    except BaseException as exc:
        post_error = {"type": type(exc).__name__, "message": str(exc)}
        post = {"status": "postcheck_failed", "error": post_error}
        post_release = {"verified": False, "checks": {}, "reason": "postcheck_snapshot_failed"}
    receipt_updated = False
    receipt_update_error = None
    try:
        receipt_updated = update_child_receipt_v2_1(
            args.output_dir,
            args.guard_receipt,
            binding,
            post,
            orphan_pids,
            post_release,
            post_error,
        )
    except BaseException as exc:
        receipt_update_error = {"type": type(exc).__name__, "message": str(exc)}
    cleanup_uncertain = bool(orphan_pids) or post_error is not None or post_release.get("verified") is not True
    if receipt_updated:
        child_receipt = json.loads((args.output_dir / "receipt.json").read_text(encoding="utf-8"))
        cleanup_uncertain = cleanup_uncertain or child_receipt.get("status") == "failed_cleanup_uncertain"
    if launch_error is not None and child is None:
        terminal_status, return_code = "failed_child_launch", 93
    else:
        terminal_status, return_code = classify_terminal_status(
            child_started=child is not None,
            receipt_updated=receipt_updated,
            receipt_update_error=receipt_update_error,
            cleanup_uncertain=cleanup_uncertain,
            timed_out=timed_out,
            child_exit=child_exit,
        )
    guard.update(
        {
            "status": terminal_status,
            "child_exit_code": child_exit,
            "child_launch_error": launch_error,
            "timed_out": timed_out,
            "postcheck": post,
            "postcheck_error": post_error,
            "postcheck_release": post_release,
            "task_owned_orphan_pids": orphan_pids,
            "orphan_process_count": len(orphan_pids),
            "child_receipt_updated": receipt_updated,
            "child_receipt_update_error": receipt_update_error,
            "elapsed_seconds": time.time() - started,
        }
    )
    write_json(args.guard_receipt, guard)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
