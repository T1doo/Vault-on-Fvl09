"""CPU-only canonical builder for the Stage-0 v1.1 attempt manifest."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ..stage0_smoke_manifest_v1_1 import (
    CANONICAL_INFRA_RECEIPT,
    CANONICAL_OUTPUT,
    build_stage0_smoke_manifest_v1_1,
)


CANONICAL_MARKDOWN_OUTPUT = CANONICAL_OUTPUT.with_suffix(".md")


def _write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--infra-receipt", type=Path, default=CANONICAL_INFRA_RECEIPT)
    parser.add_argument("--output", type=Path, default=CANONICAL_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=CANONICAL_MARKDOWN_OUTPUT)
    args = parser.parse_args()
    if args.output.resolve() != CANONICAL_OUTPUT.resolve():
        raise ValueError("Stage 0 v1.1 manifest JSON path is not canonical")
    if args.markdown_output.resolve() != CANONICAL_MARKDOWN_OUTPUT.resolve():
        raise ValueError("Stage 0 v1.1 manifest Markdown path is not canonical")
    if args.output.exists() or args.markdown_output.exists():
        raise FileExistsError("canonical Stage 0 v1.1 manifest already exists")
    manifest = build_stage0_smoke_manifest_v1_1(args.infra_receipt)
    _write_new(
        args.output,
        (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    )
    markdown = (
        "# Stage 0 Smoke Attempt Manifest V1\n\n"
        f"- implementation: `{manifest['implementation_version']}`\n"
        f"- manifest SHA-256: `{manifest['manifest_sha256']}`\n"
        "- planned attempts: `4 families × 3 r_pc = 12`\n"
        f"- F4 v13 binding: `{manifest['f4_canonical_neutral_binding_sha256_v13']}`\n"
        "- Stage 1/formal/training: not authorized\n"
    )
    _write_new(args.markdown_output, markdown.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
