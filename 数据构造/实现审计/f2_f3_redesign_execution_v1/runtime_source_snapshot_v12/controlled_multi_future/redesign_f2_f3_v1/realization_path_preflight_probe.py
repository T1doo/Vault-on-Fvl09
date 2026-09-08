"""Saved-state planner-only preflight for declared F2/F3 path waypoints."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import sapien

from ..family_runners_v3_1 import _plan_left, _planner_reset
from ..probes.lifecycle import cleanup_status, initialize_cleanup_fields, managed_scene
from ..probes.scene_inspection import _args
from .canonical import atomic_write_json, sha256_file
from .f2_saved_state_planner_probe import _set_saved_articulation
from .f2_scene import RedesignF2Scene
from .scene import RedesignF3Scene


def run(
    *,
    output: str | Path,
    family: str,
    cell_receipt: str | Path,
    trace: str | Path,
    goals_json: str | Path,
    layout_id: str = "v3",
) -> dict[str, Any]:
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    receipt_path = Path(cell_receipt)
    trace_path = Path(trace)
    goals_path = Path(goals_json)
    source_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    goal_spec = json.loads(goals_path.read_text(encoding="utf-8"))
    if family not in {"F2", "F3"} or goal_spec.get("family") != family:
        raise ValueError("preflight family differs from goal specification")
    goals = goal_spec.get("goals")
    if not isinstance(goals, list) or not goals:
        raise ValueError("preflight requires at least one named goal")
    with np.load(trace_path, allow_pickle=False) as data:
        prefix_end = int(source_receipt["prefix_end_trace_row"])
        state_row = int(goal_spec.get("state_row", prefix_end))
        if state_row < 0 or state_row >= len(data["step_index"]):
            raise ValueError("preflight state_row is outside the source trace")
        saved_qpos = np.asarray(data["joint_qpos"][state_row], dtype=np.float64)
        saved_qvel = np.asarray(data["joint_qvel"][state_row], dtype=np.float64)
        saved_object = np.asarray(data["object_pose"][state_row], dtype=np.float64)
        saved_eef = np.asarray(data["eef_pose"][state_row], dtype=np.float64)
    normalized_goals = []
    for item in goals:
        label = str(item.get("label", ""))
        value = np.asarray(item.get("pose"), dtype=np.float64)
        if not label or value.shape not in {(3,), (7,)} or not np.isfinite(value).all():
            raise ValueError("each preflight goal needs a label and finite 3-D or 7-D pose")
        pose = saved_eef.copy()
        pose[: value.size] = value
        normalized_goals.append((label, pose))
    receipt: dict[str, Any] = {
        "schema_version": "cmf_f2_f3_realization_path_preflight_v1",
        "task_id": "f2_f3_redesign_20260907",
        "family": family,
        "layout_id": layout_id if family == "F2" else None,
        "status": "running",
        "collection": False,
        "action_scenes": 0,
        "formal_data": False,
        "training": False,
        "cell_receipt_path": str(receipt_path),
        "cell_receipt_sha256": sha256_file(receipt_path),
        "trace_path": str(trace_path),
        "trace_sha256": sha256_file(trace_path),
        "goals_json_path": str(goals_path),
        "goals_json_sha256": sha256_file(goals_path),
        "prefix_end_trace_row": prefix_end,
        "saved_state_row": state_row,
        "saved_eef_pose": saved_eef.tolist(),
        "saved_object_pose": saved_object.tolist(),
        "planner_queries": [],
    }
    initialize_cleanup_fields(receipt)
    started = time.monotonic()
    scene_type = RedesignF2Scene if family == "F2" else RedesignF3Scene
    args = _args(family, output_path / "scene")
    args.update({"seed": 202609081 if family == "F2" else 202609083, "task_name": f"cmf_{family.lower()}_realization_path_preflight", "render_freq": 0, "save_data": False, "collect_data": False, "need_plan": True})
    if family == "F2":
        args["f2_layout_id"] = layout_id
    try:
        with managed_scene(scene_type, args, receipt, f"{family.lower()}-realization-path-preflight") as scene:
            actor = scene.can if family == "F2" else scene.bottle
            scene.initialize_trace(actor, "left", scene.role_actors)
            _set_saved_articulation(scene, saved_qpos, saved_qvel)
            actor.actor.set_pose(sapien.Pose(saved_object[:3], saved_object[3:]))
            _planner_reset(scene, planner_seed=20260908, variant_id=f"{family.lower()}-realization-path-preflight", arm="left")
            left_qpos = np.asarray(scene.robot.left_entity.get_qpos(), dtype=np.float64)
            for label, goal in normalized_goals:
                item: dict[str, Any] = {"label": label, "goal_eef_pose": goal.tolist()}
                try:
                    control = _plan_left(scene, goal, last_qpos=left_qpos, source=f"saved_state_{label}")
                    item["status"] = control.get("status") if isinstance(control, dict) else "non_mapping_result"
                    item["control_keys"] = sorted(control) if isinstance(control, dict) else []
                    item["control_error"] = {key: control.get(key) for key in ("error", "message", "reason") if isinstance(control, dict) and key in control}
                    item["planner_query"] = scene.planner_queries[-1] if getattr(scene, "planner_queries", None) else None
                except BaseException as exc:
                    item["status"] = "EXCEPTION"
                    item["error"] = {"type": type(exc).__name__, "message": str(exc)}
                    item["planner_query"] = scene.planner_queries[-1] if getattr(scene, "planner_queries", None) else None
                receipt["planner_queries"].append(item)
            receipt["solver_problem_count"] = int(getattr(scene, "planner_query_count", 0))
            receipt["all_goals_plannable"] = all(item.get("status") == "Success" for item in receipt["planner_queries"])
            receipt["status"] = "diagnostic_complete" if receipt["all_goals_plannable"] else "diagnostic_goals_failed"
    except BaseException as exc:
        receipt["status"] = "diagnostic_failed"
        receipt["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        receipt["budget_delta"] = {"solver_problems": int(receipt.get("solver_problem_count", 0)), "fresh_scenes": 1, "action_scenes": 0, "collection_attempts": 0, "gpu_lease_seconds": "coordinator_measured"}
        receipt["elapsed_seconds"] = time.monotonic() - started
        receipt["status"] = cleanup_status(receipt, receipt["status"])
        atomic_write_json(output_path / "realization_path_preflight_receipt.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--family", required=True, choices=("F2", "F3"))
    parser.add_argument("--cell-receipt", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--goals-json", required=True)
    parser.add_argument("--layout-id", default="v3", choices=("v1", "v2", "v3"))
    args = parser.parse_args()
    result = run(output=args.output, family=args.family, cell_receipt=args.cell_receipt, trace=args.trace, goals_json=args.goals_json, layout_id=args.layout_id)
    raise SystemExit(0 if result.get("status") == "diagnostic_complete" else 1)


if __name__ == "__main__":
    main()
