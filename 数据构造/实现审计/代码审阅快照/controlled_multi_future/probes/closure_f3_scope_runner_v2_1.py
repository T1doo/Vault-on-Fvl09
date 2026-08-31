"""Guarded child for the interface-fixed F3 V2_1 one-shot."""

from __future__ import annotations

import argparse
import json
import os
import traceback
from pathlib import Path

from ..closure_f3_scope_v2_1 import SCOPE, budget
from ..f3_common_grasp_prefix_v2_1 import IMPLEMENTATION_VERSION
from ..f3_shared_prefix_no_suffix_diagnostic_v1_1 import (
    F3SharedPrefixNoSuffixDiagnosticV1_1,
)
from ..real_sapien_adapter_closure_f3_v2_1 import (
    RoboTwinRealSapienClosureF3V2_1Adapter,
)
from .closure_f3_authorization_v2_1 import load, load_consumption, summary
from .gpu_guard_v2_4 import require_atomic_gpu_guard_v2_4


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _cleanup(rows):
    values = list(rows)
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


def _budget(result):
    frozen = budget()
    counts = result.get("budget_counts", {})
    checks = {
        "planner": 0 <= int(counts.get("planner_query_count", -1)) <= 16,
        "execution": 0 <= int(counts.get("execution_attempt_count", -1)) <= 3,
        "recovery": int(counts.get("recovery_attempt_count", -1)) == 0,
        "scene": len(result.get("cleanup_records", [])) <= 3,
        "suffix": int(result.get("suffix_planner_query_count", -1)) == 0
        and int(result.get("suffix_execution_count", -1)) == 0,
        "release": int(result.get("release_execution_count", -1)) == 0,
    }
    if not all(checks.values()):
        raise RuntimeError(f"budget {checks}")
    return {"checks": checks, "pass": True, "budget": frozen}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    authorization = load(
        args.authorization_receipt,
        requested_scope=SCOPE,
        expected_family="F3",
        expected_seed=20260829,
    )
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("Guard binding missing")
    consumption = load_consumption(Path(consumption_path), authorization)
    guard_receipt = json.loads(Path(guard_path).read_text(encoding="utf-8"))
    binding = guard_receipt["binding"]
    index = int(binding["physical_gpu_index"])
    uuid = str(binding["expected_gpu_uuid"])
    if os.environ.get("CUDA_VISIBLE_DEVICES") != uuid:
        raise RuntimeError("UUID mismatch")
    guard = require_atomic_gpu_guard_v2_4(
        authorization, consumption, expected_uuid=uuid, physical_index=index
    )
    output = Path(authorization["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    aggregate = {
        "schema_version": "cmf_post_stage0_f3_v2_1_outer",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "family": "F3",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage1_authorized": False,
        "authorization": summary(authorization),
        "authorization_consumption_receipt_sha256": consumption[
            "consumption_receipt_sha256"
        ],
        "guard_binding": guard["binding"],
        "guard_precheck": guard["precheck"],
        "result": None,
        "cleanup_records": [],
        "budget_counts": {},
        "status": "running",
    }
    _write(output / "receipt.json", aggregate)
    try:
        adapter = RoboTwinRealSapienClosureF3V2_1Adapter(
            family="F3",
            output_root=output / "scene_work",
            expected_implementation_source_sha256=authorization[
                "implementation_source_sha256"
            ],
        )
        result = F3SharedPrefixNoSuffixDiagnosticV1_1(adapter).run(
            output_dir=output / "F3CommonGraspPrefixV2_1",
            planned_root_slot_spec=authorization["planned_root_slot_spec"],
        )
        aggregate["result"] = {
            "relative_receipt_path": "F3CommonGraspPrefixV2_1/receipt.json",
            "status": result.get("status"),
            "pass": result.get("pass") is True,
            "receipt_sha256": result.get("receipt_sha256"),
        }
        aggregate["cleanup_records"] = list(result.get("cleanup_records", []))
        aggregate["budget_counts"] = dict(result.get("budget_counts", {}))
        aggregate["budget_validation"] = _budget(result)
        cleanup = _cleanup(aggregate["cleanup_records"])
        aggregate.update(cleanup)
        aggregate["status"] = (
            "accepted"
            if result.get("pass") is True and cleanup["scene_cleanup_succeeded"]
            else "failed_cleanup_uncertain"
            if not cleanup["scene_cleanup_succeeded"]
            else result.get("status", "failed_execution")
        )
    except BaseException as exc:
        inner_path = output / "F3CommonGraspPrefixV2_1/receipt.json"
        if inner_path.is_file():
            result = json.loads(inner_path.read_text(encoding="utf-8"))
            aggregate["result"] = {
                "relative_receipt_path": "F3CommonGraspPrefixV2_1/receipt.json",
                "status": result.get("status"),
                "pass": result.get("pass") is True,
                "receipt_sha256": result.get("receipt_sha256"),
                "partial": True,
            }
            aggregate["cleanup_records"] = list(result.get("cleanup_records", []))
            aggregate["budget_counts"] = dict(result.get("budget_counts", {}))
        cleanup = _cleanup(aggregate["cleanup_records"])
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
