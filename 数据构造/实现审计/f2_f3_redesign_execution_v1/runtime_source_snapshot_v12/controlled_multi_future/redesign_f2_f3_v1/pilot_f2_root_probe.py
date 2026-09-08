"""F2 pilot-root runner for inside/on/beside with exact shared prefix replay."""

from __future__ import annotations

import argparse, json, time
from pathlib import Path
from typing import Any

import numpy as np
from envs.utils.action import ArmTag
from ..family_runners_v3_1 import _execute_control, _must_action, _wait_and_record, _planner_reset
from ..probes.lifecycle import cleanup_status, initialize_cleanup_fields, managed_scene
from ..probes.scene_inspection import _args
from ..planner_dtype_v3_2 import planner_array
from .canonical import atomic_write_json, canonical_sha256, sha256_file
from .f2_scene import RedesignF2Scene
from .pilot_contract import expected_cells, planned_root_contract, reusable_cells, selected_cells


def _move_arm(scene, pose, label, *, receipt=None):
    """Plan one arm move while retaining raw control failure metadata."""
    control = scene.left_move_to_pose(pose=planner_array(pose, shape=(7,), label=f"{label} goal pose"))
    if receipt is not None:
        diagnostics = {"label": label, "status": control.get("status") if isinstance(control, dict) else None, "type": type(control).__name__}
        if isinstance(control, dict):
            for key in ("error", "message", "reason", "status", "success"):
                if key in control:
                    value = control[key]
                    diagnostics[key] = value if isinstance(value, (str, int, float, bool, type(None))) else str(value)
        receipt.setdefault("planner_control_calls", []).append(diagnostics)
    _execute_control(scene, control, label, arm="left")
    return control


def _pose(actor):
    value = actor.get_pose(); return np.asarray(value.p.tolist() + value.q.tolist(), dtype=np.float64)


def _eef(scene): return np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)


def _command_hash_rows(rows):
    keys=("effective_setpoint","requested_command","component_mask","left_gripper_joint_drive_target","right_gripper_joint_drive_target","left_gripper_joint_drive_velocity_target","right_gripper_joint_drive_velocity_target")
    return canonical_sha256({key:[np.asarray(row[key]).tolist() for row in rows] for key in keys})


def _command_hash_artifact(a):
    keys=("effective_setpoint","requested_command","component_mask","left_gripper_joint_drive_target","right_gripper_joint_drive_target","left_gripper_joint_drive_velocity_target","right_gripper_joint_drive_velocity_target")
    return canonical_sha256({key:np.asarray(a[key]).tolist() for key in keys})


def _move_event(scene, realization, dx, dz, label, receipt):
    if realization == "r_inv_motion": _must_action(scene, scene.move_by_displacement(ArmTag("left"), x=dx, z=dz), label)
    else:
        target=_eef(scene); target[0]+=dx; target[2]+=dz; _move_arm(scene,target,label)
    receipt["action_segment_count"]+=1; _wait_and_record(scene,20)


def run_cell(*, output: Path, root_id: str, program_id: str, realization_id: str, seed: int, prefix_artifact: Path | None = None, collection: bool = True, layout_id: str = "v1") -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False); receipt={"schema_version":"cmf_f2_pilot_cell_v1","root_id":root_id,"family":"F2","program_id":program_id,"realization_id":realization_id,"layout_id":layout_id,"collection":collection,"formal_data":False,"stage0_data":False,"status":"running","action_segment_count":0,"solver_problem_count":0}; initialize_cleanup_fields(receipt); started=time.monotonic(); scene=None
    if realization_id == "r_pc":
        receipt["realization_contract"] = {"kind": "baseline", "variant_applied": True, "path_variant": "direct_high_lateral", "motion_variant": "planner_default"}
    elif realization_id == "r_inv_path":
        receipt["realization_contract"] = {"kind": "path", "variant_applied": False, "path_variant": "post_prefix_y_detour_40mm", "motion_variant": "planner_default"}
    elif realization_id == "r_inv_motion":
        receipt["realization_contract"] = {"kind": "motion", "variant_applied": False, "path_variant": "direct_high_lateral", "motion_variant": "post_lateral_35_and_post_descent_40_frame_holds"}
    else:
        raise ValueError(f"unknown F2 realization: {realization_id}")
    args=_args("F2",output/"scene"); args.update({"seed":seed,"task_name":f"cmf_f2_pilot_{root_id}","f2_layout_id":layout_id,"render_freq":0,"save_data":False,"collect_data":False,"need_plan":True})
    try:
        with managed_scene(RedesignF2Scene,args,receipt,f"f2-pilot-{root_id}-{program_id}-{realization_id}") as scene:
            scene.initialize_trace(scene.can,"left",scene.role_actors); receipt["current"]=_pose(scene.can).tolist(); receipt["anchor"]=_pose(scene.can).tolist()
            _planner_reset(scene, planner_seed=20260908, variant_id=f"f2-pilot-{root_id}-{program_id}-{realization_id}", arm="left")
            if prefix_artifact is None:
                grasp=scene.grasp_actor(scene.can,ArmTag("left"),pre_grasp_dis=0.09,grasp_dis=0.0,gripper_pos=0.0,contact_point_id=0); _must_action(scene,grasp,"pilot_grasp"); receipt["action_segment_count"]+=1; _wait_and_record(scene,250)
                eef_before=_eef(scene); lift=eef_before.copy(); lift[2]+=0.16; receipt["prefix_clearance_lift_m"]=0.16; receipt["prefix_clearance_lift_steps"]=4
                for fraction in (0.25, 0.50, 0.75, 1.0):
                    lift_waypoint=eef_before + (lift-eef_before) * fraction
                    _move_arm(scene,lift_waypoint,f"pilot_lift_{int(fraction*3)}",receipt=receipt); receipt["action_segment_count"]+=1; _wait_and_record(scene,20)
                carry=lift.copy(); carry[0]+=0.14; carry[1]-=0.20; _move_arm(scene,carry,"pilot_carry",receipt=receipt); receipt["action_segment_count"]+=1; _wait_and_record(scene,30)
                # Freeze the anchor only after a full closed-gripper hold;
                # the earlier 30-frame tail could end while contact was
                # already decaying, making replayed transport non-physical.
                _wait_and_record(scene,250)
                prefix_end=len(scene.trace)-1; prefix_hash=_command_hash_rows(scene.trace[:prefix_end+1])
            else:
                a=np.load(prefix_artifact,allow_pickle=False)
                for idx in range(1,len(a["effective_setpoint"])):
                    scene.replay_effective_setpoint_step(a["effective_setpoint"][idx],requested_command=a["requested_command"][idx],component_mask=a["component_mask"][idx],left_gripper_joint_drive_target=a["left_gripper_joint_drive_target"][idx],right_gripper_joint_drive_target=a["right_gripper_joint_drive_target"][idx],left_gripper_joint_drive_velocity_target=a["left_gripper_joint_drive_velocity_target"][idx],right_gripper_joint_drive_velocity_target=a["right_gripper_joint_drive_velocity_target"][idx])
                prefix_end=len(scene.trace)-1; prefix_hash=_command_hash_artifact(a)
                # Do not hide an unstable replay with a corrective regrasp or
                # clamp.  The branch is valid only if the frozen prefix still
                # holds the dynamic can at its anchor.
                _wait_and_record(scene,50)
                carry=_eef(scene)
            anchor_rows=scene.trace[max(0,len(scene.trace)-50):]
            prefix_contact_fraction=float(np.mean([bool(row.get("selected_gripper_contact",False)) for row in anchor_rows])) if anchor_rows else 0.0
            receipt["prefix_anchor_contact_fraction"]=prefix_contact_fraction
            receipt["prefix_anchor_contact_stable"]=prefix_contact_fraction>=0.8
            if prefix_artifact is not None and not receipt["prefix_anchor_contact_stable"]:
                raise RuntimeError("frozen prefix anchor lost gripper contact")
            receipt["prefix_end_trace_row"]=prefix_end; receipt["prefix_sha256"]=prefix_hash
            target=carry.copy(); support_name={"inside":"f2_redesign_box_bottom","on":"f2_redesign_scale","beside":"f2_redesign_stand"}[program_id]
            # Bind every branch to the measured carried-object pose.  The
            # grasp transform is asset/pose-specific; a fixed EEF z offset
            # can leave the can floating above the box bottom after release.
            carried_object = _pose(scene.can)
            grasp_offset = carried_object[:3] - carry[:3]
            if program_id == "inside":
                # The open-bottomed box has a usable support plane at the
                # measured top of its static bottom.  Move above the box at a
                # proven clearance, then descend to this binding while the
                # can remains in the gripper.  This keeps the can centered in
                # the frozen interior and makes support_identity observable.
                support_center = np.asarray(scene.box_center, dtype=np.float64)
                support_top = float(support_center[2] + 0.005)
                desired_can = np.asarray([float(support_center[0]), float(support_center[1]), support_top], dtype=np.float64)
            else:
                support_center = scene.scale_center if program_id == "on" else scene.stand_center
                support_top = float(support_center[2] + (0.005 if program_id == "on" else 0.035))
                desired_can = np.asarray([float(support_center[0]), float(support_center[1]), support_top], dtype=np.float64)
            target[:3] = desired_can - grasp_offset
            receipt["target_binding"] = {"carried_eef": carry[:3].tolist(), "carried_object": carried_object[:3].tolist(), "grasp_offset": grasp_offset.tolist(), "support_identity": support_name, "desired_can": desired_can.tolist(), "target_eef": target[:3].tolist()}
            # The prefix itself already carries the can above the wall top.
            # Keep that proven height for the branch lateral move; an extra
            # branch lift makes an otherwise reachable target planner-infeasible.
            carry_high = carry.copy()
            lateral_target = target.copy(); lateral_target[2] = carry_high[2]
            if realization_id == "r_inv_path":
                detour_start = carry_high.copy(); detour_start[1] -= 0.04
                detour_end = lateral_target.copy(); detour_end[1] -= 0.04
                _move_arm(scene, detour_start, f"pilot_{program_id}_path_detour_start",receipt=receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 20)
                _move_arm(scene, detour_end, f"pilot_{program_id}_path_detour_end",receipt=receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 20)
                receipt["realization_contract"]["variant_applied"] = True
            _move_arm(scene, lateral_target, f"pilot_{program_id}_lateral_high",receipt=receipt); receipt["action_segment_count"] += 1; _wait_and_record(scene, 30)
            if realization_id == "r_inv_motion":
                _wait_and_record(scene, 35)
                receipt["realization_contract"]["variant_applied"] = True
            _move_arm(scene,target,f"pilot_{program_id}_descent",receipt=receipt); receipt["action_segment_count"]+=1; _wait_and_record(scene,60); support_end=len(scene.trace)-1
            if realization_id == "r_inv_motion":
                _wait_and_record(scene, 40)
                support_end=len(scene.trace)-1
            _must_action(scene,scene.open_gripper(ArmTag("left"),pos=1.0),"pilot_open"); receipt["action_segment_count"]+=1; _wait_and_record(scene,50)
            if program_id == "beside":
                # Local beside exits are IK-failing from the release state;
                # the saved-state preflight validates the original neutral
                # pose as a safe empty-hand terminal instead.
                exit_target=np.asarray(scene.robot.left_original_pose, dtype=np.float64)
                _move_arm(scene,exit_target,"pilot_empty_hand_exit_origin",receipt=receipt); receipt["action_segment_count"]+=1; _wait_and_record(scene,70)
            else:
                # A diagonal retreat clears the on-scale edge before rising.
                exit_target=_eef(scene); exit_target[2]+=0.10; exit_target[0]+=-0.15; _move_arm(scene,exit_target,"pilot_empty_hand_exit",receipt=receipt); receipt["action_segment_count"]+=1; _wait_and_record(scene,70)
            rows=scene.trace; support_rows=rows[max(0,support_end-59):support_end+1]; exit_rows=rows[-50:]; can_name=scene.can.get_name()
            def pair_has(row,first,second): return any(first in {str(p.get("body_a","")),str(p.get("body_b",""))} and second in {str(p.get("body_a","")),str(p.get("body_b",""))} for p in row.get("contact_pairs",[]))
            support_fraction=float(np.mean([pair_has(row,can_name,support_name) for row in support_rows])) if support_rows else 0.0; exit_contact=float(np.mean([row.get("selected_gripper_contact",False) for row in exit_rows])) if exit_rows else 1.0; final=_pose(scene.can)
            lower=np.asarray(scene._cmf_f2_box_contract["interior_lower_m"]); upper=np.asarray(scene._cmf_f2_box_contract["interior_upper_m"])
            inside=bool(np.all(final[:2]>=lower[:2]) and np.all(final[:2]<=upper[:2])); on=bool(abs(final[0]-float(scene.scale_center[0]))<0.08 and abs(final[1]-float(scene.scale_center[1]))<0.08); beside=bool(abs(final[0]-float(scene.stand_center[0]))<0.08 and abs(final[1]-float(scene.stand_center[1]))<0.08 and not inside and not on)
            receipt["solver_problem_count"]=int(getattr(scene,"planner_query_count",0)); receipt["events"]={"support_fraction":support_fraction,"exit_contact_fraction":exit_contact,"final_can_pose":final.tolist()}; receipt["gates"]={"relation_exclusive":{"inside":inside,"on":on,"beside":beside}[program_id],"support_identity":support_fraction>=0.8,"empty_hand_exit":exit_contact==0.0,"prefix_present":bool(prefix_hash),"prefix_anchor_contact_stable":receipt["prefix_anchor_contact_stable"],"program_order":program_id in {"inside","on","beside"},"realization_variant_applied":bool(receipt["realization_contract"]["variant_applied"])}
            trace_path=output/"trace.npz"; receipt["trace"]=scene.save_trace(trace_path); receipt["trace_path"]=str(trace_path); receipt["status"]="cell_pass" if all(receipt["gates"].values()) else "cell_failed_gates"
    except BaseException as exc: receipt["status"]="cell_failed_execution"; receipt["error"]={"type":type(exc).__name__,"message":str(exc)}
    finally:
        # Preserve partial raw traces for planner/physics failures as well as
        # successful cells; failure evidence must remain inspectable.
        if scene is not None and getattr(scene, "trace", None) and "trace_path" not in receipt:
            try:
                trace_path=output/"trace.npz"; receipt["trace"]=scene.save_trace(trace_path); receipt["trace_path"]=str(trace_path)
            except BaseException as exc:
                receipt["trace_save_error"]={"type":type(exc).__name__,"message":str(exc)}
        receipt["status"]=cleanup_status(receipt,receipt["status"]); receipt["elapsed_seconds"]=time.monotonic()-started; atomic_write_json(output/"cell_receipt.json",receipt)
    return receipt


def run_root(
    output_root: str | Path,
    root_id: str,
    external_prefix: Path | None = None,
    existing_root: Path | None = None,
    programs: list[str] | tuple[str, ...] | None = None,
    realizations: list[str] | tuple[str, ...] | None = None,
    cell_keys: list[str] | tuple[str, ...] | None = None,
    collection: bool = True,
    build_prefix: bool = False,
    layout_id: str = "v1",
):
    """Run a full root or resume only missing programs into a new receipt.

    Reused cells are references to already accepted raw traces.  They are
    counted in the six-cell root gate, but never executed or charged again.
    A resume always requires the frozen external prefix artifact so a newly
    collected suffix cannot silently become a new prefix.
    """
    root_output = Path(output_root); root_output.mkdir(parents=True, exist_ok=True)
    contract = planned_root_contract(root_id)
    full_cells = expected_cells(root_id)
    run_cells = selected_cells(root_id, programs, realizations, cell_keys)
    run_keys = {(cell["program_id"], cell["realization_id"]) for cell in run_cells}
    run_programs = tuple(dict.fromkeys(cell["program_id"] for cell in run_cells))
    run_realizations = tuple(dict.fromkeys(cell["realization_id"] for cell in run_cells))
    if existing_root is not None and programs is None and realizations is None and cell_keys is None:
        raise ValueError("resume root requires an explicit program or realization subset")
    if existing_root is None and len(run_keys) != len(full_cells):
        raise ValueError("a partial root run requires an existing root for immutable reuse")
    if existing_root is not None and external_prefix is None and not build_prefix:
        raise ValueError("resume root requires the frozen external prefix artifact")
    reused: dict[tuple[str, str], dict[str, Any]] = {}
    source_receipt_sha = None
    if existing_root is not None:
        source_receipt_path = Path(existing_root) / "root_receipt.json"
        source = json.loads(source_receipt_path.read_text(encoding="utf-8"))
        if layout_id != "v1" and source.get("layout_id") != layout_id:
            raise ValueError("old root layout cannot be reused across F2 layout versions")
        reuse_keys = {(cell["program_id"], cell["realization_id"]) for cell in full_cells} - run_keys
        reused_list = reusable_cells(source, root_id, cell_keys=reuse_keys)
        reused = {(cell["program_id"], cell["realization_id"]): cell for cell in reused_list}
        source_receipt_sha = sha256_file(source_receipt_path)
    cells: list[dict[str, Any]] = []
    artifact = external_prefix
    for cell in full_cells:
        key = (cell["program_id"], cell["realization_id"])
        if key in reused:
            cells.append(reused[key])
            continue
        if key not in run_keys:
            raise ValueError(f"cell {key} is neither selected for execution nor available for reuse")
        cell_dir = root_output / f"{cell['program_id']}_{cell['realization_id']}"
        receipt = run_cell(output=cell_dir, root_id=root_id, program_id=cell["program_id"], realization_id=cell["realization_id"], seed=contract["scene_seed"], prefix_artifact=artifact, collection=collection, layout_id=layout_id)
        cells.append(receipt)
        if artifact is None and receipt.get("status") == "cell_pass":
            z = np.load(cell_dir / "trace.npz", allow_pickle=False); n = int(receipt["prefix_end_trace_row"]) + 1; artifact = root_output / "prefix_artifact.npz"
            np.savez(artifact, effective_setpoint=z["controller_effective_setpoint"][:n], requested_command=z["requested_command"][:n], component_mask=z["component_masks"][:n], left_gripper_joint_drive_target=z["left_gripper_joint_drive_target"][:n], right_gripper_joint_drive_target=z["right_gripper_joint_drive_target"][:n], left_gripper_joint_drive_velocity_target=z["left_gripper_joint_drive_velocity_target"][:n], right_gripper_joint_drive_velocity_target=z["right_gripper_joint_drive_velocity_target"][:n])
    current = {json.dumps(x.get("current"), sort_keys=True) for x in cells}; anchors = {json.dumps(x.get("anchor"), sort_keys=True) for x in cells}; prefixes = {x.get("prefix_sha256") for x in cells}
    accepted = collection and len(cells) == len(full_cells) and all(x.get("status") == "cell_pass" for x in cells) and len(current) == 1 and len(anchors) == 1 and len(prefixes) == 1
    new_cell_count = len(full_cells) - len(reused)
    receipt = {"schema_version": "cmf_f2_pilot_root_receipt_v1", "root_id": root_id, "family": "F2", "layout_id": layout_id, "contract": {**contract, "layout_id": layout_id}, "cells": cells, "current_equivalence": len(current) == 1, "anchor_equivalence": len(anchors) == 1, "prefix_exact_replay": len(prefixes) == 1, "accepted": accepted, "status": "ACCEPTED" if accepted else "INCOMPLETE", "collection": collection, "collection_count": new_cell_count if collection else 0, "run_programs": list(run_programs), "run_realizations": list(run_realizations), "new_cell_keys": [f"{key[0]}:{key[1]}" for key in sorted(run_keys)], "new_cell_count": new_cell_count, "reused_cell_count": len(reused), "reused_from_root_receipt": source_receipt_sha, "reused_cell_keys": [f"{key[0]}:{key[1]}" for key in reused], "prefix_mode": "freshly_built_from_first_new_cell" if build_prefix else ("external_frozen_artifact" if external_prefix is not None else "cell_local")}
    atomic_write_json(root_output / "root_receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", required=True); parser.add_argument("--root-id", required=True); parser.add_argument("--prefix-artifact"); parser.add_argument("--existing-root"); parser.add_argument("--programs", help="comma-separated programs to execute; remaining cells are reused from --existing-root"); parser.add_argument("--realizations", help="comma-separated realizations to execute; remaining cells are reused from --existing-root"); parser.add_argument("--cell-keys", help="comma-separated program:realization cells to execute"); parser.add_argument("--qualification", action="store_true", help="run as non-collection transport qualification"); parser.add_argument("--build-prefix", action="store_true", help="build a fresh shared prefix from the first newly executed cell"); parser.add_argument("--layout-id", default="v1", choices=("v1", "v2", "v3")); args = parser.parse_args()
    programs = [item for item in args.programs.split(",") if item] if args.programs else None
    realizations = [item for item in args.realizations.split(",") if item] if args.realizations else None
    cell_keys = [item for item in args.cell_keys.split(",") if item] if args.cell_keys else None
    result = run_root(args.output, args.root_id, Path(args.prefix_artifact) if args.prefix_artifact else None, Path(args.existing_root) if args.existing_root else None, programs, realizations, cell_keys, collection=not args.qualification, build_prefix=args.build_prefix, layout_id=args.layout_id)
    raise SystemExit(0 if result["accepted"] else 1)


if __name__=="__main__": main()
