"""F4 B/C/AB staircase after the runtime-v3_4 corridor+A Gate."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .current_hasher import hash_json
from .f4_staged_block_gate_v1 import F4StagedBlockExecutionGateV1
from .root_orchestrator_v1_1 import _write_json


SCHEMA_VERSION = "cmf_f4_bc_ab_gate_v10"


class F4BCABExecutionGateV10:
    def __init__(self, adapter):
        if adapter.family != "F4":
            raise ValueError("F4 B/C/AB Gate requires F4 adapter")
        self.adapter = adapter

    def run(self, *, output_dir: Path, planned_root_slot_spec) -> dict:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        planned = deepcopy(planned_root_slot_spec)
        prerequisite = planned.get("prerequisite_receipts", {}).get(
            "F4_corridor_A_v10"
        )
        if not isinstance(prerequisite, dict) or prerequisite.get("pass") is not True:
            raise ValueError("F4 B/C/AB Gate lacks passing corridor+A prerequisite")
        selected = prerequisite.get("selected_corridor_id")
        if not isinstance(selected, str):
            raise ValueError("F4 corridor+A prerequisite lacks selected corridor")
        planned["selected_f4_corridor_id"] = selected
        gate = F4StagedBlockExecutionGateV1(
            self.adapter,
            gate_sequence=(("B",), ("C",), ("A", "B")),
            implementation_version="controlled_multi_future_runtime_v3_4",
        ).run(
            output_dir=output_dir / "staged_B_C_AB",
            planned_root_slot_spec=planned,
        )
        roles = [item.get("roles") for item in gate.get("gate_receipts", [])]
        checks = {
            "corridor_A_prerequisite_pass": prerequisite.get("pass") is True,
            "selected_corridor_bound": selected == planned["selected_f4_corridor_id"],
            "fixed_B_C_AB_sequence": roles == [["B"], ["C"], ["A", "B"]],
            "three_staged_executions": int(gate.get("execution_attempt_count", 0)) == 3,
            "all_staged_semantic_pass": gate.get("status")
            == "passed_f4_staged_block_gate",
        }
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": "controlled_multi_future_runtime_v3_4",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "accepted_root_increment": 0,
            "selected_corridor_id": selected,
            "staged_gate_relative_path": "staged_B_C_AB",
            "staged_gate_receipt_sha256": hash_json(gate),
            "checks": checks,
            "pass": all(checks.values()),
            "status": "passed_f4_B_C_AB_gate_v10"
            if all(checks.values())
            else "failed_f4_B_C_AB_gate_v10",
            "budget_counts": {
                "planner_query_count": int(gate.get("planner_query_count", 0)),
                "execution_attempt_count": int(gate.get("execution_attempt_count", 0)),
                "recovery_attempt_count": 0,
            },
            "cleanup_records": list(gate.get("cleanup_records", [])),
        }
        receipt["receipt_sha256"] = hash_json(receipt)
        _write_json(output_dir / "receipt.json", receipt)
        return receipt


__all__ = ["F4BCABExecutionGateV10"]
