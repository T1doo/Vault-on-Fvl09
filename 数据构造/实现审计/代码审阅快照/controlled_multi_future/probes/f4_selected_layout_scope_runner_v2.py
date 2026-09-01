"""Guarded child for the one selected F4 V2 layout planner-only Gate."""

from __future__ import annotations

import argparse
import json
import os
import traceback
from pathlib import Path

from ..canonical_artifact import canonical_write_json
from ..f4_layout_candidate_search_v2 import (
    IMPLEMENTATION_VERSION,
    finalize_single_selected_layout_dispatch_v2,
    validate_selected_layout_runtime_binding_v2,
)
from ..f4_post_stage0_planner_only_v1 import F4PostStage0PlannerOnlyV1
from ..f4_selected_layout_scope_v2 import SCOPE, budget
from ..real_sapien_adapter_f4_selected_layout_v2 import (
    RoboTwinRealSapienF4SelectedLayoutV2Adapter,
)
from .f4_selected_layout_authorization_v2 import load, load_consumption, summary
from .gpu_guard_v2_4 import require_atomic_gpu_guard_v2_4


def _write(path, value):
    canonical_write_json(path, value)


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
    visibility = list(result.get("rendered_visibility_receipts", []))
    checks = {
        "planner": 0 <= int(counts.get("planner_query_count", -1)) <= 96,
        "prefix": 0
        <= int(counts.get("canonical_prefix_reference_execution_count", -1))
        <= 1,
        "suffix_execution": int(counts.get("suffix_execution_attempt_count", -1))
        == 0,
        "release": int(counts.get("release_execution_count", -1)) == 0,
        "recovery": int(counts.get("recovery_attempt_count", -1)) == 0,
        "scenes": len(result.get("cleanup_records", [])) <= 4,
        "visibility_receipts": len(visibility) <= 4
        and all(item.get("pass") is True for item in visibility),
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
        expected_family="F4",
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
    planned = authorization["planned_root_slot_spec"]
    runtime_binding = validate_selected_layout_runtime_binding_v2(planned)
    dispatch = planned["f4_single_selected_layout_dispatch_v2"]
    output = Path(authorization["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    aggregate = {
        "schema_version": "cmf_f4_selected_layout_v2_outer",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "family": "F4",
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
        "selected_layout_runtime_binding_v2": {
            key: value for key, value in runtime_binding.items() if key != "candidate"
        },
        "result": None,
        "dispatch_terminal": None,
        "cleanup_records": [],
        "budget_counts": {},
        "status": "running",
        "automatic_fallback": False,
        "later_candidate_attempt_allowed": False,
    }
    _write(output / "receipt.json", aggregate)
    try:
        adapter = RoboTwinRealSapienF4SelectedLayoutV2Adapter(
            family="F4",
            output_root=output / "scene_work",
            expected_implementation_source_sha256=authorization[
                "implementation_source_sha256"
            ],
        )
        result = F4PostStage0PlannerOnlyV1(
            adapter, implementation_version=IMPLEMENTATION_VERSION
        ).run(
            output_dir=output / "F4SelectedLayoutV2PlannerOnly",
            planned_root_slot_spec=planned,
        )
        visibility = list(result.get("rendered_visibility_receipts", []))
        visibility_pass = len(visibility) == 4 and all(
            item.get("pass") is True for item in visibility
        )
        dispatch_terminal = finalize_single_selected_layout_dispatch_v2(
            dispatch,
            attempted_candidate_id=runtime_binding["candidate_id"],
            complete_planner_only_pass=result.get("pass") is True,
            rendered_segmentation_visibility_pass=visibility_pass,
        )
        aggregate["result"] = {
            "relative_receipt_path": "F4SelectedLayoutV2PlannerOnly/receipt.json",
            "status": result.get("status"),
            "pass": result.get("pass") is True,
            "receipt_sha256": result.get("receipt_sha256"),
            "rendered_visibility_receipt_count": len(visibility),
            "rendered_visibility_pass": visibility_pass,
        }
        aggregate["dispatch_terminal"] = dispatch_terminal
        aggregate["cleanup_records"] = list(result.get("cleanup_records", []))
        aggregate["budget_counts"] = dict(result.get("budget_counts", {}))
        aggregate["budget_validation"] = _budget(result)
        cleanup = _cleanup(aggregate["cleanup_records"])
        aggregate.update(cleanup)
        aggregate["status"] = (
            "accepted"
            if dispatch_terminal["pass"] is True
            and cleanup["scene_cleanup_succeeded"]
            else "failed_cleanup_uncertain"
            if not cleanup["scene_cleanup_succeeded"]
            else "failed_selected_layout_no_fallback"
        )
    except BaseException as exc:
        inner_path = output / "F4SelectedLayoutV2PlannerOnly/receipt.json"
        if inner_path.is_file():
            result = json.loads(inner_path.read_text(encoding="utf-8"))
            aggregate["result"] = {
                "relative_receipt_path": "F4SelectedLayoutV2PlannerOnly/receipt.json",
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
            else "failed_selected_layout_no_fallback"
        )
        aggregate["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    aggregate["pass"] = aggregate["status"] == "accepted"
    aggregate["failure_requires_higher_level_redesign"] = not aggregate["pass"]
    _write(output / "receipt.json", aggregate)
    return 0 if aggregate["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
