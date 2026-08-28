"""Atomic fresh-idle gate and ownership-scoped cleanup wrapper for GPU probes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


ALLOWED_PHYSICAL_GPU_INDICES = tuple(range(8))
CHILD_ENVIRONMENT_VERSION = "robotwin_workspace_cuda12_1_v1"


def build_child_environment(base_environment, expected_uuid, workspace=None):
    workspace = Path(workspace) if workspace is not None else Path(__file__).resolve().parents[4]
    robotwin_root = workspace / "project/RoboTwin"
    robotwin_env = workspace / "env"
    robotwin_cuda = workspace / "tools/cuda-12.1"
    miniforge = workspace / "tools/miniforge3"
    environment = dict(base_environment)
    environment.pop("LD_LIBRARY_PATH", None)
    clean_path = [
        item for item in environment.get("PATH", "").split(":")
        if item and not item.startswith("/share/apps/cuda/") and not item.startswith("/usr/local/cuda")
    ]
    environment.update({
        "ROBOTWIN_WORKSPACE": str(workspace),
        "ROBOTWIN_ROOT": str(robotwin_root),
        "ROBOTWIN_ENV": str(robotwin_env),
        "ROBOTWIN_CUDA": str(robotwin_cuda),
        "CUDA_HOME": str(robotwin_cuda),
        "TORCH_CUDA_ARCH_LIST": "8.6",
        "CONDARC": str(workspace / "config/condarc"),
        "CONDA_PKGS_DIRS": str(workspace / "cache/conda/pkgs"),
        "CONDA_ENVS_PATH": str(workspace / "envs"),
        "PIP_CONFIG_FILE": str(workspace / "config/pip.conf"),
        "PIP_CACHE_DIR": str(workspace / "cache/pip"),
        "TORCH_HOME": str(workspace / "cache/torch"),
        "HF_HOME": str(workspace / "cache/huggingface"),
        "HUGGINGFACE_HUB_CACHE": str(workspace / "cache/huggingface/hub"),
        "XDG_CACHE_HOME": str(workspace / "cache/xdg"),
        "MPLCONFIGDIR": str(workspace / "cache/matplotlib"),
        "TMPDIR": str(workspace / "tmp"),
        "CUDA_VISIBLE_DEVICES": expected_uuid,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PATH": ":".join([str(robotwin_env / "bin"), str(robotwin_cuda / "bin"), str(miniforge / "bin"), *clean_path]),
    })
    return environment


def _gpu_rows():
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,uuid,memory.used,utilization.gpu,pstate", "--format=csv,noheader,nounits"],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = {}
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        index, uuid, memory, utilization, pstate = [item.strip() for item in line.split(",")]
        rows[int(index)] = {
            "physical_index": int(index),
            "uuid": uuid,
            "memory_used_mib": int(memory),
            "utilization_percent": int(utilization),
            "pstate": pstate,
        }
    return rows


def _compute_processes():
    result = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,used_memory", "--format=csv,noheader,nounits"],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = []
    for line in result.stdout.splitlines():
        parts = [item.strip() for item in line.split(",")]
        if len(parts) != 3 or not parts[1].isdigit():
            continue
        rows.append({"gpu_uuid": parts[0], "pid": int(parts[1]), "used_memory_mib": int(parts[2])})
    return rows


def snapshot(index, expected_uuid):
    row = _gpu_rows()[index]
    if row["uuid"] != expected_uuid:
        raise RuntimeError(f"GPU UUID mismatch for physical index {index}: {row['uuid']} != {expected_uuid}")
    row["compute_processes"] = [item for item in _compute_processes() if item["gpu_uuid"] == expected_uuid]
    row["captured_at"] = datetime.now(timezone.utc).astimezone().isoformat()
    return row


def is_idle(row):
    return (
        row["memory_used_mib"] <= 100
        and row["utilization_percent"] <= 1
        and row["pstate"] == "P8"
        and not row["compute_processes"]
    )


def pids_in_process_group(pgid):
    result = subprocess.run(["ps", "-eo", "pid=,pgid="], check=True, capture_output=True, text=True)
    pids = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and int(parts[1]) == pgid:
            pids.append(int(parts[0]))
    return pids


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_post_release(pre, post):
    baseline_limit = max(100, int(pre["memory_used_mib"]) + 50)
    pre_pids = {int(item["pid"]) for item in pre.get("compute_processes", [])}
    new_processes = [item for item in post.get("compute_processes", []) if int(item["pid"]) not in pre_pids]
    checks = {
        "memory_returned_to_baseline": int(post["memory_used_mib"]) <= baseline_limit,
        "utilization_idle": int(post["utilization_percent"]) <= 1,
        "no_compute_process": not post.get("compute_processes"),
    }
    return {
        "verified": all(checks.values()),
        "checks": checks,
        "baseline_memory_limit_mib": baseline_limit,
        "new_compute_processes": new_processes,
        "pstate_observed": post.get("pstate"),
        "pstate_note": "recorded but not a hard postcheck because driver cooldown may lag after process release",
    }


def update_child_receipt(output_dir, guard_path, post, orphan_pids, post_release, post_error=None):
    child_path = output_dir / "receipt.json"
    if not child_path.exists():
        return False
    payload = json.loads(child_path.read_text(encoding="utf-8"))
    payload["gpu_postcheck"] = post
    payload["gpu_postcheck_error"] = post_error
    payload["gpu_postcheck_release"] = post_release
    scene_orphan_count = int(payload.get("orphan_process_count") or 0)
    payload["scene_orphan_process_count"] = scene_orphan_count
    payload["guard_process_group_orphan_count"] = len(orphan_pids)
    payload["orphan_process_count"] = scene_orphan_count + len(orphan_pids)
    payload["task_owned_orphan_pids"] = orphan_pids
    payload["guard_receipt"] = str(guard_path)
    if payload["orphan_process_count"] or post_error is not None or post_release.get("verified") is not True or (payload.get("scene_created") and not payload.get("scene_cleanup_succeeded")):
        payload["status"] = "failed_cleanup_uncertain"
    write_json(child_path, payload)
    return True


def classify_terminal_status(*, child_started, receipt_updated, receipt_update_error, cleanup_uncertain, timed_out, child_exit):
    """Fail closed when a launched child leaves no valid terminal receipt."""

    if cleanup_uncertain:
        return "failed_cleanup_uncertain", 90
    if child_started and receipt_update_error is not None:
        return "failed_invalid_child_receipt", 92
    if child_started and not receipt_updated:
        return "failed_missing_child_receipt", 91
    if timed_out:
        return "timeout", 124
    if child_exit not in (None, 0):
        return "completed_child_failed", int(child_exit)
    return "completed", 0


def main():
    parser = argparse.ArgumentParser()
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
    if args.guard_receipt.exists() or args.output_dir.exists():
        raise FileExistsError("guard receipt and child output must use a new immutable namespace")

    started = time.time()
    guard = {
        "schema_version": "cmf_gpu_guard_v2",
        "purpose": "nonformal_feasibility",
        "formal_data": False,
        "stage0_data": False,
        "physical_gpu_index": args.physical_index,
        "expected_gpu_uuid": args.expected_uuid,
        "guard_pid": os.getpid(),
        "timeout_seconds": args.timeout_seconds,
        "command": command,
        "status": "starting",
    }
    child = None
    child_exit = None
    timed_out = False
    orphan_pids = []
    launch_error = None
    try:
        pre = snapshot(args.physical_index, args.expected_uuid)
    except BaseException as exc:
        guard.update({
            "status": "failed_gpu_precheck",
            "precheck_error": {"type": type(exc).__name__, "message": str(exc)},
            "elapsed_seconds": time.time() - started,
        })
        write_json(args.guard_receipt, guard)
        return 95
    guard["precheck"] = pre
    if not is_idle(pre):
        guard.update({"status": "blocked_precheck_not_idle", "elapsed_seconds": time.time() - started})
        write_json(args.guard_receipt, guard)
        return 42

    guard["status"] = "precheck_passed"
    write_json(args.guard_receipt, guard)

    stdout_path = args.guard_receipt.with_suffix(".stdout.log")
    stderr_path = args.guard_receipt.with_suffix(".stderr.log")
    environment = build_child_environment(os.environ, args.expected_uuid)
    environment["CMF_GPU_GUARD_RECEIPT"] = str(args.guard_receipt.resolve())
    environment["CMF_GPU_GUARD_PHYSICAL_INDEX"] = str(args.physical_index)
    guard["child_environment_contract"] = {
        "version": CHILD_ENVIRONMENT_VERSION,
        "ld_library_path": "unset",
        "cuda_home": environment["CUDA_HOME"],
        "path_prefix": environment["PATH"].split(":")[:3],
    }
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            child = subprocess.Popen(command, env=environment, stdout=stdout, stderr=stderr, start_new_session=True)
            guard.update({"status": "running", "child_pid": child.pid, "child_pgid": child.pid, "stdout": str(stdout_path), "stderr": str(stderr_path)})
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
        post_release = {"verified": False, "checks": {}, "new_compute_processes": [], "reason": "postcheck_snapshot_failed"}
    receipt_updated = False
    receipt_update_error = None
    try:
        receipt_updated = update_child_receipt(args.output_dir, args.guard_receipt, post, orphan_pids, post_release, post_error)
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
    guard.update({
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
    })
    write_json(args.guard_receipt, guard)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
