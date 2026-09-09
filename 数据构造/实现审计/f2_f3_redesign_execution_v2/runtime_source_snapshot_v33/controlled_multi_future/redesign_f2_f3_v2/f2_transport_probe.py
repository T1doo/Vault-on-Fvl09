"""One-cell, non-collection F2 transport qualification.

This entry point intentionally does not create a pilot root.  It builds a
fresh shared prefix in the cell itself, checks anchor grasp stability, and
records one named transport result for diagnosis before any production
collection budget is spent.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .canonical import atomic_write_json
from .pilot_f2_root_probe import run_cell


def run(output: str | Path, *, program_id: str = "on", realization_id: str = "r_pc", root_id: str = "F2-A", seed: int = 202609081, layout_id: str = "v1") -> dict[str, Any]:
    root = Path(output); root.mkdir(parents=True, exist_ok=True)
    cell = run_cell(output=root / f"{program_id}_{realization_id}", root_id=root_id, program_id=program_id, realization_id=realization_id, seed=seed, prefix_artifact=None, collection=False, layout_id=layout_id)
    result = {
        "schema_version": "cmf_f2_transport_probe_receipt_v1",
        "root_id": root_id,
        "family": "F2",
        "program_id": program_id,
        "realization_id": realization_id,
        "layout_id": layout_id,
        "qualification": True,
        "collection": False,
        "fresh_scene_count": 1,
        "action_scene_count": 1,
        "collection_attempt_count": 0,
        "qualification_pass": cell.get("status") == "cell_pass" and bool(cell.get("gates", {}).get("prefix_anchor_contact_stable")),
        "cell": cell,
    }
    atomic_write_json(root / "transport_probe_receipt.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--program", default="on", choices=("inside", "on", "beside"))
    parser.add_argument("--realization", default="r_pc", choices=("r_pc", "r_inv_path", "r_inv_motion"))
    parser.add_argument("--root-id", default="F2-A")
    parser.add_argument("--layout-id", default="v1", choices=("v1", "v2", "v3"))
    args = parser.parse_args()
    result = run(args.output, program_id=args.program, realization_id=args.realization, root_id=args.root_id, layout_id=args.layout_id)
    raise SystemExit(0 if result["qualification_pass"] else 1)


if __name__ == "__main__":
    main()
