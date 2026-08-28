"""Guarded entry point for the currently unauthorized real-SAPIEN A0 smoke."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from ..a0_orchestrator_v1_1 import A0CurrentAnchorOrchestratorV1_1
from ..real_sapien_adapter_v1_1 import RoboTwinRealSapienPilotRootAdapterV1_1
from .runtime_v3_1_authorization import authorization_summary, load_runtime_v3_1_authorization, require_atomic_gpu_guard


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=("F1", "F2", "F3", "F4"), required=True)
    parser.add_argument("--physical-index", type=int, choices=tuple(range(8)), required=True)
    parser.add_argument("--expected-uuid", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    authorization = load_runtime_v3_1_authorization(args.authorization_receipt, requested_scope="A0_current_anchor_smoke")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != args.expected_uuid:
        raise RuntimeError("CUDA_VISIBLE_DEVICES must equal the freshly guarded UUID")
    guard = require_atomic_gpu_guard(expected_uuid=args.expected_uuid, physical_index=args.physical_index)
    adapter = RoboTwinRealSapienPilotRootAdapterV1_1(family=args.family, output_root=args.output / "scene_work")
    planned = {"slot_id": "runtime_v3_1_A0", "family": args.family, "seed": 20260829}
    authorization_metadata = authorization_summary(authorization)
    for protected_key in ("stage0_authorized", "formal_data", "stage0_data"):
        if authorization_metadata.pop(protected_key) is not False:
            raise PermissionError(f"authorization summary unexpectedly enabled {protected_key}")
    receipt = A0CurrentAnchorOrchestratorV1_1(adapter).run(
        output_dir=args.output,
        planned_root_slot_spec=planned,
        receipt_metadata={
            "timeout_seconds": 600,
            "physical_gpu_index": args.physical_index,
            "expected_gpu_uuid": args.expected_uuid,
            **authorization_metadata,
            "guard_precheck": guard,
        },
    )
    return 0 if receipt["status"] == "passed_nonformal_A0" else 1


if __name__ == "__main__":
    raise SystemExit(main())
