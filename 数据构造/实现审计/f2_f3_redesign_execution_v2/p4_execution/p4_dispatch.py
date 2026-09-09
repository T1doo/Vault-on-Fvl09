"""Finite P4 dispatcher for bounded diagnostics and later collection waves.

The coordinator is CPU-only.  Each child receives one freshly guarded UUID,
and all counters settle in the independent P4 ledger before the next wave.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from controlled_multi_future.redesign_f2_f3_v2.canonical import atomic_write_json, canonical_sha256
from controlled_multi_future.redesign_f2_f3_v2.execution_ledger_v2 import ExecutionLedgerV2
from controlled_multi_future.redesign_f2_f3_v2.gpu import assign_ready_jobs, child_environment, guard_card, live_snapshot


ROOT = Path("/nfs_share/lijunhui")
PROJECT = ROOT / "Robotwin2/project/RoboTwin"
PYTHON = ROOT / "Robotwin2/env/bin/python"
BASE = ROOT / "Vault-on-Fvl09/数据构造/实现审计/f2_f3_redesign_execution_v2/p4_execution"
COUNTERS = ("fresh_scenes", "action_scenes", "collection_attempts", "solver_problems", "gpu_lease_seconds")


def _state_hash(value: dict[str, Any]) -> str:
    body = dict(value); body.pop("state_sha256", None)
    return canonical_sha256(body)


def _write_state(state: dict[str, Any]) -> None:
    state["state_sha256"] = _state_hash(state)
    atomic_write_json(BASE / "P4_STATE.json", state)


def _tree(pid: int) -> list[str]:
    try:
        result = subprocess.run(["ps", "-o", "pid=,ppid=,pgid=,stat=,cmd=", "--forest", "-g", str(pid)], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return [line.rstrip() for line in result.stdout.splitlines() if line.strip()]
    except OSError as exc:
        return [f"ps_error:{type(exc).__name__}:{exc}"]


def _normalise_job(raw: dict[str, Any]) -> dict[str, Any]:
    job = dict(raw)
    if not isinstance(job.get("job_id"), str) or not isinstance(job.get("root_id"), str):
        raise ValueError("P4 job requires job_id and root_id")
    if not isinstance(job.get("command"), list) or not job["command"] or any(not isinstance(item, str) for item in job["command"]):
        raise ValueError("P4 job command must be a non-empty string list")
    reservation = job.get("reservation")
    if not isinstance(reservation, dict) or any(isinstance(reservation.get(key), bool) or not isinstance(reservation.get(key), int) or reservation[key] < 0 for key in COUNTERS):
        raise ValueError("P4 job reservation is malformed")
    timeout = job.get("timeout_seconds")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise ValueError("P4 job timeout_seconds must be a positive integer")
    if reservation["gpu_lease_seconds"] > 0 and timeout > reservation["gpu_lease_seconds"]:
        raise ValueError("P4 job timeout_seconds cannot exceed its GPU lease reservation")
    cells = job.get("cell_keys")
    if isinstance(cells, str):
        cells = [item for item in cells.split(",") if item]
    if not isinstance(cells, list) or not cells or any(not isinstance(item, str) for item in cells):
        raise ValueError("P4 job cell_keys is malformed")
    job["cell_keys"] = cells
    return job


def _actual_usage(output: Path, lease_seconds: int, launched: bool) -> dict[str, int]:
    receipt_path = output / "saved_state_planner_receipt.json"
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        delta = receipt.get("budget_delta", {})
        return {
            "fresh_scenes": int(delta.get("fresh_scenes", 1)),
            "action_scenes": int(delta.get("action_scenes", 0)),
            "collection_attempts": int(delta.get("collection_attempts", 0)),
            "solver_problems": int(receipt.get("solver_problem_count", delta.get("solver_problems", 0))),
            "gpu_lease_seconds": int(lease_seconds),
        }
    qualification_path = output / "qualification_receipt.json"
    cell_path = output / "cell_receipt.json"
    if qualification_path.is_file() or cell_path.is_file():
        qualification = json.loads(qualification_path.read_text(encoding="utf-8")) if qualification_path.is_file() else {}
        cell = qualification.get("cell_receipt") if isinstance(qualification.get("cell_receipt"), dict) else (json.loads(cell_path.read_text(encoding="utf-8")) if cell_path.is_file() else {})
        return {
            "fresh_scenes": 1,
            "action_scenes": int(int(cell.get("action_segment_count", 0)) > 0),
            "collection_attempts": 1,
            "solver_problems": int(cell.get("solver_problem_count", 0)),
            "gpu_lease_seconds": int(lease_seconds),
        }
    root_path = output / "root_receipt.json"
    if root_path.is_file():
        root = json.loads(root_path.read_text(encoding="utf-8"))
        # A resumed root contains immutable reused cells and newly generated
        # cells. Charge only receipts whose meter output belongs to this job;
        # the seed/qualification cell was already settled by its own job.
        output_prefix = str(output.resolve())
        generated = [
            cell for cell in root.get("cells", [])
            if str(cell.get("_meter_output", "")).startswith(output_prefix)
        ]
        if not generated and int(root.get("new_cell_count", 0)) > 0:
            raise RuntimeError("P4 root receipt claims new cells but none are bound to this output")
        return {
            "fresh_scenes": len(generated),
            "action_scenes": sum(int(cell.get("action_segment_count", 0)) > 0 for cell in generated),
            "collection_attempts": sum(cell.get("collection") is True for cell in generated),
            "solver_problems": sum(int(cell.get("solver_problem_count", 0)) for cell in generated),
            "gpu_lease_seconds": int(lease_seconds),
        }
    # A child that exits during argument parsing or another pre-scene entry
    # check may never create its output directory or a receipt.  The
    # coordinator still has a measured GPU lease from its monotonic clocks;
    # settle that lease and keep physical counters at zero when no child
    # artifact exists.  A partially-created scene remains unknown and is
    # handled by the explicit error below.
    if launched and (not output.exists() or not any(output.iterdir())):
        return {
            "fresh_scenes": 0,
            "action_scenes": 0,
            "collection_attempts": 0,
            "solver_problems": 0,
            "gpu_lease_seconds": int(lease_seconds),
        }
    if launched:
        raise RuntimeError("P4 child launched without a persisted diagnostic receipt; consumption is unknown")
    return {key: 0 for key in COUNTERS}


def _run_job(job: dict[str, Any], card: dict[str, Any], ledger: ExecutionLedgerV2, state: dict[str, Any]) -> dict[str, Any]:
    job_id = job["job_id"]; output = Path(job["output"])
    if output.exists():
        if any(output.iterdir()):
            raise RuntimeError(f"P4 output already exists and is non-empty: {output}")
        output.rmdir()
    physical_index = int(card.get("physical_index", card.get("physical_gpu_index"))); gpu_uuid = str(card["gpu_uuid"]); reservation = {key: int(job["reservation"][key]) for key in COUNTERS}
    ledger.reserve(job_id, reservation, idempotency_key=f"reserve:{job_id}")
    pre = live_snapshot(); guarded = guard_card(pre, physical_index, expected_uuid=gpu_uuid)
    env = child_environment(gpu_uuid); env.update({"PYTHONPATH": str(PROJECT), "ROBOTWIN_ROOT": str(PROJECT), "ROBOTWIN_WORKSPACE": str(ROOT / "Robotwin2"), "CMF_GPU_GUARD_PHYSICAL_INDEX": str(physical_index), "CMF_BOUND_GPU_UUID": gpu_uuid})
    log_path = BASE / "worker_logs" / f"{job_id}.stdout.log"; log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic(); wall = time.time(); command = [str(item) for item in job["command"]]
    state.setdefault("jobs", {})[job_id] = {"status": "STARTING", "root_id": job["root_id"], "cell_keys": job["cell_keys"], "reservation": reservation, "physical_gpu_index": physical_index, "gpu_uuid": gpu_uuid, "command": command, "started_wall_time": wall, "started_monotonic": started, "pre_snapshot": pre, "guarded_card": guarded}
    _write_state(state)
    process = subprocess.Popen(command, cwd=PROJECT, env=env, start_new_session=True, stdout=log_path.open("w", encoding="utf-8"), stderr=subprocess.STDOUT, text=True)
    pid = int(process.pid); pgid = os.getpgid(pid); state["jobs"][job_id].update({"status": "RUNNING", "pid": pid, "pgid": pgid, "process_tree_start": _tree(pid)}); _write_state(state)
    timeout = int(job.get("timeout_seconds", 1200)); timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try: os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            try: os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait(timeout=20)
    ended = time.monotonic(); lease = max(0, int(math.ceil(ended - started))); return_code = int(process.returncode if process.returncode is not None else -999); tree_after = _tree(pid); owned_cleanup = not any(str(pid) in line.split()[:1] for line in tree_after)
    post = live_snapshot(); post_card = {int(item["physical_index"]): item for item in post["gpus"]}.get(physical_index); idle_observed = bool(post_card and post_card.get("independently_fresh_idle"))
    # Persist the end boundary before any receipt/usage parser can fail.  This
    # keeps the measured lease, exit code, process tree, and cleanup evidence
    # available for an ordinary CLI error or an unknown-consumption stop.
    end = {"schema_version":"cmf_f2_f3_v2_p4_end_evidence_v1","job_id":job_id,"root_id":job["root_id"],"cell_keys":job["cell_keys"],"physical_gpu_index":physical_index,"gpu_uuid":gpu_uuid,"command":command,"pid":pid,"pgid":pgid,"return_code":return_code,"timeout":timed_out,"pre_snapshot":pre,"guarded_card":guarded,"post_snapshot":post,"process_tree_start":state["jobs"][job_id]["process_tree_start"],"process_tree_after":tree_after,"owned_cleanup_pass":owned_cleanup,"device_idle_observed":idle_observed,"actual_usage":None,"usage_parse_error":None,"usage_basis":"end_boundary_persisted_before_usage_parse","reservation":reservation,"worker_log":str(log_path),"overrun_before_settlement":None,"output":str(output)}; end["end_evidence_sha256"]=canonical_sha256(end); atomic_write_json(BASE / f"{job_id}.end_evidence.json", end)
    try:
        actual = _actual_usage(output, lease, launched=True)
        has_artifact = output.exists() and any(output.iterdir())
        usage_basis = "measured_gpu_lease_and_persisted_child_receipt" if has_artifact else "measured_gpu_lease_no_child_artifact"
    except BaseException as exc:
        end["usage_parse_error"] = {"type": type(exc).__name__, "message": str(exc)}
        end["usage_basis"] = "unknown_child_consumption_after_end_boundary"
        end["end_evidence_sha256"] = canonical_sha256(end)
        atomic_write_json(BASE / f"{job_id}.end_evidence.json", end)
        state["jobs"][job_id].update({"status":"UNKNOWN_CONSUMPTION_AFTER_END_EVIDENCE","end_evidence":str(BASE / f"{job_id}.end_evidence.json"),"usage_parse_error":end["usage_parse_error"]}); state["status"]="STOPPED_UNKNOWN_CONSUMPTION"; state["stop_reason"]="usage parser failed after end evidence; reservation remains held"; _write_state(state)
        raise
    overrun = any(actual[key] > reservation[key] for key in COUNTERS)
    end["actual_usage"] = actual; end["usage_basis"] = usage_basis; end["overrun_before_settlement"] = overrun; end["end_evidence_sha256"] = canonical_sha256(end); atomic_write_json(BASE / f"{job_id}.end_evidence.json", end)
    event = ledger.settle(job_id, reservation, actual, idempotency_key=f"settle:{job_id}"); status = "PASS" if return_code == 0 and owned_cleanup and not overrun else "FAILED"
    receipt = {**end,"schema_version":"cmf_f2_f3_v2_p4_job_receipt_v1","budget_event_sha256":event["event_sha256"],"status":status}; atomic_write_json(BASE / f"{job_id}.json", receipt)
    state["jobs"][job_id] = receipt; state["budget_progress"] = ledger.totals(); _write_state(state)
    if status != "PASS": state["status"] = "STOPPED_AFTER_DIAGNOSTIC_FAILURE"; state["stop_reason"] = "bounded-diagnostic-failed-or-cleanup-or-budget"; _write_state(state)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--manifest", default="P4_F2_DIAGNOSTIC_MANIFEST.json"); parser.add_argument("--only-job-id"); args = parser.parse_args()
    contract = json.loads((BASE / "P4_EXECUTION_CONTRACT.json").read_text(encoding="utf-8")); manifest = json.loads((BASE / args.manifest).read_text(encoding="utf-8")); state = json.loads((BASE / "P4_STATE.json").read_text(encoding="utf-8")); state.setdefault("jobs", {}); ledger = ExecutionLedgerV2(BASE / "execution_ledger.jsonl", contract_sha256=contract["contract_sha256"], task_id=contract["task_id"], caps=contract["budget_caps"], parent_contract_sha256=contract.get("parent_contract_sha256"), ancestor_contract_sha256s=contract.get("ancestor_contract_sha256s"))
    if state.get("status") not in {"READY_BOUNDED_DIAGNOSTICS", "READY_F2_LAYOUT_REPAIR", "READY_F2_QUALIFICATION", "READY_F2_DIAGNOSTIC_REPAIR", "READY_F2_ROOT_COLLECTION", "F2_BESIDE_BLOCKED_AFTER_QUALIFICATION", "F3_B_QUALIFICATION_CELL_PASSED_ROOT_INCOMPLETE", "READY_QUALIFICATION", "RUNNING"}:
        raise RuntimeError(f"P4 dispatcher expected a ready state, got {state.get('status')}")
    jobs = [_normalise_job(job) for job in manifest.get("jobs", []) if args.only_job_id is None or job.get("job_id") == args.only_job_id]
    if not jobs: raise RuntimeError("requested P4 job is absent from manifest")
    snapshot = live_snapshot(); assignment = assign_ready_jobs(jobs, snapshot)
    if len(assignment["assignments"]) != len(jobs): raise RuntimeError("not all P4 jobs received a fresh idle GPU")
    results = []
    for job in jobs:
        card = next(item for item in assignment["assignments"] if item["job_id"] == job["job_id"]); results.append(_run_job(job, card, ledger, state))
        if results[-1]["status"] != "PASS": break
    wave_pass = len(results) == len(jobs) and all(item["status"] == "PASS" for item in results)
    if wave_pass and manifest.get("wave_name") == "P4_F2_BOUNDED_PLANNER_DIAGNOSTIC":
        state["status"] = "READY_F2_LAYOUT_REPAIR"
        state["phase"] = "BOUNDED_F2_DIAGNOSTIC_COMPLETE"
        state["next_action"] = "freeze a finite F2 layout candidate from MotionGen IK_FAIL evidence; do not dispatch collection"
    elif wave_pass:
        state["status"] = "READY_QUALIFICATION"
    else:
        state["status"] = state.get("status", "STOPPED_AFTER_DIAGNOSTIC_FAILURE")
    state["budget_progress"] = ledger.totals(); _write_state(state)
    atomic_write_json(BASE / f"P4_WAVE_{manifest.get('wave_name','WAVE')}.json", {"schema_version":"cmf_f2_f3_v2_p4_wave_receipt_v1","wave_name":manifest.get("wave_name"),"jobs":results,"pass":wave_pass}); return 0 if wave_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
