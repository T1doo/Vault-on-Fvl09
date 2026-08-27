"""Minimal CUDA/SAPIEN/CuRobo certification for one explicitly selected GPU."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--physical-index", type=int, required=True, choices=(4, 5, 6, 7))
    parser.add_argument("--expected-uuid", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--render-timeout", type=int, default=120)
    args = parser.parse_args()

    started = time.time()
    receipt = {
        "schema_version": "cmf_environment_certification_v1",
        "purpose": "implementation_audit",
        "formal_data": False,
        "stage0_data": False,
        "attempt_limit": 1,
        "timeout_seconds": args.render_timeout,
        "physical_gpu_index": args.physical_index,
        "expected_gpu_uuid": args.expected_uuid,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "pid": os.getpid(),
        "status": "running",
    }
    try:
        if receipt["cuda_visible_devices"] != args.expected_uuid:
            raise RuntimeError("CUDA_VISIBLE_DEVICES does not match the audited UUID")

        import torch
        import sapien
        from envs.robot.planner import CuroboPlanner  # noqa: F401

        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise RuntimeError("selected child must see exactly one usable CUDA device")
        tensor_sum = float(torch.ones(1024, device="cuda").sum().item())
        torch.cuda.synchronize()

        render = subprocess.run(
            [sys.executable, "script/test_render.py"],
            cwd=Path(__file__).resolve().parents[2],
            text=True,
            capture_output=True,
            timeout=args.render_timeout,
            check=False,
            env=dict(os.environ),
        )
        if render.returncode != 0 or "Render Well" not in render.stdout:
            raise RuntimeError(f"official render check failed rc={render.returncode}")

        receipt.update({
            "status": "passed_nonformal_environment_certification",
            "torch_version": torch.__version__,
            "torch_cuda_build": torch.version.cuda,
            "cuda_device_name": torch.cuda.get_device_name(0),
            "tensor_sum": tensor_sum,
            "sapien_version": getattr(sapien, "__version__", "unknown"),
            "curobo_planner_import": "passed",
            "official_render_returncode": render.returncode,
            "official_render_well": True,
            "official_render_stdout_tail": render.stdout[-2000:],
            "official_render_stderr_tail": render.stderr[-2000:],
        })
        return_code = 0
    except BaseException as exc:
        receipt.update({
            "status": "failed_nonformal_environment_certification",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        })
        return_code = 1
    finally:
        receipt["elapsed_seconds"] = time.time() - started
        _write(args.output, receipt)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
