"""Build the read-only prior + new pilot 48-cell index without reaccepting data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .canonical import atomic_write_json, canonical_sha256
from .pilot_contract import expected_cells


class IndexAuditError(ValueError):
    pass


def _prior_refs(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    cells = value.get("cells")
    accepted_cells = [cell for cell in cells if cell.get("family") in {"F1", "F4"} and cell.get("status") in {"accepted_existing", "accepted_new"}] if isinstance(cells, list) else []
    if not isinstance(cells, list) or len(accepted_cells) != 24 or value.get("accepted") != 24:
        raise IndexAuditError("legacy prior index is not the expected 24 accepted cells")
    result = []
    for cell in accepted_cells:
        family = cell.get("family")
        if family not in {"F1", "F4"} or cell.get("pilot") not in {"A", "B"}:
            raise IndexAuditError("prior index contains a non-F1/F4 cell")
        evidence = cell.get("evidence", {})
        result.append({
            "cell_key": f"{family}:{cell.get('pilot')}:{cell.get('program_id')}:{cell.get('realization')}",
            "family": family,
            "pilot": cell.get("pilot"),
            "program_id": cell.get("program_id"),
            "realization_id": cell.get("realization"),
            "raw_id": cell.get("raw_id"),
            "current_sha256": cell.get("current_sha256"),
            "trace_path": evidence.get("trace_path"),
            "read_only": True,
            "accepted_source": "legacy_goal_pilot48_v1; read-only prior evidence",
        })
    return result


def _new_refs(root_paths: list[Path]) -> list[dict[str, Any]]:
    result = []
    for root_path in root_paths:
        root = json.loads((root_path / "root_receipt.json").read_text(encoding="utf-8"))
        if root.get("accepted") is not True:
            continue
        for cell in root.get("cells", []):
            result.append({
                "cell_key": f"{root['root_id']}:{cell['program_id']}:{cell['realization_id']}",
                "root_id": root["root_id"],
                "family": root["family"],
                "program_id": cell["program_id"],
                "realization_id": cell["realization_id"],
                "trace_path": cell.get("trace_path"),
                "current": cell.get("current"),
                "anchor": cell.get("anchor"),
                "prefix_sha256": cell.get("prefix_sha256"),
                "read_only": False,
                "accepted_source": "new f2_f3_redesign_20260907 root receipt",
            })
    return result


def build_index(*, prior_path: str | Path, accepted_root_paths: list[str | Path], output: str | Path) -> dict[str, Any]:
    prior = _prior_refs(Path(prior_path)); new = _new_refs([Path(path) for path in accepted_root_paths])
    keys = [item["cell_key"] for item in prior + new]
    if len(keys) != len(set(keys)):
        raise IndexAuditError("combined index has duplicate cell keys")
    pending = []
    for root_id in ("F2-A", "F2-B", "F3-A", "F3-B"):
        for cell in expected_cells(root_id):
            key = f"{root_id}:{cell['program_id']}:{cell['realization_id']}"
            if key not in keys:
                pending.append({**cell, "cell_key": key, "read_only": False, "status": "PENDING"})
    result = {
        "schema_version": "cmf_f2_f3_combined_48_index_v1",
        "task_id": "f2_f3_redesign_20260907",
        "status": "INCOMPLETE_PENDING_F2",
        "prior_read_only_cells": prior,
        "new_accepted_cells": new,
        "pending_cells": pending,
        "counts": {"prior_read_only": len(prior), "new_accepted": len(new), "pending": len(pending), "combined_slots": len(prior) + len(new) + len(pending)},
        "prior_mutation": False,
        "duplicate_count": len(keys) - len(set(keys)),
    }
    result["index_sha256"] = canonical_sha256(result)
    atomic_write_json(output, result)
    return result
