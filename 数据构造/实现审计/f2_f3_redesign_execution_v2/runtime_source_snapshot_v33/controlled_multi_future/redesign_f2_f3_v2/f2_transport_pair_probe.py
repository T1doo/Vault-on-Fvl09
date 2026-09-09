"""Two-cell non-collection F2 standard-branch qualification.

The first on/r_pc cell builds a fresh shared prefix.  beside/r_pc replays
that exact artifact.  This deliberately stops at qualification and never
creates a pilot root or production collection record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .canonical import atomic_write_json
from .pilot_f2_root_probe import run_cell


def _prefix_from_cell(cell_dir: Path, receipt: dict[str, Any], output: Path) -> Path:
    trace = np.load(cell_dir / "trace.npz", allow_pickle=False); n = int(receipt["prefix_end_trace_row"]) + 1
    artifact = output / "prefix_artifact.npz"
    np.savez(artifact, effective_setpoint=trace["controller_effective_setpoint"][:n], requested_command=trace["requested_command"][:n], component_mask=trace["component_masks"][:n], left_gripper_joint_drive_target=trace["left_gripper_joint_drive_target"][:n], right_gripper_joint_drive_target=trace["right_gripper_joint_drive_target"][:n], left_gripper_joint_drive_velocity_target=trace["left_gripper_joint_drive_velocity_target"][:n], right_gripper_joint_drive_velocity_target=trace["right_gripper_joint_drive_velocity_target"][:n])
    return artifact


def run(output: str | Path, *, root_id: str = "F2-A", layout_id: str = "v3") -> dict[str, Any]:
    root = Path(output); root.mkdir(parents=True, exist_ok=True)
    on_dir = root / "on_r_pc"; on = run_cell(output=on_dir, root_id=root_id, program_id="on", realization_id="r_pc", seed=202609081, prefix_artifact=None, collection=False, layout_id=layout_id)
    artifact = None; artifact_sha = None
    if on.get("trace_path") and on.get("prefix_anchor_contact_stable"):
        artifact = _prefix_from_cell(on_dir, on, root); artifact_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    beside = run_cell(output=root / "beside_r_pc", root_id=root_id, program_id="beside", realization_id="r_pc", seed=202609081, prefix_artifact=artifact, collection=False, layout_id=layout_id) if artifact is not None else {"status":"not_run_prefix_unstable","reason":"on/r_pc did not produce a stable reusable prefix"}
    result = {"schema_version":"cmf_f2_transport_pair_probe_receipt_v1","task_id":"f2_f3_redesign_20260907","root_id":root_id,"layout_id":layout_id,"qualification":True,"collection":False,"fresh_scene_count":2 if artifact is not None else 1,"action_scene_count":2 if artifact is not None else 1,"collection_attempt_count":0,"prefix_artifact":str(artifact) if artifact is not None else None,"prefix_artifact_sha256":artifact_sha,"on_r_pc":on,"beside_r_pc":beside,"qualification_pass":bool(artifact is not None and on.get("status")=="cell_pass" and beside.get("status")=="cell_pass")}
    atomic_write_json(root/"transport_pair_receipt.json",result); return result


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--output",required=True); parser.add_argument("--root-id",default="F2-A"); parser.add_argument("--layout-id",default="v3",choices=("v1","v2","v3")); args=parser.parse_args(); result=run(args.output,root_id=args.root_id,layout_id=args.layout_id); raise SystemExit(0 if result["qualification_pass"] else 1)


if __name__ == "__main__": main()
