"""Non-executing F2 planner diagnostics from an explicitly bound trace state.

The probe restores saved articulation/object state and issues planner queries
only. It never sends a successful plan to the controller and is therefore a
diagnostic scene, not a collection rollout.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import sapien

from ..family_runners_v3_1 import _planner_reset, _plan_left
from ..probes.lifecycle import cleanup_status, initialize_cleanup_fields, managed_scene
from ..probes.scene_inspection import _args
from .canonical import atomic_write_json, sha256_file
from .f2_geometry_v2 import _rotation
from .f2_scene import RedesignF2Scene
from .scene_spec import scene_spec


def _set_saved_articulation(scene: Any, qpos: np.ndarray, qvel: np.ndarray) -> dict[str, Any]:
    """Restore both arm articulations from one saved 38-DoF state."""
    left = scene.robot.left_entity
    right = scene.robot.right_entity
    left_n = len(left.get_qpos())
    if qpos.size < left_n or qvel.size < left_n:
        raise ValueError("saved articulation is shorter than the left arm")
    left.set_qpos(qpos[:left_n])
    left.set_qvel(qvel[:left_n])
    if right is not left:
        right_n = len(right.get_qpos())
        if qpos.size < left_n + right_n or qvel.size < left_n + right_n:
            raise ValueError("saved articulation does not contain both arms")
        right.set_qpos(qpos[left_n:left_n + right_n])
        right.set_qvel(qvel[left_n:left_n + right_n])
    return {"left_qpos_dim": left_n, "full_saved_qpos_dim": int(qpos.size), "right_shared_entity": right is left}


def _entity(value: Any) -> Any:
    return getattr(value, "actor", value)


def _restore_saved_scene(scene: Any, trace: Any, row: int) -> dict[str, Any]:
    """Restore saved object poses/velocities and gripper drive targets."""
    qpos = np.asarray(trace["joint_qpos"][row], dtype=np.float64)
    qvel = np.asarray(trace["joint_qvel"][row], dtype=np.float64)
    articulation = _set_saved_articulation(scene, qpos, qvel)
    restored_roles: list[str] = []
    velocity_roles: list[str] = []
    for name, handle in scene.role_actors.items():
        pose_key = f"role_object_pose__{name}"
        if pose_key not in trace:
            continue
        pose = np.asarray(trace[pose_key][row], dtype=np.float64)
        if pose.shape != (7,) or not np.isfinite(pose).all():
            raise ValueError(f"saved role pose is invalid: {name}")
        actor = _entity(handle)
        actor.set_pose(sapien.Pose(pose[:3], pose[3:7]))
        restored_roles.append(name)
        linear_key = f"role_object_component_linear_velocity__{name}"
        angular_key = f"role_object_component_angular_velocity__{name}"
        if linear_key in trace and hasattr(actor, "set_velocity"):
            velocity = np.asarray(trace[linear_key][row], dtype=np.float64)
            if velocity.shape == (3,) and np.isfinite(velocity).all():
                actor.set_velocity(velocity)
                velocity_roles.append(name)
        if angular_key in trace and hasattr(actor, "set_angular_velocity"):
            angular = np.asarray(trace[angular_key][row], dtype=np.float64)
            if angular.shape == (3,) and np.isfinite(angular).all():
                actor.set_angular_velocity(angular)
    drive_fields: dict[str, bool] = {}
    for side in ("left", "right"):
        target_key = f"{side}_gripper_joint_drive_target"
        velocity_key = f"{side}_gripper_joint_drive_velocity_target"
        targets = np.asarray(trace[target_key][row], dtype=np.float64) if target_key in trace else None
        velocities = np.asarray(trace[velocity_key][row], dtype=np.float64) if velocity_key in trace else None
        joints = getattr(scene.robot, f"{side}_gripper", [])
        drive_fields[target_key] = bool(targets is not None and targets.shape == (2,))
        drive_fields[velocity_key] = bool(velocities is not None and velocities.shape == (2,))
        for index, item in enumerate(joints):
            joint = item[0] if isinstance(item, tuple) else item
            if targets is not None and index < targets.size and hasattr(joint, "set_drive_target"):
                joint.set_drive_target(float(targets[index]))
            if velocities is not None and index < velocities.size and hasattr(joint, "set_drive_velocity_target"):
                joint.set_drive_velocity_target(float(velocities[index]))
    return {"row": int(row), "articulation": articulation, "restored_role_names": sorted(restored_roles), "restored_velocity_role_names": sorted(set(velocity_roles)), "gripper_drive_fields": drive_fields}


def _load_query_list(trace: Any) -> list[dict[str, Any]]:
    if "planner_queries_json" not in trace.files:
        raise ValueError("trace does not contain planner_queries_json")
    value = trace["planner_queries_json"]
    if np.asarray(value).shape != ():
        raise ValueError("planner_queries_json is not scalar")
    parsed = json.loads(np.asarray(value).item())
    if not isinstance(parsed, list):
        raise ValueError("planner_queries_json is not a list")
    return [dict(item) for item in parsed if isinstance(item, Mapping)]


def _find_side_query(queries: list[dict[str, Any]], route: Mapping[str, Any], *, key: str) -> dict[str, Any]:
    target = np.asarray(route[key], dtype=np.float64)
    matches = []
    for query in queries:
        goal = np.asarray(query.get("goal_eef_pose", []), dtype=np.float64)
        if goal.shape == (7,):
            distance = float(np.max(np.abs(goal - target)))
            if distance <= 1e-5:
                matches.append((int(query.get("query_id", -1)), distance, query))
    if len(matches) != 1:
        raise ValueError(f"expected one {key} planner query, found {len(matches)}")
    return matches[0][2]


def _geometry_target(*, eef_pose: np.ndarray, object_pose: np.ndarray, spec: dict[str, Any]) -> np.ndarray:
    """Derive EEF target from the actual grasp transform and collision bottom."""
    f2 = spec["f2"]
    object_rotation = _rotation(object_pose[3:7])
    support_local = np.asarray(f2["support_point_local_xyz"], dtype=np.float64)
    desired_support = np.asarray([*f2["beside_target_xy"], f2["beside_table_z"]], dtype=np.float64)
    desired_object_origin = desired_support - object_rotation @ support_local
    object_to_eef = object_pose[:3] - eef_pose[:3]
    return np.r_[desired_object_origin - object_to_eef, eef_pose[3:7]]


def run(*, output: str | Path, cell_receipt: str | Path, trace: str | Path, f2_layout_id: str, post_waypoint_hold_frames: int = 20) -> dict[str, Any]:
    output_path = Path(output)
    receipt_path = Path(cell_receipt)
    trace_path = Path(trace)
    output_path.mkdir(parents=True, exist_ok=True)
    if not isinstance(f2_layout_id, str) or f2_layout_id not in {"v4_beside_y_workspace", "v5_beside_y_lower"}:
        raise ValueError("f2_layout_id must be an explicit known F2 layout candidate")
    if isinstance(post_waypoint_hold_frames, bool) or post_waypoint_hold_frames < 0:
        raise ValueError("post_waypoint_hold_frames must be a non-negative integer")
    source_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    root_id = str(source_receipt.get("root_id", ""))
    if not root_id.startswith("F2-"):
        raise ValueError("saved-state F2 diagnostic requires an F2 source root")
    if source_receipt.get("layout_id") != f2_layout_id:
        raise ValueError("source cell layout_id does not match explicit diagnostic layout")
    spec = scene_spec(root_id, f2_layout_id=f2_layout_id)
    source_scene_spec_sha256 = source_receipt.get("scene_spec_sha256")
    if not isinstance(source_scene_spec_sha256, str) or len(source_scene_spec_sha256) != 64:
        raise ValueError("source cell lacks a valid scene_spec_sha256")
    trace_data = np.load(trace_path, allow_pickle=False)
    rows = int(len(trace_data["step_index"]))
    queries = _load_query_list(trace_data)
    route = source_receipt.get("beside_route_waypoints")
    if not isinstance(route, Mapping):
        raise ValueError("source receipt lacks beside_route_waypoints")
    side_query = _find_side_query(queries, route, key="side_at_current")
    side_start = side_query.get("start_step")
    side_end = side_query.get("end_step")
    if not isinstance(side_start, int) or not isinstance(side_end, int) or not (0 <= side_start <= side_end < rows):
        raise ValueError("side_at_current query has no valid executed interval")
    s1_row = side_end + int(post_waypoint_hold_frames)
    if s1_row >= rows:
        raise ValueError("trace does not contain the full post-waypoint hold")
    s0_row = side_start
    original_target = np.asarray(route["side_at_target"], dtype=np.float64)
    s1_eef = np.asarray(trace_data["eef_pose"][s1_row], dtype=np.float64)
    s1_object = np.asarray(trace_data["object_pose"][s1_row], dtype=np.float64)
    geometry_target = _geometry_target(eef_pose=s1_eef, object_pose=s1_object, spec=spec)
    query_specs = [
        {"label": "S0_to_original_side_at_target", "state_row": s0_row, "target": original_target},
        {"label": "S1_to_original_side_at_target", "state_row": s1_row, "target": original_target},
        {"label": "S1_to_collision_bottom_geometry_target", "state_row": s1_row, "target": geometry_target},
    ]
    receipt: dict[str, Any] = {
        "schema_version": "cmf_f2_saved_state_planner_probe_v2",
        "task_id": "f2_f3_observation_contract_repair_20260909_p4",
        "status": "RUNNING",
        "collection": False,
        "formal_data": False,
        "stage0_data": False,
        "root_id": root_id,
        "f2_layout_id": f2_layout_id,
        "scene_spec_sha256": spec["spec_sha256"],
        "source_scene_spec_sha256": source_scene_spec_sha256,
        "source_scene_spec_hash_match": source_scene_spec_sha256 == spec["spec_sha256"],
        "source_scene_spec_hash_difference_reason": "source v5 trace predates collision-mesh support-point correction; physical layout_id is explicitly matched",
        "cell_receipt_path": str(receipt_path),
        "cell_receipt_sha256": sha256_file(receipt_path),
        "trace_path": str(trace_path),
        "trace_sha256": sha256_file(trace_path),
        "trace_rows": rows,
        "post_waypoint_hold_frames": int(post_waypoint_hold_frames),
        "source_planner_query_count": len(queries),
        "source_side_at_current_query": side_query,
        "state_rows": {"S0_before_side_at_current": s0_row, "side_at_current_end": side_end, "S1_before_failed_query": s1_row},
        "original_side_at_target": original_target.tolist(),
        "collision_bottom_geometry_target": geometry_target.tolist(),
        "query_specs": [{"label": item["label"], "state_row": item["state_row"], "target": item["target"].tolist()} for item in query_specs],
        "planner_queries": [],
    }
    initialize_cleanup_fields(receipt)
    started = time.monotonic()
    args = _args("F2", output_path / "scene")
    args.update({"seed": spec["scene_seed"], "task_name": "cmf_f2_saved_state_planner_probe_v2", "f2_layout_id": f2_layout_id, "scene_variant": spec["layout_variant"], "render_freq": 0, "save_data": False, "collect_data": False, "need_plan": True})
    try:
        with managed_scene(RedesignF2Scene, args, receipt, "f2-saved-state-planner-probe-v2") as scene:
            scene.robot._cmf_planner_audit = True
            scene._cmf_scene_spec = spec
            scene.initialize_trace(scene.can, "left", scene.role_actors)
            _planner_reset(scene, planner_seed=spec["scene_seed"], variant_id="f2-saved-state-planner-probe-v2", arm="left")
            for item in query_specs:
                state_evidence = _restore_saved_scene(scene, trace_data, int(item["state_row"]))
                left_qpos = np.asarray(scene.robot.left_entity.get_qpos(), dtype=np.float64)
                query = {"label": item["label"], "state_row": int(item["state_row"]), "target_eef_pose": item["target"].tolist(), "state_restore": state_evidence}
                try:
                    control = _plan_left(scene, item["target"], last_qpos=left_qpos, source=f"saved_state_v2_{item['label']}")
                    query["status"] = control.get("status") if isinstance(control, Mapping) else "non_mapping_result"
                    query["control_keys"] = sorted(str(key) for key in control) if isinstance(control, Mapping) else []
                    query["planner_query"] = scene.planner_queries[-1] if scene.planner_queries else None
                except BaseException as exc:
                    query["status"] = "EXCEPTION"
                    query["error"] = {"type": type(exc).__name__, "message": str(exc)}
                    query["planner_query"] = scene.planner_queries[-1] if scene.planner_queries else None
                receipt["planner_queries"].append(query)
            receipt["solver_problem_count"] = int(getattr(scene, "planner_query_count", 0))
            receipt["status"] = "diagnostic_complete"
    except BaseException as exc:
        receipt["status"] = "diagnostic_failed"
        receipt["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        receipt["budget_delta"] = {"solver_problems": int(receipt.get("solver_problem_count", 0)), "fresh_scenes": 1, "action_scenes": 0, "collection_attempts": 0, "gpu_lease_seconds": "coordinator_measured"}
        receipt["elapsed_seconds"] = time.monotonic() - started
        receipt["status"] = cleanup_status(receipt, receipt["status"])
        atomic_write_json(output_path / "saved_state_planner_receipt.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--cell-receipt", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--f2-layout-id", required=True, choices=("v4_beside_y_workspace", "v5_beside_y_lower"))
    parser.add_argument("--post-waypoint-hold-frames", type=int, default=20)
    args = parser.parse_args()
    result = run(output=args.output, cell_receipt=args.cell_receipt, trace=args.trace, f2_layout_id=args.f2_layout_id, post_waypoint_hold_frames=args.post_waypoint_hold_frames)
    print(json.dumps({"status": result.get("status"), "root_id": result.get("root_id"), "f2_layout_id": result.get("f2_layout_id"), "state_rows": result.get("state_rows"), "solver_problem_count": result.get("solver_problem_count")}, ensure_ascii=False))
    raise SystemExit(0 if result.get("status") == "diagnostic_complete" else 1)


if __name__ == "__main__":
    main()
