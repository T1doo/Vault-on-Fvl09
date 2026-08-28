"""One diagnosis plus at most one deterministic F3 correction rollout."""

from __future__ import annotations

import json
from pathlib import Path
import time
import traceback
from typing import Any, Mapping

from .anchor import compare_anchors
from .family_repair_orchestrator_v1_1 import FamilyRepairOrchestratorV1_1
from .runtime_v3_1_contracts import build_f3_deterministic_correction_spec


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class F3ConditionalRepairOrchestratorV1_1:
    """Enforce ``1 diagnosis + conditionally 1 correction`` with no retry."""

    def __init__(self, adapter):
        if adapter.family != "F3":
            raise ValueError("F3 conditional repair requires the F3 adapter")
        self.adapter = adapter

    def run(self, *, output_dir: Path, planned_root_slot_spec: Mapping[str, Any], program: Mapping[str, Any]) -> dict:
        output_dir.mkdir(parents=True, exist_ok=False)
        started = time.time()
        aggregate = {
            "schema_version": "cmf_f3_conditional_repair_orchestrator_v1_1",
            "implementation_version": "controlled_multi_future_runtime_v3_1",
            "program_id": program["program_id"],
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "diagnostic_execution_count": 0,
            "correction_execution_count": 0,
            "maximum_correction_execution_count": 1,
            "status": "running",
            "attempts": [],
            "cleanup_records": [],
        }
        try:
            diagnosis_receipt = FamilyRepairOrchestratorV1_1(self.adapter).run(
                output_dir=output_dir / "diagnosis",
                planned_root_slot_spec={**dict(planned_root_slot_spec), "f3_repair_phase": "diagnosis"},
                program=program,
                repair_mode="diagnosis",
            )
            aggregate["diagnostic_execution_count"] = 1
            aggregate["attempts"].append({"phase": "diagnosis", "receipt": "diagnosis/receipt.json", "status": diagnosis_receipt["status"]})
            aggregate["cleanup_records"].extend(diagnosis_receipt.get("cleanup_records", []))
            semantic = diagnosis_receipt.get("semantic_verifier", {})
            diagnosis = semantic.get("diagnosis", {})
            before_release = semantic.get("samples", {}).get("before_release", {})
            aggregate["diagnosis"] = diagnosis

            if diagnosis.get("actor_to_eef_correction_allowed") is True:
                correction_spec = build_f3_deterministic_correction_spec(
                    diagnosis,
                    before_release,
                    prior_correction_attempt_count=0,
                )
                _write(output_dir / "correction_spec.json", correction_spec)
                correction_receipt = FamilyRepairOrchestratorV1_1(self.adapter).run(
                    output_dir=output_dir / "correction",
                    planned_root_slot_spec={**dict(planned_root_slot_spec), "f3_repair_phase": "deterministic_correction"},
                    program=program,
                    repair_mode="deterministic_correction",
                    correction_spec=correction_spec,
                )
                aggregate["correction_execution_count"] = 1
                aggregate["correction_spec_sha256"] = correction_spec["correction_spec_sha256"]
                aggregate["attempts"].append({"phase": "deterministic_correction", "receipt": "correction/receipt.json", "status": correction_receipt["status"]})
                aggregate["cleanup_records"].extend(correction_receipt.get("cleanup_records", []))
                same_current = (
                    diagnosis_receipt.get("reference_current_sha256") is not None
                    and diagnosis_receipt.get("reference_current_sha256") == correction_receipt.get("reference_current_sha256")
                )
                diagnosis_anchor = json.loads((output_dir / "diagnosis" / "reference_anchor.json").read_text(encoding="utf-8"))
                correction_anchor = json.loads((output_dir / "correction" / "reference_anchor.json").read_text(encoding="utf-8"))
                anchor_equivalence = compare_anchors(diagnosis_anchor, correction_anchor)
                aggregate["diagnosis_correction_same_current"] = same_current
                aggregate["diagnosis_correction_anchor_equivalence"] = anchor_equivalence
                equivalent = same_current and anchor_equivalence["equivalent"]
                correction_pass = correction_receipt.get("repair_probe_pass") is True
                aggregate["repair_probe_pass"] = correction_pass and equivalent
                if correction_receipt.get("status") == "failed_cleanup_uncertain":
                    aggregate["status"] = "failed_cleanup_uncertain"
                elif not equivalent:
                    aggregate["status"] = "failed_current_or_anchor_equivalence"
                elif correction_pass:
                    aggregate["status"] = "passed_nonformal_deterministic_correction_full_program_incomplete"
                else:
                    aggregate["status"] = correction_receipt["status"]
            else:
                aggregate["repair_probe_pass"] = diagnosis_receipt.get("repair_probe_pass") is True
                aggregate["next_gate"] = diagnosis.get("next_gate") or diagnosis_receipt.get("next_gate")
                aggregate["status"] = diagnosis_receipt["status"]
        except BaseException as exc:
            aggregate.update(
                {
                    "status": "failed_execution",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
        aggregate["elapsed_seconds"] = time.time() - started
        aggregate["scene_created"] = any(item.get("scene_created") is True for item in aggregate["cleanup_records"])
        aggregate["scene_cleanup_succeeded"] = bool(aggregate["cleanup_records"]) and all(
            item.get("cleanup_safety_pass") is True for item in aggregate["cleanup_records"]
        )
        aggregate["orphan_process_count"] = sum(
            int(item.get("orphan_process_count") or 0) for item in aggregate["cleanup_records"]
        )
        if aggregate["correction_execution_count"] > 1:
            aggregate["status"] = "failed_budget_exhausted"
            aggregate["repair_probe_pass"] = False
        _write(output_dir / "receipt.json", aggregate)
        return aggregate
