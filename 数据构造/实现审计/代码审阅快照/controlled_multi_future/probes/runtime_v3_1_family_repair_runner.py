"""Authorized launcher for one F2/F3/F4 runtime-v3_1 repair program."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ..family_repair_orchestrator_v1_1 import FamilyRepairOrchestratorV1_1
from ..f3_conditional_repair_orchestrator_v1_1 import F3ConditionalRepairOrchestratorV1_1
from ..families import F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from ..real_sapien_adapter_v1_1 import RoboTwinRealSapienPilotRootAdapterV1_1
from .runtime_v3_1_authorization import load_runtime_v3_1_authorization, require_atomic_gpu_guard


PROGRAMS = {
    "F2": (F2TargetRelation, "F2-beside"),
    "F3": (F3MotionOrder, "F3-VHVH"),
    "F4": (F4SubtaskOrder, "F4-ABC"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=tuple(PROGRAMS), required=True)
    parser.add_argument("--physical-index", type=int, choices=tuple(range(8)), required=True)
    parser.add_argument("--expected-uuid", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    scope = f"{args.family}_bounded_nonformal_probe"
    authorization = load_runtime_v3_1_authorization(args.authorization_receipt, requested_scope=scope)
    if os.environ.get("CUDA_VISIBLE_DEVICES") != args.expected_uuid:
        raise RuntimeError("CUDA_VISIBLE_DEVICES must equal the freshly guarded UUID")
    guard = require_atomic_gpu_guard(expected_uuid=args.expected_uuid, physical_index=args.physical_index)
    family_cls, program_id = PROGRAMS[args.family]
    program = next(item for item in family_cls().checked_provisional_programs() if item["program_id"] == program_id)
    planned = {
        "slot_id": f"runtime_v3_1_{args.family.lower()}_repair",
        "family": args.family,
        "seed": 20260829,
        "origin": "bounded_nonformal_repair_probe",
        "authorization_receipt_sha256": authorization["receipt_sha256"],
    }
    args.output.mkdir(parents=True, exist_ok=False)
    adapter = RoboTwinRealSapienPilotRootAdapterV1_1(family=args.family, output_root=args.output / "scene_work")
    if args.family == "F3":
        receipt = F3ConditionalRepairOrchestratorV1_1(adapter).run(
            output_dir=args.output / "repair",
            planned_root_slot_spec=planned,
            program=program,
        )
    else:
        receipt = FamilyRepairOrchestratorV1_1(adapter).run(
            output_dir=args.output / "repair",
            planned_root_slot_spec=planned,
            program=program,
        )
    cleanup_records = receipt.get("cleanup_records", [])
    launcher = {
        "schema_version": "cmf_runtime_v3_1_family_repair_launcher_v1",
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "guard_precheck": guard,
        "repair_status": receipt["status"],
        "repair_receipt": "repair/receipt.json",
        "formal_data": False,
        "stage0_data": False,
        "scene_created": any(item.get("scene_created") is True for item in cleanup_records),
        "scene_cleanup_succeeded": bool(cleanup_records) and all(item.get("cleanup_safety_pass") is True for item in cleanup_records),
        "orphan_process_count": sum(int(item.get("orphan_process_count") or 0) for item in cleanup_records),
        "status": receipt["status"],
    }
    (args.output / "receipt.json").write_text(
        json.dumps(launcher, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if receipt.get("repair_probe_pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
