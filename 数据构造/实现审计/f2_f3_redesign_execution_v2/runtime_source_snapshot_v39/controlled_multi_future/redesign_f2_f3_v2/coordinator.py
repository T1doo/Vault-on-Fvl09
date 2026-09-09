"""Single CPU coordinator for a bounded native asset probe."""

from __future__ import annotations

import json
import math
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .canonical import atomic_write_json
from .contract import BUDGET_CAPS
from .gpu import GPUGuardError, assign_ready_jobs, child_environment, guard_card, live_snapshot
from .ledger import BudgetLedger


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dispatch_native_probe(*, vault_execution_dir: str | Path, output_root: str | Path, timeout_seconds: int = 180) -> dict[str, Any]:
    vault_dir = Path(vault_execution_dir)
    output_dir = Path(output_root) / f"stage_A_native_probe_{int(time.time())}"
    output_dir.mkdir(parents=True, exist_ok=False)
    contract_path = vault_dir / "CONTRACT.json"
    state_path = vault_dir / "STATE.json"
    ledger_path = vault_dir / "budget_ledger.jsonl"
    contract = _read_json(contract_path)
    contract_sha = __import__("hashlib").sha256(contract_path.read_bytes()).hexdigest()
    ledger = BudgetLedger(ledger_path, contract_sha256=contract_sha, parent_contract_sha256=contract.get("parent_contract_sha256"), ancestor_contract_sha256s=contract.get("ancestor_contract_sha256s"), task_id=contract["task_id"])
    pre_snapshot = live_snapshot()
    ready = [{"job_id": output_dir.name, "root_id": "stage-A-native-assets"}]
    assignment = assign_ready_jobs(ready, pre_snapshot)
    if not assignment["assignments"]:
        raise GPUGuardError("no independently fresh idle GPU available for native probe")
    selected = assignment["assignments"][0]
    launch_snapshot = live_snapshot()
    card = guard_card(launch_snapshot, selected["physical_gpu_index"], selected["gpu_uuid"])
    reservation = {"solver_problems": 0, "fresh_scenes": 1, "action_scenes": 0, "collection_attempts": 0, "gpu_lease_seconds": min(180, BUDGET_CAPS["gpu_lease_seconds"])}
    ledger.reserve(output_dir.name, reservation, idempotency_key=f"reserve:{output_dir.name}")
    atomic_write_json(output_dir / "pre_guard_snapshot.json", {"wave_snapshot": pre_snapshot, "launch_snapshot": launch_snapshot, "assignment": selected, "card": card, "reservation": reservation})
    env = child_environment(selected["gpu_uuid"])
    env["CMF_GPU_GUARD_PHYSICAL_INDEX"] = str(selected["physical_gpu_index"])
    command = [sys.executable, "-m", "controlled_multi_future.redesign_f2_f3_v1.native_probe", "--output", str(output_dir)]
    started = time.monotonic()
    launch_wall_time = time.time()
    process = subprocess.Popen(command, cwd="/nfs_share/lijunhui/Robotwin2/project/RoboTwin", env=env, start_new_session=True)
    task_pid = process.pid
    atomic_write_json(output_dir / "dispatch_checkpoint.json", {"schema_version": "cmf_dispatch_checkpoint_v1", "job_id": output_dir.name, "pid": task_pid, "pgid": task_pid, "started_monotonic": started, "started_wall_time": launch_wall_time, "selected_physical_gpu_index": selected["physical_gpu_index"], "selected_gpu_uuid": selected["gpu_uuid"], "reservation": reservation, "command": command})
    timed_out = False
    try:
        return_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            return_code = process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            return_code = process.wait(timeout=15)
    elapsed = time.monotonic() - started
    owned_cleanup_pass = process.poll() is not None
    try:
        post_snapshot = live_snapshot()
        device_idle_observed = bool(next(item for item in post_snapshot["gpus"] if item["physical_index"] == selected["physical_gpu_index"])["independently_fresh_idle"])
        post_reason = None
    except Exception as exc:
        post_snapshot = {"status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}"}
        device_idle_observed = False
        post_reason = str(exc)
    actual = {"solver_problems": 0, "fresh_scenes": 1, "action_scenes": 0, "collection_attempts": 0, "gpu_lease_seconds": max(0, math.ceil(elapsed))}
    settlement = ledger.settle(output_dir.name, reservation, actual, idempotency_key=f"settle:{output_dir.name}")
    native_receipt = _read_json(output_dir / "native_probe_receipt.json") if (output_dir / "native_probe_receipt.json").exists() else None
    job_receipt = {
        "schema_version": "cmf_f2_f3_job_receipt_v1",
        "job_id": output_dir.name,
        "pid": task_pid,
        "pgid": task_pid,
        "selected_physical_gpu_index": selected["physical_gpu_index"],
        "selected_gpu_uuid": selected["gpu_uuid"],
        "command": command,
        "return_code": return_code,
        "timed_out": timed_out,
        "owned_cleanup_pass": owned_cleanup_pass,
        "device_idle_observed": device_idle_observed,
        "device_idle_observed_reason": post_reason,
        "pre_snapshot_path": str(output_dir / "pre_guard_snapshot.json"),
        "post_snapshot": post_snapshot,
        "actual": actual,
        "settlement_event_sha256": settlement["event_sha256"],
        "native_receipt": native_receipt,
    }
    atomic_write_json(output_dir / "job_receipt.json", job_receipt)
    state = _read_json(state_path)
    totals = ledger.totals()
    state["budget"]["reserved"] = totals["reserved"]
    state["budget"]["consumed"] = totals["consumed"]
    events = ledger.events()
    state["ledger_head_sha256"] = events[-1]["event_sha256"] if events else None
    state["jobs"][output_dir.name] = {"status": "SUCCEEDED" if return_code == 0 else "FAILED", "receipt": str(output_dir / "job_receipt.json"), "pid": task_pid, "pgid": task_pid, "physical_gpu_index": selected["physical_gpu_index"], "gpu_uuid": selected["gpu_uuid"], "owned_cleanup_pass": owned_cleanup_pass, "device_idle_observed": device_idle_observed}
    state["resource_observation"]["last_pre_snapshot"] = str(output_dir / "pre_guard_snapshot.json")
    state["resource_observation"]["last_post_snapshot"] = post_snapshot
    state["resource_observation"]["nvidia_smi_status"] = "AVAILABLE"
    state["resource_observation"]["nvidia_smi_reason"] = None
    state["resource_observation"]["active_owned_processes"] = []
    atomic_write_json(state_path, state)
    return job_receipt


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--vault-execution-dir", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    result = dispatch_native_probe(vault_execution_dir=args.vault_execution_dir, output_root=args.output_root, timeout_seconds=args.timeout_seconds)
    raise SystemExit(0 if result["return_code"] == 0 else 1)
