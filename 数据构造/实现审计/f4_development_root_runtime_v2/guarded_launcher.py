#!/usr/bin/env python3
"""Independent phase-aware Guard for a future approved F4 Runtime V2 root."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from manifest_contract import (  # noqa: E402
    GUARD_ENTRY,
    POST_CHILD,
    canonical_hash,
    file_sha,
    load_and_validate_manifest_job,
)


WORKSPACE = Path("/nfs_share/lijunhui")
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"
ENV_PYTHON = WORKSPACE / "Robotwin2/env/bin/python"
BASE_GUARD = WORKSPACE / "Robotwin2/production_micro_gate_v1/guarded_launcher.py"
BASE_GUARD_SHA256 = "d666db0b9059c0abed5473024873919531dfff60d8f56346067909c357597210"


def _load_base_guard_primitives():
    if file_sha(BASE_GUARD) != BASE_GUARD_SHA256:
        raise RuntimeError("sealed base GPU Guard primitives changed")
    spec = importlib.util.spec_from_file_location("cmf_f4_v2_base_guard_primitives", BASE_GUARD)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load sealed base GPU Guard primitives")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load_base_guard_primitives()


def _terminate_group(child):
    errors = []
    if child is None:
        return errors
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(child.pid, sig)
        except ProcessLookupError:
            break
        except BaseException as exc:
            errors.append(
                {"signal": int(sig), "type": type(exc).__name__, "message": str(exc)}
            )
        try:
            child.wait(timeout=30)
            break
        except subprocess.TimeoutExpired:
            continue
    return errors


def _write_new(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def _returned_to_baseline(pre, post, physical_index, uuid):
    before = base.selected(pre, physical_index, uuid)
    after = base.selected(post, physical_index, uuid)
    return bool(
        after["memory_used_mib"] <= max(64, before["memory_used_mib"] + 32)
        and after["utilization_gpu_percent"] == 0
        and after["pstate"] in {"P8", "P12"}
        and not after["compute_processes"]
    )


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--physical-index", type=int, choices=range(8), required=True)
    parser.add_argument("--expected-uuid", required=True)
    args = parser.parse_args(argv)

    validated = load_and_validate_manifest_job(
        args.manifest,
        args.job_id,
        phase=GUARD_ENTRY,
        require_execution_authorized=True,
    )
    manifest = validated["manifest"]
    job = validated["job"]
    if args.physical_index not in manifest["allowed_physical_gpu_indices"]:
        raise PermissionError("physical GPU is outside approved indices")
    guard_dir = Path(validated["paths"]["guard_directory"])
    start_path = Path(validated["paths"]["start_receipt"])
    terminal_path = Path(validated["paths"]["guard_terminal"])
    stdout_path = Path(validated["paths"]["stdout_log"])
    stderr_path = Path(validated["paths"]["stderr_log"])
    output = Path(validated["paths"]["output"])
    cache_job = Path(validated["paths"]["cache_job"])
    lease_root = WORKSPACE / "Robotwin2/gpu_leases/production_micro_gate_v1"
    lease_root.mkdir(parents=True, exist_ok=True)
    lease_path = lease_root / f"physical_gpu_{args.physical_index}.lock"
    lease_handle = lease_path.open("a+")
    try:
        fcntl.flock(lease_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        lease_handle.close()
        raise RuntimeError("selected GPU already has a project lease") from exc

    started = time.time()
    child = None
    pre = launch = post = None
    exit_code = None
    timed_out = False
    interrupted = None
    cleanup_errors = []
    cache_removed = False
    lease_released = False
    returned = False
    child_environment = None
    try:
        pre = base.nvidia_snapshot()
        if not base.idle(base.selected(pre, args.physical_index, args.expected_uuid)):
            raise RuntimeError("selected GPU is not independently fresh-idle")
        guard_dir.mkdir(parents=True, exist_ok=False)
        start_receipt = {
            "schema_version": "cmf_f4_development_root_v2_guard_start_v1",
            "run_id": manifest["run_id"],
            "job_id": args.job_id,
            "family": "F4",
            "manifest_sha256": manifest["manifest_sha256"],
            "physical_gpu_index": args.physical_index,
            "gpu_uuid": args.expected_uuid,
            "guard_pid": os.getpid(),
            "lease_path": str(lease_path),
            "pre_snapshot": pre,
        }
        start_receipt["receipt_sha256"] = canonical_hash(start_receipt)
        _write_new(start_path, start_receipt)
        if cache_job.exists():
            raise FileExistsError("F4 V2 cache job must be new")
        cache_job.mkdir(parents=True, exist_ok=False)
        child_environment = base.child_environment(
            args.expected_uuid, args.physical_index, cache_job
        )
        child_environment["CMF_GPU_LEASE_PATH"] = str(lease_path)
        child_environment["CMF_F4_GUARD_START_RECEIPT"] = str(start_path)
        launch = base.nvidia_snapshot()
        if not base.idle(base.selected(launch, args.physical_index, args.expected_uuid)):
            raise RuntimeError("GPU stopped being idle before F4 child launch")
        runner = Path(manifest["runner_script_path"])
        command = [
            str(ENV_PYTHON),
            str(runner),
            "--manifest",
            str(args.manifest.resolve()),
            "--job-id",
            args.job_id,
        ]
        stdout_file = stdout_path.open("xb")
        stderr_file = stderr_path.open("xb")
        try:
            child = subprocess.Popen(
                command,
                cwd=str(PROJECT),
                env=child_environment,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=True,
            )
            try:
                exit_code = child.wait(timeout=int(job["timeout_seconds"]))
            except subprocess.TimeoutExpired:
                timed_out = True
                cleanup_errors.extend(_terminate_group(child))
                exit_code = 124
            except KeyboardInterrupt:
                interrupted = "KeyboardInterrupt"
                cleanup_errors.extend(_terminate_group(child))
                exit_code = 130
        finally:
            stdout_file.close()
            stderr_file.close()
        cleanup_errors.extend(_terminate_group(child))
    except BaseException as exc:
        cleanup_errors.append({"type": type(exc).__name__, "message": str(exc)})
        cleanup_errors.extend(_terminate_group(child))
        if exit_code is None:
            exit_code = 96
    finally:
        try:
            post = base.nvidia_snapshot()
            if pre is not None:
                returned = _returned_to_baseline(
                    pre, post, args.physical_index, args.expected_uuid
                )
        except BaseException as exc:
            cleanup_errors.append(
                {"post_snapshot_error": type(exc).__name__, "message": str(exc)}
            )
        if cache_job.exists():
            try:
                shutil.rmtree(cache_job)
                cache_removed = True
            except BaseException as exc:
                cleanup_errors.append(
                    {"cache_cleanup_error": type(exc).__name__, "message": str(exc)}
                )
        else:
            cache_removed = True
        try:
            fcntl.flock(lease_handle.fileno(), fcntl.LOCK_UN)
            lease_released = True
        except BaseException as exc:
            cleanup_errors.append(
                {"lease_release_error": type(exc).__name__, "message": str(exc)}
            )
        lease_handle.close()

    terminal = {
        "schema_version": "cmf_f4_development_root_v2_guard_terminal_v1",
        "run_id": manifest["run_id"],
        "job_id": args.job_id,
        "family": "F4",
        "manifest_sha256": manifest["manifest_sha256"],
        "physical_gpu_index": args.physical_index,
        "gpu_uuid": args.expected_uuid,
        "guard_pid": os.getpid(),
        "child_pid": child.pid if child is not None else None,
        "child_process_group": child.pid if child is not None else None,
        "child_exit_code": exit_code,
        "timed_out": timed_out,
        "interrupted": interrupted,
        "pre_snapshot": pre,
        "launch_snapshot": launch,
        "post_snapshot": post,
        "cache_removed": cache_removed,
        "lease_released": lease_released,
        "cleanup_errors": cleanup_errors,
        "gpu_returned_to_idle_baseline": returned,
        "task_owned_cleanup_pass": not cleanup_errors
        and cache_removed
        and lease_released
        and returned,
        "output_exists": output.exists(),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "elapsed_seconds": time.time() - started,
    }
    terminal["status"] = (
        "completed"
        if exit_code == 0 and terminal["task_owned_cleanup_pass"]
        else "failed_or_blocked_with_cleanup_evidence"
    )
    terminal["receipt_sha256"] = canonical_hash(terminal)
    _write_new(terminal_path, terminal)
    post_validation_error = None
    post_validation = None
    try:
        post_validation = load_and_validate_manifest_job(
            args.manifest,
            args.job_id,
            phase=POST_CHILD,
            require_execution_authorized=True,
            environment=child_environment or {},
        )
    except BaseException as exc:
        post_validation_error = {"type": type(exc).__name__, "message": str(exc)}
    post_receipt = {
        "schema_version": "cmf_f4_development_root_v2_post_child_validation_v1",
        "manifest_sha256": manifest["manifest_sha256"],
        "job_id": args.job_id,
        "validation_pass": post_validation_error is None,
        "validation_phase": None if post_validation is None else post_validation["phase"],
        "error": post_validation_error,
    }
    post_receipt["receipt_sha256"] = canonical_hash(post_receipt)
    _write_new(guard_dir / f"{args.job_id}.post_child_validation.json", post_receipt)
    return 0 if terminal["status"] == "completed" and post_validation_error is None else int(exit_code or 1)


if __name__ == "__main__":
    raise SystemExit(main())
