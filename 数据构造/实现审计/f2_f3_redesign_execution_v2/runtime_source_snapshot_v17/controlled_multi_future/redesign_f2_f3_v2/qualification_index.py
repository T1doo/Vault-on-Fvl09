"""Build the current research-eligibility index without mutating v1 state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .canonical import atomic_write_json
from .eligibility import empty_index, set_cell, set_root, write_index


ROOTS = {
    "F2-A": "/nfs_share/lijunhui/Robotwin2/datasets/f2_f3_redesign_v1/stage_C_F2A_resume_pilot_1788855821",
    "F2-B": "/nfs_share/lijunhui/Robotwin2/datasets/f2_f3_redesign_v1/stage_C_F2B_pilot_1788856533",
    "F3-A": "/nfs_share/lijunhui/Robotwin2/datasets/f2_f3_redesign_v1/stage_C_F3A_pilot_1788852570",
    "F3-B": "/nfs_share/lijunhui/Robotwin2/datasets/f2_f3_redesign_v1/stage_C_F3B_resume_pilot_1788855368",
}


def build(output: Path) -> dict:
    index = empty_index()
    for root_id, root_path in ROOTS.items():
        root = json.loads((Path(root_path) / "root_receipt.json").read_text(encoding="utf-8"))
        root_reasons = ["legacy implementation acceptance is retained as history only", "complete current RGB/current anchor bundle was not saved", "v2 collector and independent finalizer have not generated a replacement root"]
        set_root(index, root_id=root_id, current="BLOCKED_LEGACY_DEVELOPMENT_ONLY", reasons=root_reasons)
        for cell in root.get("cells", []):
            key = f"{root_id}:{cell['program_id']}:{cell['realization_id']}"
            reasons = ["legacy v1 acceptance is not research eligibility", "original RGB bundle and complete anchor are absent from the lineage"]
            if root_id.startswith("F2") and cell.get("program_id") == "beside":
                reasons.insert(0, "realized relation is stand-top support, not the beside annulus/table-support contract")
            if root_id.startswith("F3"):
                reasons.append("predeclared arm rest target is absent; historical verifier used the object return error for rest")
            set_cell(index, cell_key=key, historical="ACCEPTED_IN_V1_HISTORY" if cell.get("status") == "cell_pass" else str(cell.get("status")), current="BLOCKED", reasons=reasons, permitted_use=["development", "audit", "negative_or_positive_control"])
    index["summary"] = {"historical_cells": len(index["cells"]), "currently_eligible_cells": 0, "blocked_cells": len(index["cells"]), "old_complete_is_not_sufficient": True}
    return write_index(output, index)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", required=True); args = parser.parse_args(); value = build(Path(args.output)); print(json.dumps({"path": args.output, "schema_version": value["schema_version"], "blocked_cells": value["summary"]["blocked_cells"], "sha256": value["index_sha256"]}, ensure_ascii=False));


if __name__ == "__main__": main()
