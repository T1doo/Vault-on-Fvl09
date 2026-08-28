"""A0 zero-action real-SAPIEN current/anchor smoke (currently unauthorized)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
import traceback

from ..anchor import compare_anchors
from ..current_hasher import require_same_current
from ..real_sapien_adapter_v1_1 import RoboTwinRealSapienPilotRootAdapterV1_1
from ..root_orchestrator_v1_1 import SceneHandleV1_1
from .runtime_v3_1_authorization import authorization_summary, load_runtime_v3_1_authorization, require_atomic_gpu_guard


def _write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=("F1", "F2", "F3", "F4"), required=True)
    parser.add_argument("--physical-index", type=int, choices=tuple(range(8)), required=True)
    parser.add_argument("--expected-uuid", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args()
    authorization = load_runtime_v3_1_authorization(args.authorization_receipt, requested_scope="A0_current_anchor_smoke")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != args.expected_uuid:
        raise RuntimeError("CUDA_VISIBLE_DEVICES must equal the freshly guarded UUID")
    guard = require_atomic_gpu_guard(expected_uuid=args.expected_uuid, physical_index=args.physical_index)
    args.output.mkdir(parents=True, exist_ok=False)
    receipt = {
        "schema_version": "cmf_runtime_v3_1_a0_smoke_v1",
        "implementation_version": "controlled_multi_future_runtime_v3_1",
        "purpose": "implementation_audit",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "planner_query_limit": 0,
        "action_execution_count": 0,
        "timeout_seconds": 600,
        "physical_gpu_index": args.physical_index,
        "expected_gpu_uuid": args.expected_uuid,
        **authorization_summary(authorization),
        "guard_precheck": guard,
        "status": "running",
        "scenes": [],
    }
    started = time.time()
    adapter = RoboTwinRealSapienPilotRootAdapterV1_1(family=args.family, output_root=args.output / "scene_work")
    planned = {"slot_id": "runtime_v3_1_A0", "family": args.family, "seed": 20260829}
    reference_current = None
    reference_anchor = None
    try:
        for index, phase in enumerate(("A0_pristine", "A0_fresh_1", "A0_fresh_2", "A0_fresh_3")):
            context = adapter.scene(planned, phase=phase)
            handle = None
            current = None
            anchor = None
            body_error = None
            try:
                with context as handle:
                    if not isinstance(handle, SceneHandleV1_1):
                        raise TypeError("adapter did not yield SceneHandleV1_1")
                    current = adapter.capture_current(handle.scene)
                    anchor = adapter.capture_anchor(handle.scene)
            except BaseException as exc:
                body_error = exc
            cleanup = handle.cleanup_receipt if handle is not None else getattr(context, "cleanup_receipt", None)
            scene_receipt = {
                "phase": phase,
                "scene_instance_id": cleanup and cleanup.get("scene_instance_id"),
                "current": current,
                "anchor": anchor,
                "cleanup": cleanup,
            }
            receipt["scenes"].append(scene_receipt)
            if not isinstance(cleanup, dict) or cleanup.get("cleanup_safety_pass") is not True or cleanup.get("orphan_process_count") != 0:
                raise RuntimeError(f"A0 cleanup uncertain at {phase}")
            if body_error is not None:
                raise body_error
            if index == 0:
                reference_current = current
                reference_anchor = anchor
                _write(args.output / "reference_current.json", current)
                _write(args.output / "reference_anchor.json", anchor)
            else:
                require_same_current(reference_current, current)
                comparison = compare_anchors(reference_anchor, anchor)
                scene_receipt["anchor_equivalence"] = comparison
                if not comparison["equivalent"]:
                    raise RuntimeError(f"A0 anchor mismatch at {phase}: {comparison['failures']}")
        receipt["status"] = "passed_nonformal_A0"
        code = 0
    except BaseException as exc:
        receipt.update({"status": "failed_A0", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        code = 1
    receipt["elapsed_seconds"] = time.time() - started
    receipt["scene_created"] = any(item.get("cleanup", {}).get("scene_created") is True for item in receipt["scenes"])
    receipt["scene_cleanup_succeeded"] = bool(receipt["scenes"]) and all(item.get("cleanup", {}).get("cleanup_safety_pass") is True for item in receipt["scenes"])
    receipt["orphan_process_count"] = sum(int(item.get("cleanup", {}).get("orphan_process_count") or 0) for item in receipt["scenes"])
    _write(args.output / "receipt.json", receipt)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
