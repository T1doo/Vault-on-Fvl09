"""Bounded coordinator for F2 inside qualification and fresh confirmation."""

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

from .canonical import atomic_write_json, sha256_file
from .contract import BUDGET_CAPS
from .gpu import GPUGuardError, assign_ready_jobs, child_environment, guard_card, live_snapshot
from .ledger import BudgetLedger


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dispatch(*, vault_execution_dir: str | Path, output_root: str | Path, timeout_seconds: int = 300) -> dict[str, Any]:
    vault = Path(vault_execution_dir); output = Path(output_root) / f"stage_B_f2_closure_{int(time.time())}"; output.mkdir(parents=True, exist_ok=False)
    contract_path = vault / "CONTRACT.json"; state_path = vault / "STATE.json"; contract = _read(contract_path)
    ledger = BudgetLedger(vault / "budget_ledger.jsonl", contract_sha256=sha256_file(contract_path), parent_contract_sha256=contract.get("parent_contract_sha256"), ancestor_contract_sha256s=contract.get("ancestor_contract_sha256s"), task_id=contract["task_id"])
    wave = live_snapshot(); assignment = assign_ready_jobs([{"job_id": output.name, "root_id": "F2-A-closure-qualification"}], wave)
    if not assignment["assignments"]: raise GPUGuardError("no fresh idle GPU for F2 closure qualification")
    selected = assignment["assignments"][0]; launch = live_snapshot(); card = guard_card(launch, selected["physical_gpu_index"], selected["gpu_uuid"])
    reservation = {"solver_problems": 250, "fresh_scenes": 1, "action_scenes": 1, "collection_attempts": 0, "gpu_lease_seconds": min(300, BUDGET_CAPS["gpu_lease_seconds"])}
    ledger.reserve(output.name, reservation, idempotency_key=f"reserve:{output.name}")
    atomic_write_json(output / "pre_guard_snapshot.json", {"wave_snapshot": wave, "launch_snapshot": launch, "assignment": selected, "card": card, "reservation": reservation})
    env = child_environment(selected["gpu_uuid"]); env["CMF_GPU_GUARD_PHYSICAL_INDEX"] = str(selected["physical_gpu_index"])
    command = [sys.executable, "-m", "controlled_multi_future.redesign_f2_f3_v1.f2_closure_probe", "--output", str(output)]
    started = time.monotonic(); launch_wall_time = time.time(); process = subprocess.Popen(command, cwd="/nfs_share/lijunhui/Robotwin2/project/RoboTwin", env=env, start_new_session=True); pid = process.pid; atomic_write_json(output / "dispatch_checkpoint.json", {"schema_version": "cmf_dispatch_checkpoint_v1", "job_id": output.name, "pid": pid, "pgid": pid, "started_monotonic": started, "started_wall_time": launch_wall_time, "selected_physical_gpu_index": selected["physical_gpu_index"], "selected_gpu_uuid": selected["gpu_uuid"], "reservation": reservation, "command": command}); timed_out = False
    try: return_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True; os.killpg(process.pid, signal.SIGTERM)
        try: return_code = process.wait(timeout=20)
        except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL); return_code = process.wait(timeout=20)
    elapsed = time.monotonic() - started; owned_cleanup_pass = process.poll() is not None
    try:
        post = live_snapshot(); card_post = next(item for item in post["gpus"] if item["physical_index"] == selected["physical_gpu_index"]); device_idle_observed = bool(card_post["independently_fresh_idle"]); post_reason = None
    except Exception as exc:
        post = {"status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}"}; device_idle_observed = False; post_reason = str(exc)
    probe_path = output / "f2_closure_receipt.json"; probe = _read(probe_path) if probe_path.exists() else None
    actual = {"solver_problems": int(probe.get("solver_problem_count", 0)) if probe else reservation["solver_problems"], "fresh_scenes": 1, "action_scenes": 1, "collection_attempts": 0, "gpu_lease_seconds": math.ceil(elapsed)}
    unknown = probe is None
    settlement = ledger.settle(output.name, reservation, actual, idempotency_key=f"settle:{output.name}")
    job = {"schema_version": "cmf_f2_f3_job_receipt_v1", "job_id": output.name, "pid": pid, "pgid": pid, "selected_physical_gpu_index": selected["physical_gpu_index"], "selected_gpu_uuid": selected["gpu_uuid"], "command": command, "return_code": return_code, "timed_out": timed_out, "owned_cleanup_pass": owned_cleanup_pass, "device_idle_observed": device_idle_observed, "device_idle_observed_reason": post_reason, "pre_snapshot_path": str(output / "pre_guard_snapshot.json"), "post_snapshot": post, "actual": actual, "unknown_consumption": unknown, "settlement_event_sha256": settlement["event_sha256"], "probe_receipt": probe}
    atomic_write_json(output / "job_receipt.json", job)
    state = _read(state_path); totals = ledger.totals(); events = ledger.events(); state["budget"]["reserved"] = totals["reserved"]; state["budget"]["consumed"] = totals["consumed"]; state["ledger_head_sha256"] = events[-1]["event_sha256"]
    state["jobs"][output.name] = {"status": "SUCCEEDED" if return_code == 0 else "FAILED", "receipt": str(output / "job_receipt.json"), "pid": pid, "pgid": pid, "physical_gpu_index": selected["physical_gpu_index"], "gpu_uuid": selected["gpu_uuid"], "owned_cleanup_pass": owned_cleanup_pass, "device_idle_observed": device_idle_observed, "unknown_consumption": unknown}
    state["resource_observation"]["last_pre_snapshot"] = str(output / "pre_guard_snapshot.json"); state["resource_observation"]["last_post_snapshot"] = post; state["resource_observation"]["nvidia_smi_status"] = "AVAILABLE"; state["resource_observation"]["nvidia_smi_reason"] = None; state["resource_observation"]["active_owned_processes"] = []
    atomic_write_json(state_path, state)
    return job


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--vault-execution-dir", required=True); parser.add_argument("--output-root", required=True); parser.add_argument("--timeout-seconds", type=int, default=300); args = parser.parse_args(); result = dispatch(vault_execution_dir=args.vault_execution_dir, output_root=args.output_root, timeout_seconds=args.timeout_seconds); raise SystemExit(0 if result["return_code"] == 0 else 1)


if __name__ == "__main__": main()
