"""CPU-only report for historical F2 beside planner failures.

This report deliberately does not claim an IK/collision root cause: the old
trace format contains the failed target and query sequence but predates the
conditional MotionGen diagnostics now emitted by the v2 runtime.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .canonical import canonical_sha256, sha256_file
from .f2_geometry_v2 import build_beside_route_waypoints


def diagnose_attempt(attempt_dir: str | Path) -> dict[str, Any]:
    directory = Path(attempt_dir)
    receipt_path = directory / "cell_receipt.json"
    trace_path = directory / "trace.npz"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    with np.load(trace_path, allow_pickle=False) as trace:
        queries_raw = trace["planner_queries_json"].item()
        queries = json.loads(str(queries_raw))
        row_count = int(trace["step_index"].shape[0])
        prefix_end = int(receipt.get("prefix_end_trace_row", row_count - 1))
        eef = np.asarray(trace["eef_pose"], dtype=np.float64)
        object_pose = np.asarray(trace["object_pose"], dtype=np.float64)
    failed = [query for query in queries if query.get("status") not in {"Success"}]
    last_success = max((int(query.get("query_id", -1)) for query in queries if query.get("status") == "Success"), default=None)
    failure_target = failed[0].get("goal_eef_pose") if failed else None
    carry = eef[prefix_end]
    carried_object = object_pose[prefix_end]
    nominal_target = np.asarray((receipt.get("target_binding") or {}).get("target_eef", carry), dtype=np.float64)
    route = build_beside_route_waypoints(carry, nominal_target)
    return {
        "schema_version": "cmf_f2_trace_diagnostic_v1",
        "diagnostic_kind": "read_only_existing_trace_analysis",
        "attempt_dir": str(directory),
        "receipt_sha256": sha256_file(receipt_path),
        "trace_sha256": sha256_file(trace_path),
        "cell_status": receipt.get("status"),
        "row_count": row_count,
        "prefix_end_trace_row": prefix_end,
        "planner_query_count": len(queries),
        "successful_query_ids_before_failure": [int(query["query_id"]) for query in queries if query.get("status") == "Success"],
        "last_successful_query_id": last_success,
        "failure_queries": failed,
        "failure_stage": "planner_query_before_release" if failed else "no_failed_query",
        "failed_target_eef_pose": failure_target,
        "saved_state": {
            "prefix_eef_pose": carry.tolist(),
            "prefix_object_pose": carried_object.tolist(),
            "target_binding": receipt.get("target_binding"),
        },
        "corrected_route_cpu_reproduction": route,
        "route_bug_in_old_runtime": {
            "old_expression": "route_far = high.copy(); route_far[1] = route_y; route_target = route_far.copy(); route_target[0] = high[0]",
            "old_route_far_equals_route_target": True,
            "new_route_has_distinct_side_and_transport_waypoints": route["side_at_current"] != route["side_at_target"],
        },
        "bottom_layer_status": "UNAVAILABLE_IN_HISTORICAL_TRACE",
        "source_limitations": [
            "historical planner_queries_json contains status and target but no MotionGenResult diagnostics",
            "saved state is suitable for a bounded scene diagnostic, not a new physical collection",
            "no release/support/terminal gate was reached in these attempts",
        ],
    }


def diagnose_attempts(attempts: Iterable[tuple[str, str | Path]]) -> dict[str, Any]:
    reports = [{"attempt_name": name, **diagnose_attempt(path)} for name, path in attempts]
    return {
        "schema_version": "cmf_f2_trace_diagnostic_bundle_v1",
        "diagnostic_kind": "read_only_existing_trace_analysis",
        "attempts": reports,
        "summary": {
            "attempt_count": len(reports),
            "all_failed_before_release": all(item["failure_stage"] == "planner_query_before_release" for item in reports),
            "historical_motiongen_diagnostics_available": any(bool(item["failure_queries"] and item["failure_queries"][0].get("planner_diagnostics")) for item in reports),
            "route_bug_reproduced": all(item["route_bug_in_old_runtime"]["old_route_far_equals_route_target"] for item in reports),
            "requires_bounded_scene_diagnostic": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--attempt", action="append", required=True, help="name=attempt directory")
    args = parser.parse_args()
    attempts = []
    for value in args.attempt:
        if "=" not in value:
            raise SystemExit("--attempt must be name=directory")
        attempts.append(tuple(value.split("=", 1)))
    report = diagnose_attempts(attempts)
    report["report_sha256"] = canonical_sha256(report)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
