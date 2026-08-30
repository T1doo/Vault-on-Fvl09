"""One-shot guarded child entrypoint for runtime-v3_4 diagnosis-first scopes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import traceback

from ..f3_grasp_three_context_gate_v10 import (
    F3GraspDiagnosticAdapterV10,
    F3GraspThreeContextGateV10,
)
from ..f4_bc_ab_gate_v10 import F4BCABExecutionGateV10
from ..f4_corridor_a_gate_v10 import F4CorridorAExecutionGateV10
from ..families import F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from ..real_sapien_adapter_v1_4 import RoboTwinRealSapienStrictPrefixAdapterV1_4
from ..root_orchestrator_v1_2 import RealSapienStrictPrefixRootOrchestratorV1_2
from ..runtime_v3_4_budget_v1 import (
    FULL_ROOT_SCOPES,
    SCOPE_FAMILIES,
    validate_runtime_receipt_against_budget,
    validate_static_scope_activity_envelope,
)
from ..single_program_strict_prefix_gate_v1 import SingleProgramStrictPrefixGateV1
from .gpu_guard_v2_4 import require_atomic_gpu_guard_v2_4
from .runtime_v3_4_authorization_v1 import (
    authorization_summary,
    load_authorization_v3_4,
    load_consumption_receipt,
)


SCHEMA_VERSION = "cmf_runtime_v3_4_guarded_scope_receipt_v1"
FAMILY_CLASSES = {
    "F1": F1ObjectSelection,
    "F2": F2TargetRelation,
    "F3": F3MotionOrder,
    "F4": F4SubtaskOrder,
}


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _cleanup_summary(records) -> dict:
    values = [dict(item) for item in records]
    return {
        "scene_created": any(item.get("scene_created") is True for item in values),
        "scene_cleanup_succeeded": bool(values)
        and all(
            item.get("cleanup_safety_pass") is True
            and int(item.get("orphan_process_count") or 0) == 0
            for item in values
        ),
        "orphan_process_count": sum(
            int(item.get("orphan_process_count") or 0) for item in values
        ),
    }


def _root(adapter, output, planned):
    programs = FAMILY_CLASSES[adapter.family]().checked_provisional_programs()
    realization = {
        item["program_id"]: {
            "realization": "r_pc",
            "formal_data": False,
            "stage0_data": False,
        }
        for item in programs
    }
    return RealSapienStrictPrefixRootOrchestratorV1_2(adapter).run_nonformal_root(
        output_dir=output,
        planned_root_slot_spec=planned,
        realization_spec_by_program=realization,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.authorization_receipt.read_text(encoding="utf-8"))
    scopes = raw.get("approved_scopes")
    if not isinstance(scopes, list) or len(scopes) != 1:
        raise PermissionError("runtime-v3_4 runner requires exactly one scope")
    scope = str(scopes[0])
    family = SCOPE_FAMILIES.get(scope)
    if family is None:
        raise PermissionError("runtime-v3_4 runner scope is unsupported")
    authorization = load_authorization_v3_4(
        args.authorization_receipt,
        requested_scope=scope,
        expected_family=family,
    )
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("runtime-v3_4 child lacks Guard/consumption binding")
    consumption = load_consumption_receipt(Path(consumption_path), authorization)
    guard_value = json.loads(Path(guard_path).read_text(encoding="utf-8"))
    binding = guard_value.get("binding", {})
    physical_index = int(binding.get("physical_gpu_index"))
    expected_uuid = str(binding.get("expected_gpu_uuid"))
    if os.environ.get("CUDA_VISIBLE_DEVICES") != expected_uuid:
        raise RuntimeError("CUDA_VISIBLE_DEVICES differs from guarded UUID")
    guard = require_atomic_gpu_guard_v2_4(
        authorization,
        consumption,
        expected_uuid=expected_uuid,
        physical_index=physical_index,
    )
    output = Path(authorization["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    planned = dict(authorization["planned_root_slot_spec"])
    aggregate = {
        "schema_version": SCHEMA_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_4",
        "implementation_strategy": "diagnosis_first_multi_gpu_convergence",
        "authorization": authorization_summary(authorization),
        "authorization_consumption_receipt_sha256": consumption[
            "consumption_receipt_sha256"
        ],
        "guard_binding": guard["binding"],
        "guard_precheck": guard["precheck"],
        "scope": scope,
        "family": family,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "result": None,
        "cleanup_records": [],
        "budget_counts": {
            "planner_query_count": 0,
            "execution_attempt_count": 0,
            "recovery_attempt_count": 0,
        },
        "status": "running",
    }
    _write(output / "receipt.json", aggregate)
    dispatched = False
    returned = False
    try:
        aggregate["static_activity_envelope"] = (
            validate_static_scope_activity_envelope(scope)
        )
        adapter_class = (
            F3GraspDiagnosticAdapterV10
            if scope == "F3_grasp_three_context_v10"
            else RoboTwinRealSapienStrictPrefixAdapterV1_4
        )
        adapter = adapter_class(
            family=family,
            output_root=output / "scene_work",
            expected_implementation_source_sha256=authorization[
                "implementation_source_sha256"
            ],
        )
        dispatched = True
        if scope == "F2_inside_targeted_v10":
            relative = "F2_inside_targeted/receipt.json"
            result = SingleProgramStrictPrefixGateV1(
                adapter,
                program_id="F2-inside",
                gate_id="F2_inside_targeted_v10",
            ).run(
                output_dir=output / "F2_inside_targeted",
                planned_root_slot_spec=planned,
            )
            passed = result.get("pass") is True
        elif scope == "F3_grasp_three_context_v10":
            relative = "F3_grasp_three_context/receipt.json"
            result = F3GraspThreeContextGateV10(adapter).run(
                output_dir=output / "F3_grasp_three_context",
                planned_root_slot_spec=planned,
            )
            passed = result.get("pass") is True
        elif scope == "F4_corridor_A_v10":
            relative = "F4_corridor_A/receipt.json"
            result = F4CorridorAExecutionGateV10(adapter).run(
                output_dir=output / "F4_corridor_A",
                planned_root_slot_spec=planned,
            )
            passed = result.get("pass") is True
        elif scope == "F4_BC_AB_v10":
            relative = "F4_BC_AB/receipt.json"
            result = F4BCABExecutionGateV10(adapter).run(
                output_dir=output / "F4_BC_AB",
                planned_root_slot_spec=planned,
            )
            passed = result.get("pass") is True
        elif scope in FULL_ROOT_SCOPES:
            if family == "F4":
                prerequisite = planned["prerequisite_receipts"][
                    "F4_corridor_A_v10"
                ]
                planned["selected_f4_corridor_id"] = prerequisite[
                    "selected_corridor_id"
                ]
            relative = "root/root_receipt.json"
            result = _root(adapter, output / "root", planned)
            passed = result.get("status") == "accepted"
        else:
            raise ValueError("runtime-v3_4 scope dispatch is incomplete")
        returned = True
        aggregate["result"] = {
            "relative_receipt_path": relative,
            "status": result.get("status"),
            "pass": passed,
        }
        aggregate["cleanup_records"] = list(result.get("cleanup_records", []))
        aggregate["budget_counts"] = dict(result.get("budget_counts", {}))
        aggregate["budget_validation"] = validate_runtime_receipt_against_budget(
            scope, aggregate
        )
        cleanup = _cleanup_summary(aggregate["cleanup_records"])
        aggregate.update(cleanup)
        aggregate["status"] = (
            "accepted"
            if passed and cleanup["scene_cleanup_succeeded"]
            else "failed_cleanup_uncertain"
            if not cleanup["scene_cleanup_succeeded"]
            else result.get("status", "failed_execution")
        )
    except BaseException as exc:
        cleanup = _cleanup_summary(aggregate["cleanup_records"])
        aggregate["status"] = (
            "failed_cleanup_uncertain"
            if dispatched and (not returned or not cleanup["scene_cleanup_succeeded"])
            else "failed_execution"
        )
        aggregate["error_type"] = type(exc).__name__
        aggregate["error"] = str(exc)
        aggregate["traceback"] = traceback.format_exc()
        aggregate.update(cleanup)
    _write(output / "receipt.json", aggregate)
    return 0 if aggregate["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
