"""Candidate-bound online pre-close micro executor. No shared-V dispatch."""
from pathlib import Path
import importlib.util
import hashlib
import numpy as np
from controlled_multi_future.geometry import relative_pose
from controlled_multi_future.anchor import quaternion_angular_error
from controlled_multi_future.f3_physical_contact_signal_v8 import classify_contact_pair_physical_hit_v8

GATE_PATH=Path(__file__).resolve().parent.parent/"f3_preclose_physical_consistency_gate_v1_1/gate.py"
def load_gate():
    s=importlib.util.spec_from_file_location("f3_full_window_online",GATE_PATH)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
GATE=load_gate()
Q={"left":[6,14,18,22,26,30],"right":[7,15,19,23,27,31]}
A={"left":[0,1,2,3,4,5,12,13,14,15,16,17],"right":[6,7,8,9,10,11,18,19,20,21,22,23]}


def online_window(scene, execution, target, planned_segment, arm):
    start,end=execution["start_trace_row"],execution["end_trace_row"]
    last=scene.trace[end]; initial=scene.trace[0]
    masks=np.asarray([r["component_mask"] for r in scene.trace[start+1:end+1]])
    selected=list(scene.selected_gripper_links())
    from controlled_multi_future.family_runners_v3_1 import _entity
    bottle=_entity(scene.bottle).get_name(); pad=_entity(scene.pad).get_name()
    boundary={"stage":"pregrasp" if target["segment_id"].endswith("pregrasp") else "grasp",
       "arm":arm,"planned_selected_arm_qpos":np.asarray(planned_segment["end_qpos"])[Q[arm]],
       "realized_selected_arm_qpos":np.asarray(last["joint_qpos"])[Q[arm]],
       "planner_goal_eef_pose":target["pose"],"realized_eef_pose":last["eef"],
       "initial_bottle_position_m":initial["actor_pose"][:3],"realized_bottle_position_m":last["actor_pose"][:3],
       "contact_pairs":last["contact_pairs"],"selected_gripper_links":selected,
       "bottle_actor_name":bottle,"support_actor_names":["table",pad],
       "selected_arm_commanded":bool(masks[:,A[arm]].any()),
       "opposite_arm_commanded":bool(masks[:,A["right" if arm=="left" else "left"]].any())}
    rows=({"row_index":i,"contact_signal_complete":"contact_pairs" in scene.trace[i],
           "contact_pairs":scene.trace[i].get("contact_pairs",[]),
           "bottle_position_m":scene.trace[i]["actor_pose"][:3]} for i in range(start+1,end+1))
    return GATE.evaluate_window(boundary,rows,start=start,end=end)


def sequence(execute, window, close, hold, lift, verify):
    """Callbacks make sequencing testable without GPU; failure cannot reach close."""
    events=[]; windows=[]
    for stage in ("pregrasp","grasp"):
        receipt=execute(stage);events.append(stage)
        result=window(stage,receipt); windows.append(result);events.append(stage+"_gate")
        if result["pass"] is not True:
            return {"pass":False,"stop_before_close":True,"close_executed":False,
                    "events":events,"windows":windows}
    close(); events.append("close_0.50")
    hold(); events.append("hold_250")
    lift(); events.append("micro_lift_25mm")
    checked=verify();events.append("verify_and_stop")
    return {"pass":checked["pass"] is True,"stop_before_close":False,"close_executed":True,
            "events":events,"windows":windows,"post_lift":checked,"shared_v_executed":False}


def run_candidate(scene, recipe, stage_a_terminal, *, planner_seed):
    from controlled_multi_future.high_level_physical_runner_v1 import _execute_planned_segment
    from controlled_multi_future.family_runners_v3_1 import _plan_chain,_planner_reset,_must_action,_arm_tag,_wait_and_record,_arm_eef_pose,_pose,_entity
    arm=recipe["arm"]; goals=stage_a_terminal["final_pose_freeze"]["final_goal_poses"]
    grasp=np.asarray(goals["grasp"],dtype=float); lift=grasp.copy();lift[2]+=.025
    targets=[{"segment_id":"f3_micro_pregrasp","pose":goals["pregrasp"]},
             {"segment_id":"f3_micro_grasp","pose":grasp.tolist()},
             {"segment_id":"f3_micro_lift25","pose":lift.tolist()}]
    _planner_reset(scene,planner_seed=planner_seed,variant_id="f3_preclose_micro:"+recipe["recipe_id"],arm=arm)
    planned=_plan_chain(scene,targets,query_limit=3,arm=arm)
    if planned["pass"] is not True:
        return {"pass":False,"close_executed":False,"planner_result":{k:v for k,v in planned.items() if k!="controls"}}
    baseline={}
    def execute(stage):
        i=0 if stage=="pregrasp" else 1
        return _execute_planned_segment(scene,planned["controls"],targets,i,arm)
    def window(stage,e):
        i=0 if stage=="pregrasp" else 1
        return online_window(scene,e,targets[i],planned["segment_receipts"][i],arm)
    def close(): _must_action(scene,scene.close_gripper(_arm_tag(arm),pos=.50),"f3_micro_close")
    def hold():
        _wait_and_record(scene,250)
        baseline["transform"]=relative_pose(_arm_eef_pose(scene,arm),_pose(scene.bottle))
        baseline["row"]=len(scene.trace)-1
    def lift_action(): _execute_planned_segment(scene,planned["controls"],targets,2,arm)
    def verify():
        selected=set(scene.selected_gripper_links()); bottle=_entity(scene.bottle).get_name()
        support={"table",_entity(scene.pad).get_name()}
        contact=[]; off=[]; complete=[]
        for row in scene.trace[baseline["row"]+1:]:
            physical=[]; available=True
            for p in row["contact_pairs"]:
                if bottle not in {p["body_a"],p["body_b"]}:continue
                v=classify_contact_pair_physical_hit_v8(p)
                available &= v["evidence_complete"] is True
                if v["physical_hit_for_gate"]:physical.append({p["body_a"],p["body_b"]})
            contact.append(any(bool(p & selected) for p in physical))
            off.append(not any(bool(p & support) for p in physical));complete.append(available)
        transform=relative_pose(_arm_eef_pose(scene,arm),_pose(scene.bottle))
        translation=float(np.linalg.norm(transform[:3]-baseline["transform"][:3]))
        angle=quaternion_angular_error(transform[3:],baseline["transform"][3:])
        checks={"contact_continuity":bool(contact) and all(contact),"off_support":bool(off) and off[-1],
                "contact_complete":bool(complete) and all(complete),"transform_translation":translation<=.005,
                "transform_orientation":angle<=.05}
        return {"checks":checks,"pass":all(checks.values()),"translation_drift_m":translation,"orientation_drift_rad":angle}
    result=sequence(execute,window,close,hold,lift_action,verify)
    result["planner_query_count"]=len(planned["segment_receipts"])
    result["targets"]=targets
    return result
