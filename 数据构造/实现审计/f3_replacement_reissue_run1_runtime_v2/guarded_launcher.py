#!/usr/bin/env python3
"""Guard wrapper for the budget-complete F3 V2 reissue."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys


RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from job_runner import file_sha, load_manifest, preflight  # noqa: E402


BASE_GUARD = Path(
    "/nfs_share/lijunhui/Robotwin2/production_micro_gate_v1/guarded_launcher.py"
)
BASE_GUARD_SHA256 = "d666db0b9059c0abed5473024873919531dfff60d8f56346067909c357597210"


def load_base_guard():
    if file_sha(BASE_GUARD) != BASE_GUARD_SHA256:
        raise RuntimeError("sealed base Guard changed")
    spec = importlib.util.spec_from_file_location("cmf_f3_reissue_v2_base_guard", BASE_GUARD)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load sealed base Guard")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--physical-index", type=int, choices=range(8))
    parser.add_argument("--expected-uuid")
    args = parser.parse_args(argv)
    if args.preflight_only:
        print(json.dumps(preflight(args.manifest, args.job_id), sort_keys=True))
        return 0
    if args.physical_index is None or args.expected_uuid is None:
        raise ValueError("F3 V2 runtime Guard requires GPU index and UUID")
    load_manifest(args.manifest, args.job_id, phase="guard")
    base = load_base_guard()
    base.load_manifest = lambda path: load_manifest(
        Path(path), args.job_id, phase="guard"
    )[0]
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
