"""One-candidate F4 planner-only qualification execution."""

from __future__ import annotations

from pathlib import Path
import traceback
from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_write_json
from .f4_post_stage0_planner_only_v1 import F4PostStage0PlannerOnlyV1
from .f4_template_qualification_v1 import (
    IMPLEMENTATION_VERSION,
    summarize_f4_template_candidate_result_v1,
    validate_f4_template_candidate_spec_v1,
)


class F4TemplateQualificationRunnerV1:
    def __init__(self, adapter):
        if adapter.family != "F4":
            raise ValueError("F4 template qualification runner requires F4 adapter")
        self.adapter = adapter

    def run_candidate(
        self,
        *,
        output_dir: Path,
        planned_root_slot_spec: Mapping[str, Any],
    ) -> dict[str, Any]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        spec = validate_f4_template_candidate_spec_v1(planned_root_slot_spec)
        outer = {
            "schema_version": "cmf_f4_template_candidate_outer_v1",
            "implementation_version": IMPLEMENTATION_VERSION,
            "candidate_id": spec["selected_layout_candidate_id"],
            "candidate_sha256": spec["selected_layout_candidate_sha256"],
            "planned_scope_spec_sha256": spec["planned_scope_spec_sha256"],
            "planner_result": None,
            "candidate_terminal": None,
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
            "status": "running",
        }
        canonical_write_json(output_dir / "receipt.json", outer, mode=0o600)
        try:
            result = F4PostStage0PlannerOnlyV1(
                self.adapter, implementation_version=IMPLEMENTATION_VERSION
            ).run(
                output_dir=output_dir / "planner_only",
                planned_root_slot_spec=spec,
            )
            terminal = summarize_f4_template_candidate_result_v1(
                candidate_spec=spec, planner_result=result
            )
            outer["planner_result"] = {
                "relative_receipt_path": "planner_only/receipt.json",
                "receipt_sha256": result["receipt_sha256"],
                "status": result["status"],
                "pass": result["pass"],
                "budget_counts": result["budget_counts"],
                "cleanup_records": result["cleanup_records"],
            }
            outer["candidate_terminal"] = terminal
            outer["status"] = (
                "template_candidate_pass"
                if terminal["pass"]
                else "template_candidate_failed"
            )
        except BaseException as exc:
            outer["status"] = "template_candidate_failed_infrastructure"
            outer["error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
        outer["pass"] = outer["status"] == "template_candidate_pass"
        outer["receipt_sha256"] = canonical_hash_json(outer)
        canonical_write_json(output_dir / "receipt.json", outer, mode=0o600)
        return outer


__all__ = ["F4TemplateQualificationRunnerV1"]
