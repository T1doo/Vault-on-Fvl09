"""Apply the user-authorized one-time accounting exception for the lost lease."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from controlled_multi_future.redesign_f2_f3_v2.canonical import atomic_write_json, canonical_sha256, sha256_file
from controlled_multi_future.redesign_f2_f3_v2.execution_ledger_v2 import ExecutionLedgerV2
from controlled_multi_future.redesign_f2_f3_v2.gpu import live_snapshot


ROOT = Path("/nfs_share/lijunhui")
BASE = ROOT / "Vault-on-Fvl09/数据构造/实现审计/f2_f3_redesign_execution_v2/p3_execution"
DATA = ROOT / "Robotwin2/datasets/f2_f3_observation_contract_repair_p3"


def _no_owned_collector(job_id: str) -> list[str]:
    result = subprocess.run(["ps", "-eo", "pid=,ppid=,pgid=,cmd="], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    own = {str(os.getpid()), str(os.getppid())}
    return [line.strip() for line in result.stdout.splitlines() if "collector_v2" in line and job_id in line and line.split()[0] not in own]


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--job-id", default="p3-f3-a-remaining5"); args = parser.parse_args()
    contract = json.loads((BASE / "P3_EXECUTION_CONTRACT.json").read_text(encoding="utf-8")); state_path = BASE / "P3_STATE.json"; state = json.loads(state_path.read_text(encoding="utf-8")); unknown = json.loads((BASE / "P3_UNKNOWN_CONSUMPTION_RECEIPT.json").read_text(encoding="utf-8"))
    if state.get("status") != "BUDGET_UNKNOWN_CONSUMPTION_STOPPED" or args.job_id not in state.get("unknown_jobs", {}):
        raise RuntimeError("the requested unknown reservation is not in the expected stopped state")
    owned = _no_owned_collector(args.job_id)
    if owned:
        raise RuntimeError(f"owned collector process is still present: {owned}")
    post = live_snapshot()
    if not all(card.get("independently_fresh_idle") for card in post.get("gpus", [])):
        raise RuntimeError("cannot close the accounting exception while a GPU is not fresh and idle")
    reservation = {"fresh_scenes": 5, "action_scenes": 5, "collection_attempts": 5, "solver_problems": 160, "gpu_lease_seconds": 1800}
    budget_charge = {"fresh_scenes": 1, "action_scenes": 5, "collection_attempts": 1, "solver_problems": 160, "gpu_lease_seconds": 1800}
    ledger = ExecutionLedgerV2(BASE / "execution_ledger.jsonl", contract_sha256=contract["contract_sha256"], task_id=contract["task_id"], caps=contract["budget_caps"], parent_contract_sha256=contract.get("parent_contract_sha256"), ancestor_contract_sha256s=contract.get("ancestor_contract_sha256s"))
    event = ledger.accounting_exception(args.job_id, reservation, budget_charge, metadata={"actual_gpu_lease_seconds": None, "exact_measurement_available": False, "accounting_method": "USER_APPROVED_FULL_RESERVATION_WRITE_OFF", "known_usage_lower_bound": unknown.get("known_usage_lower_bound"), "source_unknown_receipt_sha256": unknown.get("receipt_sha256"), "device_idle_observed_before_close": True}, idempotency_key=f"accounting-exception:{args.job_id}")
    before_path = BASE / "P3_UNKNOWN_CONSUMPTION_RECEIPT_before_writeoff.json"
    if not before_path.exists(): atomic_write_json(before_path, unknown)
    unknown["accounting_exception"] = {"event_sha256": event["event_sha256"], "actual_gpu_lease_seconds": None, "exact_measurement_available": False, "budget_charge_gpu_lease_seconds": 1800, "accounting_method": "USER_APPROVED_FULL_RESERVATION_WRITE_OFF", "budget_charge": budget_charge, "reservation_closed": True, "closed_by": "user-approved-latest-review"}
    unknown["status"] = "CLOSED_BY_AUTHORIZED_EXCEPTION"; unknown.pop("receipt_sha256", None); unknown["receipt_sha256"] = canonical_sha256(unknown); atomic_write_json(BASE / "P3_UNKNOWN_CONSUMPTION_RECEIPT.json", unknown)
    exception_receipt = {"schema_version": "cmf_f2_f3_v2_p3_accounting_exception_receipt_v1", "job_id": args.job_id, "contract_sha256": contract["contract_sha256"], "event_sha256": event["event_sha256"], "event_type": event["event_type"], "actual_gpu_lease_seconds": None, "exact_measurement_available": False, "accounting_method": "USER_APPROVED_FULL_RESERVATION_WRITE_OFF", "budget_charge": budget_charge, "reservation": reservation, "known_usage_lower_bound": unknown.get("known_usage_lower_bound"), "post_snapshot": post, "owned_processes_absent": True, "status": "CLOSED_BY_AUTHORIZED_EXCEPTION"}; exception_receipt["receipt_sha256"] = canonical_sha256(exception_receipt); atomic_write_json(BASE / "P3_ACCOUNTING_EXCEPTION_RECEIPT.json", exception_receipt)
    state["schema_version"] = "cmf_f2_f3_v2_p3_state_v7"; state["status"] = "READY_F3_REMAINING"; state["stop_reason"] = None; state["unknown_jobs"][args.job_id].update({"reservation_held": False, "closed_by_accounting_exception": True, "accounting_exception_receipt": "数据构造/实现审计/f2_f3_redesign_execution_v2/p3_execution/P3_ACCOUNTING_EXCEPTION_RECEIPT.json"}); state.setdefault("budget_charged", {})["lost_lease_exception"] = budget_charge; state["progress"]["f3_remaining"] = "READY_NOT_STARTED_AFTER_ACCOUNTING_EXCEPTION"; state["progress"]["budget_charge_gpu_lease_seconds"] = 1800; state["next_required_step"] = "run a newly reserved F3-A remaining5 attempt"; state.pop("state_sha256", None); state["state_sha256"] = canonical_sha256(state); atomic_write_json(state_path, state)
    print(json.dumps({"event_sha256": event["event_sha256"], "exception_receipt_sha256": exception_receipt["receipt_sha256"], "state_sha256": state["state_sha256"], "ledger_totals": ledger.totals()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
