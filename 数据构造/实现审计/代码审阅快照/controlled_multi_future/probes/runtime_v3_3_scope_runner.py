"""One-shot guarded entrypoint for bounded runtime-v3_3 scopes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import traceback

from ..canonical_prefix_smoke_v1 import CanonicalPrefixRealSmokeV1
from ..f4_cube_grasp_ik_audit_v1 import F4CubeGraspIKAuditV1
from ..f4_staged_block_gate_v1 import F4StagedBlockExecutionGateV1
from ..families import F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from ..real_sapien_adapter_v1_3 import RoboTwinRealSapienStrictPrefixAdapterV1_3
from ..root_orchestrator_v1_2 import RealSapienStrictPrefixRootOrchestratorV1_2
from ..runtime_v3_3_budget_v1 import ROOT_SCOPES, validate_runtime_receipt_against_budget
from .gpu_guard_v2_4 import require_atomic_gpu_guard_v2_4
from .runtime_v3_3_authorization_v1 import (
    authorization_summary,
    load_authorization_v3_3,
    load_consumption_receipt,
)


SCOPE_FAMILIES = {
    "canonical_prefix_real_smoke": "F1",
    "F4_cube_grasp_no_action_ik": "F4",
    "F1_planner_root_per_revision": "F1",
    "F2_diagnosis_root_per_revision": "F2",
    "F3_prefix_root_per_revision": "F3",
    "F4_block_root_per_revision": "F4",
}
FAMILY_CLASSES = {
    "F1": F1ObjectSelection,
    "F2": F2TargetRelation,
    "F3": F3MotionOrder,
    "F4": F4SubtaskOrder,
}
SCHEMA_VERSION = "cmf_runtime_v3_3_guarded_scope_receipt_v1"


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _cleanup_summary(records) -> dict:
    records = [dict(item) for item in records]
    return {
        "scene_created": any(item.get("scene_created") is True for item in records),
        "scene_cleanup_succeeded": bool(records)
        and all(
            item.get("cleanup_safety_pass") is True
            and int(item.get("orphan_process_count") or 0) == 0
            for item in records
        ),
        "orphan_process_count": sum(
            int(item.get("orphan_process_count") or 0) for item in records
        ),
    }


def _result_budget_counts(scope: str, result) -> dict:
    if scope in ROOT_SCOPES:
        value = result.get("budget_counts")
        if not isinstance(value, dict):
            raise ValueError("strict-prefix root lacks authoritative budget_counts")
        return dict(value)
    if scope == "canonical_prefix_real_smoke":
        return {
            "planner_query_count": int(result["planner_query_count"]),
            "execution_attempt_count": int(result["execution_attempt_count"]),
            "recovery_attempt_count": int(result["recovery_attempt_count"]),
        }
    if scope == "F4_cube_grasp_no_action_ik":
        return {
            "planner_query_count": int(result["planner_query_count"]),
            "execution_attempt_count": int(result["execution_attempt_count"]),
            "recovery_attempt_count": 0,
        }
    raise ValueError(f"unsupported runtime-v3_3 scope {scope}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.authorization_receipt.read_text(encoding="utf-8"))
    scopes = raw.get("approved_scopes")
    if not isinstance(scopes, list) or len(scopes) != 1:
        raise PermissionError("runtime-v3_3 runner requires exactly one scope")
    scope = scopes[0]
    if scope not in SCOPE_FAMILIES:
        raise PermissionError("runtime-v3_3 runner received an unsupported scope")
    family = SCOPE_FAMILIES[scope]
    authorization = load_authorization_v3_3(
        args.authorization_receipt,
        requested_scope=scope,
        expected_family=family,
    )
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("runtime-v3_3 child lacks guard/consumption binding")
    consumption = load_consumption_receipt(Path(consumption_path), authorization)
    guard_value = json.loads(Path(guard_path).read_text(encoding="utf-8"))
    binding = guard_value.get("binding", {})
    physical_index = binding.get("physical_gpu_index")
    expected_uuid = binding.get("expected_gpu_uuid")
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
        "implementation_version": "controlled_multi_future_runtime_v3_3",
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
    try:
        adapter = RoboTwinRealSapienStrictPrefixAdapterV1_3(
            family=family, output_root=output / "scene_work"
        )
        if scope == "canonical_prefix_real_smoke":
            relative_receipt = "canonical_prefix_smoke/receipt.json"
            result = CanonicalPrefixRealSmokeV1(adapter).run(
                output_dir=output / "canonical_prefix_smoke",
                planned_root_slot_spec=planned,
            )
            passed = result.get("status") == "passed_canonical_prefix_real_smoke"
        elif scope == "F4_cube_grasp_no_action_ik":
            relative_receipt = "f4_cube_grasp_ik/receipt.json"
            result = F4CubeGraspIKAuditV1(adapter).run(
                output_dir=output / "f4_cube_grasp_ik",
                planned_root_slot_spec=planned,
            )
            passed = result.get("status") == "passed_f4_cube_grasp_no_action_ik"
        else:
            programs = FAMILY_CLASSES[family]().checked_provisional_programs()
            realization_specs = {
                item["program_id"]: {
                    "realization": "r_pc",
                    "formal_data": False,
                    "stage0_data": False,
                }
                for item in programs
            }
            if scope == "F4_block_root_per_revision":
                gate = F4StagedBlockExecutionGateV1(adapter).run(
                    output_dir=output / "f4_staged_gate",
                    planned_root_slot_spec=planned,
                )
                if gate.get("status") != "passed_f4_staged_block_gate":
                    relative_receipt = "f4_staged_gate/receipt.json"
                    result = {
                        "status": gate.get("status"),
                        "cleanup_records": list(gate.get("cleanup_records", [])),
                        "budget_counts": {
                            "planner_query_count": int(
                                gate.get("planner_query_count", 0)
                            ),
                            "execution_attempt_count": int(
                                gate.get("execution_attempt_count", 0)
                            ),
                            "recovery_attempt_count": 0,
                        },
                    }
                    passed = False
                else:
                    root = RealSapienStrictPrefixRootOrchestratorV1_2(
                        adapter
                    ).run_nonformal_root(
                        output_dir=output / "root",
                        planned_root_slot_spec=planned,
                        realization_spec_by_program=realization_specs,
                    )
                    relative_receipt = "root/root_receipt.json"
                    result = {
                        "status": root.get("status"),
                        "cleanup_records": list(gate.get("cleanup_records", []))
                        + list(root.get("cleanup_records", [])),
                        "budget_counts": {
                            "planner_query_count": int(
                                gate.get("planner_query_count", 0)
                            )
                            + int(
                                root.get("budget_counts", {}).get(
                                    "planner_query_count", 0
                                )
                            ),
                            "execution_attempt_count": int(
                                gate.get("execution_attempt_count", 0)
                            )
                            + int(
                                root.get("budget_counts", {}).get(
                                    "execution_attempt_count", 0
                                )
                            ),
                            "recovery_attempt_count": 0,
                        },
                        "staged_gate": {
                            "relative_receipt_path": "f4_staged_gate/receipt.json",
                            "status": gate.get("status"),
                        },
                        "root": root,
                    }
                    passed = root.get("status") == "accepted"
            else:
                relative_receipt = "root/root_receipt.json"
                result = RealSapienStrictPrefixRootOrchestratorV1_2(
                    adapter
                ).run_nonformal_root(
                    output_dir=output / "root",
                    planned_root_slot_spec=planned,
                    realization_spec_by_program=realization_specs,
                )
                passed = result.get("status") == "accepted"
        aggregate["result"] = {
            "relative_receipt_path": relative_receipt,
            "status": result.get("status"),
        }
        aggregate["cleanup_records"] = list(result.get("cleanup_records", []))
        aggregate["budget_counts"] = _result_budget_counts(scope, result)
        aggregate["budget_validation"] = validate_runtime_receipt_against_budget(
            scope, aggregate
        )
        cleanup = _cleanup_summary(aggregate["cleanup_records"])
        aggregate.update(cleanup)
        if cleanup["scene_cleanup_succeeded"] is not True:
            aggregate["status"] = "failed_cleanup_uncertain"
        else:
            aggregate["status"] = "accepted" if passed else result.get(
                "status", "failed_execution"
            )
    except BaseException as exc:
        aggregate["status"] = "failed_cleanup_uncertain" if any(
            item.get("cleanup_safety_pass") is not True
            for item in aggregate["cleanup_records"]
        ) else "failed_execution"
        aggregate["error_type"] = type(exc).__name__
        aggregate["error"] = str(exc)
        aggregate["traceback"] = traceback.format_exc()
        aggregate.update(_cleanup_summary(aggregate["cleanup_records"]))
    _write(output / "receipt.json", aggregate)
    return 0 if aggregate["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
