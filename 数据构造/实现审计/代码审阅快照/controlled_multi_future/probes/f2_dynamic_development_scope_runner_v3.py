"""Guard-child implementation for bounded F2 V3 dynamic audit and one root."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import traceback
from typing import Any, Mapping

from ..f2_asset_bound_runtime_v3 import (
    RoboTwinRealSapienF2AssetBoundAdapterV3,
)
from ..f2_dynamic_development_scope_v3 import (
    SCOPE,
    f2_dynamic_development_budget_v3,
    planned_f2_asset_bound_root_spec_v3,
)
from ..f2_dynamic_search_contract_v3 import (
    build_dynamic_selected_asset_layout_binding_v3,
    build_provisional_dynamic_candidate_binding_v3,
    decide_bounded_dynamic_search_v3,
    validate_cpu_static_screening_v3,
)
from ..f2_official_asset_compatibility_matrix_v3 import (
    PROGRAM_IDS,
    REQUIRED_GATE_IDS,
    apply_gate_receipts_v3,
    build_gate_receipt_v3,
    validate_static_compatibility_matrix_v3,
)
from ..root_orchestrator_v1_2 import RealSapienStrictPrefixRootOrchestratorV1_2
from .f2_dynamic_development_authorization_v3 import (
    load,
    load_consumption,
    summary,
)
from .gpu_guard_v2_4 import require_atomic_gpu_guard_v2_4


def _hash_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _terminal_gate_chain(
    row, *, inside, on_pass, layout_pass, planner_pass, runtime_layout_payload
):
    outcomes = {
        "strict_full_object_inside_margin": bool(inside.get("pass")),
        "on_passive_stability": bool(on_pass),
        "beside_mutual_exclusion": bool(layout_pass),
        "asset_derived_scene_layout": bool(layout_pass),
        "same_arm_three_branch_planner": bool(planner_pass),
    }
    first_failure = next((gate for gate in REQUIRED_GATE_IDS if not outcomes[gate]), None)
    receipts = []
    predecessor = None
    layout_sha = None
    for gate_id in REQUIRED_GATE_IDS:
        passed = first_failure is None or REQUIRED_GATE_IDS.index(gate_id) < REQUIRED_GATE_IDS.index(first_failure)
        if first_failure is None:
            passed = True
        if gate_id == first_failure:
            passed = False
        if first_failure is not None and REQUIRED_GATE_IDS.index(gate_id) > REQUIRED_GATE_IDS.index(first_failure):
            passed = False
        if gate_id == "strict_full_object_inside_margin":
            evidence = inside if passed else {"reason": "strict_full_envelope_rejected"}
        elif gate_id == "on_passive_stability":
            evidence = (
                {
                    "runtime_or_complete_geometry_evidence": True,
                    "passive_250hz_settle_verified": True,
                    "continuous_scale_support": True,
                    "stable_window_pass": True,
                }
                if passed
                else {"reason": "passive_on_failed_or_not_run"}
            )
        elif gate_id == "beside_mutual_exclusion":
            evidence = (
                {
                    "runtime_or_complete_geometry_evidence": True,
                    "asset_derived_predicates": True,
                    "zero_overlap": True,
                    "table_clearance_pass": True,
                }
                if passed
                else {"reason": "layout_mutual_exclusion_failed_or_not_run"}
            )
        elif gate_id == "asset_derived_scene_layout":
            layout_sha = layout_sha or _hash_json(runtime_layout_payload)
            evidence = (
                {
                    "runtime_or_complete_geometry_evidence": True,
                    "fresh_scene_layout_realized": True,
                    "facility_clearance_pass": True,
                    "layout_payload_sha256": layout_sha,
                }
                if passed
                else {"reason": "fresh_layout_realization_failed_or_not_run"}
            )
        else:
            evidence = (
                {
                    "runtime_or_complete_geometry_evidence": True,
                    "selected_execution_arm": "left",
                    "program_ids": list(PROGRAM_IDS),
                    "same_start_qpos_and_seed": True,
                    "complete_planner_chains": True,
                    "same_main_object_for_all_programs": True,
                    "same_execution_arm_for_all_programs": True,
                }
                if passed
                else {"reason": "three_chain_planner_failed_or_not_run"}
            )
        receipt = build_gate_receipt_v3(
            row,
            gate_id=gate_id,
            status="passed" if passed else "rejected",
            evidence=evidence,
            predecessor_gate_receipt_sha256=predecessor,
        )
        receipts.append(receipt)
        predecessor = receipt["gate_receipt_sha256"]
    return receipts


class F2DynamicThenDevelopmentRunnerV3:
    def __init__(
        self,
        *,
        matrix: Mapping[str, Any],
        screening: Mapping[str, Any],
        authorization: Mapping[str, Any],
        expected_source_sha256: str,
        output_dir: Path,
    ):
        self.matrix = validate_static_compatibility_matrix_v3(matrix)
        self.screening = validate_cpu_static_screening_v3(screening)
        self.authorization = dict(authorization)
        if (
            self.authorization.get("matrix_sha256") != self.matrix["matrix_sha256"]
            or self.authorization.get("screening_sha256")
            != self.screening["screening_sha256"]
        ):
            raise ValueError("F2 child authorization publications differ")
        if expected_source_sha256 != self.authorization[
            "implementation_source_sha256"
        ]:
            raise ValueError("F2 child implementation source SHA differs from authorization")
        self.expected_source_sha256 = expected_source_sha256
        self.output_dir = Path(output_dir)

    def _adapter(self, binding, *, planner_only, output):
        return RoboTwinRealSapienF2AssetBoundAdapterV3(
            output_root=output,
            expected_implementation_source_sha256=self.expected_source_sha256,
            binding=binding,
            planner_only=planner_only,
        )

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=False)
        evaluated_rows = []
        selected_binding = None
        dynamic_receipts = []
        cleanup_records = []
        planner_queries_total = 0
        prefix_reference_executions = 0
        for scope_index, candidate in enumerate(
            self.screening["dynamic_scope"]["candidates"]
        ):
            binding = build_provisional_dynamic_candidate_binding_v3(
                self.screening, scope_index=scope_index
            )
            row = dict(self.matrix["rows"][candidate["rank"]])
            candidate_dir = self.output_dir / f"candidate_{scope_index:02d}_rank_{candidate['rank']:04d}"
            adapter = self._adapter(
                binding, planner_only=True, output=candidate_dir
            )
            planned = planned_f2_asset_bound_root_spec_v3(
                binding, slot_id=f"f2-dynamic-rank-{candidate['rank']:04d}"
            )
            layout_pass = False
            passive = None
            passive_context = adapter.scene(
                planned, phase="passive_on", program=None
            )
            with passive_context as handle:
                scene = handle.scene
                layout_audit = adapter.controller_v3_3._require_layout_v2(scene)
                layout_pass = all(layout_audit["checks"].values())
                passive = adapter.controller_v3_3.audit_passive_on_scene(scene)
            if passive_context.cleanup_receipt is not None:
                cleanup_records.append(dict(passive_context.cleanup_receipt))
            planner_root = None
            planner_pass = False
            if passive["pass"] is True and layout_pass:
                realization = {
                    program_id: {
                        "realization": "r_pc",
                        "formal_data": False,
                        "stage0_data": False,
                        "stage1_authorized": False,
                    }
                    for program_id in PROGRAM_IDS
                }
                planner_root = RealSapienStrictPrefixRootOrchestratorV1_2(
                    adapter, implementation_version="controlled_multi_future_f2_asset_redesign_v3"
                ).run_nonformal_root(
                    output_dir=candidate_dir / "planner_only_root",
                    planned_root_slot_spec=planned,
                    realization_spec_by_program=realization,
                    stage0_data=False,
                    stage0_authorized=False,
                    development_video_required=False,
                )
                gate = planner_root.get("family_suffix_gate", {})
                planner_queries_total += int(
                    planner_root.get("planner_query_count_total") or 0
                )
                prefix_reference_executions += int(
                    planner_root.get("canonical_prefix_reference_execution_count")
                    or 0
                )
                budget = self.authorization["budget"]
                if planner_queries_total > budget["maximum_planner_queries_total"]:
                    raise RuntimeError("F2 dynamic audit exceeded planner-query budget")
                if prefix_reference_executions > budget[
                    "maximum_prefix_reference_executions"
                ]:
                    raise RuntimeError("F2 dynamic audit exceeded prefix-execution budget")
                planner_pass = (
                    gate.get("intentional_stop_before_suffix_execution") is True
                    and gate.get("all_three_complete_planner_chains_pass") is True
                    and planner_root.get("branch_execution_attempt_count") == 0
                )
                cleanup_records.extend(
                    list(planner_root.get("cleanup_records", []))
                )
            receipts = _terminal_gate_chain(
                row,
                inside=self.screening["terminal_cpu_candidate_receipts"][candidate["rank"]]["inside_cpu_evidence"],
                on_pass=passive["pass"] is True,
                layout_pass=layout_pass,
                planner_pass=planner_pass,
                runtime_layout_payload=binding["layout_payload"],
            )
            evaluated = apply_gate_receipts_v3(row, receipts)
            evaluated_rows.append(evaluated)
            dynamic_receipts.append(
                {
                    "scope_index": scope_index,
                    "rank": candidate["rank"],
                    "binding_sha256": binding["binding_sha256"],
                    "passive_on_receipt": passive,
                    "layout_realization_pass": layout_pass,
                    "planner_root_status": None if planner_root is None else planner_root.get("status"),
                    "planner_only_pass": planner_pass,
                    "evaluated_row_sha256": evaluated["evaluated_row_sha256"],
                }
            )
            decision = decide_bounded_dynamic_search_v3(
                self.screening, evaluated_rows
            )
            if decision["status"] == "first_all_gates_candidate_selected_binding_required":
                selected_binding = build_dynamic_selected_asset_layout_binding_v3(
                    screening=self.screening,
                    evaluated_rows=evaluated_rows,
                    selected_execution_arm="left",
                    layout_payload=binding["layout_payload"],
                )
                break
        if selected_binding is None:
            return {
                "status": "higher_level_redesign_required",
                "dynamic_candidate_receipts": dynamic_receipts,
                "selected_binding": None,
                "development_root": None,
                "planner_query_count_total": planner_queries_total,
                "prefix_reference_execution_count": prefix_reference_executions,
                "branch_execution_attempt_count": 0,
                "recovery_attempt_count": 0,
                "cleanup_records": cleanup_records,
                "formal_data": False,
                "stage0_data": False,
                "stage1_authorized": False,
            }
        execution_dir = self.output_dir / "selected_one_development_root"
        execution_adapter = self._adapter(
            selected_binding, planner_only=False, output=execution_dir
        )
        planned = planned_f2_asset_bound_root_spec_v3(
            selected_binding, slot_id="f2-selected-one-development-root-v3"
        )
        realization = {
            program_id: {
                "realization": "r_pc",
                "formal_data": False,
                "stage0_data": False,
                "stage1_authorized": False,
            }
            for program_id in PROGRAM_IDS
        }
        root = RealSapienStrictPrefixRootOrchestratorV1_2(
            execution_adapter,
            implementation_version="controlled_multi_future_f2_asset_redesign_v3",
        ).run_nonformal_root(
            output_dir=execution_dir / "root",
            planned_root_slot_spec=planned,
            realization_spec_by_program=realization,
            stage0_data=False,
            stage0_authorized=False,
            development_video_required=True,
        )
        planner_queries_total += int(root.get("planner_query_count_total") or 0)
        prefix_reference_executions += int(
            root.get("canonical_prefix_reference_execution_count") or 0
        )
        if planner_queries_total > self.authorization["budget"][
            "maximum_planner_queries_total"
        ]:
            raise RuntimeError("F2 development scope exceeded planner-query budget")
        if int(root.get("branch_execution_attempt_count") or 0) > 3:
            raise RuntimeError("F2 development root exceeded three executions")
        cleanup_records.extend(list(root.get("cleanup_records", [])))
        return {
            "status": (
                "selected_development_root_completed"
                if root.get("status") == "accepted"
                else "selected_development_root_failed_with_evidence"
            ),
            "dynamic_candidate_receipts": dynamic_receipts,
            "selected_binding": selected_binding,
            "development_root": root,
            "planner_query_count_total": planner_queries_total,
            "prefix_reference_execution_count": prefix_reference_executions,
            "branch_execution_attempt_count": int(
                root.get("branch_execution_attempt_count") or 0
            ),
            "recovery_attempt_count": 0,
            "cleanup_records": cleanup_records,
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
        }


def _load(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_child_budget_cleanup_v3(result: Mapping[str, Any]) -> dict[str, Any]:
    budget = f2_dynamic_development_budget_v3()
    counts = {
        "planner_query_count": int(result.get("planner_query_count_total") or 0),
        "prefix_reference_execution_count": int(
            result.get("prefix_reference_execution_count") or 0
        ),
        "branch_execution_attempt_count": int(
            result.get("branch_execution_attempt_count") or 0
        ),
        "recovery_attempt_count": int(result.get("recovery_attempt_count") or 0),
    }
    cleanup = list(result.get("cleanup_records", []))
    checks = {
        "planner": 0 <= counts["planner_query_count"]
        <= budget["maximum_planner_queries_total"],
        "prefix": 0 <= counts["prefix_reference_execution_count"]
        <= budget["maximum_prefix_reference_executions"],
        "execution": 0 <= counts["branch_execution_attempt_count"]
        <= budget["maximum_suffix_execution_attempts"],
        "recovery": counts["recovery_attempt_count"] == 0,
        "cleanup": bool(cleanup)
        and all(
            item.get("cleanup_safety_pass") is True
            and int(item.get("orphan_process_count") or 0) == 0
            for item in cleanup
        ),
    }
    return {
        "counts": counts,
        "cleanup_record_count": len(cleanup),
        "checks": checks,
        "pass": all(checks.values()),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    authorization = load(
        args.authorization_receipt,
        requested_scope=SCOPE,
        expected_family="F2",
        expected_seed=20260829,
    )
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("Guard binding missing")
    consumption = load_consumption(Path(consumption_path), authorization)
    guard_receipt = json.loads(Path(guard_path).read_text(encoding="utf-8"))
    binding = guard_receipt["binding"]
    physical_index = int(binding["physical_gpu_index"])
    gpu_uuid = str(binding["expected_gpu_uuid"])
    if os.environ.get("CUDA_VISIBLE_DEVICES") != gpu_uuid:
        raise RuntimeError("UUID mismatch")
    guard = require_atomic_gpu_guard_v2_4(
        authorization,
        consumption,
        expected_uuid=gpu_uuid,
        physical_index=physical_index,
    )
    output = Path(authorization["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    aggregate = {
        "schema_version": "cmf_f2_dynamic_development_outer_receipt_v3",
        "implementation_version": authorization["implementation_version"],
        "scope": SCOPE,
        "family": "F2",
        "authorization": summary(authorization),
        "authorization_consumption_receipt_sha256": consumption[
            "consumption_receipt_sha256"
        ],
        "guard_binding": guard["binding"],
        "guard_precheck": guard["precheck"],
        "result": None,
        "cleanup_records": [],
        "budget_counts": {},
        "status": "running",
        "pass": False,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage1_authorized": False,
    }
    aggregate["receipt_sha256"] = _hash_json(aggregate)
    (output / "receipt.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        result = F2DynamicThenDevelopmentRunnerV3(
            matrix=_load(Path(authorization["matrix_publication_path"])),
            screening=_load(Path(authorization["screening_publication_path"])),
            authorization=authorization,
            expected_source_sha256=authorization[
                "implementation_source_sha256"
            ],
            output_dir=output / "scope",
        ).run()
        aggregate["result"] = result
        aggregate["cleanup_records"] = list(result.get("cleanup_records", []))
        validation = validate_child_budget_cleanup_v3(result)
        aggregate["budget_counts"] = validation["counts"]
        aggregate["budget_validation"] = validation
        aggregate["pass"] = (
            result.get("status") == "selected_development_root_completed"
            and validation["pass"]
        )
        aggregate["status"] = (
            "accepted" if aggregate["pass"] else result.get("status")
        )
    except BaseException as exc:
        aggregate["status"] = "failed_infrastructure"
        aggregate["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    aggregate["receipt_sha256"] = _hash_json(
        {key: value for key, value in aggregate.items() if key != "receipt_sha256"}
    )
    (output / "receipt.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if aggregate["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "F2DynamicThenDevelopmentRunnerV3",
    "main",
    "validate_child_budget_cleanup_v3",
]
