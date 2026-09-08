"""Guarded coordinator for a non-executing saved-state F2 planner probe."""

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


def dispatch(*, vault_execution_dir: str | Path, output_root: str | Path, cell_receipt: str | Path, trace: str | Path, timeout_seconds: int = 1800, stand_xs: list[float] | None = None) -> dict[str, Any]:
    vault=Path(vault_execution_dir); output=Path(output_root)/f"stage_D_F2_saved_state_diagnostic_{int(time.time())}"; output.mkdir(parents=True,exist_ok=False)
    contract_path=vault/"CONTRACT.json"; state_path=vault/"STATE.json"; contract=_read(contract_path); ledger=BudgetLedger(vault/"budget_ledger.jsonl",contract_sha256=sha256_file(contract_path),parent_contract_sha256=contract.get("parent_contract_sha256"),task_id=contract["task_id"])
    wave=live_snapshot(); assignment=assign_ready_jobs([{"job_id":output.name,"root_id":"F2-saved-state-diagnostic"}],wave)
    if not assignment["assignments"]: raise RuntimeError("no fresh idle GPU for saved-state diagnostic")
    selected=assignment["assignments"][0]; launch=live_snapshot(); card=guard_card(launch,selected["physical_gpu_index"],selected["gpu_uuid"])
    reservation={"solver_problems":32,"fresh_scenes":1,"action_scenes":0,"collection_attempts":0,"gpu_lease_seconds":min(1800,BUDGET_CAPS["gpu_lease_seconds"])}
    ledger.reserve(output.name,reservation,idempotency_key=f"reserve:{output.name}"); atomic_write_json(output/"pre_guard_snapshot.json",{"wave_snapshot":wave,"launch_snapshot":launch,"assignment":selected,"card":card,"reservation":reservation,"source_cell_receipt":str(cell_receipt),"source_trace":str(trace)})
    env=child_environment(selected["gpu_uuid"]); env["CMF_GPU_GUARD_PHYSICAL_INDEX"]=str(selected["physical_gpu_index"]); command=[sys.executable,"-m","controlled_multi_future.redesign_f2_f3_v1.f2_saved_state_planner_probe","--output",str(output),"--cell-receipt",str(cell_receipt),"--trace",str(trace)]
    if stand_xs: command.extend(["--stand-xs",",".join(str(x) for x in stand_xs)])
    started=time.monotonic(); launch_wall_time=time.time(); process=subprocess.Popen(command,cwd="/nfs_share/lijunhui/Robotwin2/project/RoboTwin",env=env,start_new_session=True); pid=process.pid; atomic_write_json(output/"dispatch_checkpoint.json",{"schema_version":"cmf_dispatch_checkpoint_v1","job_id":output.name,"pid":pid,"pgid":pid,"started_monotonic":started,"started_wall_time":launch_wall_time,"selected_physical_gpu_index":selected["physical_gpu_index"],"selected_gpu_uuid":selected["gpu_uuid"],"reservation":reservation,"command":command}); timed_out=False
    try: return_code=process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out=True; os.killpg(process.pid,signal.SIGTERM)
        try: return_code=process.wait(timeout=30)
        except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL); return_code=process.wait(timeout=30)
    elapsed=time.monotonic()-started; owned_cleanup_pass=process.poll() is not None
    try: post=live_snapshot(); post_card=next(item for item in post["gpus"] if item["physical_index"]==selected["physical_gpu_index"]); device_idle_observed=bool(post_card["independently_fresh_idle"]); post_reason=None
    except Exception as exc: post={"status":"UNAVAILABLE","error":f"{type(exc).__name__}: {exc}"}; device_idle_observed=False; post_reason=str(exc)
    diag_path=output/"saved_state_planner_receipt.json"; diag=_read(diag_path) if diag_path.exists() else None; actual={"solver_problems":int(diag.get("solver_problem_count",0)) if diag else 0,"fresh_scenes":1,"action_scenes":0,"collection_attempts":0,"gpu_lease_seconds":math.ceil(elapsed)}; unknown=diag is None; settlement=ledger.settle(output.name,reservation,actual,idempotency_key=f"settle:{output.name}")
    job={"schema_version":"cmf_f2_saved_state_planner_job_receipt_v1","job_id":output.name,"command":command,"pid":pid,"pgid":pid,"selected_physical_gpu_index":selected["physical_gpu_index"],"selected_gpu_uuid":selected["gpu_uuid"],"return_code":return_code,"timed_out":timed_out,"owned_cleanup_pass":owned_cleanup_pass,"device_idle_observed":device_idle_observed,"device_idle_observed_reason":post_reason,"post_snapshot":post,"actual":actual,"unknown_consumption":unknown,"settlement_event_sha256":settlement["event_sha256"],"diagnostic_receipt":diag}
    atomic_write_json(output/"job_receipt.json",job); state=_read(state_path); totals=ledger.totals(); state["budget"]["reserved"]=totals["reserved"]; state["budget"]["consumed"]=totals["consumed"]; state["ledger_head_sha256"]=ledger.events()[-1]["event_sha256"]; state["jobs"][output.name]={"status":"SUCCEEDED" if return_code==0 else "FAILED","receipt":str(output/"job_receipt.json"),"pid":pid,"pgid":pid,"physical_gpu_index":selected["physical_gpu_index"],"gpu_uuid":selected["gpu_uuid"],"owned_cleanup_pass":owned_cleanup_pass,"device_idle_observed":device_idle_observed,"unknown_consumption":unknown}; state["resource_observation"]["last_pre_snapshot"]=str(output/"pre_guard_snapshot.json"); state["resource_observation"]["last_post_snapshot"]=post; state["resource_observation"]["active_owned_processes"]=[]; atomic_write_json(state_path,state); return job


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--vault-execution-dir",required=True); parser.add_argument("--output-root",required=True); parser.add_argument("--cell-receipt",required=True); parser.add_argument("--trace",required=True); parser.add_argument("--stand-xs",default=""); parser.add_argument("--timeout-seconds",type=int,default=1800); args=parser.parse_args(); stand_xs=[float(item) for item in args.stand_xs.split(",") if item.strip()] if args.stand_xs else None; result=dispatch(vault_execution_dir=args.vault_execution_dir,output_root=args.output_root,cell_receipt=args.cell_receipt,trace=args.trace,timeout_seconds=args.timeout_seconds,stand_xs=stand_xs); raise SystemExit(0 if result["return_code"]==0 else 1)


if __name__ == "__main__": main()
