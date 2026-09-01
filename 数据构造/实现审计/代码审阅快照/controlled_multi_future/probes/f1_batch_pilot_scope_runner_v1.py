"""Guard-bound child entrypoint for one F1 family batch-pilot job."""

from __future__ import annotations

import argparse
import json
import os
import traceback
from pathlib import Path

from ..canonical_artifact import canonical_write_json
from ..f1_batch_generation_pilot_v1 import IMPLEMENTATION_VERSION
from ..f1_batch_pilot_root_runner_v1 import F1BatchPilotRootRunnerV1
from ..f1_batch_pilot_scope_runner_v1 import F1BatchPilotScopeRunnerV1
from ..f1_batch_pilot_scope_v1 import SCOPE
from ..real_sapien_adapter_f1_batch_v1 import RoboTwinRealSapienF1BatchPilotAdapterV1
from .f1_batch_pilot_authorization_v1 import load, load_consumption, summary
from .gpu_guard_v2_4 import require_atomic_gpu_guard_v2_4


def _write(path, value):
    canonical_write_json(path, value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    authorization = load(
        args.authorization_receipt,
        requested_scope=SCOPE,
        expected_family="F1",
        expected_seed=2026083101,
    )
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("Guard binding missing")
    consumption = load_consumption(Path(consumption_path), authorization)
    guard_receipt = json.loads(Path(guard_path).read_text(encoding="utf-8"))
    binding = guard_receipt["binding"]
    physical_index = int(binding["physical_gpu_index"])
    gpu_uuid = str(binding["expected_gpu_uuid"])
    if os.environ.get("CUDA_VISIBLE_DEVICES") != gpu_uuid:
        raise RuntimeError("UUID mismatch")
    guard = require_atomic_gpu_guard_v2_4(
        authorization,
        consumption,
        expected_uuid=gpu_uuid,
        physical_index=physical_index,
    )
    output = Path(authorization["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    aggregate = {
        "schema_version": "cmf_f1_batch_pilot_outer_receipt_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "family": "F1",
        "authorization": summary(authorization),
        "authorization_consumption_receipt_sha256": consumption[
            "consumption_receipt_sha256"
        ],
        "guard_binding": guard["binding"],
        "guard_precheck": guard["precheck"],
        "batch_result": None,
        "status": "running",
        "pass": False,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage1_authorized": False,
    }
    _write(output / "receipt.json", aggregate)

    def adapter_factory(slot, attempt_dir):
        return RoboTwinRealSapienF1BatchPilotAdapterV1(
            family="F1",
            output_root=attempt_dir / "scene_work",
            expected_implementation_source_sha256=authorization[
                "implementation_source_sha256"
            ],
        )

    try:
        result = F1BatchPilotScopeRunnerV1(
            adapter_factory=adapter_factory,
            root_runner_factory=F1BatchPilotRootRunnerV1,
        ).run(
            output_dir=output / "batch",
            plan=authorization["planned_root_slot_spec"]["plan"],
        )
        aggregate["batch_result"] = {
            "relative_receipt_path": "batch/f1_batch_scope_receipt.json",
            "receipt_sha256": result.get("receipt_sha256"),
            "scope_terminal": result.get("scope_terminal"),
            "five_accepted_roots": result.get("five_accepted_roots"),
            "stop_reason": result.get("stop_reason"),
            "budget_validation": result.get("budget_validation"),
        }
        aggregate["status"] = (
            "completed_five_accepted_roots"
            if result.get("five_accepted_roots") is True
            else "completed_reserve_exhausted"
            if result.get("scope_terminal") is True
            else "failed_nonterminal_or_cleanup_uncertain"
        )
        aggregate["pass"] = result.get("pass") is True
    except BaseException as exc:
        partial_path = output / "batch/f1_batch_scope_receipt.json"
        if partial_path.is_file():
            partial = json.loads(partial_path.read_text(encoding="utf-8"))
            aggregate["batch_result"] = {
                "relative_receipt_path": "batch/f1_batch_scope_receipt.json",
                "receipt_sha256": partial.get("receipt_sha256"),
                "partial": True,
            }
        aggregate["status"] = "failed_infrastructure"
        aggregate["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    _write(output / "receipt.json", aggregate)
    return 0 if aggregate["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
