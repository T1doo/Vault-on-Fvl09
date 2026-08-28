"""Real runtime-v3_1 root runner; execution requires a sealed authorization."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ..families import F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from ..real_sapien_adapter_v1_1 import RoboTwinRealSapienPilotRootAdapterV1_1
from ..root_orchestrator_v1_1 import RealSapienPilotRootOrchestratorV1_1
from .runtime_v3_1_authorization import load_runtime_v3_1_authorization


FAMILIES = {"F1": F1ObjectSelection, "F2": F2TargetRelation, "F3": F3MotionOrder, "F4": F4SubtaskOrder}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=("F1",), required=True)
    parser.add_argument("--physical-index", type=int, choices=tuple(range(8)), required=True)
    parser.add_argument("--expected-uuid", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    scope = f"{args.family}_bounded_nonformal_probe"
    authorization = load_runtime_v3_1_authorization(args.authorization_receipt, requested_scope=scope)
    if os.environ.get("CUDA_VISIBLE_DEVICES") != args.expected_uuid:
        raise RuntimeError("CUDA_VISIBLE_DEVICES must equal the freshly guarded UUID")
    programs = FAMILIES[args.family]().checked_provisional_programs()
    planned = {
        "slot_id": f"runtime_v3_1_{args.family.lower()}_nonformal",
        "family": args.family,
        "seed": 20260829,
        "origin": "bounded_nonformal_probe",
        "authorization_receipt_sha256": authorization["receipt_sha256"],
    }
    adapter = RoboTwinRealSapienPilotRootAdapterV1_1(family=args.family, output_root=args.output / "scene_work")
    receipt = RealSapienPilotRootOrchestratorV1_1(adapter).run_nonformal_root(
        output_dir=args.output / "root",
        planned_root_slot_spec=planned,
        realization_spec_by_program={program["program_id"]: {"realization": "r_pc", "formal_data": False, "stage0_data": False} for program in programs},
    )
    (args.output / "launcher_receipt.json").write_text(
        json.dumps({"authorization": authorization, "root_status": receipt["status"], "formal_data": False, "stage0_data": False}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if receipt["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
