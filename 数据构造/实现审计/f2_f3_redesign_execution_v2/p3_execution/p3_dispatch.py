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
import argparse
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
    cell_receipts = []
    if output.exists():
        for path in output.rglob("cell_receipt.json"):
            cell_receipts.append(json.loads(path.read_text(encoding="utf-8")))
    launched = True
    captured = sum(1 for receipt in cell_receipts if receipt.get("t0_capture"))
    acted = sum(1 for receipt in cell_receipts if receipt.get("action_segment_count", 0) > 0)
    return {
        "fresh_scenes": int(captured),
        "action_scenes": int(acted),
        "collection_attempts": max(1, len(cell_receipts)) if launched else 0,
        "solver_problems": int(sum(receipt.get("solver_problem_count", 0) for receipt in cell_receipts)),
        "gpu_lease_seconds": int(lease_seconds),
    }


def _run_job(job: dict[str, Any], card: dict[str, Any], ledger: ExecutionLedgerV2, state: dict[str, Any]) -> dict[str, Any]:
    job_id = str(job["job_id"])
    base_output = DATA / job_id
    prior_outputs = sorted(DATA.glob(f"{job_id}.retry*"))
    if base_output.exists() and any(base_output.iterdir()):
        output = DATA / f"{job_id}.retry{len(prior_outputs) + 1}"
        attempt = len(prior_outputs) + 1
    else:
        output = base_output
        attempt = 0
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"job attempt output already exists and is non-empty: {output}")
    physical_index = int(card.get("physical_index", card.get("physical_gpu_index")))
    gpu_uuid = str(card.get("gpu_uuid"))
    reservation = {key: int(value) for key, value in job["reservation"].items()}
    ledger.reserve(job_id, reservation, idempotency_key=f"reserve:{job_id}:attempt:{attempt}")
    pre = live_snapshot()
    guarded = guard_card(pre, physical_index, expected_uuid=gpu_uuid)
    command = [str(PYTHON), "-m", "controlled_multi_future.redesign_f2_f3_v2.collector_v2", "--output", str(output), "--root-id", str(job["root_id"]), "--cell-keys", str(job["cell_keys"] if job.get("cell_keys") else job["cell_key"])]
    if job.get("existing_root"):
        command.extend(["--existing-root", str(job["existing_root"])])
    environment = child_environment(gpu_uuid)
    environment.update({"PYTHONPATH": str(PROJECT), "ROBOTWIN_ROOT": str(PROJECT), "ROBOTWIN_WORKSPACE": str(ROOT / "Robotwin2"), "CMF_GPU_GUARD_PHYSICAL_INDEX": str(physical_index), "CMF_BOUND_GPU_UUID": gpu_uuid})
    started = time.monotonic()
    log_dir = BASE / "worker_logs"; log_dir.mkdir(parents=True, exist_ok=True); log_path = log_dir / f"{job_id}.attempt{attempt}.stdout.log"
    process = subprocess.Popen(command, cwd=PROJECT, env=environment, start_new_session=True, stdout=log_path.open("w", encoding="utf-8"), stderr=subprocess.STDOUT, text=True)
    pid = int(process.pid); pgid = os.getpgid(pid)
    state["running_by_job_id"][job_id] = {"pid": pid, "pgid": pgid, "root_id": job["root_id"], "physical_gpu_index": physical_index, "gpu_uuid": gpu_uuid, "started_monotonic": started}
    state["jobs"][job_id] = {"status": "RUNNING", "pid": pid, "pgid": pgid, "root_id": job["root_id"], "cell_key": job["cell_key"], "physical_gpu_index": physical_index, "gpu_uuid": gpu_uuid, "reservation": reservation, "pre_snapshot": pre, "guarded_card": guarded, "command": command, "process_tree_start": _process_tree(pid)}
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
        post_card = {item["physical_index"]: item for item in post["gpus"]}.get(physical_index)
        idle_observed = bool(post_card and post_card.get("independently_fresh_idle"))
    except BaseException as exc:
        post = {"error": {"type": type(exc).__name__, "message": str(exc)}}
        idle_observed = False
    actual = _actual_usage(job, output, lease_seconds)
    overrun = any(actual[key] > reservation[key] for key in reservation)
    event = ledger.settle(job_id, reservation, actual, idempotency_key=f"settle:{job_id}:attempt:{attempt}")
    receipt = {"schema_version": "cmf_f2_f3_v2_p3_job_receipt_v1", "job_id": job_id, "attempt": attempt, "root_id": job["root_id"], "cell_key": job["cell_key"], "physical_gpu_index": physical_index, "gpu_uuid": gpu_uuid, "allowed_physical_gpu_indices": list(range(8)), "command": command, "pid": pid, "pgid": pgid, "return_code": process_return, "timeout": timed_out, "pre_snapshot": pre, "guarded_card": guarded, "post_snapshot": post, "process_tree_start": state["jobs"][job_id]["process_tree_start"], "process_tree_after": tree_after, "owned_cleanup_pass": owned_cleanup, "device_idle_observed": idle_observed, "actual_usage": actual, "reservation": reservation, "budget_event_sha256": event["event_sha256"], "worker_log": str(log_path), "status": "PASS" if process_return == 0 and owned_cleanup and not overrun else "FAILED", "output": str(output)}
    atomic_write_json(BASE / f"{job_id}.json", receipt)
    state["running_by_job_id"].pop(job_id, None)
    state.setdefault("attempt_history", {}).setdefault(job_id, []).append(receipt)
    state["jobs"][job_id] = receipt
    for key in ("fresh_scenes", "action_scenes", "collection_attempts", "solver_problems", "gpu_lease_seconds"):
        state["progress"][key] += actual[key]
    if receipt["status"] != "PASS":
        state["status"] = "STOPPED_AFTER_FIRST_WAVE_FAILURE"
        state["stop_reason"] = "first-validation-job-failed-or-budget-overrun"
    _write_state(state)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--only-job-id"); parser.add_argument("--manifest", default="P3_JOB_MANIFEST.json"); args = parser.parse_args()
    contract = json.loads((BASE / "P3_EXECUTION_CONTRACT.json").read_text(encoding="utf-8")); manifest = json.loads((BASE / args.manifest).read_text(encoding="utf-8")); state = json.loads((BASE / "P3_STATE.json").read_text(encoding="utf-8")); ledger = ExecutionLedgerV2(BASE / "execution_ledger.jsonl", contract_sha256=contract["contract_sha256"], task_id=contract["task_id"], caps=contract["budget_caps"], parent_contract_sha256=contract.get("parent_contract_sha256"), ancestor_contract_sha256s=contract.get("ancestor_contract_sha256s"))
    allowed_states = {"READY_FIRST_TWO", "READY_FIRST_TWO_RECOVERY", "READY_F3_FIRST", "READY_F3_REMAINING"}
    if state.get("status") not in allowed_states:
        raise RuntimeError(f"P3 dispatcher expected a first-wave-ready state, got {state.get('status')}")
    jobs = [job for job in manifest["jobs"] if args.only_job_id is None or job.get("job_id") == args.only_job_id]
    if not jobs:
        raise RuntimeError("requested job id is absent from the frozen first-wave manifest")
    snapshot = live_snapshot(); assignment = assign_ready_jobs(jobs, snapshot)
    if len(assignment["assignments"]) != len(jobs):
        raise RuntimeError("not all first-wave jobs received a fresh idle GPU")
    results = []
    for job in jobs:
        selected = next(item for item in assignment["assignments"] if item["job_id"] == job["job_id"])
        results.append(_run_job(job, selected, ledger, state))
        if results[-1]["status"] != "PASS":
            break
    wave_pass = len(results) == len(jobs) and all(item["status"] == "PASS" for item in results)
    if args.only_job_id:
        state["progress"]["f3_first"] = "PASSED" if wave_pass else "FAILED"
        if wave_pass: state["status"] = "READY_F3_REMAINING"
    else:
        state["progress"]["first_two"] = "PASSED" if wave_pass else "FAILED"
        if wave_pass: state["status"] = "READY_REMAINING_22"
    _write_state(state)
    receipt_name = "P3_F3_FIRST_RECEIPT.json" if args.only_job_id else ("P3_F3A_REMAINING_RECEIPT.json" if args.manifest != "P3_JOB_MANIFEST.json" else "P3_FIRST_WAVE_RECEIPT.json")
    atomic_write_json(BASE / receipt_name, {"schema_version": "cmf_f2_f3_v2_p3_first_wave_receipt_v1", "jobs": results, "selected_job_id": args.only_job_id, "pass": wave_pass})
    return 0 if wave_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
