"""Finite four-root parallel coordinator for F2/F3 HD saved-state replay."""

from __future__ import annotations

import argparse
import json
import math
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .canonical import atomic_write_json, canonical_sha256, sha256_file
from .gpu import assign_ready_jobs, child_environment, guard_card, live_snapshot


ROOTS = {
    "F2-A": "/nfs_share/lijunhui/Robotwin2/datasets/f2_f3_redesign_v1/stage_C_F2A_resume_pilot_1788855821/root_receipt.json",
    "F2-B": "/nfs_share/lijunhui/Robotwin2/datasets/f2_f3_redesign_v1/stage_C_F2B_pilot_1788856533/root_receipt.json",
    "F3-A": "/nfs_share/lijunhui/Robotwin2/datasets/f2_f3_redesign_v1/stage_C_F3A_pilot_1788852570/root_receipt.json",
    "F3-B": "/nfs_share/lijunhui/Robotwin2/datasets/f2_f3_redesign_v1/stage_C_F3B_resume_pilot_1788855368/root_receipt.json",
}


def _owned_processes(pgid: int) -> list[dict[str, Any]]:
    completed = subprocess.run(["ps", "-eo", "pid=,ppid=,pgid=,stat=,comm="], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    result = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 4)
        if len(parts) == 5 and int(parts[2]) == pgid:
            result.append({"pid": int(parts[0]), "ppid": int(parts[1]), "pgid": int(parts[2]), "stat": parts[3], "command": parts[4]})
    return result


def run(audit_dir: Path, timeout_seconds: int) -> dict[str, Any]:
    audit_dir.mkdir(parents=True, exist_ok=False)
    ready = [{"job_id": f"hd_{root.lower().replace('-', '_')}", "root_id": root} for root in ROOTS]
    wave = live_snapshot()
    assignment = assign_ready_jobs(ready, wave)
    if len(assignment["assignments"]) != 4:
        raise RuntimeError("four independently fresh idle GPUs are required for this finite parallel wave")
    plan = {
        "schema_version": "cmf_f2_f3_hd_parallel_display_plan_v1",
        "authorized_by_user": True,
        "scope": "saved-state HD display of accepted F2/F3 traces; no new rollout",
        "allowed_physical_gpu_indices": list(range(8)),
        "max_concurrent_gpu_jobs": 4,
        "one_root_one_gpu": True,
        "root_receipts": {root: {"path": path, "sha256": sha256_file(Path(path))} for root, path in ROOTS.items()},
        "assignments": assignment["assignments"],
        "wave_snapshot": wave,
        "caps": {"root_jobs": 4, "display_scenes": 24, "published_videos": 48, "gpu_lease_seconds": 28800, "production_action_scenes": 0, "collection_attempts": 0},
        "no_automatic_retry": True,
    }
    plan["receipt_sha256"] = canonical_sha256(plan)
    atomic_write_json(audit_dir / "HD_PARALLEL_PLAN.json", plan)
    running: dict[str, dict[str, Any]] = {}
    for selected in assignment["assignments"]:
        root = selected["root_id"]
        launch = live_snapshot()
        card = guard_card(launch, selected["physical_gpu_index"], selected["gpu_uuid"])
        output = audit_dir / "jobs" / root
        command = [sys.executable, "-m", "controlled_multi_future.redesign_f2_f3_v1.hd_saved_state_worker", "--root-receipt", ROOTS[root], "--output", str(output)]
        env = child_environment(selected["gpu_uuid"])
        env["CMF_GPU_GUARD_PHYSICAL_INDEX"] = str(selected["physical_gpu_index"])
        started = time.monotonic()
        process = subprocess.Popen(command, cwd="/nfs_share/lijunhui/Robotwin2/project/RoboTwin", env=env, start_new_session=True)
        checkpoint = {
            "schema_version": "cmf_f2_f3_hd_dispatch_checkpoint_v1",
            "root_id": root,
            "pid": process.pid,
            "ppid": os.getpid(),
            "pgid": process.pid,
            "started_monotonic": started,
            "started_wall_time": time.time(),
            "physical_gpu_index": selected["physical_gpu_index"],
            "gpu_uuid": selected["gpu_uuid"],
            "launch_snapshot": launch,
            "guard_card": card,
            "command": command,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(audit_dir / f"{root}_dispatch_checkpoint.json", checkpoint)
        running[root] = {"process": process, "started": started, "selected": selected, "checkpoint": checkpoint, "timed_out": False}
    deadline = time.monotonic() + timeout_seconds
    while any(item["process"].poll() is None for item in running.values()):
        if time.monotonic() >= deadline:
            for item in running.values():
                process = item["process"]
                if process.poll() is None:
                    item["timed_out"] = True
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            time.sleep(5)
            for item in running.values():
                process = item["process"]
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            break
        time.sleep(2)
    jobs = []
    for root, item in running.items():
        process = item["process"]
        try:
            return_code = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            return_code = None
        elapsed = time.monotonic() - item["started"]
        owned = _owned_processes(process.pid)
        receipt_path = audit_dir / "jobs" / root / "root_render_receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else None
        jobs.append({
            "root_id": root,
            "pid": process.pid,
            "pgid": process.pid,
            "return_code": return_code,
            "timed_out": item["timed_out"],
            "elapsed_seconds": elapsed,
            "gpu_lease_seconds": math.ceil(elapsed),
            "physical_gpu_index": item["selected"]["physical_gpu_index"],
            "gpu_uuid": item["selected"]["gpu_uuid"],
            "owned_processes_after_wait": owned,
            "owned_cleanup_pass": not owned,
            "root_render_receipt": receipt,
            "root_render_receipt_sha256": sha256_file(receipt_path) if receipt_path.exists() else None,
        })
    post = live_snapshot()
    for job in jobs:
        card = next(value for value in post["gpus"] if value["physical_index"] == job["physical_gpu_index"])
        job["post_card"] = card
        job["device_idle_observed"] = bool(card["independently_fresh_idle"])
    result = {
        "schema_version": "cmf_f2_f3_hd_parallel_display_receipt_v1",
        "pass": all(job["return_code"] == 0 and not job["timed_out"] and job["owned_cleanup_pass"] and job["root_render_receipt"] and job["root_render_receipt"]["pass"] for job in jobs),
        "plan_sha256": plan["receipt_sha256"],
        "jobs": jobs,
        "root_job_count": len(jobs),
        "display_scene_count": sum((job["root_render_receipt"] or {}).get("display_scene_count", 0) for job in jobs),
        "published_video_count": sum((job["root_render_receipt"] or {}).get("published_video_count", 0) for job in jobs),
        "total_gpu_lease_seconds": sum(job["gpu_lease_seconds"] for job in jobs),
        "production_budget_delta": {"solver_problems": 0, "fresh_scenes": 0, "action_scenes": 0, "collection_attempts": 0},
        "post_snapshot": post,
    }
    result["receipt_sha256"] = canonical_sha256(result)
    atomic_write_json(audit_dir / "HD_PARALLEL_RECEIPT.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=7200)
    args = parser.parse_args()
    result = run(Path(args.audit_dir), args.timeout_seconds)
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
