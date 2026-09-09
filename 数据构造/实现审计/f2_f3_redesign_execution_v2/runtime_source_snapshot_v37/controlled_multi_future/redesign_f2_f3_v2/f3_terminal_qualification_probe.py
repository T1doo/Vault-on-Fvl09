"""One-cell non-collection qualification for strict F3 return/release gates."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .canonical import atomic_write_json
from .pilot_contract import planned_root_contract
from .pilot_f3_root_probe import run_cell


def run(output: str | Path, *, program_id: str = "VHVH", realization_id: str = "r_pc", root_id: str = "F3-A") -> dict[str, Any]:
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    contract = planned_root_contract(root_id)
    cell = run_cell(output=root / f"{program_id}_{realization_id}", root_id=root_id, program_id=program_id, realization_id=realization_id, seed=contract["scene_seed"], prefix_artifact=None, collection=False)
    result = {
        "schema_version": "cmf_f3_terminal_qualification_receipt_v1",
        "root_id": root_id,
        "family": "F3",
        "program_id": program_id,
        "realization_id": realization_id,
        "qualification": True,
        "collection": False,
        "fresh_scene_count": 1,
        "action_scene_count": 1,
        "collection_attempt_count": 0,
        "qualification_pass": cell.get("status") == "cell_pass" and bool(cell.get("event_verifier", {}).get("pass")) and bool(cell.get("terminal_verifier", {}).get("pass")),
        "cell": cell,
    }
    atomic_write_json(root / "terminal_qualification_receipt.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--program", default="VHVH", choices=("VVHH", "VHVH", "VHHV"))
    parser.add_argument("--realization", default="r_pc", choices=("r_pc", "r_inv_path", "r_inv_motion"))
    parser.add_argument("--root-id", default="F3-A")
    args = parser.parse_args()
    result = run(args.output, program_id=args.program, realization_id=args.realization, root_id=args.root_id)
    raise SystemExit(0 if result["qualification_pass"] else 1)


if __name__ == "__main__":
    main()
