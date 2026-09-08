"""Coordinator for one bounded six-cell pilot root."""

from __future__ import annotations

import argparse, json, math, os, signal, subprocess, sys, time
from pathlib import Path
from typing import Any

from .canonical import atomic_write_json, sha256_file
from .contract import BUDGET_CAPS
from .gpu import GPUGuardError, assign_ready_jobs, child_environment, guard_card, live_snapshot
from .ledger import BudgetLedger
from .pilot_contract import expected_cells, selected_cells


def _read(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))


def dispatch(*, vault_execution_dir: str | Path, output_root: str | Path, root_id: str = "F3-A", timeout_seconds: int = 1800, existing_root: str | Path | None = None, programs: list[str] | tuple[str, ...] | None = None, realizations: list[str] | tuple[str, ...] | None = None, qualification: bool = False, build_prefix: bool = False, single_cell: tuple[str, str] | None = None, layout_id: str = "v1") -> dict[str, Any]:
    vault = Path(vault_execution_dir)
    if single_cell is not None and (not root_id.startswith(("F2", "F3")) or not qualification):
        raise ValueError("single-cell probe is only a non-collection F2/F3 qualification")
    if single_cell is not None and (existing_root is not None or programs is not None or realizations is not None):
        raise ValueError("single-cell transport probe cannot combine with root resume arguments")
    if existing_root is not None and programs is None and realizations is None:
        raise ValueError("a resume dispatch requires an explicit program or realization subset")
    if single_cell is not None:
        run_programs = (single_cell[0],); cell_count = 1; suffix = "transport_probe" if root_id.startswith("F2") else "terminal_probe"; dispatch_root_id = f"{root_id}-{suffix}-{single_cell[0]}-{single_cell[1]}"
    else:
        run_cells = selected_cells(root_id, programs, realizations)
        run_programs = tuple(planned["program_id"] for planned in run_cells)
        run_realizations = tuple(planned["realization_id"] for planned in run_cells)
        # selected_cells returns one entry per realization; reservation is per cell.
        cell_count = len(run_cells); suffix = "qualification" if qualification else ("resume_pilot" if existing_root is not None else "pilot"); dispatch_root_id = root_id
    if single_cell is not None:
        run_realizations = (single_cell[1],)
    output = Path(output_root) / f"stage_C_{root_id.replace('-', '')}_{suffix}_{int(time.time())}"; output.mkdir(parents=True, exist_ok=False)
    contract_path = vault / "CONTRACT.json"; state_path = vault / "STATE.json"; contract = _read(contract_path); ledger = BudgetLedger(vault / "budget_ledger.jsonl", contract_sha256=sha256_file(contract_path), parent_contract_sha256=contract.get("parent_contract_sha256"), task_id=contract["task_id"])
    state = _read(state_path)
    dispatch_control = state.get("dispatch_control", {})
    if not qualification and dispatch_control.get("production_dispatch_allowed") is False:
        raise GPUGuardError(f"production dispatch paused: {dispatch_control.get('reason', 'state control')}")
    wave = live_snapshot(); assignment = assign_ready_jobs([{"job_id": output.name, "root_id": dispatch_root_id}], wave)
    if not assignment["assignments"]: raise GPUGuardError("no fresh idle GPU for pilot root")
    selected = assignment["assignments"][0]; launch = live_snapshot(); card = guard_card(launch, selected["physical_gpu_index"], selected["gpu_uuid"])
    reservation = {"solver_problems": 500, "fresh_scenes": cell_count, "action_scenes": cell_count, "collection_attempts": 0 if qualification else cell_count, "gpu_lease_seconds": min(1800, BUDGET_CAPS["gpu_lease_seconds"])}
    ledger.reserve(output.name, reservation, idempotency_key=f"reserve:{output.name}"); atomic_write_json(output / "pre_guard_snapshot.json", {"wave_snapshot": wave, "launch_snapshot": launch, "assignment": selected, "card": card, "reservation": reservation})
    env = child_environment(selected["gpu_uuid"]); env["CMF_GPU_GUARD_PHYSICAL_INDEX"] = str(selected["physical_gpu_index"])
    child_module = "controlled_multi_future.redesign_f2_f3_v1.pilot_f2_root_probe" if root_id.startswith("F2") else "controlled_multi_future.redesign_f2_f3_v1.pilot_f3_root_probe"
    if single_cell is not None:
        probe_module = "controlled_multi_future.redesign_f2_f3_v1.f2_transport_probe" if root_id.startswith("F2") else "controlled_multi_future.redesign_f2_f3_v1.f3_terminal_qualification_probe"
        command = [sys.executable, "-m", probe_module, "--output", str(output), "--root-id", root_id, "--program", single_cell[0], "--realization", single_cell[1]]
        if root_id.startswith("F2"):
            command.extend(["--layout-id", layout_id])
    else:
        command = [sys.executable, "-m", child_module, "--output", str(output), "--root-id", root_id]
    if root_id.startswith("F2") and single_cell is None:
        if not build_prefix:
            prefix_path = Path(existing_root) / "prefix_artifact.npz" if existing_root is not None else Path("/nfs_share/lijunhui/Robotwin2/datasets/f2_f3_redesign_v1/f2_qualification_prefix_artifact.npz")
            command.extend(["--prefix-artifact", str(prefix_path)])
        if existing_root is not None:
            command.extend(["--existing-root", str(existing_root)])
            if programs is not None:
                command.extend(["--programs", ",".join(programs)])
            if realizations is not None:
                command.extend(["--realizations", ",".join(realizations)])
        if qualification:
            command.append("--qualification")
        if build_prefix:
            command.append("--build-prefix")
        command.extend(["--layout-id", layout_id])
    elif root_id.startswith("F3") and existing_root is not None:
        command.extend(["--existing-root", str(existing_root)])
        if programs is not None:
            command.extend(["--programs", ",".join(programs)])
        if realizations is not None:
            command.extend(["--realizations", ",".join(realizations)])
    started = time.monotonic(); launch_wall_time = time.time(); process = subprocess.Popen(command, cwd="/nfs_share/lijunhui/Robotwin2/project/RoboTwin", env=env, start_new_session=True); pid = process.pid; atomic_write_json(output / "dispatch_checkpoint.json", {"schema_version": "cmf_dispatch_checkpoint_v1", "job_id": output.name, "pid": pid, "pgid": pid, "started_monotonic": started, "started_wall_time": launch_wall_time, "selected_physical_gpu_index": selected["physical_gpu_index"], "selected_gpu_uuid": selected["gpu_uuid"], "reservation": reservation, "command": command}); timed_out = False
    try: return_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True; os.killpg(process.pid, signal.SIGTERM)
        try: return_code = process.wait(timeout=30)
        except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL); return_code = process.wait(timeout=30)
    elapsed = time.monotonic() - started; owned_cleanup_pass = process.poll() is not None
    try:
        post = live_snapshot(); post_card = next(item for item in post["gpus"] if item["physical_index"] == selected["physical_gpu_index"]); device_idle_observed = bool(post_card["independently_fresh_idle"]); post_reason = None
    except Exception as exc:
        post = {"status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}"}; device_idle_observed = False; post_reason = str(exc)
    root_path = output / "root_receipt.json"; root = _read(root_path) if root_path.exists() else None
    probe_path = output / "transport_probe_receipt.json"; probe = _read(probe_path) if probe_path.exists() else None
    if probe is None:
        probe_path = output / "terminal_qualification_receipt.json"; probe = _read(probe_path) if probe_path.exists() else None
    cells = root.get("cells", []) if root else []
    partial_cells = list(output.glob("*/cell_receipt.json"))
    if probe:
        probe_cell = probe.get("cell", {}); actual = {"solver_problems": int(probe_cell.get("solver_problem_count", 0)), "fresh_scenes": 1, "action_scenes": 1, "collection_attempts": 0, "gpu_lease_seconds": math.ceil(elapsed)}
    elif root:
        new_keys = set(root.get("new_cell_keys", []))
        if new_keys:
            charged_cells = [item for item in cells if f"{item.get('program_id')}:{item.get('realization_id')}" in new_keys]
        else:
            run_set = set(root.get("run_programs", []))
            charged_cells = [item for item in cells if item.get("program_id") in run_set]
        actual = {"solver_problems": sum(int(item.get("solver_problem_count", 0)) for item in charged_cells), "fresh_scenes": int(root.get("new_cell_count", len(charged_cells))), "action_scenes": int(root.get("new_cell_count", len(charged_cells))), "collection_attempts": int(root.get("collection_count", 0 if qualification else len(charged_cells))), "gpu_lease_seconds": math.ceil(elapsed)}
    else:
        actual = {"solver_problems": 0, "fresh_scenes": len(partial_cells), "action_scenes": len(partial_cells), "collection_attempts": len(partial_cells), "gpu_lease_seconds": math.ceil(elapsed)}
    unknown = root is None and probe is None; settlement = ledger.settle(output.name, reservation, actual, idempotency_key=f"settle:{output.name}")
    job = {"schema_version": "cmf_pilot_root_job_receipt_v1", "job_id": output.name, "root_id": root_id, "layout_id": layout_id, "run_programs": list(sorted(set(run_programs))), "run_realizations": list(sorted(set(run_realizations))), "existing_root": str(existing_root) if existing_root is not None else None, "qualification": qualification, "build_prefix": build_prefix, "single_cell": list(single_cell) if single_cell is not None else None, "pid": pid, "pgid": pid, "selected_physical_gpu_index": selected["physical_gpu_index"], "selected_gpu_uuid": selected["gpu_uuid"], "command": command, "return_code": return_code, "timed_out": timed_out, "owned_cleanup_pass": owned_cleanup_pass, "device_idle_observed": device_idle_observed, "device_idle_observed_reason": post_reason, "post_snapshot": post, "actual": actual, "unknown_consumption": unknown, "settlement_event_sha256": settlement["event_sha256"], "root_receipt": root, "transport_probe": probe}
    atomic_write_json(output / "job_receipt.json", job)
    totals = ledger.totals(); state["budget"]["reserved"] = totals["reserved"]; state["budget"]["consumed"] = totals["consumed"]; state["ledger_head_sha256"] = ledger.events()[-1]["event_sha256"]; state["jobs"][output.name] = {"status": "SUCCEEDED" if return_code == 0 else "FAILED", "receipt": str(output / "job_receipt.json"), "pid": pid, "pgid": pid, "physical_gpu_index": selected["physical_gpu_index"], "gpu_uuid": selected["gpu_uuid"], "owned_cleanup_pass": owned_cleanup_pass, "device_idle_observed": device_idle_observed, "unknown_consumption": unknown}; state["resource_observation"]["last_pre_snapshot"] = str(output / "pre_guard_snapshot.json"); state["resource_observation"]["last_post_snapshot"] = post; state["resource_observation"]["nvidia_smi_status"] = "AVAILABLE"; state["resource_observation"]["nvidia_smi_reason"] = None; state["resource_observation"]["active_owned_processes"] = []; atomic_write_json(state_path, state)
    return job


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--vault-execution-dir", required=True); parser.add_argument("--output-root", required=True); parser.add_argument("--root-id", default="F3-A"); parser.add_argument("--timeout-seconds", type=int, default=1800); parser.add_argument("--existing-root"); parser.add_argument("--programs", help="comma-separated programs to execute for a resume"); parser.add_argument("--realizations", help="comma-separated realizations to execute for a resume"); parser.add_argument("--qualification", action="store_true", help="run a non-collection transport qualification"); parser.add_argument("--build-prefix", action="store_true", help="build a fresh shared prefix from the first new cell"); parser.add_argument("--transport-probe", help="single-cell F2 qualification as program,realization"); parser.add_argument("--terminal-probe", help="single-cell F3 strict terminal qualification as program,realization"); parser.add_argument("--layout-id", default="v1", choices=("v1","v2","v3")); args = parser.parse_args()
    programs = [item for item in args.programs.split(",") if item] if args.programs else None
    realizations = [item for item in args.realizations.split(",") if item] if args.realizations else None
    if args.transport_probe and args.terminal_probe:
        raise ValueError("choose only one single-cell qualification probe")
    single_value = args.transport_probe or args.terminal_probe
    single_cell = tuple(single_value.split(",", 1)) if single_value else None
    result = dispatch(vault_execution_dir=args.vault_execution_dir, output_root=args.output_root, root_id=args.root_id, timeout_seconds=args.timeout_seconds, existing_root=args.existing_root, programs=programs, realizations=realizations, qualification=args.qualification, build_prefix=args.build_prefix, single_cell=single_cell, layout_id=args.layout_id)
    raise SystemExit(0 if result["return_code"] == 0 else 1)


if __name__ == "__main__": main()
