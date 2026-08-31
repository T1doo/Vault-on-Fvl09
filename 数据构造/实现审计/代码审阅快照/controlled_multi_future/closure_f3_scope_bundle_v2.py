"""CPU publications and one-shot bundle for Closure-V1 F3 V2."""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
import hashlib,json,os,subprocess
from pathlib import Path
from .closure_f3_scope_v2 import *
from .current_hasher import hash_json
from .f3_common_grasp_prefix_v2 import IMPLEMENTATION_VERSION
from .gpu_parallel_policy_v2 import current_gpu_policy_artifact
from .probes.closure_f3_authorization_v2 import AUTH_SCHEMA,receipt_sha,validate
from .probes.gpu_guard_v2_1 import command_sha256
from .probes.runtime_v3_3_authorization_v1 import CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,CANONICAL_GPU_LEASE_DIRECTORY,CANONICAL_JOB_CACHE_DIRECTORY
from .runtime_source_lock_v1 import capture_runtime_source_lock,write_runtime_source_lock
ROOT=Path("/nfs_share/lijunhui");REPO=ROOT/"Robotwin2/project/RoboTwin";ACTIVE=REPO/"controlled_multi_future";SNAP=ROOT/"Vault-on-Fvl09/数据构造/实现审计/代码审阅快照/controlled_multi_future";VAULT=ROOT/"Vault-on-Fvl09";PYTHON=ROOT/"Robotwin2/env/bin/python"
def _fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def _tree(root):
 h=hashlib.sha256()
 for p in sorted(Path(root).rglob("*.py")):h.update(p.relative_to(root).as_posix().encode());h.update(b"\0");h.update(p.read_bytes());h.update(b"\0")
 return h.hexdigest()
def _git(*a):return subprocess.run(["git","-C",str(VAULT),*a],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.strip()
def _new(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,"wb") as f:f.write((json.dumps(v,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode());f.flush();os.fsync(f.fileno())
def write_publications():
 values={BUDGET:budget(),PUBLICATION:publication(),PARENT:parent()}
 for p,v in values.items():
  if p.exists():
   if json.loads(p.read_text())!=v:raise RuntimeError(f"existing publication changed {p}")
  else:_new(p,v)
 return {str(p):{"sha256":_fsha(p),"bytes":p.stat().st_size} for p in values}
def build_bundle():
 head=_git("rev-parse","HEAD");origin=_git("rev-parse","origin/main")
 if head!=origin:raise RuntimeError("Vault HEAD not published")
 ledger=Path(CANONICAL_CONSUMPTION_LEDGER_DIRECTORY)/f"{AUTH_ID}.json";cache=Path(CANONICAL_JOB_CACHE_DIRECTORY)/AUTH_ID
 if any(p.exists() for p in (OUTPUT,GUARD,AUTH,ledger,cache)):raise RuntimeError("F3 Closure run1 exists")
 active=_tree(ACTIVE)
 if _tree(SNAP)!=active:raise RuntimeError("active/snapshot differ")
 write_publications();source=capture_runtime_source_lock(family="F3")
 if source["snapshot"]["implementation_source_sha256"]!=active:raise RuntimeError("source hash")
 child=[str(PYTHON),"-m","controlled_multi_future.probes.closure_f3_scope_runner_v2","--authorization-receipt",str(AUTH.resolve())];policy=current_gpu_policy_artifact();b=budget();s=spec();par=parent();pub=publication();ev=json.loads(EVIDENCE.read_text())
 request={"schema_version":"cmf_closure_v1_f3_request_v2","implementation_version":IMPLEMENTATION_VERSION,"scope":SCOPE,"family":"F3","scene_seed":SEED,"planned_root_slot_spec":s,"planned_root_slot_spec_sha256":s["planned_scope_spec_sha256"],"scope_publication_sha256":pub["scope_publication_sha256"],"budget_receipt_sha256":b["budget_receipt_sha256"],"source_evidence_result_payload_sha256":ev["result_payload_sha256"],"implementation_source_sha256":active,"reviewed_content_commit":head,"uncommitted_source_bound_by_source_lock":True,"parent_user_authorization_sha256":par["parent_user_authorization_sha256"],"authorized_command":child,"authorized_command_sha256":command_sha256(child),"output_namespace":str(OUTPUT.resolve()),"guard_receipt_path":str(GUARD.resolve()),"allowed_physical_gpu_indices":list(range(8)),"gpu_policy_sha256":policy["policy_sha256"],"automatic_retry":False,"recovery_attempts":0,"formal_data":False,"stage0_data":False,"stage0_authorized":False,"stage1_authorized":False};request["scope_request_sha256"]=hash_json(request);write_runtime_source_lock(SOURCE,source);_new(REQUEST,request)
 issued=datetime.now(timezone.utc);a={"schema_version":AUTH_SCHEMA,"implementation_version":IMPLEMENTATION_VERSION,"approved":True,"approved_scopes":[SCOPE],"authorization_id":AUTH_ID,"authorized_run_id":AUTH_ID+"-run","issued_at":issued.isoformat(),"expires_at":(issued+timedelta(seconds=3600)).isoformat(),"family":"F3","scene_seed":SEED,"max_invocations":1,"automatic_retry":False,"recovery_attempts":0,"formal_data":False,"stage0_data":False,"stage0_authorized":False,"stage1_authorized":False,"planned_root_slot_spec":s,"planned_root_slot_spec_sha256":s["planned_scope_spec_sha256"],"scope_publication_path":str(PUBLICATION.resolve()),"scope_publication_file_sha256":_fsha(PUBLICATION),"scope_publication_sha256":pub["scope_publication_sha256"],"budget_publication_path":str(BUDGET.resolve()),"budget_publication_file_sha256":_fsha(BUDGET),"budget_receipt_sha256":b["budget_receipt_sha256"],"planner_query_limit":b["planner_query_limit"],"controlled_action_limit":b["execution_limit"],"physics_step_limit":-1,"timeout_seconds":b["timeout_seconds"],"source_evidence_path":str(EVIDENCE.resolve()),"source_evidence_file_sha256":_fsha(EVIDENCE),"source_lock_receipt_path":str(SOURCE.resolve()),"source_lock_receipt_sha256":source["source_lock_receipt_sha256"],"implementation_source_sha256":active,"reviewed_content_commit":head,"uncommitted_source_bound_by_source_lock":True,"parent_user_authorization_path":str(PARENT.resolve()),"parent_user_authorization_file_sha256":_fsha(PARENT),"parent_user_authorization_sha256":par["parent_user_authorization_sha256"],"approval_request_path":str(REQUEST.resolve()),"approval_request_file_sha256":_fsha(REQUEST),"approval_request_sha256":request["scope_request_sha256"],"authorized_command":child,"authorized_command_sha256":command_sha256(child),"output_namespace":str(OUTPUT.resolve()),"guard_receipt_path":str(GUARD.resolve()),"consumption_ledger_directory":CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,"gpu_lease_directory":CANONICAL_GPU_LEASE_DIRECTORY,"job_cache_root_directory":CANONICAL_JOB_CACHE_DIRECTORY,**{k:policy[k] for k in ("gpu_policy_version","allowed_physical_gpu_indices","dynamic_fresh_idle_selection","parallel_different_cards_authorized","one_project_job_per_gpu","one_root_one_gpu","root_sharding_authorized","share_busy_gpu_authorized","atomic_guard_recheck_before_launch","automatic_gpu0_fallback")}};a["receipt_sha256"]=receipt_sha(a);_new(AUTH,a);validate(a,requested_scope=SCOPE,now=issued+timedelta(seconds=1),expected_family="F3",expected_seed=SEED,expected_output_namespace=str(OUTPUT.resolve()),expected_reviewed_content_commit=head)
 return {"schema_version":"cmf_closure_v1_f3_bundle_v2","authorization_receipt_sha256":a["receipt_sha256"],"authorization_path":str(AUTH),"source_sha256":active,"source_lock_sha256":source["source_lock_receipt_sha256"],"output":str(OUTPUT),"guard":str(GUARD),"child_command":child,"allowed_physical_gpu_indices":list(range(8))}
