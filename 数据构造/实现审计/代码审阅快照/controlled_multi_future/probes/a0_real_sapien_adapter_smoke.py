"""Current v5 entry point for a future one-shot real-SAPIEN A0 smoke."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ..a0_orchestrator_v1_2 import A0CurrentAnchorOrchestratorV1_2
from ..real_sapien_adapter_v1_2 import RoboTwinRealSapienPilotRootAdapterV1_2
from ..runtime_v3_1_budget_v1_2 import validate_runtime_receipt_against_budget
from .gpu_guard_v2_2 import require_atomic_gpu_guard_v2_2
from .runtime_v3_1_authorization_v1_2 import (
    authorization_summary,
    load_authorization_v1_2,
    load_consumption_receipt,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    authorization = load_authorization_v1_2(
        args.authorization_receipt,
        requested_scope="A0_current_anchor_smoke",
        expected_family="F1",
        expected_seed=20260829,
    )
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("A0 child requires bound guard and consumption receipts")
    consumption = load_consumption_receipt(Path(consumption_path), authorization)
    guard_value = json.loads(Path(guard_path).read_text(encoding="utf-8"))
    binding = guard_value.get("binding")
    if not isinstance(binding, dict):
        raise PermissionError("A0 guard binding is missing")
    physical_index = binding.get("physical_gpu_index")
    expected_uuid = binding.get("expected_gpu_uuid")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != expected_uuid:
        raise RuntimeError("CUDA_VISIBLE_DEVICES must equal the freshly guarded UUID")
    guard = require_atomic_gpu_guard_v2_2(
        authorization,
        consumption,
        expected_uuid=expected_uuid,
        physical_index=physical_index,
    )
    output = Path(authorization["output_namespace"])
    planned = dict(authorization["planned_root_slot_spec"])
    adapter = RoboTwinRealSapienPilotRootAdapterV1_2(
        family=authorization["family"],
        output_root=output / "scene_work",
    )
    authorization_metadata = authorization_summary(authorization)
    authorization_metadata.pop("planned_root_slot_spec_sha256")
    for protected_key in ("stage0_authorized", "formal_data", "stage0_data"):
        if authorization_metadata.pop(protected_key) is not False:
            raise PermissionError(f"authorization summary unexpectedly enabled {protected_key}")
    receipt = A0CurrentAnchorOrchestratorV1_2(adapter).run(
        output_dir=output,
        planned_root_slot_spec=planned,
        receipt_metadata={
            "timeout_seconds": authorization["timeout_seconds"],
            "physical_gpu_index": physical_index,
            "expected_gpu_uuid": expected_uuid,
            **authorization_metadata,
            "a0_execution_authorized_by_receipt": True,
            "authorization_consumption_receipt_sha256": consumption["consumption_receipt_sha256"],
            "guard_binding": guard["binding"],
            "guard_precheck": guard["precheck"],
        },
    )
    budget_validation = validate_runtime_receipt_against_budget("A0_current_anchor_smoke", receipt)
    receipt["budget_validation"] = budget_validation
    (output / "receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if receipt["status"] == "passed_nonformal_A0" else 1


if __name__ == "__main__":
    raise SystemExit(main())
