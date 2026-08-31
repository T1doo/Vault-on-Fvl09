"""Fail-closed Closure-V1 F4 V2 authorization."""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib,json,os,re
from pathlib import Path
from ..closure_f3_scope_v2 import parent
from ..closure_f4_scope_v2 import *
from ..current_hasher import hash_json
from ..gpu_parallel_policy_v2 import validate_current_gpu_authorization
from ..real_sapien_adapter_closure_f4_v2 import IMPLEMENTATION_VERSION
from ..runtime_source_lock_v1 import load_runtime_source_lock
from .runtime_v3_3_authorization_v1 import AuthorizationBindingError,AuthorizationExpiredError,AuthorizationReplayError,CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,CANONICAL_GPU_LEASE_DIRECTORY,CANONICAL_JOB_CACHE_DIRECTORY
AUTH_SCHEMA="cmf_closure_v1_f4_authorization_v2";CONSUMPTION_SCHEMA="cmf_closure_v1_f4_consumption_v2";HEX40=re.compile(r"^[0-9a-f]{40}$");HEX64=re.compile(r"^[0-9a-f]{64}$")
def _fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def receipt_sha(v):p=dict(v);p.pop("receipt_sha256",None);return hash_json(p)
def _file(v,label):
 p=Path(v).resolve() if isinstance(v,str) else Path("/")
 if not str(p).startswith("/nfs_share/lijunhui/") or not p.is_file():raise AuthorizationBindingError(f"{label} invalid")
 return p
def _path(v,label):
 p=Path(v).resolve() if isinstance(v,str) else Path("/")
 if not str(p).startswith("/nfs_share/lijunhui/"):raise AuthorizationBindingError(f"{label} invalid")
 return p
def _time(v):
 try:r=datetime.fromisoformat(v)
 except Exception as e:raise AuthorizationBindingError("time") from e
 if r.tzinfo is None:raise AuthorizationBindingError("timezone")
 return r.astimezone(timezone.utc)
def validate(v,*,requested_scope,now=None,expected_output_namespace=None,expected_family=None,expected_seed=None,expected_reviewed_content_commit=None):
 if requested_scope!=SCOPE:raise AuthorizationBindingError("scope")
 r=json.loads(json.dumps(v,sort_keys=True,allow_nan=False));fixed={"schema_version":AUTH_SCHEMA,"implementation_version":IMPLEMENTATION_VERSION,"approved":True,"approved_scopes":[SCOPE],"authorization_id":AUTH_ID,"authorized_run_id":AUTH_ID+"-run","family":"F4","scene_seed":SEED,"max_invocations":1,"automatic_retry":False,"recovery_attempts":0,"formal_data":False,"stage0_data":False,"stage0_authorized":False,"stage1_authorized":False}
 for k,e in fixed.items():
  if r.get(k)!=e:raise AuthorizationBindingError(f"field {k}")
 if expected_family not in (None,"F4") or expected_seed not in (None,SEED):raise AuthorizationBindingError("family/seed")
 if r.get("receipt_sha256")!=receipt_sha(r):raise AuthorizationBindingError("hash")
 issued,expires=_time(r.get("issued_at")),_time(r.get("expires_at"));current=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
 if not 0<(expires-issued).total_seconds()<=3600 or not issued<=current<expires:raise AuthorizationExpiredError("inactive")
 validate_current_gpu_authorization(r);b=budget()
 for k,e in (("budget_receipt_sha256",b["budget_receipt_sha256"]),("planner_query_limit",96),("controlled_action_limit",1),("physics_step_limit",-1),("timeout_seconds",14400)):
  if r.get(k)!=e:raise AuthorizationBindingError(f"budget {k}")
 for field,path,value in (("budget_publication_path",BUDGET,budget()),("scope_publication_path",PUBLICATION,publication()),("parent_user_authorization_path",PARENT,parent())):
  p=_file(r.get(field),field);sf=field.replace("_path","_file_sha256")
  if p!=path.resolve() or _fsha(p)!=r.get(sf) or json.loads(p.read_text())!=value:raise AuthorizationBindingError(f"publication {field}")
 if r.get("planned_root_slot_spec")!=spec() or r.get("planned_root_slot_spec_sha256")!=spec()["planned_scope_spec_sha256"]:raise AuthorizationBindingError("spec")
 rv=_file(r.get("layout_review_path"),"review");oi=_file(r.get("old_inner_receipt_path"),"old inner")
 if rv!=REVIEW.resolve() or _fsha(rv)!=r.get("layout_review_file_sha256") or json.loads(rv.read_text()).get("review_payload_sha256")!="ca9c3c1419a4513c849311eed904246c4784da3b36f306bcee8e9021f133e043" or oi!=OLD_INNER.resolve() or _fsha(oi)!="deef47bee0e58ca1081f355857033898143b84c68f36e7c7a6a51acf65d3a186":raise AuthorizationBindingError("evidence")
 sp=_file(r.get("source_lock_receipt_path"),"source");source=load_runtime_source_lock(sp,expected_family="F4")
 if sp!=SOURCE.resolve() or source["source_lock_receipt_sha256"]!=r.get("source_lock_receipt_sha256") or source["snapshot"]["implementation_source_sha256"]!=r.get("implementation_source_sha256"):raise AuthorizationBindingError("source")
 rp=_file(r.get("approval_request_path"),"request");req=json.loads(rp.read_text());q=dict(req);d=q.pop("scope_request_sha256",None)
 if rp!=REQUEST.resolve() or _fsha(rp)!=r.get("approval_request_file_sha256") or hash_json(q)!=d or d!=r.get("approval_request_sha256") or req.get("authorized_command_sha256")!=r.get("authorized_command_sha256") or req.get("output_namespace")!=r.get("output_namespace"):raise AuthorizationBindingError("request")
 ex={"consumption_ledger_directory":CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,"gpu_lease_directory":CANONICAL_GPU_LEASE_DIRECTORY,"job_cache_root_directory":CANONICAL_JOB_CACHE_DIRECTORY,"output_namespace":str(OUTPUT.resolve()),"guard_receipt_path":str(GUARD.resolve())}
 for k,e in ex.items():
  if str(_path(r.get(k),k))!=e:raise AuthorizationBindingError(f"path {k}")
 if expected_output_namespace is not None and Path(expected_output_namespace).resolve()!=OUTPUT.resolve():raise AuthorizationBindingError("output")
 if not isinstance(r.get("reviewed_content_commit"),str) or not HEX40.fullmatch(r["reviewed_content_commit"]) or (expected_reviewed_content_commit is not None and r["reviewed_content_commit"]!=expected_reviewed_content_commit):raise AuthorizationBindingError("commit")
 if not isinstance(r.get("authorized_command_sha256"),str) or not HEX64.fullmatch(r["authorized_command_sha256"]):raise AuthorizationBindingError("command")
 return r
def load(path,*,requested_scope,**kwargs):
 p=Path(path).resolve()
 if p!=AUTH.resolve():raise AuthorizationBindingError("auth path")
 return validate(json.loads(p.read_text()),requested_scope=requested_scope,**kwargs)
def consumption_sha(v):p=dict(v);p.pop("consumption_receipt_sha256",None);p.pop("path",None);return hash_json(p)
def consume(a,*,ledger_directory):
 l=Path(ledger_directory).resolve()
 if str(l)!=CANONICAL_CONSUMPTION_LEDGER_DIRECTORY:raise AuthorizationBindingError("ledger")
 l.mkdir(parents=True,exist_ok=True);p=l/f"{AUTH_ID}.json";v={"schema_version":CONSUMPTION_SCHEMA,"implementation_version":IMPLEMENTATION_VERSION,"authorization_id":AUTH_ID,"authorization_receipt_sha256":a["receipt_sha256"],"approved_scope":SCOPE,"family":"F4","scene_seed":SEED,"consumed_at":datetime.now(timezone.utc).isoformat(),"max_invocations":1};v["consumption_receipt_sha256"]=consumption_sha(v)
 try:fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 except FileExistsError as e:raise AuthorizationReplayError("consumed") from e
 with os.fdopen(fd,"wb") as h:h.write((json.dumps(v,indent=2,sort_keys=True)+"\n").encode());h.flush();os.fsync(h.fileno())
 return {**v,"path":str(p)}
def validate_consumption(v,a):
 r=dict(v);e={"schema_version":CONSUMPTION_SCHEMA,"implementation_version":IMPLEMENTATION_VERSION,"authorization_id":AUTH_ID,"authorization_receipt_sha256":a.get("receipt_sha256"),"approved_scope":SCOPE,"family":"F4","scene_seed":SEED,"max_invocations":1}
 if any(r.get(k)!=x for k,x in e.items()) or r.get("consumption_receipt_sha256")!=consumption_sha(r):raise AuthorizationBindingError("consumption")
 return r
def load_consumption(path,a):r=validate_consumption(json.loads(Path(path).read_text()),a);r["path"]=str(Path(path).resolve());return r
def summary(v):return {k:v.get(k) for k in ("authorization_id","receipt_sha256","approved_scopes","family","scene_seed","planned_root_slot_spec_sha256","implementation_source_sha256","budget_receipt_sha256","parent_user_authorization_sha256","reviewed_content_commit","output_namespace","timeout_seconds","allowed_physical_gpu_indices")}
