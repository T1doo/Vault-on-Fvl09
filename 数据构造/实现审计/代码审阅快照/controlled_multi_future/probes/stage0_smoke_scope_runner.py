"""Guarded child entrypoint for F4 hash validation and Stage 0 family smoke."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import traceback

from ..current_hasher import hash_json
from ..f4_corridor_selection_gate_v12 import F4CorridorSelectionGateV12
from ..real_sapien_adapter_v1_6 import RoboTwinRealSapienStage0SmokeAdapterV1_6
from ..stage0_smoke_budget_v1 import (
    F4_INFRA_SCOPE,
    SCOPE_FAMILIES,
    STAGE0_SCOPES,
    validate_runtime_counts,
)
from ..stage0_smoke_family_runner_v1 import Stage0SmokeFamilyRunnerV1
from ..root_orchestrator_v1_1 import _write_json
from .gpu_guard_v2_4 import require_atomic_gpu_guard_v2_4
from .stage0_smoke_authorization_v1 import (
    authorization_summary,
    load_consumption_receipt,
    load_stage0_smoke_authorization,
)


SCHEMA_VERSION = "cmf_stage0_smoke_guarded_scope_receipt_v1"


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.authorization_receipt.read_text(encoding="utf-8"))
    scopes = raw.get("approved_scopes")
    if not isinstance(scopes, list) or len(scopes) != 1:
        raise PermissionError("Stage 0 runner requires exactly one scope")
    scope = str(scopes[0])
    family = SCOPE_FAMILIES.get(scope)
    if family is None:
        raise PermissionError("Stage 0 runner scope is unsupported")
    authorization = load_stage0_smoke_authorization(
        args.authorization_receipt,
        requested_scope=scope,
        expected_family=family,
    )
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("Stage 0 child lacks Guard/consumption binding")
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
        "implementation_version": "controlled_multi_future_stage0_smoke_v1",
        "scope": scope,
        "family": family,
        "authorization": authorization_summary(authorization),
        "authorization_consumption_receipt_sha256": consumption[
            "consumption_receipt_sha256"
        ],
        "guard_binding": guard["binding"],
        "guard_precheck": guard["precheck"],
        "formal_data": False,
        "stage0_data": authorization["stage0_data"],
        "stage0_authorized": True,
        "status": "running",
        "pipeline_integrity_pass": False,
        "cleanup_records": [],
        "budget_counts": {
            "planner_query_count": 0,
            "execution_attempt_count": 0,
            "recovery_attempt_count": 0,
        },
    }
    _write_json(output / "receipt.json", aggregate)
    try:
        adapter = RoboTwinRealSapienStage0SmokeAdapterV1_6(
            family=family,
            output_root=output / "scene_work",
            expected_implementation_source_sha256=authorization[
                "implementation_source_sha256"
            ],
        )
        if scope == F4_INFRA_SCOPE:
            result = F4CorridorSelectionGateV12(adapter).run(
                output_dir=output / "F4_hash_infrastructure_v12",
                planned_root_slot_spec=planned,
            )
            hash_audit = result.get("hash_infrastructure_audit_v12", {})
            pipeline_pass = hash_audit.get("pass") is True
            aggregate.update(
                {
                    "result_relative_path": (
                        "F4_hash_infrastructure_v12/receipt.json"
                    ),
                    "hash_infrastructure_pass": pipeline_pass,
                    "corridor_selection_pass": result.get("pass") is True,
                    "selected_corridor_candidate_v11": result.get(
                        "selected_corridor_candidate_v11"
                    ),
                    "hash_infrastructure_audit_v12": hash_audit,
                    "status": (
                        "completed_f4_hash_infrastructure"
                        if pipeline_pass
                        else "failed_f4_hash_infrastructure"
                    ),
                }
            )
        elif scope in STAGE0_SCOPES:
            blocker = planned.get("f4_shared_preflight_blocker")
            result = Stage0SmokeFamilyRunnerV1(adapter).run(
                output_dir=output / "stage0_family",
                planned_root_slot_spec=planned,
                shared_preflight_blocker=blocker,
            )
            pipeline_pass = result.get("pipeline_integrity_pass") is True
            aggregate.update(
                {
                    "result_relative_path": (
                        "stage0_family/stage0_family_receipt.json"
                    ),
                    "stage0_family_outcome": result.get("outcome"),
                    "stage0_attempt_count": result.get(
                        "stage0_attempt_count"
                    ),
                    "successful_attempt_count": result.get(
                        "successful_attempt_count"
                    ),
                    "failed_attempt_count": result.get(
                        "failed_attempt_count"
                    ),
                    "generated_trajectory_count": result.get(
                        "generated_trajectory_count"
                    ),
                    "status": (
                        "completed_stage0_smoke"
                        if pipeline_pass
                        else "failed_stage0_pipeline_integrity"
                    ),
                }
            )
        else:
            raise ValueError("Stage 0 scope dispatch is incomplete")
        aggregate["cleanup_records"] = list(result.get("cleanup_records", []))
        aggregate["budget_counts"] = dict(result.get("budget_counts", {}))
        aggregate["budget_validation"] = validate_runtime_counts(
            scope, aggregate["budget_counts"]
        )
        cleanup = _cleanup_summary(aggregate["cleanup_records"])
        if not aggregate["cleanup_records"] and scope in STAGE0_SCOPES:
            cleanup = {
                "scene_created": False,
                "scene_cleanup_succeeded": result.get("cleanup_pass") is True,
                "orphan_process_count": int(
                    result.get("orphan_process_count", 0)
                ),
            }
        aggregate.update(cleanup)
        aggregate["pipeline_integrity_pass"] = bool(
            pipeline_pass and cleanup["scene_cleanup_succeeded"]
        )
        if not aggregate["pipeline_integrity_pass"]:
            aggregate["status"] = "failed_cleanup_or_pipeline_integrity"
    except BaseException as exc:
        cleanup = _cleanup_summary(aggregate["cleanup_records"])
        aggregate.update(cleanup)
        aggregate["status"] = (
            "failed_cleanup_uncertain"
            if aggregate["cleanup_records"]
            and not cleanup["scene_cleanup_succeeded"]
            else "failed_stage0_runner"
        )
        aggregate["error_type"] = type(exc).__name__
        aggregate["error"] = str(exc)
        aggregate["traceback"] = traceback.format_exc()
    payload = dict(aggregate)
    payload.pop("receipt_sha256", None)
    aggregate["receipt_sha256"] = hash_json(payload)
    _write_json(output / "receipt.json", aggregate)
    return 0 if aggregate["pipeline_integrity_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
