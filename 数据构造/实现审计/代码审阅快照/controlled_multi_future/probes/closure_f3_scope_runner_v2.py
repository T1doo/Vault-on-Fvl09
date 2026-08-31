"""Guarded Closure-V1 F3CommonGraspPrefixV2 child."""
from __future__ import annotations
import argparse,json,os,traceback
from pathlib import Path
from ..closure_f3_scope_v2 import SCOPE,budget
from ..f3_common_grasp_prefix_v2 import IMPLEMENTATION_VERSION
from ..f3_shared_prefix_no_suffix_diagnostic_v1 import F3SharedPrefixNoSuffixDiagnosticV1
from ..real_sapien_adapter_closure_f3_v2 import RoboTwinRealSapienClosureF3V2Adapter
from .closure_f3_authorization_v2 import load,load_consumption,summary
from .gpu_guard_v2_4 import require_atomic_gpu_guard_v2_4
def _write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def _clean(rows):rows=list(rows);return {"scene_created":any(x.get("scene_created") is True for x in rows),"scene_cleanup_succeeded":bool(rows) and all(x.get("cleanup_safety_pass") is True and int(x.get("orphan_process_count") or 0)==0 for x in rows),"orphan_process_count":sum(int(x.get("orphan_process_count") or 0) for x in rows)}
def _budget(r):
 b=budget();c=r.get("budget_counts",{});checks={"planner":0<=int(c.get("planner_query_count",-1))<=16,"execution":0<=int(c.get("execution_attempt_count",-1))<=3,"recovery":int(c.get("recovery_attempt_count",-1))==0,"scene":len(r.get("cleanup_records",[]))<=3,"suffix":int(r.get("suffix_planner_query_count",-1))==0 and int(r.get("suffix_execution_count",-1))==0,"release":int(r.get("release_execution_count",-1))==0}
 if not all(checks.values()):raise RuntimeError(f"budget {checks}")
 return {"checks":checks,"pass":True,"budget":b}
def main():
 p=argparse.ArgumentParser();p.add_argument("--authorization-receipt",type=Path,required=True);x=p.parse_args();a=load(x.authorization_receipt,requested_scope=SCOPE,expected_family="F3",expected_seed=20260829);cp=os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT");gp=os.environ.get("CMF_GPU_GUARD_RECEIPT")
 if not cp or not gp:raise PermissionError("Guard binding missing")
 c=load_consumption(Path(cp),a);g=json.loads(Path(gp).read_text());bind=g["binding"];idx=int(bind["physical_gpu_index"]);uuid=str(bind["expected_gpu_uuid"])
 if os.environ.get("CUDA_VISIBLE_DEVICES")!=uuid:raise RuntimeError("UUID mismatch")
 guard=require_atomic_gpu_guard_v2_4(a,c,expected_uuid=uuid,physical_index=idx);out=Path(a["output_namespace"]);out.mkdir(parents=True,exist_ok=False);agg={"schema_version":"cmf_closure_v1_f3_outer_v2","implementation_version":IMPLEMENTATION_VERSION,"scope":SCOPE,"family":"F3","formal_data":False,"stage0_data":False,"stage0_authorized":False,"stage1_authorized":False,"authorization":summary(a),"authorization_consumption_receipt_sha256":c["consumption_receipt_sha256"],"guard_binding":guard["binding"],"guard_precheck":guard["precheck"],"result":None,"cleanup_records":[],"budget_counts":{},"status":"running"};_write(out/"receipt.json",agg)
 try:
  adapter=RoboTwinRealSapienClosureF3V2Adapter(family="F3",output_root=out/"scene_work",expected_implementation_source_sha256=a["implementation_source_sha256"]);r=F3SharedPrefixNoSuffixDiagnosticV1(adapter).run(output_dir=out/"F3CommonGraspPrefixV2",planned_root_slot_spec=a["planned_root_slot_spec"]);agg["result"]={"relative_receipt_path":"F3CommonGraspPrefixV2/receipt.json","status":r.get("status"),"pass":r.get("pass") is True,"receipt_sha256":r.get("receipt_sha256")};agg["cleanup_records"]=list(r.get("cleanup_records",[]));agg["budget_counts"]=dict(r.get("budget_counts",{}));agg["budget_validation"]=_budget(r);cl=_clean(agg["cleanup_records"]);agg.update(cl);agg["status"]="accepted" if r.get("pass") is True and cl["scene_cleanup_succeeded"] else "failed_cleanup_uncertain" if not cl["scene_cleanup_succeeded"] else r.get("status","failed_execution")
 except BaseException as e:
  q=out/"F3CommonGraspPrefixV2/receipt.json"
  if q.is_file():r=json.loads(q.read_text());agg["result"]={"relative_receipt_path":"F3CommonGraspPrefixV2/receipt.json","status":r.get("status"),"pass":r.get("pass") is True,"receipt_sha256":r.get("receipt_sha256"),"partial":True};agg["cleanup_records"]=list(r.get("cleanup_records",[]));agg["budget_counts"]=dict(r.get("budget_counts",{}))
  cl=_clean(agg["cleanup_records"]);agg.update(cl);agg["status"]="failed_cleanup_uncertain" if agg["scene_created"] and not cl["scene_cleanup_succeeded"] else "failed_execution";agg["error"]={"type":type(e).__name__,"message":str(e),"traceback":traceback.format_exc()}
 agg["pass"]=agg["status"]=="accepted";_write(out/"receipt.json",agg);return 0 if agg["pass"] else 1
if __name__=="__main__":raise SystemExit(main())
