"""Exact F4 corridor selection followed by one A-only execution."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .current_hasher import hash_json
from .f4_exact_corridor_selection_gate_v11 import (
    F4ExactCorridorSelectionGateV11,
)
from .f4_staged_block_gate_v1 import F4StagedBlockExecutionGateV1
from .root_orchestrator_v1_1 import _write_json


class F4ExactCorridorAExecutionGateV11:
    def __init__(self, adapter):
        if adapter.family != "F4":
            raise ValueError("F4 exact corridor+A Gate requires F4 adapter")
        self.adapter = adapter

    def run(self, *, output_dir: Path, planned_root_slot_spec) -> dict:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        planned = deepcopy(planned_root_slot_spec)
        selection = F4ExactCorridorSelectionGateV11(self.adapter).run(
            output_dir=output_dir / "exact_corridor_selection",
            planned_root_slot_spec=planned,
        )
        candidate = selection.get("selected_corridor_candidate_v11")
        if selection.get("pass") is True and isinstance(candidate, dict):
            planned["selected_f4_corridor_candidate_v11"] = candidate
            planned["exact_corridor_selection_receipt_sha256"] = selection[
                "receipt_sha256"
            ]
            a_gate = F4StagedBlockExecutionGateV1(
                self.adapter,
                gate_sequence=(("A",),),
                implementation_version="controlled_multi_future_runtime_v3_4_1",
            ).run(
                output_dir=output_dir / "A_only_execution",
                planned_root_slot_spec=planned,
            )
        else:
            a_gate = None
        roles = [] if a_gate is None else [
            item.get("roles") for item in a_gate.get("gate_receipts", [])
        ]
        checks = {
            "complete_corridor_selected": selection.get("pass") is True,
            "selection_evidence_complete": selection.get(
                "corridor_planner_audit", {}
            ).get("evidence_complete")
            is True,
            "A_executed_once": a_gate is not None
            and int(a_gate.get("execution_attempt_count", 0)) == 1,
            "A_only_fixed_scope": roles == [["A"]],
            "A_semantic_pass": a_gate is not None
            and a_gate.get("status") == "passed_f4_staged_block_gate",
            "B_C_full_not_executed": roles in ([], [["A"]]),
        }
        cleanup = list(selection.get("cleanup_records", [])) + (
            [] if a_gate is None else list(a_gate.get("cleanup_records", []))
        )
        receipt = {
            "schema_version": "cmf_f4_exact_corridor_A_gate_v11",
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": "controlled_multi_future_runtime_v3_4_1",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "accepted_root_increment": 0,
            "selected_corridor_candidate_v11": candidate,
            "selection_receipt_sha256": selection.get("receipt_sha256"),
            "A_gate_receipt_sha256": None
            if a_gate is None
            else hash_json(a_gate),
            "checks": checks,
            "pass": all(checks.values()),
            "status": "passed_f4_exact_corridor_A_gate_v11"
            if all(checks.values())
            else "failed_f4_exact_corridor_A_gate_v11",
            "budget_counts": {
                "planner_query_count": int(
                    selection.get("planner_query_count", 0)
                )
                + (0 if a_gate is None else int(a_gate.get("planner_query_count", 0))),
                "execution_attempt_count": 0
                if a_gate is None
                else int(a_gate.get("execution_attempt_count", 0)),
                "recovery_attempt_count": 0,
            },
            "cleanup_records": cleanup,
        }
        receipt["receipt_sha256"] = hash_json(receipt)
        _write_json(output_dir / "receipt.json", receipt)
        return receipt


__all__ = ["F4ExactCorridorAExecutionGateV11"]
