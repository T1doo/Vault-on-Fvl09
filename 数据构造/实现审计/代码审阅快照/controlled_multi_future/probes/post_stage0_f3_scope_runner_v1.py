"""Guarded child for the one post-Stage-0 F3 no-suffix diagnostic."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import traceback

from ..f3_contact_preserving_prefix_v11 import IMPLEMENTATION_VERSION
from ..f3_shared_prefix_no_suffix_diagnostic_v1 import (
    F3SharedPrefixNoSuffixDiagnosticV1,
)
from ..post_stage0_f3_scope_v1 import SCOPE, post_stage0_f3_budget_v1
from ..real_sapien_adapter_post_stage0_f3_v1 import (
    RoboTwinRealSapienPostStage0F3AdapterV1,
)
from .gpu_guard_v2_4 import require_atomic_gpu_guard_v2_4
from .post_stage0_f3_authorization_v1 import (
    authorization_summary,
    load_post_stage0_f3_authorization_v1,
    load_post_stage0_f3_consumption_v1,
)


SCHEMA_VERSION = "cmf_post_stage0_f3_guarded_scope_receipt_v1"


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


def _validate_budget(result) -> dict:
    budget = post_stage0_f3_budget_v1()
    counts = result.get("budget_counts", {})
    checks = {
        "planner_within_limit": 0
        <= int(counts.get("planner_query_count", -1))
        <= budget["planner_query_limit"],
        "execution_within_limit": 0
        <= int(counts.get("execution_attempt_count", -1))
        <= budget["execution_limit"],
        "recovery_zero": int(counts.get("recovery_attempt_count", -1)) == 0,
        "fresh_scene_limit": len(result.get("cleanup_records", []))
        <= budget["fresh_scene_limit"],
        "suffix_planner_zero": int(result.get("suffix_planner_query_count", -1)) == 0,
        "suffix_execution_zero": int(result.get("suffix_execution_count", -1)) == 0,
        "release_execution_zero": int(result.get("release_execution_count", -1)) == 0,
    }
    value = {"budget": budget, "checks": checks, "pass": all(checks.values())}
    if not value["pass"]:
        raise RuntimeError(f"post-Stage-0 F3 diagnostic exceeded budget: {checks}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    authorization = load_post_stage0_f3_authorization_v1(
        args.authorization_receipt,
        requested_scope=SCOPE,
        expected_family="F3",
        expected_seed=20260829,
    )
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("post-Stage-0 F3 child lacks Guard binding")
    consumption = load_post_stage0_f3_consumption_v1(
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
    output = Path(authorization["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    aggregate = {
        "schema_version": SCHEMA_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "family": "F3",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage0_reopened": False,
        "stage1_authorized": False,
        "authorization": authorization_summary(authorization),
        "authorization_consumption_receipt_sha256": consumption[
            "consumption_receipt_sha256"
        ],
        "guard_binding": guard["binding"],
        "guard_precheck": guard["precheck"],
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
        adapter = RoboTwinRealSapienPostStage0F3AdapterV1(
            family="F3",
            output_root=output / "scene_work",
            expected_implementation_source_sha256=authorization[
                "implementation_source_sha256"
            ],
        )
        result = F3SharedPrefixNoSuffixDiagnosticV1(adapter).run(
            output_dir=output / "F3_shared_prefix_no_suffix",
            planned_root_slot_spec=authorization["planned_root_slot_spec"],
        )
        aggregate["result"] = {
            "relative_receipt_path": "F3_shared_prefix_no_suffix/receipt.json",
            "status": result.get("status"),
            "pass": result.get("pass") is True,
            "receipt_sha256": result.get("receipt_sha256"),
        }
        aggregate["cleanup_records"] = list(result.get("cleanup_records", []))
        aggregate["budget_counts"] = dict(result.get("budget_counts", {}))
        aggregate["budget_validation"] = _validate_budget(result)
        cleanup = _cleanup_summary(aggregate["cleanup_records"])
        aggregate.update(cleanup)
        aggregate["status"] = (
            "accepted"
            if result.get("pass") is True and cleanup["scene_cleanup_succeeded"]
            else "failed_cleanup_uncertain"
            if not cleanup["scene_cleanup_succeeded"]
            else result.get("status", "failed_execution")
        )
    except BaseException as exc:
        partial_path = output / "F3_shared_prefix_no_suffix/receipt.json"
        if partial_path.is_file():
            partial = json.loads(partial_path.read_text(encoding="utf-8"))
            aggregate["result"] = {
                "relative_receipt_path": "F3_shared_prefix_no_suffix/receipt.json",
                "status": partial.get("status"),
                "pass": partial.get("pass") is True,
                "receipt_sha256": partial.get("receipt_sha256"),
                "partial_receipt_propagated": True,
            }
            aggregate["cleanup_records"] = list(
                partial.get("cleanup_records", [])
            )
            aggregate["budget_counts"] = dict(
                partial.get("budget_counts", aggregate["budget_counts"])
            )
        cleanup = _cleanup_summary(aggregate["cleanup_records"])
        aggregate.update(cleanup)
        aggregate["status"] = (
            "failed_cleanup_uncertain"
            if aggregate["scene_created"] and not cleanup["scene_cleanup_succeeded"]
            else "failed_execution"
        )
        aggregate["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    aggregate["pass"] = aggregate["status"] == "accepted"
    _write(output / "receipt.json", aggregate)
    return 0 if aggregate["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
