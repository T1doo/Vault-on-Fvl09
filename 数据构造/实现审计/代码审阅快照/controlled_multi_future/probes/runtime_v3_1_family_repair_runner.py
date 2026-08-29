"""Authorized launcher for one F2/F3/F4 runtime-v3_1 repair program."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ..family_repair_orchestrator_v1_1 import FamilyRepairOrchestratorV1_1
from ..f3_conditional_repair_orchestrator_v1_1 import F3ConditionalRepairOrchestratorV1_1
from ..families import F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from ..real_sapien_adapter_v1_2 import RoboTwinRealSapienPilotRootAdapterV1_2
from ..runtime_v3_1_budget_v1_1 import validate_runtime_receipt_against_budget
from .gpu_guard_v2_1 import require_atomic_gpu_guard_v2_1
from .runtime_v3_1_authorization_v1_1 import (
    authorization_summary,
    load_authorization_v1_1,
    load_consumption_receipt,
)


PROGRAMS = {
    "F2": (F2TargetRelation, "F2-beside"),
    "F3": (F3MotionOrder, "F3-VHVH"),
    "F4": (F4SubtaskOrder, "F4-ABC"),
}
SCOPES = {
    "F2": "F2_beside_nonformal_probe",
    "F3": "F3_release_diagnosis_nonformal_probe",
    "F4": "F4_common_carry_nonformal_probe",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.authorization_receipt.read_text(encoding="utf-8"))
    scopes = raw.get("approved_scopes")
    if not isinstance(scopes, list) or len(scopes) != 1:
        raise PermissionError("family repair runner requires one scope")
    scope = scopes[0]
    family = next((name for name, expected in SCOPES.items() if expected == scope), None)
    if family is None:
        raise PermissionError("family repair authorization scope is unsupported")
    authorization = load_authorization_v1_1(
        args.authorization_receipt,
        requested_scope=scope,
        expected_family=family,
    )
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("family repair child requires bound guard and consumption receipts")
    consumption = load_consumption_receipt(Path(consumption_path), authorization)
    guard_value = json.loads(Path(guard_path).read_text(encoding="utf-8"))
    binding = guard_value.get("binding", {})
    physical_index = binding.get("physical_gpu_index")
    expected_uuid = binding.get("expected_gpu_uuid")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != expected_uuid:
        raise RuntimeError("CUDA_VISIBLE_DEVICES must equal the freshly guarded UUID")
    guard = require_atomic_gpu_guard_v2_1(
        authorization,
        consumption,
        expected_uuid=expected_uuid,
        physical_index=physical_index,
    )
    family_cls, program_id = PROGRAMS[family]
    program = next(item for item in family_cls().checked_provisional_programs() if item["program_id"] == program_id)
    planned = dict(authorization["planned_root_slot_spec"])
    output = Path(authorization["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    adapter = RoboTwinRealSapienPilotRootAdapterV1_2(family=family, output_root=output / "scene_work")
    if family == "F3":
        receipt = F3ConditionalRepairOrchestratorV1_1(adapter).run(
            output_dir=output / "repair",
            planned_root_slot_spec=planned,
            program=program,
        )
    else:
        receipt = FamilyRepairOrchestratorV1_1(adapter).run(
            output_dir=output / "repair",
            planned_root_slot_spec=planned,
            program=program,
        )
    budget_validation = validate_runtime_receipt_against_budget(scope, receipt)
    cleanup_records = receipt.get("cleanup_records", [])
    launcher = {
        "schema_version": "cmf_runtime_v3_1_family_repair_launcher_v1",
        "authorization": authorization_summary(authorization),
        "authorization_consumption_receipt_sha256": consumption["consumption_receipt_sha256"],
        "guard_binding": guard["binding"],
        "guard_precheck": guard["precheck"],
        "budget_validation": budget_validation,
        "repair_status": receipt["status"],
        "repair_receipt": "repair/receipt.json",
        "formal_data": False,
        "stage0_data": False,
        "scene_created": any(item.get("scene_created") is True for item in cleanup_records),
        "scene_cleanup_succeeded": bool(cleanup_records) and all(item.get("cleanup_safety_pass") is True for item in cleanup_records),
        "orphan_process_count": sum(int(item.get("orphan_process_count") or 0) for item in cleanup_records),
        "status": receipt["status"],
    }
    (output / "receipt.json").write_text(
        json.dumps(launcher, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if receipt.get("repair_probe_pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
