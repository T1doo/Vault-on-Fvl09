"""Real runtime-v3_1 root runner; execution requires a sealed authorization."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ..families import F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from ..real_sapien_adapter_v1_1 import RoboTwinRealSapienPilotRootAdapterV1_1
from ..root_orchestrator_v1_1 import RealSapienPilotRootOrchestratorV1_1
from .runtime_v3_1_authorization import load_runtime_v3_1_authorization, require_atomic_gpu_guard


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
    guard = require_atomic_gpu_guard(expected_uuid=args.expected_uuid, physical_index=args.physical_index)
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
    cleanup_records = receipt.get("cleanup_records", [])
    launcher = {
        "schema_version": "cmf_runtime_v3_1_root_launcher_v1",
        "authorization": authorization,
        "guard_precheck": guard,
        "root_status": receipt["status"],
        "root_receipt": "root/root_receipt.json",
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
    return 0 if receipt["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
