"""Small single-coordinator dispatcher for the approved v2 first wave.

The coordinator stays CPU-only.  Each child is a fresh Python process bound to
one UUID-selected physical GPU; the child itself runs the existing v2 collector
and writes its private root output.  This module is intentionally finite and
does not dispatch beyond the jobs listed in ``P3_JOB_MANIFEST.json``.
"""

from __future__ import annotations

import json
import math
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from controlled_multi_future.redesign_f2_f3_v2.canonical import atomic_write_json, canonical_sha256
from controlled_multi_future.redesign_f2_f3_v2.gpu import assign_ready_jobs, child_environment, guard_card, live_snapshot
from controlled_multi_future.redesign_f2_f3_v2.execution_ledger_v2 import ExecutionLedgerV2


ROOT = Path("/nfs_share/lijunhui")
PROJECT = ROOT / "Robotwin2/project/RoboTwin"
PYTHON = ROOT / "Robotwin2/env/bin/python"
BASE = ROOT / "Vault-on-Fvl09/数据构造/实现审计/f2_f3_redesign_execution_v2/p3_execution"
DATA = ROOT / "Robotwin2/datasets/f2_f3_observation_contract_repair_p3"


def _state_hash(value: dict[str, Any]) -> str:
    body = dict(value)
    body.pop("state_sha256", None)
    return canonical_sha256(body)


def _write_state(state: dict[str, Any]) -> None:
    state["state_sha256"] = _state_hash(state)
    atomic_write_json(BASE / "P3_STATE.json", state)


def _process_tree(pid: int) -> list[str]:
    try:
        result = subprocess.run(["ps", "-o", "pid=,ppid=,pgid=,stat=,cmd=", "--forest", "-g", str(pid)], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except OSError as exc:
        return [f"ps_error:{type(exc).__name__}:{exc}"]
    return [line.rstrip() for line in result.stdout.splitlines() if line.strip()]


def _actual_usage(job: dict[str, Any], output: Path, lease_seconds: int) -> dict[str, int]:
    cell_receipt = None
    for path in output.rglob("cell_receipt.json"):
        cell_receipt = json.loads(path.read_text(encoding="utf-8"))
        break
    launched = True
    captured = bool(cell_receipt and cell_receipt.get("t0_capture"))
    return {
        "fresh_scenes": 1 if captured else 0,
        "action_scenes": 1 if cell_receipt and cell_receipt.get("action_segment_count", 0) > 0 else 0,
        "collection_attempts": 1 if launched else 0,
        "solver_problems": int(cell_receipt.get("solver_problem_count", 0)) if cell_receipt else 0,
        "gpu_lease_seconds": int(lease_seconds),
    }


def _run_job(job: dict[str, Any], card: dict[str, Any], ledger: ExecutionLedgerV2, state: dict[str, Any]) -> dict[str, Any]:
    job_id = str(job["job_id"]); output = DATA / job_id
    if output.exists():
        raise RuntimeError(f"job output already exists: {output}")
    output.mkdir(parents=True)
    reservation = {key: int(value) for key, value in job["reservation"].items()}
    ledger.reserve(job_id, reservation, idempotency_key=f"reserve:{job_id}")
    pre = live_snapshot()
    guarded = guard_card(pre, int(card["physical_index"]), expected_uuid=str(card["gpu_uuid"]))
    command = [str(PYTHON), "-m", "controlled_multi_future.redesign_f2_f3_v2.collector_v2", "--output", str(output), "--root-id", str(job["root_id"]), "--cell-keys", str(job["cell_key"])]
    environment = child_environment(str(card["gpu_uuid"]))
    environment.update({"PYTHONPATH": str(PROJECT), "ROBOTWIN_ROOT": str(PROJECT), "ROBOTWIN_WORKSPACE": str(ROOT / "Robotwin2"), "CMF_GPU_GUARD_PHYSICAL_INDEX": str(card["physical_index"]), "CMF_BOUND_GPU_UUID": str(card["gpu_uuid"])})
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=PROJECT, env=environment, start_new_session=True, stdout=(output / "worker.stdout.log").open("w", encoding="utf-8"), stderr=subprocess.STDOUT, text=True)
    pid = int(process.pid); pgid = os.getpgid(pid)
    state["running_by_job_id"][job_id] = {"pid": pid, "pgid": pgid, "root_id": job["root_id"], "physical_gpu_index": card["physical_index"], "gpu_uuid": card["gpu_uuid"], "started_monotonic": started}
    state["jobs"][job_id] = {"status": "RUNNING", "pid": pid, "pgid": pgid, "root_id": job["root_id"], "cell_key": job["cell_key"], "physical_gpu_index": card["physical_index"], "gpu_uuid": card["gpu_uuid"], "reservation": reservation, "pre_snapshot": pre, "guarded_card": guarded, "command": command, "process_tree_start": _process_tree(pid)}
    _write_state(state)
    timeout_seconds = 900
    timed_out = False
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=20)
    ended = time.monotonic(); lease_seconds = max(0, int(math.ceil(ended - started)))
    process_return = int(process.returncode if process.returncode is not None else -999)
    tree_after = _process_tree(pid)
    owned_cleanup = not tree_after or not any(str(pid) in line.split()[:1] for line in tree_after)
    try:
        post = live_snapshot()
        post_card = {item["physical_index"]: item for item in post["gpus"]}.get(int(card["physical_index"]))
        idle_observed = bool(post_card and post_card.get("independently_fresh_idle"))
    except BaseException as exc:
        post = {"error": {"type": type(exc).__name__, "message": str(exc)}}
        idle_observed = False
    actual = _actual_usage(job, output, lease_seconds)
    overrun = any(actual[key] > reservation[key] for key in reservation)
    event = ledger.settle(job_id, reservation, actual, idempotency_key=f"settle:{job_id}")
    receipt = {"schema_version": "cmf_f2_f3_v2_p3_job_receipt_v1", "job_id": job_id, "root_id": job["root_id"], "cell_key": job["cell_key"], "physical_gpu_index": card["physical_index"], "gpu_uuid": card["gpu_uuid"], "allowed_physical_gpu_indices": list(range(8)), "command": command, "pid": pid, "pgid": pgid, "return_code": process_return, "timeout": timed_out, "pre_snapshot": pre, "guarded_card": guarded, "post_snapshot": post, "process_tree_start": state["jobs"][job_id]["process_tree_start"], "process_tree_after": tree_after, "owned_cleanup_pass": owned_cleanup, "device_idle_observed": idle_observed, "actual_usage": actual, "reservation": reservation, "budget_event_sha256": event["event_sha256"], "status": "PASS" if process_return == 0 and owned_cleanup and not overrun else "FAILED", "output": str(output)}
    atomic_write_json(BASE / f"{job_id}.json", receipt)
    state["running_by_job_id"].pop(job_id, None)
    state["jobs"][job_id] = receipt
    for key in ("fresh_scenes", "action_scenes", "collection_attempts", "solver_problems", "gpu_lease_seconds"):
        state["progress"][key] += actual[key]
    if receipt["status"] != "PASS":
        state["status"] = "STOPPED_AFTER_FIRST_WAVE_FAILURE"
        state["stop_reason"] = "first-validation-job-failed-or-budget-overrun"
    _write_state(state)
    return receipt


def main() -> int:
    contract = json.loads((BASE / "P3_EXECUTION_CONTRACT.json").read_text(encoding="utf-8")); manifest = json.loads((BASE / "P3_JOB_MANIFEST.json").read_text(encoding="utf-8")); state = json.loads((BASE / "P3_STATE.json").read_text(encoding="utf-8")); ledger = ExecutionLedgerV2(BASE / "execution_ledger.jsonl", contract_sha256=contract["contract_sha256"], task_id=contract["task_id"], caps=contract["budget_caps"])
    if state.get("status") != "READY_FIRST_TWO":
        raise RuntimeError(f"P3 dispatcher expected READY_FIRST_TWO, got {state.get('status')}")
    snapshot = live_snapshot(); assignment = assign_ready_jobs(manifest["jobs"], snapshot)
    if len(assignment["assignments"]) != len(manifest["jobs"]):
        raise RuntimeError("not all first-wave jobs received a fresh idle GPU")
    results = []
    for job in manifest["jobs"]:
        selected = next(item for item in assignment["assignments"] if item["job_id"] == job["job_id"])
        results.append(_run_job(job, selected, ledger, state))
        if results[-1]["status"] != "PASS":
            break
    state["progress"]["first_two"] = "PASSED" if len(results) == len(manifest["jobs"]) and all(item["status"] == "PASS" for item in results) else "FAILED"
    if state["progress"]["first_two"] == "PASSED": state["status"] = "READY_REMAINING_22"
    _write_state(state)
    atomic_write_json(BASE / "P3_FIRST_WAVE_RECEIPT.json", {"schema_version": "cmf_f2_f3_v2_p3_first_wave_receipt_v1", "jobs": results, "pass": state["progress"]["first_two"] == "PASSED"})
    return 0 if state["progress"]["first_two"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
