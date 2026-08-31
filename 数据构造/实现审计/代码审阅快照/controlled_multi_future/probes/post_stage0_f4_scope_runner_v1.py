"""Guarded child for F4 post-Stage-0 planner-only audit."""
from __future__ import annotations
import argparse,json,os,traceback
from pathlib import Path
from ..f4_post_stage0_planner_only_v1 import F4PostStage0PlannerOnlyV1
from ..post_stage0_f4_scope_v1 import SCOPE,post_stage0_f4_budget_v1
from ..real_sapien_adapter_post_stage0_f4_v1 import IMPLEMENTATION_VERSION,RoboTwinRealSapienPostStage0F4AdapterV1
from .gpu_guard_v2_4 import require_atomic_gpu_guard_v2_4
from .post_stage0_f4_authorization_v1 import authorization_summary,load_post_stage0_f4_authorization_v1,load_post_stage0_f4_consumption_v1
def _write(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def _cleanup(rows):
    rows=list(rows); return {"scene_created":any(x.get("scene_created") is True for x in rows),"scene_cleanup_succeeded":bool(rows) and all(x.get("cleanup_safety_pass") is True and int(x.get("orphan_process_count") or 0)==0 for x in rows),"orphan_process_count":sum(int(x.get("orphan_process_count") or 0) for x in rows)}
def _budget(r):
    b=post_stage0_f4_budget_v1(); c=r.get("budget_counts",{}); checks={"planner":0<=int(c.get("planner_query_count",-1))<=b["planner_query_limit"],"prefix_execution":0<=int(c.get("canonical_prefix_reference_execution_count",-1))<=1,
        "suffix_zero":int(c.get("suffix_execution_attempt_count",-1))==0,"release_zero":int(c.get("release_execution_count",-1))==0,"recovery_zero":int(c.get("recovery_attempt_count",-1))==0,"scenes":len(r.get("cleanup_records",[]))<=4}
    if not all(checks.values()): raise RuntimeError(f"F4 budget exceeded: {checks}")
    return {"budget":b,"checks":checks,"pass":True}
def main():
    p=argparse.ArgumentParser(); p.add_argument("--authorization-receipt",type=Path,required=True); a=p.parse_args(); auth=load_post_stage0_f4_authorization_v1(a.authorization_receipt,requested_scope=SCOPE,expected_family="F4",expected_seed=20260829)
    cp=os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT"); gp=os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not cp or not gp: raise PermissionError("F4 child lacks Guard binding")
    consumption=load_post_stage0_f4_consumption_v1(Path(cp),auth); gv=json.loads(Path(gp).read_text()); bind=gv.get("binding",{}); index=int(bind["physical_gpu_index"]); uuid=str(bind["expected_gpu_uuid"])
    if os.environ.get("CUDA_VISIBLE_DEVICES")!=uuid: raise RuntimeError("guarded UUID mismatch")
    guard=require_atomic_gpu_guard_v2_4(auth,consumption,expected_uuid=uuid,physical_index=index); out=Path(auth["output_namespace"]); out.mkdir(parents=True,exist_ok=False)
    agg={"schema_version":"cmf_post_stage0_f4_guarded_scope_receipt_v1","implementation_version":IMPLEMENTATION_VERSION,"scope":SCOPE,"family":"F4","formal_data":False,"stage0_data":False,"stage0_authorized":False,"stage0_reopened":False,"stage1_authorized":False,
        "authorization":authorization_summary(auth),"authorization_consumption_receipt_sha256":consumption["consumption_receipt_sha256"],"guard_binding":guard["binding"],"guard_precheck":guard["precheck"],"result":None,"cleanup_records":[],"budget_counts":{},"status":"running"}; _write(out/"receipt.json",agg)
    try:
        adapter=RoboTwinRealSapienPostStage0F4AdapterV1(family="F4",output_root=out/"scene_work",expected_implementation_source_sha256=auth["implementation_source_sha256"])
        result=F4PostStage0PlannerOnlyV1(adapter).run(output_dir=out/"F4_planner_only",planned_root_slot_spec=auth["planned_root_slot_spec"])
        agg["result"]={"relative_receipt_path":"F4_planner_only/receipt.json","status":result.get("status"),"pass":result.get("pass") is True,"receipt_sha256":result.get("receipt_sha256")}; agg["cleanup_records"]=list(result.get("cleanup_records",[])); agg["budget_counts"]=dict(result.get("budget_counts",{})); agg["budget_validation"]=_budget(result); clean=_cleanup(agg["cleanup_records"]); agg.update(clean)
        agg["status"]="accepted" if result.get("pass") is True and clean["scene_cleanup_succeeded"] else "failed_cleanup_uncertain" if not clean["scene_cleanup_succeeded"] else result.get("status","failed_execution")
    except BaseException as exc:
        partial=out/"F4_planner_only/receipt.json"
        if partial.is_file():
            r=json.loads(partial.read_text()); agg["result"]={"relative_receipt_path":"F4_planner_only/receipt.json","status":r.get("status"),"pass":r.get("pass") is True,"receipt_sha256":r.get("receipt_sha256"),"partial_receipt_propagated":True}; agg["cleanup_records"]=list(r.get("cleanup_records",[])); agg["budget_counts"]=dict(r.get("budget_counts",{}))
        clean=_cleanup(agg["cleanup_records"]); agg.update(clean); agg["status"]="failed_cleanup_uncertain" if agg["scene_created"] and not clean["scene_cleanup_succeeded"] else "failed_execution"; agg["error"]={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
    agg["pass"]=agg["status"]=="accepted"; _write(out/"receipt.json",agg); return 0 if agg["pass"] else 1
if __name__=="__main__": raise SystemExit(main())
