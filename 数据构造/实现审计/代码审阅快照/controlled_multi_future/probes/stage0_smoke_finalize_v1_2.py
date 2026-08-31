"""Write the authoritative replacement-aware Stage-0 v1.2 seal."""

from __future__ import annotations

import json
from pathlib import Path

from ..stage0_smoke_finalizer_v1_2 import (
    CANONICAL_OUTPUT,
    CANONICAL_SEAL_OUTPUT,
    build_stage0_terminal_seal_v1_2,
    finalize_stage0_smoke_v1_2,
)


def _write_new(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    if CANONICAL_OUTPUT.exists() or CANONICAL_SEAL_OUTPUT.exists():
        raise FileExistsError("Stage 0 v1.2 canonical seal outputs already exist")
    result = finalize_stage0_smoke_v1_2()
    seal = build_stage0_terminal_seal_v1_2(result)
    _write_new(CANONICAL_OUTPUT, result)
    _write_new(CANONICAL_SEAL_OUTPUT, seal)
    print(
        json.dumps(
            {
                "stage0_completed": result["stage0_completed"],
                "stage0_outcome": result["stage0_outcome"],
                "result_sha256": result["receipt_sha256"],
                "seal_sha256": seal["seal_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["stage0_completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
