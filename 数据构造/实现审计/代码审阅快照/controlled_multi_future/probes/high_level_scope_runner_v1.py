"""Atomic-Guard child dispatcher for high-level candidate jobs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import traceback

from ..canonical_artifact import canonical_hash_json, canonical_write_json
from ..high_level_physical_runner_v1 import HighLevelPhysicalRunnerV1
from ..high_level_planner_runner_v1 import HighLevelPlannerRunnerV1
from ..real_sapien_adapter_high_level_v1 import (
    RoboTwinRealSapienF2HierarchicalStageAV1Adapter,
    RoboTwinRealSapienF3AssetGraspV2Adapter,
    RoboTwinRealSapienF4HierarchicalStageAV1Adapter,
)
from .gpu_guard_v2_4 import require_atomic_gpu_guard_v2_4
from .high_level_authorization_v1 import (
    IMPLEMENTATION_VERSION,
    load,
    load_consumption,
)


def _load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _adapter(authorization, work: Path):
    common = {
        "output_root": work / "scene_work",
        "expected_implementation_source_sha256": authorization[
            "implementation_source_sha256"
        ],
        "planned_spec": authorization["planned_root_slot_spec"],
    }
    family = authorization["family"]
    if family == "F2":
        return RoboTwinRealSapienF2HierarchicalStageAV1Adapter(**common)
    if family == "F3":
        return RoboTwinRealSapienF3AssetGraspV2Adapter(**common)
    if family == "F4":
        return RoboTwinRealSapienF4HierarchicalStageAV1Adapter(**common)
    raise ValueError("high-level authorization family is unsupported")


def _dispatch(authorization, work: Path):
    adapter = _adapter(authorization, work)
    job_kind = authorization["job_kind"]
    spec = authorization["planned_root_slot_spec"]
    if job_kind in {
        "F2_STAGE_A_PLANNER",
        "F3_LEVEL1_PLANNER",
        "F4_STAGE_A_PLANNER",
        "F4_STAGE_B_PLANNER",
    }:
        result = HighLevelPlannerRunnerV1(adapter).run(
            output_dir=work / "candidate", planned_spec=spec
        )
    elif job_kind in {"F2_INSIDE_PHYSICAL", "F3_LEVEL2_PHYSICAL"}:
        result = HighLevelPhysicalRunnerV1(adapter).run(
            output_dir=work / "candidate", planned_spec=spec
        )
    else:
        raise ValueError("high-level job kind has no dispatcher")
    return {
        "result": result,
        "scope_completed": not str(result.get("status", "")).endswith(
            "infrastructure"
        )
        and result.get("status")
        not in {
            "planner_candidate_failed_execution_or_infrastructure",
            "physical_candidate_failed_execution_or_infrastructure",
        },
        "pass": result.get("pass") is True,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    raw = _load_json(args.authorization_receipt)
    scope = raw["approved_scopes"][0]
    authorization = load(args.authorization_receipt, requested_scope=scope)
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("high-level child lacks Guard binding")
    consumption = load_consumption(Path(consumption_path), authorization)
    guard_receipt = _load_json(Path(guard_path))
    binding = guard_receipt["binding"]
    physical_index = int(binding["physical_gpu_index"])
    gpu_uuid = str(binding["expected_gpu_uuid"])
    if os.environ.get("CUDA_VISIBLE_DEVICES") != gpu_uuid:
        raise RuntimeError("high-level child GPU UUID mismatch")
    guard = require_atomic_gpu_guard_v2_4(
        authorization,
        consumption,
        expected_uuid=gpu_uuid,
        physical_index=physical_index,
    )
    output = Path(authorization["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    outer = {
        "schema_version": "cmf_high_level_candidate_job_outer_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": authorization["authorization_id"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "authorization_consumption_receipt_sha256": consumption[
            "consumption_receipt_sha256"
        ],
        "job_kind": authorization["job_kind"],
        "family": authorization["family"],
        "scope": scope,
        "guard_binding": guard["binding"],
        "guard_precheck": guard["precheck"],
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
        "scope_completed": False,
        "pass": False,
        "status": "running",
        "result": None,
    }
    canonical_write_json(output / "receipt.json", outer, mode=0o600)
    try:
        dispatch = _dispatch(authorization, output / "work")
        outer["result"] = dispatch["result"]
        outer["scope_completed"] = dispatch["scope_completed"]
        outer["pass"] = dispatch["pass"]
        outer["status"] = (
            "completed_pass"
            if outer["pass"]
            else "completed_with_failure_evidence"
            if outer["scope_completed"]
            else "failed_infrastructure"
        )
    except BaseException as exc:
        outer["status"] = "failed_infrastructure"
        outer["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    outer["receipt_sha256"] = canonical_hash_json(outer)
    canonical_write_json(output / "receipt.json", outer, mode=0o600)
    return 0 if outer["scope_completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
