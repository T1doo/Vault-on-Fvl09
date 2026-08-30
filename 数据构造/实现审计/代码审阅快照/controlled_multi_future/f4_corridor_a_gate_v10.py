"""Runtime-v3_4 F4 planner-only corridor selection followed by one A execution."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .current_hasher import hash_json
from .f4_corridor_selection_gate_v10 import F4CorridorSelectionGateV10
from .f4_staged_block_gate_v1 import F4StagedBlockExecutionGateV1
from .root_orchestrator_v1_1 import _write_json


SCHEMA_VERSION = "cmf_f4_corridor_a_gate_v10"


class F4CorridorAExecutionGateV10:
    def __init__(self, adapter):
        if adapter.family != "F4":
            raise ValueError("F4 corridor+A Gate requires F4 adapter")
        self.adapter = adapter

    def run(self, *, output_dir: Path, planned_root_slot_spec) -> dict:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        planned = deepcopy(planned_root_slot_spec)
        selection = F4CorridorSelectionGateV10(self.adapter).run(
            output_dir=output_dir / "corridor_selection",
            planned_root_slot_spec=planned,
        )
        if selection.get("pass") is True:
            selected = str(selection["selected_corridor_id"])
            planned["selected_f4_corridor_id"] = selected
            planned["corridor_selection_receipt_sha256"] = selection[
                "receipt_sha256"
            ]
            a_gate = F4StagedBlockExecutionGateV1(
                self.adapter,
                gate_sequence=(("A",),),
                implementation_version="controlled_multi_future_runtime_v3_4",
            ).run(
                output_dir=output_dir / "A_execution_gate",
                planned_root_slot_spec=planned,
            )
        else:
            selected = None
            a_gate = None
        a_pass = (
            isinstance(a_gate, dict)
            and a_gate.get("status") == "passed_f4_staged_block_gate"
            and len(a_gate.get("gate_receipts", [])) == 1
            and a_gate["gate_receipts"][0].get("roles") == ["A"]
        )
        checks = {
            "planner_only_corridor_selected": selection.get("pass") is True,
            "selected_before_execution": selected is not None,
            "A_executed_once": a_pass
            and int(a_gate.get("execution_attempt_count", 0)) == 1,
            "A_semantic_pass": a_pass,
            "no_B_C_AB_or_full_execution": a_pass
            and len(a_gate.get("gate_receipts", [])) == 1,
        }
        selection_budget = selection.get("budget_counts", {})
        a_planner = int(a_gate.get("planner_query_count", 0)) if a_gate else 0
        a_execution = int(a_gate.get("execution_attempt_count", 0)) if a_gate else 0
        cleanup = list(selection.get("cleanup_records", [])) + (
            list(a_gate.get("cleanup_records", [])) if a_gate else []
        )
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": "controlled_multi_future_runtime_v3_4",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "accepted_root_increment": 0,
            "selected_corridor_id": selected,
            "corridor_selection_receipt_sha256": selection.get(
                "receipt_sha256"
            ),
            "A_execution_gate_relative_path": "A_execution_gate"
            if a_gate
            else None,
            "A_execution_gate_receipt_sha256": hash_json(a_gate)
            if a_gate
            else None,
            "checks": checks,
            "pass": all(checks.values()),
            "status": "passed_f4_corridor_A_gate_v10"
            if all(checks.values())
            else "failed_f4_corridor_A_gate_v10",
            "budget_counts": {
                "planner_query_count": int(
                    selection_budget.get("planner_query_count", 0)
                )
                + a_planner,
                "execution_attempt_count": a_execution,
                "recovery_attempt_count": 0,
            },
            "cleanup_records": cleanup,
        }
        receipt["receipt_sha256"] = hash_json(receipt)
        _write_json(output_dir / "receipt.json", receipt)
        return receipt


__all__ = ["F4CorridorAExecutionGateV10"]
