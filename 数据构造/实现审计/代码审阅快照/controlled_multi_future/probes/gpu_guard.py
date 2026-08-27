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


def update_child_receipt(output_dir, guard_path, post, orphan_pids):
    child_path = output_dir / "receipt.json"
    if not child_path.exists():
        return False
    payload = json.loads(child_path.read_text(encoding="utf-8"))
    payload["gpu_postcheck"] = post
    payload["orphan_process_count"] = len(orphan_pids)
    payload["task_owned_orphan_pids"] = orphan_pids
    payload["guard_receipt"] = str(guard_path)
    if orphan_pids or (payload.get("scene_created") and not payload.get("scene_cleanup_succeeded")):
        payload["status"] = "failed_cleanup_uncertain"
    write_json(child_path, payload)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--physical-index", type=int, choices=tuple(range(8)), required=True)
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
        "schema_version": "cmf_gpu_guard_v1",
        "purpose": "nonformal_feasibility",
        "formal_data": False,
        "stage0_data": False,
        "physical_gpu_index": args.physical_index,
        "expected_gpu_uuid": args.expected_uuid,
        "timeout_seconds": args.timeout_seconds,
        "command": command,
        "status": "starting",
    }
    child = None
    child_exit = None
    timed_out = False
    orphan_pids = []
    pre = snapshot(args.physical_index, args.expected_uuid)
    guard["precheck"] = pre
    if not is_idle(pre):
        guard.update({"status": "blocked_precheck_not_idle", "elapsed_seconds": time.time() - started})
        write_json(args.guard_receipt, guard)
        return 42

    stdout_path = args.guard_receipt.with_suffix(".stdout.log")
    stderr_path = args.guard_receipt.with_suffix(".stderr.log")
    environment = os.environ.copy()
    environment["CUDA_VISIBLE_DEVICES"] = args.expected_uuid
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
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
    finally:
        if child is not None:
            orphan_pids = pids_in_process_group(child.pid)
            if orphan_pids:
                os.killpg(child.pid, signal.SIGKILL)
                time.sleep(1)
                orphan_pids = pids_in_process_group(child.pid)

    time.sleep(1)
    post = snapshot(args.physical_index, args.expected_uuid)
    receipt_updated = update_child_receipt(args.output_dir, args.guard_receipt, post, orphan_pids)
    cleanup_uncertain = bool(orphan_pids)
    if receipt_updated:
        child_receipt = json.loads((args.output_dir / "receipt.json").read_text(encoding="utf-8"))
        cleanup_uncertain = cleanup_uncertain or child_receipt.get("status") == "failed_cleanup_uncertain"
    guard.update({
        "status": "failed_cleanup_uncertain" if cleanup_uncertain else ("timeout" if timed_out else "completed"),
        "child_exit_code": child_exit,
        "timed_out": timed_out,
        "postcheck": post,
        "task_owned_orphan_pids": orphan_pids,
        "orphan_process_count": len(orphan_pids),
        "child_receipt_updated": receipt_updated,
        "elapsed_seconds": time.time() - started,
    })
    write_json(args.guard_receipt, guard)
    if cleanup_uncertain:
        return 90
    if timed_out:
        return 124
    return int(child_exit or 0)


if __name__ == "__main__":
    raise SystemExit(main())
