"""Frozen four-candidate qualification and online micro dispatch."""
import argparse,json,os,traceback,importlib.util
from pathlib import Path
import numpy as np
from unittest.mock import patch
from manifest_contract import candidates,load_manifest,check_budget,canonical,sha,AUDIT
from candidate_executor import run_candidate

HELPER=Path("/nfs_share/lijunhui/Robotwin2/production_micro_gate_v1/job_runner.py")
HELPER_SHA="376ddfbe07b1c9ae3e6e3b2d1975344a8605c6e81e49f27e92241c88a851a1d4"
def helper():
    if sha(HELPER)!=HELPER_SHA:raise ValueError("helper source")
    s=importlib.util.spec_from_file_location("f3_micro_helper",HELPER)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def write_new(p,d):
    from controlled_multi_future.canonical_artifact import canonical_jsonable
    d=canonical_jsonable(d); d["receipt_sha256"]=canonical({k:v for k,v in d.items() if k!="receipt_sha256"})
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x") as f:json.dump(d,f,sort_keys=True,indent=2,ensure_ascii=False)
    return d

def record_scene_attempt(open_scene, prepare, execute, save_trace):
    """Always return failure/accounting/cleanup evidence, including setup failures."""
    context=None;scene=None;result=None;before=after=None;trace=None;errors=[];preparation=None
    def error(exc,stage):errors.append({"stage":stage,"type":type(exc).__name__,"message":str(exc),"evidence":getattr(exc,"evidence",None)})
    try:
        with open_scene() as (scene,context):
            before=int(getattr(scene,"planner_query_count",0))
            try:
                preparation=prepare(scene)
                result=execute(scene)
            finally:
                try:after=int(scene.planner_query_count)
                except Exception as exc:error(exc,"counter_finally")
                try:trace=save_trace(scene)
                except Exception as exc:error(exc,"trace_finally")
    except Exception as exc:error(exc,"scene_attempt")
    delta=None if before is None or after is None else after-before
    # Before scene entry no planner dispatch is possible; missing post-entry counts
    # remain unknown, never falsely recorded as zero.
    if scene is None:delta=0
    complete=delta is not None and delta>=0
    return {"result":result,"error":errors or None,"planner_before":before,"planner_after":after,
            "planner_delta":delta,"accounting_complete":complete,
            "scene_instance_id":getattr(scene,"_cmf_scene_instance_id",None),"scene_binding_equivalence":preparation,
            "cleanup":None if context is None else context.cleanup_receipt,"trace":trace}

def cpu_bound_specs(m):
    from controlled_multi_future.f3_asset_grasp_qualification_v2 import build_f3_asset_grasp_qualification_v2
    from controlled_multi_future.high_level_runtime_specs_v1 import build_f3_runtime_spec_v1
    from controlled_multi_future.planner_qualification_manifests_v2_3 import _f3_scene_binding
    from controlled_multi_future.f3_planner_integration_v3_1 import build_f3_stage_a_planner_spec_v3_1
    tuples=build_f3_asset_grasp_qualification_v2()["grasp_tuples"]
    rows=[]
    for i,recipe in enumerate(candidates()):
        t=next(x for x in tuples if x["asset"]==recipe["asset"] and x["arm"]==recipe["arm"])
        legacy=build_f3_runtime_spec_v1(t["tuple_id"],purpose="f3_level1_planner")
        a=build_f3_stage_a_planner_spec_v3_1(recipe,_f3_scene_binding(recipe),slot_id=m["jobs"][0]["job_id"]+"-a-"+str(i),
                     panel_sha256=m["candidate_freeze_sha256"],planner_reset_nonce=2026090700+10*(i+1))
        rows.append((i,recipe,t,legacy,a))
    return rows

def run(m):
    from controlled_multi_future.f3_asset_grasp_qualification_v2 import build_f3_asset_grasp_qualification_v2
    from controlled_multi_future.high_level_runtime_specs_v1 import build_f3_runtime_spec_v1
    from controlled_multi_future.planner_qualification_manifests_v2_3 import _f3_scene_binding
    from controlled_multi_future.f3_planner_integration_v3_1 import build_f3_stage_a_planner_spec_v3_1,build_f3_stage_b_planner_spec_v3_1,run_f3_stage_a_planner_v3_1,run_f3_stage_b_planner_v3_1
    from controlled_multi_future.f3_lift_anchored_event_center_v1 import build_f3_lift_anchored_stage_b_targets_v1
    h=helper();job=m["jobs"][0];out=Path(job["output_namespace"])
    out.mkdir(parents=True,exist_ok=False)
    all_receipts=[];qualified=[];physical=[];total=0;planner_scenes=0;physical_scenes=0
    phase_queries={"qualification":0,"physical":0}
    tuples=build_f3_asset_grasp_qualification_v2()["grasp_tuples"]
    def attempt(recipe,legacy,directory,phase,execute,is_physical=False):
        nonlocal total,planner_scenes,physical_scenes
        if is_physical:physical_scenes+=1
        else:planner_scenes+=1
        check_budget(total,planner_scenes,physical_scenes,len(physical))
        holder={}
        def open_scene():
            holder["adapter"]=h.adapter_for("F3",legacy,directory/"adapter",m["implementation_source_sha256"])
            return h.opened_scene(holder["adapter"],legacy,phase=phase,program=None,family="F3")
        def prepare(scene):
            if not hasattr(scene,"planner_query_count"):scene.planner_query_count=0
            binding=h.prepare_f3_scene(scene,holder["adapter"],recipe,_f3_scene_binding(recipe))
            if is_physical:scene.initialize_trace(scene.bottle,recipe["arm"],role_actors=scene.role_actors)
            return binding
        def save_trace(scene):
            if is_physical and getattr(scene,"trace",None):
                directory.mkdir(parents=True,exist_ok=True)
                return h.save_trace(scene,directory/"physical_trace.npz")
        receipt=record_scene_attempt(open_scene,prepare,execute,save_trace)
        receipt.update(recipe_sha256=recipe["recipe_sha256"],phase=phase)
        receipt=write_new(directory/"scene_receipt.json",receipt)
        all_receipts.append(receipt)
        if not receipt["accounting_complete"]:raise RuntimeError("unknown planner accounting; stop")
        delta=receipt["planner_delta"];total+=delta
        role="physical" if is_physical else "qualification"
        phase_queries[role]+=delta
        if delta>(3 if is_physical or phase=="F3_MICRO_STAGE_A" else 7):raise RuntimeError("per-scene query cap exceeded")
        if phase_queries["qualification"]>40 or phase_queries["physical"]>12:raise RuntimeError("phase query cap exceeded")
        check_budget(total,planner_scenes,physical_scenes,len(physical))
        if receipt["error"] is not None:raise RuntimeError("scene attempt failed: "+str(receipt["error"]))
        if (receipt["cleanup"] or {}).get("cleanup_safety_pass") is not True:raise RuntimeError("scene cleanup failed")
        return receipt["result"]
    error=None
    try:
        for i,recipe,t,legacy,a in cpu_bound_specs(m):
            ta=attempt(recipe,legacy,out/str(i)/"stage_a","F3_MICRO_STAGE_A",lambda scene:run_f3_stage_a_planner_v3_1(scene,a))
            if ta.get("stage_a_pass") is not True:continue
            b=build_f3_stage_b_planner_spec_v3_1(ta,a,slot_id=job["job_id"]+"-b-"+str(i),
                     selection_policy_sha256=m["candidate_freeze_sha256"],planner_reset_nonce=2026090701+10*(i+1))
            targets=build_f3_lift_anchored_stage_b_targets_v1(b["stage_a_lift_pose"])
            names=("central_1","V_plus","V_minus","central_2","H_plus","H_minus","central_3")
            targets=[{"segment_id":"f3_v3_stage_b_"+n,"pose":v["pose"]} for n,v in zip(names,targets)]
            def stage_b(scene):
                with patch("controlled_multi_future.f3_planner_integration_v3_1.build_f3_stage_b_targets_v3_1",return_value=targets):
                    return run_f3_stage_b_planner_v3_1(scene,b)
            tb=attempt(recipe,legacy,out/str(i)/"stage_b","F3_MICRO_STAGE_B",stage_b)
            if tb.get("stage_b_pass") is True:qualified.append((i,recipe,t,ta))
        for i,recipe,t,ta in qualified:
            legacy=build_f3_runtime_spec_v1(t["tuple_id"],purpose="f3_level2_physical")
            result=attempt(recipe,legacy,out/str(i)/"physical","F3_PRECLOSE_MICRO",lambda scene:run_candidate(scene,recipe,ta,planner_seed=20260829),True)
            physical.append({"recipe_id":recipe["recipe_id"],"recipe_sha256":recipe["recipe_sha256"],"result":result})
            if sum(x["result"].get("pass") is True for x in physical)>=2:break
    except Exception as exc:error={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
    terminal={"schema_version":"cmf_f3_preclose_micro_terminal_v1","manifest_sha256":m["manifest_sha256"],
      "planner_queries":total,"phase_queries":phase_queries,"planner_scenes":planner_scenes,"physical_scenes":physical_scenes,
      "accounting_complete":all(r["accounting_complete"] for r in all_receipts),
      "physical_attempts":physical_scenes,"physical_rows":physical,"scene_receipts":all_receipts,"error":error,
      "pass":error is None and sum(x["result"].get("pass") is True for x in physical)>=2,
      "shared_v":0,"no_suffix":0,"root":0,"raw":0,"formal":0}
    return write_new(out/"job_terminal.json",terminal)

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--manifest",type=Path,required=True);p.add_argument("--job-id");p.add_argument("--preflight-only",action="store_true")
    a=p.parse_args(argv);m=load_manifest(a.manifest,execution=not a.preflight_only,runner=not a.preflight_only)
    if a.preflight_only:
        bound=cpu_bound_specs(m)
        print(json.dumps({"pass":True,"candidates":[r["recipe_id"] for r in candidates()],"caps":m["caps"],"execution_dispatch":"run_candidate","gpu_used":False,
            "bound_stage_a_specs":[{"recipe_id":r[1]["recipe_id"],"spec_sha256":r[4]["spec_sha256"]} for r in bound]}))
        return 0
    if not os.environ.get("CUDA_VISIBLE_DEVICES","").startswith("GPU-") or "LD_LIBRARY_PATH" in os.environ:raise PermissionError("Guard environment")
    return 0 if run(m)["pass"] else 1
if __name__=="__main__":raise SystemExit(main())
