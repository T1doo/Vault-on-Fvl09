"""Three-context pre-release F3 grasp diagnostic Gate for runtime-v3_4."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .current_hasher import hash_json
from .f3_grasp_robustness_v10 import (
    PROGRAMS,
    audit_f3_three_context_gate_v10,
)
from .real_sapien_adapter_v1_4 import RoboTwinRealSapienStrictPrefixAdapterV1_4
from .root_orchestrator_v1_1 import _write_json
from .root_orchestrator_v1_2 import RealSapienStrictPrefixRootOrchestratorV1_2


SCHEMA_VERSION = "cmf_f3_grasp_three_context_gate_v10"


class F3GraspDiagnosticAdapterV10(RoboTwinRealSapienStrictPrefixAdapterV1_4):
    """Diagnostic-only alias adapter that stops after one suffix event."""

    def __init__(self, **kwargs):
        if kwargs.get("family") != "F3":
            raise ValueError("F3 diagnostic adapter requires family F3")
        super().__init__(**kwargs)

    def build_programs(self, pristine_scene):
        values = deepcopy(super().build_programs(pristine_scene))
        for item in values:
            original = str(item["program_id"])
            if not original.startswith("F3-"):
                raise ValueError("F3 diagnostic source program ID changed")
            item["diagnostic_alias_for_program_id"] = original
            item["program_id"] = "D3-" + original.split("-", 1)[1]
        return values

    def execute_frozen_suffix_spec(
        self, scene, program, execution_spec, replay, realization_spec
    ):
        spec = deepcopy(execution_spec)
        spec["expected_canonical_prefix_action_sha256"] = replay[
            "executed_prefix_action_sha256"
        ]
        return self.controller_v3_3.execute_grasp_robustness_diagnostic_v10(
            scene, program, spec, replay, realization_spec
        )


class F3GraspThreeContextGateV10:
    def __init__(self, adapter: F3GraspDiagnosticAdapterV10):
        if adapter.family != "F3":
            raise ValueError("F3 three-context Gate requires F3 adapter")
        self.adapter = adapter

    def run(self, *, output_dir: Path, planned_root_slot_spec) -> dict:
        output_dir = Path(output_dir)
        realization_specs = {
            f"D3-{program}": {
                "realization": "grasp_robustness_diagnostic_v10",
                "formal_data": False,
                "stage0_data": False,
            }
            for program in PROGRAMS
        }
        root = RealSapienStrictPrefixRootOrchestratorV1_2(
            self.adapter
        ).run_nonformal_root(
            output_dir=output_dir / "diagnostic_group",
            planned_root_slot_spec=planned_root_slot_spec,
            realization_spec_by_program=realization_specs,
        )
        diagnostic_receipts = []
        for branch in root.get("branch_receipts", []):
            semantic = branch.get("verifier", {}).get(
                "family_semantic_verifier", {}
            )
            diagnostic = semantic.get("grasp_robustness_diagnostic_v10")
            if isinstance(diagnostic, dict):
                diagnostic_receipts.append(diagnostic)
        # The root execution order is the frozen candidate order.  Diagnostic
        # aliases prevent the generic finalizer from requiring equal final
        # states after deliberately different first suffix events.
        diagnostic_receipts.sort(
            key=lambda item: PROGRAMS.index(item.get("program"))
            if item.get("program") in PROGRAMS
            else len(PROGRAMS)
        )
        gate = audit_f3_three_context_gate_v10(diagnostic_receipts)
        checks = {
            "generic_three_fresh_branch_lifecycle": root.get("status") == "accepted",
            "diagnostic_three_context_gate": gate["pass"],
            "diagnostic_not_accepted_root": True,
            "release_never_executed": gate.get("checks", {}).get(
                "all_stopped_before_release"
            )
            is True,
        }
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": "controlled_multi_future_runtime_v3_4",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "diagnostic_nonroot": True,
            "accepted_root_increment": 0,
            "status": "passed_f3_grasp_three_context_gate_v10"
            if all(checks.values())
            else "failed_f3_grasp_three_context_gate_v10",
            "pass": all(checks.values()),
            "checks": checks,
            "three_context_gate": gate,
            "diagnostic_group_relative_path": "diagnostic_group",
            "diagnostic_group_receipt_sha256": hash_json(root),
            "budget_counts": dict(root.get("budget_counts", {})),
            "cleanup_records": list(root.get("cleanup_records", [])),
            "receipt_sha256": None,
        }
        receipt["receipt_sha256"] = hash_json(
            {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(output_dir / "receipt.json", receipt)
        return receipt


__all__ = ["F3GraspDiagnosticAdapterV10", "F3GraspThreeContextGateV10"]
