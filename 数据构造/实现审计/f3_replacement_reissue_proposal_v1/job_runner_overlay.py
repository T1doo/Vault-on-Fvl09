#!/usr/bin/env python3
"""Proposal-only overlay fixing the zero-scene F3 wrapper lookup error."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


OLD_RUNNER = Path(
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/"
    "f3_replacement_run1_runtime_v1/job_runner.py"
)
OLD_RUNNER_SHA256 = "36e447e8bc7b9909af4ac88dbf5930c83548d0f6c56db947e6797b7e1c3f4728"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_corrected_runner():
    if file_sha(OLD_RUNNER) != OLD_RUNNER_SHA256:
        raise RuntimeError("sealed failed F3 runner changed")
    spec = importlib.util.spec_from_file_location(
        "cmf_f3_failed_runner_for_overlay", OLD_RUNNER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import sealed failed F3 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    wrapper = module.base
    old_direct_adapter_for_present = callable(getattr(wrapper, "adapter_for", None))
    if old_direct_adapter_for_present:
        raise RuntimeError("sealed failure shape changed: outer wrapper now has adapter_for")
    helper = getattr(wrapper, "base", None)
    required = (
        "adapter_for",
        "opened_scene",
        "prepare_f3_scene",
        "record_physical_scene",
        "write_new",
    )
    if helper is None or not all(callable(getattr(helper, name, None)) for name in required):
        raise RuntimeError("F3 inner helper module is incomplete")
    module.base = helper
    return module, required, old_direct_adapter_for_present


def preflight():
    module, required, old_direct_adapter_for_present = load_corrected_runner()
    result = {
        "schema_version": "cmf_f3_replacement_reissue_wiring_preflight_v1",
        "old_runner_sha256": OLD_RUNNER_SHA256,
        "old_direct_adapter_for_present": old_direct_adapter_for_present,
        "inner_helper_path_resolved": True,
        "resolved_helper_module": module.base.__name__,
        "required_helper_callables": {
            name: callable(getattr(module.base, name, None)) for name in required
        },
        "replacement_candidates_started": 0,
        "scene_created": False,
        "gpu_context_created": False,
        "execution_authorized": False,
        "pass": True,
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true", required=True)
    args = parser.parse_args(argv)
    if not args.preflight_only:
        raise PermissionError("F3 reissue overlay is proposal-only")
    print(json.dumps(preflight(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
