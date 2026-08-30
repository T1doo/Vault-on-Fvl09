"""Planner-only B/C preflight for the exact runtime-v3_4_1 F4 corridor."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .current_hasher import hash_json
from .f4_staged_block_gate_v1 import F4StagedBlockExecutionGateV1
from .root_orchestrator_v1_1 import _write_json


SCHEMA_VERSION = "cmf_f4_bc_preflight_gate_v11"


class F4BCPreflightGateV11:
    """Prove B and C planner chains with the A-selected exact route.

    Each role preflight runs in a fresh scene through the staged Gate helper.
    No controller execution is permitted in this scope.
    """

    def __init__(self, adapter):
        if adapter.family != "F4":
            raise ValueError("F4 B/C preflight requires F4 adapter")
        self.adapter = adapter

    def run(self, *, output_dir: Path, planned_root_slot_spec) -> dict:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        planned = deepcopy(planned_root_slot_spec)
        prerequisite = planned.get("prerequisite_receipts", {}).get(
            "F4_exact_corridor_A_v11"
        )
        if not isinstance(prerequisite, dict) or prerequisite.get("pass") is not True:
            raise ValueError("F4 B/C preflight lacks passing exact corridor+A prerequisite")
        selected = prerequisite.get("selected_corridor_candidate_v11")
        if not isinstance(selected, dict):
            raise ValueError("F4 exact corridor+A prerequisite lacks selected candidate")
        planned["selected_f4_corridor_candidate_v11"] = deepcopy(selected)
        gate = F4StagedBlockExecutionGateV1(
            self.adapter,
            gate_sequence=(("B",), ("C",)),
            implementation_version="controlled_multi_future_runtime_v3_4_1",
            planner_only=True,
        ).run(
            output_dir=output_dir / "planner_only_B_C",
            planned_root_slot_spec=planned,
        )
        roles = [item.get("roles") for item in gate.get("gate_receipts", [])]
        statuses = [
            item.get("status") for item in gate.get("gate_receipts", [])
        ]
        checks = {
            "exact_corridor_A_prerequisite_pass": prerequisite.get("pass") is True,
            "selected_candidate_hash_bound": selected.get(
                "candidate_application_sha256"
            )
            == planned["selected_f4_corridor_candidate_v11"].get(
                "candidate_application_sha256"
            ),
            "fixed_B_then_C_order": roles == [["B"], ["C"]],
            "B_C_planner_preflights_pass": statuses
            == ["passed_planner_preflight", "passed_planner_preflight"],
            "zero_execution": int(gate.get("execution_attempt_count", -1)) == 0,
            "planner_only_mode": gate.get("planner_only") is True,
            "fresh_scene_cleanup_complete": bool(gate.get("cleanup_records"))
            and all(
                item.get("cleanup_safety_pass") is True
                and int(item.get("orphan_process_count") or 0) == 0
                for item in gate["cleanup_records"]
            ),
        }
        passed = all(checks.values())
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": "controlled_multi_future_runtime_v3_4_1",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "accepted_root_increment": 0,
            "selected_corridor_candidate_v11": selected,
            "planner_only_gate_relative_path": "planner_only_B_C",
            "planner_only_gate_receipt_sha256": hash_json(gate),
            "checks": checks,
            "pass": passed,
            "status": (
                "passed_f4_BC_preflight_gate_v11"
                if passed
                else "failed_f4_BC_preflight_gate_v11"
            ),
            "budget_counts": {
                "planner_query_count": int(gate.get("planner_query_count", 0)),
                "execution_attempt_count": 0,
                "recovery_attempt_count": 0,
            },
            "cleanup_records": list(gate.get("cleanup_records", [])),
        }
        receipt["receipt_sha256"] = hash_json(receipt)
        _write_json(output_dir / "receipt.json", receipt)
        return receipt


__all__ = ["F4BCPreflightGateV11"]
