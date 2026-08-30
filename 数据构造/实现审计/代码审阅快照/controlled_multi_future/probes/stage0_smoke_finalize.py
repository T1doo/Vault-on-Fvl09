"""Canonical CPU-only production entrypoint for Stage 0 finalization."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ..stage0_smoke_finalizer_v1 import (
    finalize_stage0_smoke_v1,
)
from ..stage0_smoke_scope_bundle_v1 import CANONICAL_STAGE0_MANIFEST


CANONICAL_OUTPUT = Path(
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/"
    "STAGE0_SMOKE_RESULT_V1_20260830.json"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=CANONICAL_STAGE0_MANIFEST)
    parser.add_argument("--output", type=Path, default=CANONICAL_OUTPUT)
    args = parser.parse_args()
    if args.manifest.resolve() != CANONICAL_STAGE0_MANIFEST.resolve():
        raise ValueError("Stage 0 finalizer manifest path is not canonical")
    if args.output.resolve() != CANONICAL_OUTPUT.resolve():
        raise ValueError("Stage 0 finalizer output path is not canonical")
    if args.output.exists():
        raise FileExistsError("Stage 0 final receipt must be new")
    result = finalize_stage0_smoke_v1(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return 0 if result["stage0_completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
