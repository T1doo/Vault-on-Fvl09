"""Sequential bounded executor for one authorized F1 development batch."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import traceback
from typing import Any, Callable, Mapping

from .current_hasher import hash_json
from .f1_batch_generation_pilot_v1 import validate_f1_batch_pilot_plan_v1
from .f1_batch_pilot_finalizer_v1 import (
    build_reserve_activation_receipt_v1,
    finalize_f1_batch_pilot_v1,
)
from .f1_batch_pilot_scope_v1 import budget
from .root_orchestrator_v1_1 import _write_json


SCHEMA_VERSION = "cmf_f1_batch_pilot_scope_execution_v1"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _receipt_hash_valid(value: Mapping[str, Any]) -> bool:
    payload = dict(value)
    claimed = payload.pop("receipt_sha256", None)
    return isinstance(claimed, str) and claimed == hash_json(payload)


def _cleanup_pass(value: Mapping[str, Any]) -> bool:
    records = list(value.get("cleanup_records", []))
    return bool(records) and all(
        item.get("cleanup_safety_pass") is True
        and int(item.get("orphan_process_count", -1)) == 0
        for item in records
    )


def _terminal_exception_receipt(
    *, slot: Mapping[str, Any], attempt_dir: Path, error: BaseException
) -> dict[str, Any]:
    root_path = attempt_dir / "root/root_receipt.json"
    root = None
    if root_path.is_file():
        try:
            root = json.loads(root_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            root = None
    cleanup = list(root.get("cleanup_records", [])) if isinstance(root, Mapping) else []
    cleanup_pass = _cleanup_pass({"cleanup_records": cleanup})
    value = {
        "schema_version": "cmf_f1_batch_pilot_terminal_failure_receipt_v1",
        "implementation_version": slot["implementation_version"],
        "root_slot_id": slot["slot_id"],
        "root_status": root.get("status") if isinstance(root, Mapping) else "missing_root_receipt",
        "accepted_development_root": False,
        "trajectory_count": 0,
        "pass": False,
        "terminal_attempt_evidence": isinstance(root, Mapping) and cleanup_pass,
        "cleanup_records": cleanup,
        "cleanup_safety_pass": cleanup_pass,
        "budget_counts": dict(root.get("budget_counts", {}))
        if isinstance(root, Mapping)
        else {},
        "elapsed_seconds": root.get("elapsed_seconds")
        if isinstance(root, Mapping)
        else None,
        "root_receipt_reference": {
            "relative_path": "root/root_receipt.json",
            "file_sha256": _file_sha256(root_path),
        }
        if isinstance(root, Mapping)
        else None,
        "error": {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        },
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
        "accepted_root_increment": 0,
    }
    value["receipt_sha256"] = hash_json(value)
    _write_json(attempt_dir / "terminal_failure_receipt.json", value)
    return value


def validate_f1_batch_scope_budget_v1(
    *, root_receipts: Mapping[str, Mapping[str, Any]], activation_count: int
) -> dict[str, Any]:
    frozen = budget()
    receipts = list(root_receipts.values())
    planner = sum(
        int(item.get("budget_counts", {}).get("planner_query_count", 0))
        for item in receipts
    )
    execution = sum(
        int(item.get("budget_counts", {}).get("execution_attempt_count", 0))
        for item in receipts
    )
    recovery = sum(
        int(item.get("budget_counts", {}).get("recovery_attempt_count", 0))
        for item in receipts
    )
    scenes = sum(len(item.get("cleanup_records", [])) for item in receipts)
    checks = {
        "root_attempt_limit": len(receipts) <= frozen["total_root_attempt_limit"],
        "activation_limit": activation_count
        <= frozen["ordered_reserve_activation_limit"],
        "planner_limit": planner <= frozen["planner_query_limit"],
        "execution_limit": execution <= frozen["trajectory_execution_limit"],
        "scene_limit": scenes <= frozen["fresh_scene_limit"],
        "recovery_zero": recovery == frozen["recovery_attempt_limit"],
        "receipt_hashes": all(_receipt_hash_valid(item) for item in receipts),
    }
    return {
        "counts": {
            "root_attempt_count": len(receipts),
            "reserve_activation_count": activation_count,
            "planner_query_count": planner,
            "execution_attempt_count": execution,
            "fresh_scene_count": scenes,
            "recovery_attempt_count": recovery,
        },
        "checks": checks,
        "pass": all(checks.values()),
        "budget": frozen,
    }


class F1BatchPilotScopeRunnerV1:
    def __init__(
        self,
        *,
        adapter_factory: Callable[[Mapping[str, Any], Path], Any],
        root_runner_factory: Callable[[Any], Any],
    ):
        self.adapter_factory = adapter_factory
        self.root_runner_factory = root_runner_factory

    def run(self, *, output_dir: Path, plan: Mapping[str, Any]) -> dict[str, Any]:
        if validate_f1_batch_pilot_plan_v1(plan).get("pass") is not True:
            raise ValueError("F1 batch scope received an invalid frozen plan")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        _write_json(output_dir / "f1_batch_pilot_plan.json", plan)
        queue = [dict(item) for item in plan["primary_slots"]]
        receipts: dict[str, dict[str, Any]] = {}
        activations: list[dict[str, Any]] = []
        attempted: set[str] = set()
        stop_reason = None
        while queue:
            slot = queue.pop(0)
            slot_id = str(slot["slot_id"])
            if slot_id in attempted:
                raise RuntimeError("F1 batch attempted one root more than once")
            attempted.add(slot_id)
            attempt_dir = output_dir / "root_attempts" / slot_id
            try:
                adapter = self.adapter_factory(slot, attempt_dir)
                runner = self.root_runner_factory(adapter)
                receipt = dict(
                    runner.run(
                        output_dir=attempt_dir,
                        planned_root_slot_spec=slot,
                    )
                )
                if not _receipt_hash_valid(receipt):
                    raise RuntimeError("F1 root runner returned an invalid receipt hash")
            except BaseException as exc:
                receipt = _terminal_exception_receipt(
                    slot=slot, attempt_dir=attempt_dir, error=exc
                )
            receipts[slot_id] = receipt
            if receipt.get("accepted_development_root") is True and receipt.get("pass") is True:
                accepted_count = sum(
                    item.get("accepted_development_root") is True
                    and item.get("pass") is True
                    for item in receipts.values()
                )
                if accepted_count == plan["target_accepted_root_count"]:
                    stop_reason = "five_accepted_development_roots"
                    break
                continue
            terminal_evidence = receipt.get(
                "terminal_attempt_evidence", _cleanup_pass(receipt)
            )
            if terminal_evidence is not True or not _cleanup_pass(receipt):
                stop_reason = "nonterminal_or_cleanup_uncertain_root_failure"
                break
            if len(activations) >= len(plan["ordered_reserve_slots"]):
                stop_reason = "ordered_reserve_exhausted"
                continue
            activation = build_reserve_activation_receipt_v1(
                plan=plan,
                failed_slot_id=slot_id,
                prior_activations=activations,
            )
            activations.append(activation)
            activation_path = (
                output_dir
                / "reserve_activations"
                / f"reserve_{activation['reserve_rank']:02d}.json"
            )
            _write_json(activation_path, activation)
            # Root-spec hash is immutable; activation is carried separately.
            reserve = dict(plan["ordered_reserve_slots"][activation["reserve_rank"] - 1])
            queue.append(reserve)

        finalizer = finalize_f1_batch_pilot_v1(
            plan=plan,
            root_receipts=receipts,
            reserve_activations=activations,
        )
        scope_budget = validate_f1_batch_scope_budget_v1(
            root_receipts=receipts, activation_count=len(activations)
        )
        terminal = finalizer["status"] != "INCOMPLETE"
        result = {
            "schema_version": SCHEMA_VERSION,
            "implementation_version": plan["implementation_version"],
            "plan_sha256": plan["plan_sha256"],
            "attempt_order": list(receipts),
            "root_receipts": receipts,
            "reserve_activations": activations,
            "finalizer": finalizer,
            "budget_validation": scope_budget,
            "stop_reason": stop_reason,
            "scope_terminal": terminal,
            "five_accepted_roots": finalizer["pass"],
            "pass": terminal and scope_budget["pass"],
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "stage1_authorized": False,
            "formal_trajectory_increment": 0,
        }
        result["receipt_sha256"] = hash_json(result)
        _write_json(output_dir / "f1_batch_scope_receipt.json", result)
        return result


__all__ = [
    "F1BatchPilotScopeRunnerV1",
    "validate_f1_batch_scope_budget_v1",
]
