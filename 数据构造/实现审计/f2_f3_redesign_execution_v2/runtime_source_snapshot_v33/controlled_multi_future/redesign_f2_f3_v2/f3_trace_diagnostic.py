"""CPU-only decomposition of F3 H/V event failures.

The production event gate measures bottle pose in the world frame.  That is
the correct acceptance measurement, but it cannot by itself distinguish an
EEF rotation from a bottle sliding in the grasp.  This module reads the
already saved trace and reports both frames without changing any acceptance
threshold or retroactively reclassifying a cell.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .canonical import canonical_sha256, sha256_file


ORIENTATION_THRESHOLD_RAD = 0.05


def _scalar_json(array: np.ndarray) -> Any:
    value = array.item() if getattr(array, "ndim", 0) == 0 else array[-1]
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return json.loads(str(value))


def _qnorm(value: np.ndarray) -> np.ndarray:
    value = np.asarray(value, dtype=np.float64)
    norm = np.linalg.norm(value, axis=-1, keepdims=True)
    if np.any(norm <= 0) or not np.isfinite(norm).all():
        raise ValueError("quaternion contains a zero or non-finite value")
    return value / norm


def _qmul(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    w1, x1, y1, z1 = np.moveaxis(_qnorm(first), -1, 0)
    w2, x2, y2, z2 = np.moveaxis(_qnorm(second), -1, 0)
    return np.stack(
        [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ],
        axis=-1,
    )


def _qinv(value: np.ndarray) -> np.ndarray:
    result = _qnorm(value).copy()
    result[..., 1:] *= -1.0
    return result


def _qdist(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    dot = np.sum(_qnorm(first) * _qnorm(second), axis=-1)
    return 2.0 * np.arccos(np.clip(np.abs(dot), -1.0, 1.0))


def _qrotate(quaternion: np.ndarray, vector: np.ndarray) -> np.ndarray:
    """Rotate one or more 3-vectors by wxyz quaternions."""
    zeros = np.zeros(np.asarray(vector).shape[:-1] + (1,), dtype=np.float64)
    rotated = _qmul(_qmul(quaternion, np.concatenate([zeros, vector], axis=-1)), _qinv(quaternion))
    return rotated[..., 1:]


def _event_queries(queries: list[dict[str, Any]], start: int, end: int) -> list[dict[str, Any]]:
    return [
        query
        for query in queries
        if query.get("start_step") is not None
        and query.get("end_step") is not None
        and int(query["end_step"]) >= start
        and int(query["start_step"]) <= end
    ]


def _movement_and_hold_rows(queries: list[dict[str, Any]], start: int, end: int) -> tuple[np.ndarray, np.ndarray]:
    relevant = _event_queries(queries, start, end)
    movement: set[int] = set()
    hold: set[int] = set()
    for index, query in enumerate(relevant):
        query_start = max(start, int(query["start_step"]))
        query_end = min(end + 1, int(query["end_step"]))
        movement.update(range(query_start, query_end))
        next_start = (
            int(relevant[index + 1]["start_step"])
            if index + 1 < len(relevant) and relevant[index + 1].get("start_step") is not None
            else end + 1
        )
        hold_start = max(query_end, query_start)
        hold_end = min(end + 1, next_start)
        hold.update(range(hold_start, hold_end))
    return np.asarray(sorted(movement), dtype=np.int64), np.asarray(sorted(hold), dtype=np.int64)


def _first_exceed(rows: np.ndarray, values: np.ndarray, threshold: float = ORIENTATION_THRESHOLD_RAD) -> int | None:
    indices = np.flatnonzero(values > threshold)
    return int(rows[indices[0]]) if indices.size else None


def _phase_metrics(
    rows: np.ndarray,
    *,
    eef: np.ndarray,
    bottle: np.ndarray,
    relative: np.ndarray,
    contact: np.ndarray,
    eef_angular_velocity: np.ndarray,
    bottle_angular_velocity: np.ndarray,
    origin_index: int,
) -> dict[str, Any]:
    if rows.size == 0:
        return {"row_count": 0}
    rel_drift = _qdist(relative[rows], relative[origin_index])
    eef_drift = _qdist(eef[rows, 3:], eef[origin_index, 3:])
    bottle_drift = _qdist(bottle[rows, 3:], bottle[origin_index, 3:])
    return {
        "row_count": int(rows.size),
        "contact_fraction": float(np.mean(contact[rows])),
        "max_eef_angular_velocity_rps": float(np.linalg.norm(eef_angular_velocity[rows], axis=1).max()),
        "max_bottle_angular_velocity_rps": float(np.linalg.norm(bottle_angular_velocity[rows], axis=1).max()),
        "eef_world_orientation_drift_rad": float(eef_drift.max()),
        "bottle_world_orientation_drift_rad": float(bottle_drift.max()),
        "bottle_relative_eef_orientation_drift_rad": float(rel_drift.max()),
    }


def _classify_event(*, eef_drift: float, relative_drift: float, bottle_drift: float) -> str:
    eef_bad = eef_drift > ORIENTATION_THRESHOLD_RAD
    relative_bad = relative_drift > ORIENTATION_THRESHOLD_RAD
    bottle_bad = bottle_drift > ORIENTATION_THRESHOLD_RAD
    if relative_bad and not eef_bad:
        return "bottle_relative_slip_supported"
    if eef_bad and not relative_bad:
        return "eef_rotation_supported"
    if eef_bad and relative_bad:
        return "mixed_eef_and_relative_motion"
    if bottle_bad:
        return "bottle_world_rotation_without_thresholded_eef_rotation"
    return "within_orientation_threshold"


def diagnose_case(case_name: str, case_dir: str | Path) -> dict[str, Any]:
    directory = Path(case_dir)
    receipt_path = directory / "cell_receipt.json"
    trace_path = directory / "trace.npz"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    with np.load(trace_path, allow_pickle=False) as trace:
        eef = np.asarray(trace["eef_pose"], dtype=np.float64)
        bottle = np.asarray(trace["object_pose"], dtype=np.float64)
        contact = np.asarray(trace["selected_gripper_contact"], dtype=bool)
        eef_angular_velocity = np.asarray(trace["eef_angular_velocity"], dtype=np.float64)
        bottle_angular_velocity = np.asarray(trace["object_angular_velocity"], dtype=np.float64)
        qpos = np.asarray(trace["joint_qpos"], dtype=np.float64)
        effective = np.asarray(trace["controller_effective_setpoint"], dtype=np.float64)
        query_ids = np.asarray(trace["planner_query_id"], dtype=np.int64)
        queries = _scalar_json(trace["planner_queries_json"])

    if len(eef) != len(bottle) or len(eef) != len(contact):
        raise ValueError(f"{case_name}: trace state arrays have different lengths")
    relative = _qmul(_qinv(eef[:, 3:]), bottle[:, 3:])
    relative_position = _qrotate(_qinv(eef[:, 3:]), bottle[:, :3] - eef[:, :3])
    events: list[dict[str, Any]] = []
    for event_index, event in enumerate(receipt.get("event_segments", []), 1):
        start = int(event["start_row"])
        end = int(event["end_row"])
        if not (0 <= start <= end < len(eef)):
            raise ValueError(f"{case_name}: event {event_index} lies outside trace")
        rows = np.arange(start, end + 1, dtype=np.int64)
        bottle_drift = _qdist(bottle[rows, 3:], bottle[start, 3:])
        eef_drift = _qdist(eef[rows, 3:], eef[start, 3:])
        relative_drift = _qdist(relative[rows], relative[start])
        movement_rows, hold_rows = _movement_and_hold_rows(queries, start, end)

        goal_errors: list[dict[str, Any]] = []
        relevant_queries = _event_queries(queries, start, end)
        goal_orientations: list[np.ndarray] = []
        for query in relevant_queries:
            goal = np.asarray(query.get("goal_eef_pose", []), dtype=np.float64)
            if goal.shape != (7,):
                continue
            goal_orientations.append(goal[3:])
            query_end = min(end, max(start, int(query["end_step"]) - 1))
            goal_errors.append(
                {
                    "query_id": int(query["query_id"]),
                    "status": query.get("status"),
                    "start_step": int(query["start_step"]),
                    "end_step": int(query["end_step"]),
                    "actual_eef_position_error_m": float(np.linalg.norm(eef[query_end, :3] - goal[:3])),
                    "actual_eef_orientation_error_rad": float(_qdist(eef[query_end, 3:], goal[3:])),
                    "planner_diagnostics": query.get("planner_diagnostics"),
                }
            )

        # The first six effective setpoints are the left arm positions and
        # realized dual-arm qpos stores that arm at indices 6:12 in this
        # runtime.  This is a measured command-vs-realization diagnostic, not
        # a replacement for a full FK reconstruction.
        qpos_error = None
        active = query_ids[rows, 0] >= 0
        if effective.ndim == 2 and effective.shape[1] >= 6 and qpos.ndim == 2 and qpos.shape[1] >= 12 and np.any(active):
            qpos_error = np.abs(effective[rows[active], :6] - qpos[rows[active], 6:12])

        event_result = {
            "event_index": event_index,
            "axis": event.get("axis"),
            "trace_rows": [start, end],
            "hold_frames": event.get("hold_frames"),
            "movement": _phase_metrics(movement_rows, eef=eef, bottle=bottle, relative=relative, contact=contact, eef_angular_velocity=eef_angular_velocity, bottle_angular_velocity=bottle_angular_velocity, origin_index=start),
            "hold": _phase_metrics(hold_rows, eef=eef, bottle=bottle, relative=relative, contact=contact, eef_angular_velocity=eef_angular_velocity, bottle_angular_velocity=bottle_angular_velocity, origin_index=start),
            "whole_event": {
                "contact_fraction": float(np.mean(contact[rows])),
                "eef_world_orientation_drift_rad": float(eef_drift.max()),
                "bottle_world_orientation_drift_rad": float(bottle_drift.max()),
                "bottle_relative_eef_orientation_drift_rad": float(relative_drift.max()),
                "bottle_relative_eef_translation_drift_m": float(np.linalg.norm(relative_position[rows] - relative_position[start], axis=1).max()),
                "first_bottle_world_orientation_exceed_row": _first_exceed(rows, bottle_drift),
                "first_eef_world_orientation_exceed_row": _first_exceed(rows, eef_drift),
                "first_bottle_relative_eef_orientation_exceed_row": _first_exceed(rows, relative_drift),
            },
            "planner_goal_endpoint_errors": goal_errors,
            "planner_goal_orientation_range_rad": float(max((_qdist(goal, goal_orientations[0]) for goal in goal_orientations), default=0.0)),
            "command_vs_realized_left_arm_qpos_error_max_rad": float(qpos_error.max()) if qpos_error is not None and qpos_error.size else None,
        }
        event_result["diagnostic_classification"] = _classify_event(
            eef_drift=event_result["whole_event"]["eef_world_orientation_drift_rad"],
            relative_drift=event_result["whole_event"]["bottle_relative_eef_orientation_drift_rad"],
            bottle_drift=event_result["whole_event"]["bottle_world_orientation_drift_rad"],
        )
        events.append(event_result)

    classifications = [event["diagnostic_classification"] for event in events]
    slip_supported = classifications.count("bottle_relative_slip_supported")
    return {
        "schema_version": "cmf_f3_trace_diagnostic_v1",
        "diagnostic_kind": "read_only_existing_trace_analysis",
        "case_name": case_name,
        "case_dir": str(directory),
        "receipt_sha256": sha256_file(receipt_path),
        "trace_sha256": sha256_file(trace_path),
        "cell_status": receipt.get("status"),
        "acceptance_thresholds_unchanged": {"orientation_threshold_rad": ORIENTATION_THRESHOLD_RAD},
        "source_limitations": [
            "planner_goal_eef_pose is an endpoint command; this report does not claim a full planned FK trajectory",
            "relative EEF/bottle motion is diagnostic evidence and does not replace the world-frame event gate",
            "old traces predate planner_diagnostics_v2, so missing raw MotionGen fields remain missing",
        ],
        "events": events,
        "summary": {
            "event_count": len(events),
            "classifications": classifications,
            "bottle_relative_slip_events": slip_supported,
            "supported_bottle_slip_root_cause": slip_supported > 0,
        },
    }


def diagnose_cases(cases: Iterable[tuple[str, str | Path]]) -> dict[str, Any]:
    reports = [diagnose_case(name, path) for name, path in cases]
    slip_events = sum(report["summary"]["bottle_relative_slip_events"] for report in reports)
    return {
        "schema_version": "cmf_f3_trace_diagnostic_bundle_v1",
        "diagnostic_kind": "read_only_existing_trace_analysis",
        "cases": reports,
        "summary": {
            "case_count": len(reports),
            "bottle_relative_slip_events": slip_events,
            "supported_bottle_slip_root_cause": slip_events > 0,
            "acceptance_changed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--case", action="append", required=True, help="name=cell directory")
    args = parser.parse_args()
    cases = []
    for value in args.case:
        if "=" not in value:
            raise SystemExit("--case must be name=directory")
        name, directory = value.split("=", 1)
        cases.append((name, directory))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = diagnose_cases(cases)
    report["report_sha256"] = canonical_sha256(report)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
