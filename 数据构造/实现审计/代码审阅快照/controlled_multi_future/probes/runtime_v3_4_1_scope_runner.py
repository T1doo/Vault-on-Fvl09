"""One-shot guarded child entrypoint for runtime-v3_4_1 scopes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import traceback

from ..common_scope_counter_schema_v3_4_1 import (
    build_execution_attempt_counts,
    build_planner_query_counts,
    build_primary_failure_cleanup_receipt,
)
from ..f3_three_context_diagnostic_runner_v11 import (
    F3ThreeContextDiagnosticRunnerV11,
)
from ..f4_bc_preflight_gate_v11 import F4BCPreflightGateV11
from ..f4_exact_corridor_a_gate_v11 import F4ExactCorridorAExecutionGateV11
from ..families import F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from ..real_sapien_adapter_v1_5 import RoboTwinRealSapienStrictPrefixAdapterV1_5
from ..root_orchestrator_v1_2 import RealSapienStrictPrefixRootOrchestratorV1_2
from ..runtime_v3_4_1_budget_v1 import (
    FULL_ROOT_SCOPES,
    SCOPE_FAMILIES,
    validate_runtime_receipt_against_budget,
    validate_static_scope_activity_envelope,
)
from ..single_program_strict_prefix_gate_v1_1 import SingleProgramStrictPrefixGateV1_1
from .gpu_guard_v2_4 import require_atomic_gpu_guard_v2_4
from .runtime_v3_4_1_authorization_v1 import (
    authorization_summary,
    load_authorization_v3_4_1,
    load_consumption_receipt,
)


SCHEMA_VERSION = "cmf_runtime_v3_4_1_guarded_scope_receipt_v1"
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


def _structured_counts(scope, result, budget_counts):
    planner_total = int(budget_counts.get("planner_query_count", 0))
    existing_planner = result.get("planner_query_counts")
    if isinstance(existing_planner, dict):
        planner_counts = existing_planner
    elif scope == "F1_shared_regression_v3_4_1":
        target = 0
        chain = 0
        for branch in result.get("branch_receipts", []):
            counts = branch.get("suffix_planner", {}).get(
                "planner_query_counts", {}
            )
            target += int(counts.get("target_construction", 0))
            chain += int(counts.get("suffix_control_chain", 0))
        canonical = planner_total - target - chain
        if canonical < 0:
            raise ValueError("F1 structured planner count exceeds scope total")
        planner_counts = build_planner_query_counts(
            canonical_prefix=canonical,
            target_construction=target,
            suffix_control_chain=chain,
        )
    else:
        # The targeted diagnostic/full-root receipt does not expose a stable
        # category split yet. Preserve the exact scope total without pretending
        # that an executable control cache contains every query.
        planner_counts = build_planner_query_counts(
            diagnostic_only=planner_total
        )
    execution_total = int(budget_counts.get("execution_attempt_count", 0))
    existing_execution = result.get("execution_attempt_counts")
    execution_counts = (
        existing_execution
        if isinstance(existing_execution, dict)
        else build_execution_attempt_counts(
            dispatch_started=execution_total,
            controller_entered=execution_total,
            terminal_receipt_written=execution_total,
        )
    )
    return planner_counts, execution_counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.authorization_receipt.read_text(encoding="utf-8"))
    scopes = raw.get("approved_scopes")
    if not isinstance(scopes, list) or len(scopes) != 1:
        raise PermissionError("runtime-v3_4_1 runner requires exactly one scope")
    scope = str(scopes[0])
    family = SCOPE_FAMILIES.get(scope)
    if family is None:
        raise PermissionError("runtime-v3_4_1 runner scope is unsupported")
    authorization = load_authorization_v3_4_1(
        args.authorization_receipt,
        requested_scope=scope,
        expected_family=family,
    )
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("runtime-v3_4_1 child lacks Guard/consumption binding")
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
        "implementation_version": "controlled_multi_future_runtime_v3_4_1",
        "implementation_strategy": "one_shot_postmortem_hardening",
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
    relative = None
    primary_failure = None
    try:
        aggregate["static_activity_envelope"] = (
            validate_static_scope_activity_envelope(scope)
        )
        adapter = RoboTwinRealSapienStrictPrefixAdapterV1_5(
            family=family,
            output_root=output / "scene_work",
            expected_implementation_source_sha256=authorization[
                "implementation_source_sha256"
            ],
        )
        dispatched = True
        if scope == "F2_inside_targeted_v11":
            relative = "F2_inside_targeted/receipt.json"
            result = SingleProgramStrictPrefixGateV1_1(
                adapter,
                program_id="F2-inside",
                gate_id="F2_inside_targeted_v11",
            ).run(
                output_dir=output / "F2_inside_targeted",
                planned_root_slot_spec=planned,
            )
            passed = result.get("pass") is True
        elif scope == "F3_three_context_targeted_v11":
            relative = "F3_three_context_targeted/receipt.json"
            result = F3ThreeContextDiagnosticRunnerV11(adapter).run(
                output_dir=output / "F3_three_context_targeted",
                planned_root_slot_spec=planned,
            )
            passed = result.get("pass") is True
        elif scope == "F4_exact_corridor_A_v11":
            relative = "F4_exact_corridor_A/receipt.json"
            result = F4ExactCorridorAExecutionGateV11(adapter).run(
                output_dir=output / "F4_exact_corridor_A",
                planned_root_slot_spec=planned,
            )
            passed = result.get("pass") is True
        elif scope == "F4_BC_preflight_v11":
            relative = "F4_BC_preflight/receipt.json"
            result = F4BCPreflightGateV11(adapter).run(
                output_dir=output / "F4_BC_preflight",
                planned_root_slot_spec=planned,
            )
            passed = result.get("pass") is True
        elif scope in FULL_ROOT_SCOPES:
            relative = "root/root_receipt.json"
            result = _root(adapter, output / "root", planned)
            passed = result.get("status") == "accepted"
        else:
            raise ValueError("runtime-v3_4_1 scope dispatch is incomplete")
        returned = True
        aggregate["result"] = {
            "relative_receipt_path": relative,
            "status": result.get("status"),
            "pass": passed,
        }
        aggregate["cleanup_records"] = list(result.get("cleanup_records", []))
        aggregate["budget_counts"] = dict(result.get("budget_counts", {}))
        (
            aggregate["planner_query_counts"],
            aggregate["execution_attempt_counts"],
        ) = _structured_counts(scope, result, aggregate["budget_counts"])
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
        if aggregate["status"] != "accepted":
            primary_failure = {
                "stage": "scope_result",
                "type": str(result.get("error_type") or result.get("status")),
                "message": str(
                    result.get("error")
                    or "targeted/full nonformal scope did not pass"
                ),
            }
    except BaseException as exc:
        primary_failure = {
            "stage": "scope_dispatch" if dispatched else "pre_dispatch",
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if relative is not None:
            partial_path = output / relative
            if partial_path.is_file():
                partial = json.loads(partial_path.read_text(encoding="utf-8"))
                aggregate["result"] = {
                    "relative_receipt_path": relative,
                    "status": partial.get("status"),
                    "pass": partial.get("pass") is True,
                    "partial_receipt_propagated": True,
                }
                aggregate["cleanup_records"] = list(
                    partial.get("cleanup_records", [])
                )
                aggregate["budget_counts"] = dict(
                    partial.get("budget_counts", aggregate["budget_counts"])
                )
                try:
                    (
                        aggregate["planner_query_counts"],
                        aggregate["execution_attempt_counts"],
                    ) = _structured_counts(
                        scope, partial, aggregate["budget_counts"]
                    )
                except BaseException as counter_exc:
                    aggregate["counter_propagation_error"] = {
                        "type": type(counter_exc).__name__,
                        "message": str(counter_exc),
                    }
        cleanup = _cleanup_summary(aggregate["cleanup_records"])
        aggregate["status"] = (
            "failed_cleanup_uncertain"
            if dispatched and not cleanup["scene_cleanup_succeeded"]
            else "failed_execution"
        )
        aggregate["error_type"] = type(exc).__name__
        aggregate["error"] = str(exc)
        aggregate["traceback"] = traceback.format_exc()
        aggregate.update(cleanup)
    cleanup = _cleanup_summary(aggregate["cleanup_records"])
    aggregate["primary_failure_cleanup"] = build_primary_failure_cleanup_receipt(
        primary_failure=primary_failure,
        cleanup_status={
            "attempted": bool(aggregate["cleanup_records"]),
            "passed": cleanup["scene_cleanup_succeeded"],
            "uncertainty": dispatched and not cleanup["scene_cleanup_succeeded"],
        },
        receipt_propagation_status=(
            "normal_return"
            if primary_failure is None
            else "partial_child_receipt_recovered"
            if aggregate.get("result", {}).get("partial_receipt_propagated")
            else "no_child_terminal_receipt_available"
        ),
    )
    _write(output / "receipt.json", aggregate)
    return 0 if aggregate["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
