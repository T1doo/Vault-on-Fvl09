"""Resume a frozen F3-B root with the approved time-scaled control rule."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .collector_v2 import run_root


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--root-id", required=True)
    parser.add_argument("--existing-root", required=True)
    parser.add_argument("--cell-keys", required=True)
    parser.add_argument("--time-scale", type=float, default=1.5)
    args = parser.parse_args()
    os.environ["CMF_F3_TIME_SCALE"] = str(float(args.time_scale))
    result = run_root(output=args.output, root_id=args.root_id, cell_keys=[item for item in args.cell_keys.split(",") if item], existing_root=args.existing_root, collection=True)
    print(json.dumps({"root_id": result.get("root_id"), "status": result.get("status"), "accepted": result.get("accepted"), "completed_cell_keys": result.get("completed_cell_keys")}, ensure_ascii=False))
    return 0 if result.get("accepted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
