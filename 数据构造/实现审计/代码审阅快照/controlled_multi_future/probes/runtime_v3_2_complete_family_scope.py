"""One-shot pre-Stage-0 family scope: bounded repair gate then real root."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ..f3_conditional_repair_orchestrator_v1_1 import F3ConditionalRepairOrchestratorV1_1
from ..families import F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from ..family_repair_orchestrator_v1_1 import FamilyRepairOrchestratorV1_1
from ..real_sapien_adapter_v1_2 import RoboTwinRealSapienPilotRootAdapterV1_2
from ..root_orchestrator_v1_1 import RealSapienPilotRootOrchestratorV1_1
from ..runtime_v3_2_budget_v1 import validate_runtime_receipt_against_budget
from .gpu_guard_v2_3 import require_atomic_gpu_guard_v2_3
from .runtime_v3_2_authorization_v1 import (
    authorization_summary,
    load_authorization_v3_2,
    load_consumption_receipt,
)


SCOPE_FAMILIES = {
    "F1_three_branch_nonformal_probe_v3_2": "F1",
    "F2_asset_mapping_and_three_branch_nonformal_probe_v3_2": "F2",
    "F3_grasp_lift_and_full_program_nonformal_probe_v3_2": "F3",
    "F4_arm_asset_layout_and_full_program_nonformal_probe_v3_2": "F4",
}
FAMILY_CLASSES = {
    "F1": F1ObjectSelection,
    "F2": F2TargetRelation,
    "F3": F3MotionOrder,
    "F4": F4SubtaskOrder,
}


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _root_planner_count(root_receipt) -> int:
    return int(root_receipt.get("planner_solvability_query_count_total", 0)) + sum(
        int(item.get("rollout_planner_query_count") or 0)
        for item in root_receipt.get("branch_receipts", [])
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.authorization_receipt.read_text(encoding="utf-8"))
    scopes = raw.get("approved_scopes")
    if not isinstance(scopes, list) or len(scopes) != 1 or scopes[0] not in SCOPE_FAMILIES:
        raise PermissionError("complete family runner requires one supported family scope")
    scope = scopes[0]
    family = SCOPE_FAMILIES[scope]
    authorization = load_authorization_v3_2(
        args.authorization_receipt,
        requested_scope=scope,
        expected_family=family,
    )
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("complete family child requires bound guard and consumption receipts")
    consumption = load_consumption_receipt(Path(consumption_path), authorization)
    guard_value = json.loads(Path(guard_path).read_text(encoding="utf-8"))
    binding = guard_value.get("binding", {})
    physical_index = binding.get("physical_gpu_index")
    expected_uuid = binding.get("expected_gpu_uuid")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != expected_uuid:
        raise RuntimeError("CUDA_VISIBLE_DEVICES must equal the freshly guarded UUID")
    guard = require_atomic_gpu_guard_v2_3(
        authorization,
        consumption,
        expected_uuid=expected_uuid,
        physical_index=physical_index,
    )

    output = Path(authorization["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    planned = dict(authorization["planned_root_slot_spec"])
    adapter = RoboTwinRealSapienPilotRootAdapterV1_2(family=family, output_root=output / "scene_work")
    programs = FAMILY_CLASSES[family]().checked_provisional_programs()
    aggregate = {
        "schema_version": "cmf_complete_pre_stage0_family_scope_v3_2_v1",
        "authorization": authorization_summary(authorization),
        "authorization_consumption_receipt_sha256": consumption["consumption_receipt_sha256"],
        "guard_binding": guard["binding"],
        "guard_precheck": guard["precheck"],
        "family": family,
        "scope": scope,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "repair_gate": None,
        "root_receipt": None,
        "branch_receipts": [],
        "cleanup_records": [],
        "budget_counts": {
            "planner_query_count": 0,
            "execution_attempt_count": 0,
            "recovery_attempt_count": 0,
        },
        "status": "running",
    }
    _write(output / "receipt.json", aggregate)

    if family == "F3":
        diagnostic_program = next(item for item in programs if item["program_id"] == "F3-VHVH")
        repair = F3ConditionalRepairOrchestratorV1_1(adapter).run(
            output_dir=output / "repair_gate",
            planned_root_slot_spec=planned,
            program=diagnostic_program,
        )
        aggregate["repair_gate"] = {"path": "repair_gate/receipt.json", "status": repair["status"]}
        aggregate["cleanup_records"].extend(repair.get("cleanup_records", []))
        aggregate["budget_counts"]["planner_query_count"] += sum(
            int(item.get("planner_solvability_query_count", 0))
            + int(item.get("rollout_planner_query_count", 0))
            for item in repair.get("planner_query_count_by_run", [])
        )
        aggregate["budget_counts"]["execution_attempt_count"] += int(repair.get("diagnostic_execution_count", 0))
        aggregate["budget_counts"]["execution_attempt_count"] += int(repair.get("correction_execution_count", 0))
        if repair.get("repair_probe_pass") is not True:
            aggregate["status"] = repair["status"]
            aggregate["scene_created"] = any(item.get("scene_created") is True for item in aggregate["cleanup_records"])
            aggregate["scene_cleanup_succeeded"] = bool(aggregate["cleanup_records"]) and all(
                item.get("cleanup_safety_pass") is True for item in aggregate["cleanup_records"]
            )
            aggregate["orphan_process_count"] = sum(int(item.get("orphan_process_count") or 0) for item in aggregate["cleanup_records"])
            _write(output / "receipt.json", aggregate)
            return 1
    elif family == "F4":
        repair_program = next(item for item in programs if item["program_id"] == "F4-ABC")
        repair = FamilyRepairOrchestratorV1_1(adapter).run(
            output_dir=output / "repair_gate",
            planned_root_slot_spec=planned,
            program=repair_program,
        )
        aggregate["repair_gate"] = {"path": "repair_gate/receipt.json", "status": repair["status"]}
        aggregate["cleanup_records"].extend(repair.get("cleanup_records", []))
        aggregate["budget_counts"]["planner_query_count"] += int(
            repair.get("planner_solvability_query_count_total", 0)
        ) + int(repair.get("rollout_planner_query_count") or 0)
        aggregate["budget_counts"]["execution_attempt_count"] += int(repair.get("execution_attempt_count", 0))
        if repair.get("repair_probe_pass") is not True:
            aggregate["status"] = repair["status"]
            aggregate["scene_created"] = any(item.get("scene_created") is True for item in aggregate["cleanup_records"])
            aggregate["scene_cleanup_succeeded"] = bool(aggregate["cleanup_records"]) and all(
                item.get("cleanup_safety_pass") is True for item in aggregate["cleanup_records"]
            )
            aggregate["orphan_process_count"] = sum(int(item.get("orphan_process_count") or 0) for item in aggregate["cleanup_records"])
            _write(output / "receipt.json", aggregate)
            return 1

    root = RealSapienPilotRootOrchestratorV1_1(
        adapter,
        implementation_version="controlled_multi_future_runtime_v3_2",
    ).run_nonformal_root(
        output_dir=output / "root",
        planned_root_slot_spec=planned,
        realization_spec_by_program={
            program["program_id"]: {
                "realization": "r_pc",
                "formal_data": False,
                "stage0_data": False,
            }
            for program in programs
        },
    )
    aggregate["root_receipt"] = {"path": "root/root_receipt.json", "status": root["status"]}
    aggregate["branch_receipts"] = list(root.get("branch_receipts", []))
    aggregate["cleanup_records"].extend(root.get("cleanup_records", []))
    aggregate["budget_counts"]["planner_query_count"] += _root_planner_count(root)
    aggregate["budget_counts"]["execution_attempt_count"] += len(root.get("branch_receipts", []))
    aggregate["root_finalization"] = root.get("root_finalization")
    aggregate["status"] = "accepted" if root.get("status") == "accepted" else root.get("status", "failed_execution")
    aggregate["scene_created"] = any(item.get("scene_created") is True for item in aggregate["cleanup_records"])
    aggregate["scene_cleanup_succeeded"] = bool(aggregate["cleanup_records"]) and all(
        item.get("cleanup_safety_pass") is True for item in aggregate["cleanup_records"]
    )
    aggregate["orphan_process_count"] = sum(
        int(item.get("orphan_process_count") or 0) for item in aggregate["cleanup_records"]
    )
    aggregate["budget_validation"] = validate_runtime_receipt_against_budget(scope, aggregate)
    _write(output / "receipt.json", aggregate)
    return 0 if aggregate["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
