"""One-cell F2 qualification entry point for a frozen layout candidate.

This intentionally runs the real collector cell and writes a qualification
receipt, but it does not pretend that one cell is a complete root.  The job
must be declared and budgeted as a collection attempt before launch.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .canonical import atomic_write_json, canonical_sha256
from .collector_v2 import _f2_cell, _save_prefix
from .finalizer import finalize_cell
from .scene_spec import scene_spec


def run(*, output: str | Path, root_id: str, program_id: str, realization_id: str, f2_layout_id: str = "v4_beside_y_workspace", f2_route_mode: str = "three_segment_high") -> dict:
    output_path = Path(output)
    result = _f2_cell(output=output_path, root_id=root_id, program_id=program_id, realization_id=realization_id, artifact=None, collection=True, f2_layout_id=f2_layout_id, f2_route_mode=f2_route_mode)
    prefix_artifact = _save_prefix(output_path.parent, result) if result.get("status") == "cell_pass" else None
    finalizer = {"pass": False, "status": "NOT_RUN"}
    if result.get("trace_path"):
        try:
            finalizer = finalize_cell(cell_dir=output_path, spec=scene_spec(root_id, f2_layout_id=f2_layout_id), expected_relation=program_id, artifact_path=output_path.parent / "prefix_artifact.npz")
        except BaseException as exc:
            finalizer = {"pass": False, "status": "EXCEPTION", "error": {"type": type(exc).__name__, "message": str(exc)}}
    qualification = {
        "schema_version": "cmf_f2_f3_v2_f2_qualification_receipt_v1",
        "root_id": root_id,
        "program_id": program_id,
        "realization_id": realization_id,
        "layout_id": f2_layout_id,
        "route_mode": f2_route_mode,
        "collection": True,
        "cell_receipt": result,
        "prefix_artifact": str(prefix_artifact) if prefix_artifact else None,
        "independent_finalizer": finalizer,
        "pass": bool(result.get("status") == "cell_pass" and finalizer.get("pass") is True),
    }
    qualification["receipt_sha256"] = canonical_sha256(qualification)
    atomic_write_json(output_path / "qualification_receipt.json", qualification)
    return qualification


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--root-id", required=True)
    parser.add_argument("--program-id", required=True)
    parser.add_argument("--realization-id", required=True)
    parser.add_argument("--f2-layout-id", choices=("v4_beside_y_workspace", "v5_beside_y_lower"), default="v4_beside_y_workspace")
    parser.add_argument("--f2-route-mode", choices=("three_segment_high", "side_then_geometry_target"), default="three_segment_high")
    args = parser.parse_args()
    result = run(output=args.output, root_id=args.root_id, program_id=args.program_id, realization_id=args.realization_id, f2_layout_id=args.f2_layout_id, f2_route_mode=args.f2_route_mode)
    print(json.dumps({"pass": result["pass"], "status": result["cell_receipt"].get("status"), "finalizer": result["independent_finalizer"].get("pass")}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
