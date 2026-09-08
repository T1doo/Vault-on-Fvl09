"""GPU-guarded coordinator for saved-state realization path preflight."""

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
from .gpu import assign_ready_jobs, child_environment, guard_card, live_snapshot
from .ledger import BudgetLedger


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dispatch(*, vault_execution_dir: str | Path, output_root: str | Path, family: str, cell_receipt: str | Path, trace: str | Path, goals_json: str | Path, layout_id: str = "v3", timeout_seconds: int = 1800) -> dict[str, Any]:
    vault = Path(vault_execution_dir)
    goal_count = len(_read(Path(goals_json)).get("goals", []))
    if goal_count < 1:
        raise ValueError("preflight goal specification is empty")
    output = Path(output_root) / f"stage_D_{family}_realization_path_preflight_{int(time.time())}"
    output.mkdir(parents=True, exist_ok=False)
    contract_path = vault / "CONTRACT.json"
    state_path = vault / "STATE.json"
    contract = _read(contract_path)
    ledger = BudgetLedger(vault / "budget_ledger.jsonl", contract_sha256=sha256_file(contract_path), parent_contract_sha256=contract.get("parent_contract_sha256"), task_id=contract["task_id"])
    wave = live_snapshot()
    assignment = assign_ready_jobs([{"job_id": output.name, "root_id": f"{family}-realization-path-preflight"}], wave)
    if not assignment["assignments"]:
        raise RuntimeError("no fresh idle GPU for realization path preflight")
    selected = assignment["assignments"][0]
    launch = live_snapshot()
    card = guard_card(launch, selected["physical_gpu_index"], selected["gpu_uuid"])
    reservation = {"solver_problems": goal_count, "fresh_scenes": 1, "action_scenes": 0, "collection_attempts": 0, "gpu_lease_seconds": min(1800, BUDGET_CAPS["gpu_lease_seconds"])}
    ledger.reserve(output.name, reservation, idempotency_key=f"reserve:{output.name}")
    atomic_write_json(output / "pre_guard_snapshot.json", {"wave_snapshot": wave, "launch_snapshot": launch, "assignment": selected, "card": card, "reservation": reservation, "source_cell_receipt": str(cell_receipt), "source_trace": str(trace), "goals_json": str(goals_json)})
    env = child_environment(selected["gpu_uuid"])
    env["CMF_GPU_GUARD_PHYSICAL_INDEX"] = str(selected["physical_gpu_index"])
    command = [sys.executable, "-m", "controlled_multi_future.redesign_f2_f3_v1.realization_path_preflight_probe", "--output", str(output), "--family", family, "--cell-receipt", str(cell_receipt), "--trace", str(trace), "--goals-json", str(goals_json), "--layout-id", layout_id]
    started = time.monotonic()
    launch_wall_time = time.time()
    process = subprocess.Popen(command, cwd="/nfs_share/lijunhui/Robotwin2/project/RoboTwin", env=env, start_new_session=True)
    pid = process.pid
    atomic_write_json(output / "dispatch_checkpoint.json", {"schema_version": "cmf_dispatch_checkpoint_v1", "job_id": output.name, "pid": pid, "pgid": pid, "started_monotonic": started, "started_wall_time": launch_wall_time, "selected_physical_gpu_index": selected["physical_gpu_index"], "selected_gpu_uuid": selected["gpu_uuid"], "reservation": reservation, "command": command})
    timed_out = False
    try:
        return_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            return_code = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            return_code = process.wait(timeout=30)
    elapsed = time.monotonic() - started
    owned_cleanup_pass = process.poll() is not None
    try:
        post = live_snapshot()
        post_card = next(item for item in post["gpus"] if item["physical_index"] == selected["physical_gpu_index"])
        device_idle_observed = bool(post_card["independently_fresh_idle"])
        post_reason = None
    except Exception as exc:
        post = {"status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}"}
        device_idle_observed = False
        post_reason = str(exc)
    receipt_path = output / "realization_path_preflight_receipt.json"
    receipt = _read(receipt_path) if receipt_path.exists() else None
    actual = {"solver_problems": int(receipt.get("solver_problem_count", 0)) if receipt else 0, "fresh_scenes": 1, "action_scenes": 0, "collection_attempts": 0, "gpu_lease_seconds": math.ceil(elapsed)}
    unknown = receipt is None
    settlement = ledger.settle(output.name, reservation, actual, idempotency_key=f"settle:{output.name}")
    job = {"schema_version": "cmf_f2_f3_realization_path_preflight_job_v1", "job_id": output.name, "family": family, "command": command, "pid": pid, "pgid": pid, "selected_physical_gpu_index": selected["physical_gpu_index"], "selected_gpu_uuid": selected["gpu_uuid"], "return_code": return_code, "timed_out": timed_out, "owned_cleanup_pass": owned_cleanup_pass, "device_idle_observed": device_idle_observed, "device_idle_observed_reason": post_reason, "post_snapshot": post, "actual": actual, "unknown_consumption": unknown, "settlement_event_sha256": settlement["event_sha256"], "preflight_receipt": receipt}
    atomic_write_json(output / "job_receipt.json", job)
    state = _read(state_path)
    totals = ledger.totals()
    state["budget"]["reserved"] = totals["reserved"]
    state["budget"]["consumed"] = totals["consumed"]
    state["ledger_head_sha256"] = ledger.events()[-1]["event_sha256"]
    state["jobs"][output.name] = {"status": "SUCCEEDED" if return_code == 0 else "FAILED", "receipt": str(output / "job_receipt.json"), "pid": pid, "pgid": pid, "physical_gpu_index": selected["physical_gpu_index"], "gpu_uuid": selected["gpu_uuid"], "owned_cleanup_pass": owned_cleanup_pass, "device_idle_observed": device_idle_observed, "unknown_consumption": unknown}
    state["resource_observation"]["last_pre_snapshot"] = str(output / "pre_guard_snapshot.json")
    state["resource_observation"]["last_post_snapshot"] = post
    state["resource_observation"]["active_owned_processes"] = []
    atomic_write_json(state_path, state)
    return job


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault-execution-dir", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--family", required=True, choices=("F2", "F3"))
    parser.add_argument("--cell-receipt", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--goals-json", required=True)
    parser.add_argument("--layout-id", default="v3", choices=("v1", "v2", "v3"))
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()
    result = dispatch(vault_execution_dir=args.vault_execution_dir, output_root=args.output_root, family=args.family, cell_receipt=args.cell_receipt, trace=args.trace, goals_json=args.goals_json, layout_id=args.layout_id, timeout_seconds=args.timeout_seconds)
    raise SystemExit(0 if result["return_code"] == 0 else 1)


if __name__ == "__main__":
    main()
