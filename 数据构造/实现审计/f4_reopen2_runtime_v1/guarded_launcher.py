#!/usr/bin/env python3
"""Executable F4 reopen2 Guard plus zero-GPU production-path preflight."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


RUNTIME_DIR = Path(__file__).resolve().parent
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from manifest_contract import (  # noqa: E402
    canonical_hash,
    file_sha,
    load_and_validate_manifest_job,
)


WORKSPACE = Path("/nfs_share/lijunhui")
ENV_PYTHON = WORKSPACE / "Robotwin2/env/bin/python"
BASE_GUARD = WORKSPACE / "Robotwin2/production_micro_gate_v1/guarded_launcher.py"
BASE_GUARD_SHA256 = "d666db0b9059c0abed5473024873919531dfff60d8f56346067909c357597210"


def _load_base_guard():
    if file_sha(BASE_GUARD) != BASE_GUARD_SHA256:
        raise RuntimeError("sealed base GPU Guard changed")
    spec = importlib.util.spec_from_file_location("cmf_f4_reopen2_base_guard", BASE_GUARD)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load sealed base GPU Guard")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def production_path_preflight(manifest_path: Path, job_id: str) -> dict:
    """Run exact Guard + runner validation and stop before lease/nvidia-smi."""

    validated = load_and_validate_manifest_job(manifest_path, job_id)
    output = Path(validated["output_namespace"])
    guard_directory = Path(validated["guard_directory"])
    cache_job = Path(validated["cache_directory"]) / job_id
    before = {
        "output_exists": output.exists(),
        "guard_directory_exists": guard_directory.exists(),
        "cache_job_exists": cache_job.exists(),
    }
    if any(before.values()):
        raise RuntimeError("F4 preflight requires pristine output/guard/cache paths")
    environment = dict(os.environ)
    for key in (
        "CUDA_VISIBLE_DEVICES",
        "CMF_GPU_GUARD_PHYSICAL_INDEX",
        "NVIDIA_VISIBLE_DEVICES",
    ):
        environment.pop(key, None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(WORKSPACE / "Robotwin2/project/RoboTwin")
    environment["CMF_F4_PREFLIGHT_NO_GPU"] = "1"
    runner = Path(validated["runner_path"])
    command = [
        str(ENV_PYTHON),
        str(runner),
        "--manifest",
        str(Path(manifest_path).resolve()),
        "--job-id",
        job_id,
        "--preflight-only",
    ]
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
        env=environment,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "F4 runner subprocess preflight failed: " + completed.stderr[-2000:]
        )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise RuntimeError("F4 runner preflight emitted unexpected stdout")
    runner_receipt = json.loads(lines[0])
    if runner_receipt.get("pass") is not True:
        raise RuntimeError("F4 runner dispatch preflight did not pass")
    after = {
        "output_exists": output.exists(),
        "guard_directory_exists": guard_directory.exists(),
        "cache_job_exists": cache_job.exists(),
    }
    if any(after.values()):
        raise RuntimeError("F4 CPU preflight created a forbidden runtime path")
    result = {
        "schema_version": "cmf_f4_reopen2_production_path_preflight_v1",
        "manifest_sha256": validated["manifest_sha256"],
        "job_id": job_id,
        "guard_shared_contract_validation": True,
        "runner_subprocess_command": command,
        "runner_subprocess_returncode": completed.returncode,
        "runner_dispatch_receipt": runner_receipt,
        "before_paths": before,
        "after_paths": after,
        "lease_acquisition_reached": False,
        "nvidia_smi_called": False,
        "gpu_context_created": False,
        "scene_created": False,
        "authorization_consumed": False,
        "pass": True,
    }
    result["receipt_sha256"] = canonical_hash(result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--physical-index", type=int, choices=range(8))
    parser.add_argument("--expected-uuid")
    args = parser.parse_args(argv)
    if args.preflight_only:
        if args.physical_index is not None or args.expected_uuid is not None:
            raise ValueError("CPU preflight must not receive a GPU binding")
        print(
            json.dumps(
                production_path_preflight(args.manifest, args.job_id),
                sort_keys=True,
                ensure_ascii=False,
            )
        )
        return 0
    if args.physical_index is None or args.expected_uuid is None:
        raise ValueError("runtime Guard requires physical index and UUID")
    validated = load_and_validate_manifest_job(args.manifest, args.job_id)
    base = _load_base_guard()

    def shared_loader(_path):
        return load_and_validate_manifest_job(args.manifest, args.job_id)["manifest"]

    base.load_manifest = shared_loader
    return base.main(
        [
            "--manifest",
            str(args.manifest),
            "--job-id",
            args.job_id,
            "--physical-index",
            str(args.physical_index),
            "--expected-uuid",
            args.expected_uuid,
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
