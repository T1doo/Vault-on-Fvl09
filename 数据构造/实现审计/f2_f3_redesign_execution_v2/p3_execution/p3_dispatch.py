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
COUNTERS = ("fresh_scenes", "action_scenes", "collection_attempts", "solver_problems", "gpu_lease_seconds")


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


def _normalise_job(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize every manifest field before any reservation/launch."""
    job = dict(raw)
    if not isinstance(job.get("job_id"), str) or not job["job_id"] or not isinstance(job.get("root_id"), str) or not job["root_id"]:
        raise ValueError("job_id and root_id are required")
    cells = job.get("cell_keys")
    if cells is None and job.get("cell_key") is not None:
        cells = [job["cell_key"]]
    elif isinstance(cells, str):
        cells = [item for item in cells.split(",") if item]
    elif isinstance(cells, (tuple, list)):
        cells = [str(item) for item in cells if str(item)]
    else:
        raise ValueError("job must provide cell_keys as a non-empty list or comma-separated string")
    if not cells or len(set(cells)) != len(cells):
        raise ValueError("job cell_keys are empty or duplicated")
    reservation = job.get("reservation")
    if not isinstance(reservation, dict) or any(isinstance(reservation.get(key), bool) or not isinstance(reservation.get(key), int) or reservation[key] < 0 for key in COUNTERS):
        raise ValueError("job reservation must contain finite non-negative counters")
    timeout = job.get("timeout_seconds")
    if timeout is not None and (isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0):
        raise ValueError("timeout_seconds must be a positive integer")
    if job.get("existing_root") is not None and not Path(str(job["existing_root"])).is_absolute():
        raise ValueError("existing_root must be an absolute workspace path")
    job["cell_keys"] = cells
    job["cell_key"] = ",".join(cells)
    return job


def _actual_usage(job: dict[str, Any], output: Path, lease_seconds: int) -> dict[str, int]:
    cell_receipts = []
    meters = []
    if output.exists():
        for path in output.rglob("cell_receipt.json"):
            cell_receipts.append(json.loads(path.read_text(encoding="utf-8")))
        for path in output.rglob("execution_meter.json"):
            meters.append(json.loads(path.read_text(encoding="utf-8")))
    launched = True
    captured = sum(1 for receipt in cell_receipts if receipt.get("t0_capture"))
    captured = max(captured, sum(1 for meter in meters if any(event.get("stage") == "t0_captured" for event in meter.get("events", []))))
    acted = sum(1 for receipt in cell_receipts if receipt.get("action_segment_count", 0) > 0)
    acted = max(acted, sum(1 for meter in meters if any(event.get("stage") == "action_started" for event in meter.get("events", []))))
    solver = int(sum(receipt.get("solver_problem_count", 0) for receipt in cell_receipts))
    solver = max(solver, int(sum(max((int(event.get("solver_problem_count", 0)) for event in meter.get("events", []) if event.get("solver_problem_count") is not None), default=0) for meter in meters)))
    return {
        "fresh_scenes": int(captured),
        "action_scenes": int(acted),
        "collection_attempts": max(1, len(cell_receipts), len(meters)) if launched else 0,
        "solver_problems": solver,
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
    command = [str(PYTHON), "-m", "controlled_multi_future.redesign_f2_f3_v2.collector_v2", "--output", str(output), "--root-id", str(job["root_id"]), "--cell-keys", ",".join(job["cell_keys"])]
    if job.get("existing_root"):
        command.extend(["--existing-root", str(job["existing_root"])])
    environment = child_environment(gpu_uuid)
    environment.update({"PYTHONPATH": str(PROJECT), "ROBOTWIN_ROOT": str(PROJECT), "ROBOTWIN_WORKSPACE": str(ROOT / "Robotwin2"), "CMF_GPU_GUARD_PHYSICAL_INDEX": str(physical_index), "CMF_BOUND_GPU_UUID": gpu_uuid})
    log_dir = BASE / "worker_logs"; log_dir.mkdir(parents=True, exist_ok=True); log_path = log_dir / f"{job_id}.attempt{attempt}.stdout.log"
    cell_label = ",".join(job["cell_keys"])
    started = time.monotonic()
    start_wall = time.time()
    state["jobs"][job_id] = {"status": "STARTING", "pid": None, "pgid": None, "root_id": job["root_id"], "cell_key": cell_label, "physical_gpu_index": physical_index, "gpu_uuid": gpu_uuid, "reservation": reservation, "pre_snapshot": pre, "guarded_card": guarded, "command": command, "worker_log": str(log_path), "started_wall_time": start_wall, "started_monotonic": started, "process_tree_start": []}
    _write_state(state)
    process = subprocess.Popen(command, cwd=PROJECT, env=environment, start_new_session=True, stdout=log_path.open("w", encoding="utf-8"), stderr=subprocess.STDOUT, text=True)
    pid = int(process.pid); pgid = os.getpgid(pid)
    state["running_by_job_id"][job_id] = {"pid": pid, "pgid": pgid, "root_id": job["root_id"], "physical_gpu_index": physical_index, "gpu_uuid": gpu_uuid, "started_monotonic": started, "started_wall_time": start_wall}
    state["jobs"][job_id].update({"status": "RUNNING", "pid": pid, "pgid": pgid, "process_tree_start": _process_tree(pid)})
    _write_state(state)
    timeout_seconds = int(job.get("timeout_seconds", 1200 if len(job["cell_keys"]) == 1 else 2400))
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
    end_record = {"schema_version": "cmf_f2_f3_v2_p3_end_evidence_v1", "job_id": job_id, "attempt": attempt, "root_id": job["root_id"], "cell_key": cell_label, "physical_gpu_index": physical_index, "gpu_uuid": gpu_uuid, "command": command, "pid": pid, "pgid": pgid, "return_code": process_return, "timeout": timed_out, "pre_snapshot": pre, "guarded_card": guarded, "post_snapshot": post, "process_tree_start": state["jobs"][job_id]["process_tree_start"], "process_tree_after": tree_after, "owned_cleanup_pass": owned_cleanup, "device_idle_observed": idle_observed, "actual_usage": actual, "reservation": reservation, "worker_log": str(log_path), "overrun_before_settlement": overrun, "settlement_status": "PENDING", "output": str(output)}
    end_record["end_evidence_sha256"] = canonical_sha256(end_record)
    atomic_write_json(BASE / f"{job_id}.attempt{attempt}.end_evidence.json", end_record)
    settlement_error = None
    event = None
    try:
        event = ledger.settle(job_id, reservation, actual, idempotency_key=f"settle:{job_id}:attempt:{attempt}")
    except BaseException as exc:
        settlement_error = {"type": type(exc).__name__, "message": str(exc)}
    if settlement_error is not None:
        end_record["settlement_status"] = "UNKNOWN"
        receipt_status = "UNKNOWN_CONSUMPTION"
    else:
        end_record["settlement_status"] = event["event_type"]
        receipt_status = "PASS" if process_return == 0 and owned_cleanup and not overrun else "FAILED"
    receipt = {**end_record, "schema_version": "cmf_f2_f3_v2_p3_job_receipt_v1", "budget_event_sha256": event["event_sha256"] if event else None, "settlement_error": settlement_error, "status": receipt_status}
    atomic_write_json(BASE / f"{job_id}.json", receipt)
    state["running_by_job_id"].pop(job_id, None)
    state.setdefault("attempt_history", {}).setdefault(job_id, []).append(receipt)
    state["jobs"][job_id] = receipt
    if settlement_error is None:
        for key in ("fresh_scenes", "action_scenes", "collection_attempts", "solver_problems", "gpu_lease_seconds"):
            state["progress"][key] += actual[key]
    if receipt["status"] == "UNKNOWN_CONSUMPTION":
        state["status"] = "BUDGET_UNKNOWN_CONSUMPTION_STOPPED"
        state.setdefault("unknown_jobs", {})[job_id] = {"receipt": str(BASE / f"{job_id}.json"), "reservation_held": True, "settlement_error": settlement_error}
    elif receipt["status"] != "PASS":
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
    jobs = [_normalise_job(job) for job in manifest["jobs"] if args.only_job_id is None or job.get("job_id") == args.only_job_id]
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
    wave_name = str(manifest.get("wave_name", "FIRST_TWO"))
    if wave_name == "F3_A_FIRST" or (args.only_job_id and jobs[0].get("root_id") == "F3-A-v2" and jobs[0].get("cell_keys") == ["VHVH:r_pc"]):
        state["progress"]["f3_first"] = "PASSED" if wave_pass else "FAILED"
        if wave_pass: state["status"] = "READY_F3_REMAINING"
    elif wave_name == "F3_A_REMAINING_FIVE":
        state["progress"]["f3_remaining"] = "PASSED" if wave_pass else "FAILED"
        if wave_pass:
            state["progress"]["completed_cells"] = int(state["progress"].get("completed_cells", 0)) + sum(int(item.get("actual_usage", {}).get("fresh_scenes", 0)) for item in results)
        if wave_pass: state["status"] = "READY_F3_B_FIRST"
    else:
        state["progress"]["first_two"] = "PASSED" if wave_pass else "FAILED"
        if wave_pass: state["status"] = "READY_REMAINING_22"
    _write_state(state)
    attempt_label = results[-1].get("attempt", "unknown") if results else "none"
    receipt_name = f"P3_WAVE_{wave_name}_{jobs[0]['job_id']}_attempt{attempt_label}.json"
    atomic_write_json(BASE / receipt_name, {"schema_version": "cmf_f2_f3_v2_p3_wave_receipt_v2", "wave_name": wave_name, "jobs": results, "selected_job_id": args.only_job_id, "manifest": args.manifest, "pass": wave_pass})
    return 0 if wave_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
