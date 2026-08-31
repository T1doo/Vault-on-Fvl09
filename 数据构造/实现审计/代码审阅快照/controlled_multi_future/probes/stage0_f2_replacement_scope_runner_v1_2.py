"""Guarded child for the three F2 Stage-0 replacement attempts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import traceback

from ..current_hasher import hash_json
from ..real_sapien_adapter_v1_8 import (
    RoboTwinRealSapienF2ReplacementAdapterV1_8,
)
from ..root_orchestrator_v1_1 import _write_json
from ..stage0_f2_replacement_manifest_v1_2 import (
    CANONICAL_OUTPUT,
    IMPLEMENTATION_VERSION,
    SCOPE,
    f2_replacement_budget_v1_2,
    validate_stage0_f2_replacement_manifest_v1_2,
)
from ..stage0_f2_replacement_runner_v1_2 import (
    Stage0F2ReplacementRunnerV1_2,
)
from .gpu_guard_v2_4 import require_atomic_gpu_guard_v2_4
from .stage0_f2_replacement_authorization_v1_2 import (
    authorization_summary,
    load_stage0_f2_replacement_authorization_v1_2,
    load_stage0_f2_replacement_consumption_v1_2,
)


SCHEMA_VERSION = "cmf_stage0_f2_replacement_guarded_scope_receipt_v1_2"


def _cleanup(records) -> dict:
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


def _budget_validation(counts) -> dict:
    budget = f2_replacement_budget_v1_2()
    checks = {
        "planner": int(counts.get("planner_query_count", -1))
        <= budget["planner_query_limit"],
        "execution": int(counts.get("execution_attempt_count", -1))
        <= budget["execution_limit"],
        "recovery": int(counts.get("recovery_attempt_count", -1)) == 0,
    }
    return {"checks": checks, "pass": all(checks.values())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    authorization = load_stage0_f2_replacement_authorization_v1_2(
        args.authorization_receipt, requested_scope=SCOPE, expected_family="F2"
    )
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("F2 replacement child lacks Guard/consumption binding")
    consumption = load_stage0_f2_replacement_consumption_v1_2(
        Path(consumption_path), authorization
    )
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
    manifest = validate_stage0_f2_replacement_manifest_v1_2(
        json.loads(CANONICAL_OUTPUT.read_text(encoding="utf-8"))
    )
    output = Path(authorization["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    aggregate = {
        "schema_version": SCHEMA_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "family": "F2",
        "authorization": authorization_summary(authorization),
        "authorization_consumption_receipt_sha256": consumption[
            "consumption_receipt_sha256"
        ],
        "guard_binding": guard["binding"],
        "guard_precheck": guard["precheck"],
        "replacement_manifest_sha256": manifest["manifest_sha256"],
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
        "stage1_authorized": False,
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
        adapter = RoboTwinRealSapienF2ReplacementAdapterV1_8(
            family="F2",
            output_root=output / "scene_work",
            expected_implementation_source_sha256=authorization[
                "implementation_source_sha256"
            ],
        )
        result = Stage0F2ReplacementRunnerV1_2(adapter).run(
            output_dir=output / "stage0_f2_replacement",
            planned_root_slot_spec=manifest["replacement_root_spec"],
            replacement_manifest=manifest,
        )
        pipeline_pass = result.get("pipeline_integrity_pass") is True
        result_path = (
            output
            / "stage0_f2_replacement/stage0_f2_replacement_family_receipt.json"
        )
        if not result_path.is_file():
            raise ValueError("F2 replacement family receipt is missing")
        aggregate.update(
            {
                "result_relative_path": (
                    "stage0_f2_replacement/"
                    "stage0_f2_replacement_family_receipt.json"
                ),
                "result_receipt_file_sha256": hashlib.sha256(
                    result_path.read_bytes()
                ).hexdigest(),
                "result_receipt_payload_sha256": result.get("receipt_sha256"),
                "stage0_family_outcome": result.get("outcome"),
                "stage0_attempt_count": result.get("stage0_attempt_count"),
                "successful_attempt_count": result.get(
                    "successful_attempt_count"
                ),
                "failed_attempt_count": result.get("failed_attempt_count"),
                "generated_trajectory_count": result.get(
                    "generated_trajectory_count"
                ),
                "generated_video_count": result.get("generated_video_count"),
                "active_slot_terminal_evidence_valid": result.get(
                    "active_slot_terminal_evidence_valid"
                ),
                "cleanup_records": list(result.get("cleanup_records", [])),
                "budget_counts": dict(result.get("budget_counts", {})),
                "status": "completed_stage0_f2_replacement_v1_2"
                if pipeline_pass
                else "failed_stage0_f2_replacement_pipeline_integrity",
            }
        )
        cleanup = _cleanup(aggregate["cleanup_records"])
        aggregate.update(cleanup)
        aggregate["budget_validation"] = _budget_validation(
            aggregate["budget_counts"]
        )
        aggregate["pipeline_integrity_pass"] = bool(
            pipeline_pass
            and cleanup["scene_cleanup_succeeded"]
            and aggregate["budget_validation"]["pass"]
        )
        if not aggregate["pipeline_integrity_pass"]:
            aggregate["status"] = "failed_cleanup_or_pipeline_integrity"
    except BaseException as exc:
        cleanup = _cleanup(aggregate["cleanup_records"])
        aggregate.update(cleanup)
        aggregate["status"] = (
            "failed_cleanup_uncertain"
            if aggregate["cleanup_records"]
            and not cleanup["scene_cleanup_succeeded"]
            else "failed_stage0_f2_replacement_runner"
        )
        aggregate["error_type"] = type(exc).__name__
        aggregate["error"] = str(exc)
        aggregate["traceback"] = traceback.format_exc()
    payload = dict(aggregate)
    payload.pop("child_payload_sha256", None)
    aggregate["child_payload_sha256"] = hash_json(payload)
    _write_json(output / "receipt.json", aggregate)
    return 0 if aggregate["pipeline_integrity_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
