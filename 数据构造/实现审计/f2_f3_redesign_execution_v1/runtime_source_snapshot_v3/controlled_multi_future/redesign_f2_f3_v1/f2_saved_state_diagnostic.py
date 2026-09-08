"""CPU-only F2 saved-state planner diagnosis.

This tool reads an existing failed trace/receipt and derives the exact
anchor, grasp offset, branch targets, and static layout clearances.  It does
not construct a scene, call a planner, consume GPU/action/solver budget, or
create production data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .canonical import atomic_write_json, canonical_sha256


CAN_EXTENTS_M = np.asarray([0.07114912222011581, 0.09646788818255601, 0.07118775383879648], dtype=np.float64)
WALL_TOP_M = 0.855
SCALE_CENTER_M = np.asarray([0.08, -0.18, 0.755], dtype=np.float64)
STAND_CENTER_M = np.asarray([0.23, -0.18, 0.79], dtype=np.float64)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def diagnose(*, cell_receipt: str | Path, trace: str | Path, output: str | Path) -> dict[str, Any]:
    receipt_path = Path(cell_receipt); trace_path = Path(trace); output_path = Path(output)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")); arrays = np.load(trace_path, allow_pickle=False)
    rows = int(len(arrays["step_index"])); prefix_end = int(receipt.get("prefix_end_trace_row", min(rows - 1, 0)))
    eef = np.asarray(arrays["eef_pose"], dtype=np.float64); obj = np.asarray(arrays["object_pose"], dtype=np.float64); contact = np.asarray(arrays["selected_gripper_contact"], dtype=bool)
    anchor_eef = eef[prefix_end]; anchor_object = obj[prefix_end]; offset = anchor_object[:3] - anchor_eef[:3]
    target_binding = receipt.get("target_binding") or {}
    desired_can = np.asarray(target_binding.get("desired_can", [0.08, -0.18, 0.7905938769193982]), dtype=np.float64)
    nominal_lateral_eef = desired_can - offset; nominal_lateral_eef[2] = anchor_eef[2]
    nominal_descent_eef = desired_can - offset
    after = np.flatnonzero(~contact[prefix_end + 1 :]); first_loss = int(prefix_end + 1 + after[0]) if len(after) else None
    prefix_contact_fraction = float(contact[max(0, prefix_end - 49) : prefix_end + 1].mean()) if prefix_end >= 0 else 0.0
    post_contact_fraction = float(contact[prefix_end + 1 : min(rows, prefix_end + 51)].mean()) if prefix_end + 1 < rows else 0.0
    source_control_diagnostics = receipt.get("planner_control_calls", [])
    solver_count = int(receipt.get("solver_problem_count", 0))
    result: dict[str, Any] = {
        "schema_version": "cmf_f2_saved_state_planner_diagnostic_v1",
        "task_id": "f2_f3_redesign_20260907",
        "status": "DIAGNOSTIC_ONLY",
        "collection": False,
        "formal_data": False,
        "physical_acceptance": False,
        "training": False,
        "source": {"cell_receipt": str(receipt_path), "cell_receipt_sha256": _sha256(receipt_path), "trace": str(trace_path), "trace_sha256": _sha256(trace_path), "trace_rows": rows},
        "identity": {"root_id": receipt.get("root_id"), "program_id": receipt.get("program_id"), "realization_id": receipt.get("realization_id"), "prefix_sha256": receipt.get("prefix_sha256")},
        "anchor": {"prefix_end_trace_row": prefix_end, "eef_pose": anchor_eef.tolist(), "object_pose": anchor_object.tolist(), "grasp_offset_object_minus_eef_m": offset.tolist(), "prefix_contact_fraction_last50": prefix_contact_fraction, "post_prefix_contact_fraction_next50": post_contact_fraction, "first_contact_loss_row_after_prefix": first_loss},
        "target_geometry": {"desired_can_center_m": desired_can.tolist(), "nominal_lateral_eef_pose": nominal_lateral_eef.tolist(), "nominal_descent_eef_pose": nominal_descent_eef.tolist(), "can_scaled_extents_m": CAN_EXTENTS_M.tolist(), "wall_top_m": WALL_TOP_M, "scale_center_m": SCALE_CENTER_M.tolist(), "stand_center_m": STAND_CENTER_M.tolist(), "anchor_can_bottom_clearance_above_wall_m": float(anchor_object[2] - CAN_EXTENTS_M[2] / 2.0 - WALL_TOP_M), "target_can_bottom_m": float(desired_can[2] - CAN_EXTENTS_M[2] / 2.0)},
        "planner_failure": {"receipt_error": receipt.get("error"), "failure_stage": (receipt.get("error") or {}).get("message"), "solver_problem_count_receipt": solver_count, "solver_count_provenance": "cell_receipt_only; zero is not independently proven absent raw planner diagnostics", "raw_control_diagnostics_present": bool(source_control_diagnostics), "raw_control_diagnostics": source_control_diagnostics},
        "diagnostic_conclusion": {"prefix_contact_replay_stable": post_contact_fraction >= 0.8, "target_geometry_recorded": True, "bottom_level_planner_failure_cause_resolved": bool(source_control_diagnostics), "interpretation": "Saved-state geometry and contact are recorded without claiming IK/collision/path cause. A future isolated planner call must preserve raw control status/error before any production dispatch."},
        "budget_delta": {"solver_problems": 0, "fresh_scenes": 0, "action_scenes": 0, "collection_attempts": 0, "gpu_lease_seconds": 0},
    }
    result["diagnostic_sha256"] = canonical_sha256(result); atomic_write_json(output_path, result); return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--cell-receipt", required=True); parser.add_argument("--trace", required=True); parser.add_argument("--output", required=True); args = parser.parse_args()
    diagnose(cell_receipt=args.cell_receipt, trace=args.trace, output=args.output)


if __name__ == "__main__": main()
