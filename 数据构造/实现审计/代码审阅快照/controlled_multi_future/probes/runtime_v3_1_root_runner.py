"""Real runtime-v3_1 root runner; execution requires a sealed authorization."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ..families import F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from ..real_sapien_adapter_v1_2 import RoboTwinRealSapienPilotRootAdapterV1_2
from ..root_orchestrator_v1_1 import RealSapienPilotRootOrchestratorV1_1
from ..runtime_v3_1_budget_v1_2 import validate_runtime_receipt_against_budget
from .gpu_guard_v2_2 import require_atomic_gpu_guard_v2_2
from .runtime_v3_1_authorization_v1_2 import (
    authorization_summary,
    load_authorization_v1_2,
    load_consumption_receipt,
)


FAMILIES = {"F1": F1ObjectSelection, "F2": F2TargetRelation, "F3": F3MotionOrder, "F4": F4SubtaskOrder}
SCOPE_FAMILIES = {
    "F1_three_branch_nonformal_probe": "F1",
    "F2_workspace_and_three_branch_nonformal_probe": "F2",
    "F3_release_and_full_program_nonformal_probe": "F3",
    "F4_common_carry_and_full_program_nonformal_probe": "F4",
    "real_sapien_root_integration_nonformal_probe": "F1",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.authorization_receipt.read_text(encoding="utf-8"))
    scopes = raw.get("approved_scopes")
    if not isinstance(scopes, list) or len(scopes) != 1 or scopes[0] not in SCOPE_FAMILIES:
        raise PermissionError("root runner authorization scope is not supported")
    scope = scopes[0]
    expected_family = SCOPE_FAMILIES[scope]
    authorization = load_authorization_v1_2(
        args.authorization_receipt,
        requested_scope=scope,
        expected_family=expected_family,
    )
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("root child requires bound guard and consumption receipts")
    consumption = load_consumption_receipt(Path(consumption_path), authorization)
    guard_value = json.loads(Path(guard_path).read_text(encoding="utf-8"))
    binding = guard_value.get("binding", {})
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
    family = authorization["family"]
    output = Path(authorization["output_namespace"])
    programs = FAMILIES[family]().checked_provisional_programs()
    planned = dict(authorization["planned_root_slot_spec"])
    adapter = RoboTwinRealSapienPilotRootAdapterV1_2(family=family, output_root=output / "scene_work")
    receipt = RealSapienPilotRootOrchestratorV1_1(adapter).run_nonformal_root(
        output_dir=output / "root",
        planned_root_slot_spec=planned,
        realization_spec_by_program={program["program_id"]: {"realization": "r_pc", "formal_data": False, "stage0_data": False} for program in programs},
    )
    budget_validation = validate_runtime_receipt_against_budget(scope, receipt)
    cleanup_records = receipt.get("cleanup_records", [])
    launcher = {
        "schema_version": "cmf_runtime_v3_1_root_launcher_v1",
        "authorization": authorization_summary(authorization),
        "authorization_consumption_receipt_sha256": consumption["consumption_receipt_sha256"],
        "guard_binding": guard["binding"],
        "guard_precheck": guard["precheck"],
        "budget_validation": budget_validation,
        "root_status": receipt["status"],
        "root_receipt": "root/root_receipt.json",
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
    return 0 if receipt["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
