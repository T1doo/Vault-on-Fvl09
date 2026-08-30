"""CPU-only canonical Stage 0 manifest builder after the F4 infrastructure Gate."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ..stage0_smoke_manifest_v1 import (
    CANONICAL_INFRA_RECEIPT,
    build_stage0_smoke_manifest,
)


CANONICAL_OUTPUT = Path(
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/"
    "STAGE0_SMOKE_MANIFEST_V1_20260830.json"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--infra-receipt", type=Path, default=CANONICAL_INFRA_RECEIPT)
    parser.add_argument("--output", type=Path, default=CANONICAL_OUTPUT)
    args = parser.parse_args()
    if args.output.resolve() != CANONICAL_OUTPUT.resolve():
        raise ValueError("Stage 0 manifest output path is not canonical")
    if args.output.exists():
        raise FileExistsError("canonical Stage 0 manifest already exists")
    manifest = build_stage0_smoke_manifest(args.infra_receipt)
    data = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
