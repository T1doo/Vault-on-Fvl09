"""CPU planning/dispatch guard for the v2 collection contract.

The ``--plan`` operation is CPU only.  Physical execution intentionally
requires a separately approved budget manifest; no implicit reuse of v1
ledger balance is permitted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .canonical import atomic_write_json, canonical_sha256
from .pilot_contract import planned_root_contract
from .scene_spec import scene_spec


ALLOWED_PHYSICAL_GPU_INDICES = list(range(8))


def validate_budget_request(value: dict) -> dict:
    """Recompute every root/spec binding before a request can be used."""
    checks: dict[str, bool] = {
        "schema_version": value.get("schema_version") == "cmf_f2_f3_v2_complete_budget_request_v1",
        "allowed_physical_gpu_indices": value.get("allowed_physical_gpu_indices") == ALLOWED_PHYSICAL_GPU_INDICES,
        "caps": value.get("requested_independent_contract_caps") == {"fresh_scenes": 28, "action_scenes": 28, "collection_attempts": 28, "solver_problems": 340, "gpu_lease_seconds": 4800},
        "old_goal_or_ledger_reused": value.get("old_goal_or_ledger_reused") is False,
    }
    root_specs = value.get("root_specs", {})
    for root_id in ("F2-A-v2", "F2-B-v2", "F3-A-v2", "F3-B-v2"):
        contract = planned_root_contract(root_id); spec = scene_spec(root_id); entry = root_specs.get(root_id, {})
        checks[f"{root_id}.contract_sha256"] = entry.get("contract_sha256") == canonical_sha256(contract)
        checks[f"{root_id}.scene_spec_sha256"] = entry.get("scene_spec_sha256") == spec["spec_sha256"]
        checks[f"{root_id}.execution_order"] = entry.get("execution_order") == contract["execution_order"]
    checks["pass"] = all(checks.values())
    return checks


def build_budget_request(output: Path) -> dict:
    roots = {}
    for root_id in ("F2-A-v2", "F2-B-v2", "F3-A-v2", "F3-B-v2"):
        contract = planned_root_contract(root_id); spec = scene_spec(root_id)
        roots[root_id] = {"contract_sha256": canonical_sha256(contract), "scene_spec_sha256": spec["spec_sha256"], "execution_order": contract["execution_order"], "cell_count": 6, "fresh_success_cells": 6, "collection_success_cells": 6, "ledger_action_scene_success_cells": 6}
    value = {
        "schema_version": "cmf_f2_f3_v2_complete_budget_request_v1",
        "status": "REQUEST_ONLY_NOT_AUTHORIZED",
        "based_on": {"reconciliation_commit": "91a34e797d9d0e486908d71190830fe3874eb9a0", "plan_commit": "b7117ed68bdc2064a1608a2a14a8df7d58bc06cb"},
        "old_goal_or_ledger_reused": False,
        "allowed_physical_gpu_indices": ALLOWED_PHYSICAL_GPU_INDICES,
        "scope": "four new roots, 24 complete F2/F3 cells with original t0 RGB/state/anchor/future/candidate outputs",
        "root_specs": roots,
        "success_baseline": {"fresh_scenes": 24, "action_scenes": 24, "collection_attempts": 24, "solver_problems": 220, "gpu_lease_seconds": 3600, "internal_action_segments_diagnostic": 244},
        "finite_recovery_reserve": {"fresh_scenes": 4, "action_scenes": 4, "collection_attempts": 4, "solver_problems": 120, "gpu_lease_seconds": 1200, "attempt_cap": 4, "one_change_per_attempt": True},
        "requested_independent_contract_caps": {"fresh_scenes": 28, "action_scenes": 28, "collection_attempts": 28, "solver_problems": 340, "gpu_lease_seconds": 4800},
        "accounting_notes": ["24 success cells include the two first-validation cells; do not count them as 26", "CPU scene-spec/negative tests are zero physical scenes", "220 solver queries and 244 action segments are the measured v1 lineage profile for four six-cell roots with shared-prefix replay (F2-A 31/36, F2-B 25/34, F3-A 85/90, F3-B 79/84); v2 values remain caps, not consumption", "actual ledger settlement remains per job and never duplicates the cap per GPU"],
        "stop_conditions": ["budget overrun or unknown consumption", "capture or anchor source integrity failure", "first two validation cells fail same implementation", "owned cleanup failure", "missing fresh idle GPU"],
        "physical_execution_authorized": False,
    }
    value["consistency_checks"] = validate_budget_request(value)
    if not value["consistency_checks"]["pass"]:
        raise ValueError("budget request is not self-consistent with current v2 contract/spec")
    value["request_sha256"] = canonical_sha256(value); atomic_write_json(output, value); return value


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--budget-request", required=True); args = parser.parse_args(); value = build_budget_request(Path(args.budget_request)); print(json.dumps({"path": args.budget_request, "request_sha256": value["request_sha256"], "physical_execution_authorized": value["physical_execution_authorized"]}, ensure_ascii=False))


if __name__ == "__main__": main()
