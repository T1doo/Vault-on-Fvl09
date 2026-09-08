"""Non-executing F2 planner preflight from a saved trace state."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import sapien

from ..family_runners_v3_1 import PlannerChainFailure, _planner_reset, _plan_left
from ..probes.lifecycle import cleanup_status, initialize_cleanup_fields, managed_scene
from ..probes.scene_inspection import _args
from .canonical import atomic_write_json, sha256_file
from .f2_scene import RedesignF2Scene


def _set_saved_articulation(scene, qpos: np.ndarray, qvel: np.ndarray) -> dict[str, Any]:
    left = scene.robot.left_entity; right = scene.robot.right_entity
    left_n = len(left.get_qpos())
    if qpos.size < left_n:
        raise ValueError(f"saved qpos has {qpos.size} values but left articulation needs {left_n}")
    left.set_qpos(qpos[:left_n]); left.set_qvel(qvel[:left_n])
    if right is not left:
        right_n = len(right.get_qpos())
        if qpos.size < left_n + right_n:
            raise ValueError("saved qpos does not contain the right articulation")
        right.set_qpos(qpos[left_n:left_n + right_n]); right.set_qvel(qvel[left_n:left_n + right_n])
    return {"left_qpos_dim": left_n, "full_saved_qpos_dim": int(qpos.size), "right_shared_entity": right is left}


def run(*, output: str | Path, cell_receipt: str | Path, trace: str | Path, stand_xs: list[float] | None = None) -> dict[str, Any]:
    output_path = Path(output); receipt_path = Path(cell_receipt); trace_path = Path(trace); output_path.mkdir(parents=True, exist_ok=True)
    source_receipt = json.loads(receipt_path.read_text(encoding="utf-8")); z = np.load(trace_path, allow_pickle=False); rows = len(z["step_index"]); prefix_end = int(source_receipt.get("prefix_end_trace_row", rows - 1))
    saved_qpos = np.asarray(z["joint_qpos"][prefix_end], dtype=np.float64); saved_qvel = np.asarray(z["joint_qvel"][prefix_end], dtype=np.float64); saved_object = np.asarray(z["object_pose"][prefix_end], dtype=np.float64); saved_eef = np.asarray(z["eef_pose"][prefix_end], dtype=np.float64)
    target_binding = source_receipt.get("target_binding") or {}; target_value = np.asarray(target_binding.get("target_eef", saved_eef[:3]), dtype=np.float64); descent = target_value.copy() if target_value.size == 7 else saved_eef.copy(); descent[:3] = target_value[:3]; lateral = descent.copy(); lateral[2] = float(saved_eef[2])
    variants: list[tuple[str, np.ndarray, np.ndarray]] = [("original", lateral, descent)]
    offset = saved_object[:3] - saved_eef[:3]
    for stand_x in stand_xs or []:
        desired = np.asarray([float(stand_x), -0.18, 0.825 + 0.07118775383879648 / 2.0], dtype=np.float64)
        candidate_descent = saved_eef.copy(); candidate_descent[:3] = desired - offset; candidate_lateral = candidate_descent.copy(); candidate_lateral[2] = saved_eef[2]
        variants.append((f"stand_x_{float(stand_x):.3f}", candidate_lateral, candidate_descent))
    receipt: dict[str, Any] = {"schema_version":"cmf_f2_saved_state_planner_probe_v1","task_id":"f2_f3_redesign_20260907","status":"running","collection":False,"formal_data":False,"stage0_data":False,"cell_receipt_path":str(receipt_path),"cell_receipt_sha256":sha256_file(receipt_path),"trace_path":str(trace_path),"trace_sha256":sha256_file(trace_path),"prefix_end_trace_row":prefix_end,"saved_qpos_dim":int(saved_qpos.size),"saved_object_pose":saved_object.tolist(),"goals":{"lateral_high":lateral.tolist(),"descent":descent.tolist()},"layout_variants":[{"id":label,"lateral_high":goal_a.tolist(),"descent":goal_b.tolist()} for label,goal_a,goal_b in variants],"planner_queries":[]}
    initialize_cleanup_fields(receipt); started=time.monotonic(); args=_args("F2", output_path/"scene"); args.update({"seed":202609081,"task_name":"cmf_f2_saved_state_planner_probe","render_freq":0,"save_data":False,"collect_data":False,"need_plan":True})
    try:
        with managed_scene(RedesignF2Scene,args,receipt,"f2-saved-state-planner-probe") as scene:
            scene.initialize_trace(scene.can,"left",scene.role_actors); _set_saved_articulation(scene,saved_qpos,saved_qvel); scene.can.actor.set_pose(sapien.Pose(saved_object[:3],saved_object[3:])); _planner_reset(scene,planner_seed=20260908,variant_id="f2-saved-state-planner-probe",arm="left")
            left_qpos = np.asarray(scene.robot.left_entity.get_qpos(), dtype=np.float64)
            for variant, lateral_goal, descent_goal in variants:
                for label, goal in ((f"{variant}_lateral_high",lateral_goal),(f"{variant}_descent",descent_goal)):
                    item={"label":label,"goal_eef_pose":goal.tolist()}
                    try:
                        control=_plan_left(scene,goal,last_qpos=left_qpos,source=f"saved_state_{label}")
                        item["status"] = control.get("status") if isinstance(control,dict) else "non_mapping_result"
                        item["control_keys"] = sorted(control.keys()) if isinstance(control,dict) else []
                        item["control_error"] = {key:control.get(key) for key in ("error","message","reason") if isinstance(control,dict) and key in control}
                        item["planner_query"] = scene.planner_queries[-1] if getattr(scene,"planner_queries",None) else None
                    except BaseException as exc:
                        item["status"]="EXCEPTION"; item["error"]={"type":type(exc).__name__,"message":str(exc)}; item["planner_query"] = scene.planner_queries[-1] if getattr(scene,"planner_queries",None) else None
                    receipt["planner_queries"].append(item)
            receipt["solver_problem_count"] = int(getattr(scene,"planner_query_count",0)); receipt["saved_articulation"]={"left_qpos_dim":len(scene.robot.left_entity.get_qpos()),"current_left_eef":np.asarray(scene.robot.get_left_ee_pose(),dtype=np.float64).tolist()}; receipt["status"]="diagnostic_complete"
    except BaseException as exc:
        receipt["status"]="diagnostic_failed"; receipt["error"]={"type":type(exc).__name__,"message":str(exc)}
    finally:
        receipt["budget_delta"]={"solver_problems":int(receipt.get("solver_problem_count",0)),"fresh_scenes":1,"action_scenes":0,"collection_attempts":0,"gpu_lease_seconds":"coordinator_measured"}; receipt["elapsed_seconds"]=time.monotonic()-started; receipt["status"]=cleanup_status(receipt,receipt["status"]); atomic_write_json(output_path/"saved_state_planner_receipt.json",receipt)
    return receipt


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--output",required=True); parser.add_argument("--cell-receipt",required=True); parser.add_argument("--trace",required=True); parser.add_argument("--stand-xs",default=""); args=parser.parse_args(); stand_xs=[float(item) for item in args.stand_xs.split(",") if item.strip()] if args.stand_xs else None; result=run(output=args.output,cell_receipt=args.cell_receipt,trace=args.trace,stand_xs=stand_xs); raise SystemExit(0 if result.get("status")=="diagnostic_complete" else 1)


if __name__ == "__main__": main()
