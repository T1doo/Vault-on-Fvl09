"""Authorized launcher for one F2/F3/F4 runtime-v3_1 repair program."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ..family_repair_orchestrator_v1_1 import FamilyRepairOrchestratorV1_1
from ..families import F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from ..real_sapien_adapter_v1_1 import RoboTwinRealSapienPilotRootAdapterV1_1
from .runtime_v3_1_authorization import load_runtime_v3_1_authorization


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
    receipt = FamilyRepairOrchestratorV1_1(adapter).run(
        output_dir=args.output / "repair",
        planned_root_slot_spec=planned,
        program=program,
    )
    (args.output / "launcher_receipt.json").write_text(
        json.dumps({"authorization_receipt_sha256": authorization["receipt_sha256"], "repair_status": receipt["status"], "formal_data": False, "stage0_data": False}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if receipt.get("repair_probe_pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
