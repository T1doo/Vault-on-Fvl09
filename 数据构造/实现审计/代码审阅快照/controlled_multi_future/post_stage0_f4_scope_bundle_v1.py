"""CPU publications and one-shot bundle for F4 planner-only audit."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib, json, os, subprocess
from pathlib import Path

from .current_hasher import hash_json
from .gpu_parallel_policy_v2 import current_gpu_policy_artifact
from .post_stage0_f4_scope_v1 import *
from .probes.gpu_guard_v2_1 import command_sha256
from .probes.post_stage0_f4_authorization_v1 import AUTHORIZATION_SCHEMA_VERSION, authorization_receipt_sha256, validate_post_stage0_f4_authorization_v1
from .probes.runtime_v3_3_authorization_v1 import CANONICAL_CONSUMPTION_LEDGER_DIRECTORY, CANONICAL_GPU_LEASE_DIRECTORY, CANONICAL_JOB_CACHE_DIRECTORY
from .real_sapien_adapter_post_stage0_f4_v1 import IMPLEMENTATION_VERSION
from .runtime_source_lock_v1 import capture_runtime_source_lock, write_runtime_source_lock

ROOT=Path("/nfs_share/lijunhui"); REPO=ROOT/"Robotwin2/project/RoboTwin"; ACTIVE=REPO/"controlled_multi_future"
SNAP=ROOT/"Vault-on-Fvl09/数据构造/实现审计/代码审阅快照/controlled_multi_future"; VAULT=ROOT/"Vault-on-Fvl09"; PYTHON=ROOT/"Robotwin2/env/bin/python"

def _file_sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def _tree(root):
    h=hashlib.sha256()
    for p in sorted(Path(root).rglob("*.py")):
        h.update(p.relative_to(root).as_posix().encode()); h.update(b"\0"); h.update(p.read_bytes()); h.update(b"\0")
    return h.hexdigest()
def _git(*args): return subprocess.run(["git","-C",str(VAULT),*args],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.strip()
def _new(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"wb") as f: f.write((json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode()); f.flush(); os.fsync(f.fileno())

def write_post_stage0_f4_cpu_publications_v1():
    values={BUDGET_PUBLICATION:post_stage0_f4_budget_v1(),SCOPE_PUBLICATION:post_stage0_f4_scope_publication_v1(),PARENT_AUTHORIZATION:post_stage0_f4_parent_authorization_v1()}
    for p,v in values.items(): _new(p,v)
    return {str(p):{"bytes":p.stat().st_size,"sha256":_file_sha(p)} for p in values}

def build_post_stage0_f4_bundle_v1():
    head=_git("rev-parse","HEAD"); origin=_git("rev-parse","origin/main")
    if head!=origin: raise RuntimeError("Vault HEAD differs from origin/main")
    ledger=Path(CANONICAL_CONSUMPTION_LEDGER_DIRECTORY)/f"{AUTHORIZATION_ID}.json"; cache=Path(CANONICAL_JOB_CACHE_DIRECTORY)/AUTHORIZATION_ID
    if any(p.exists() for p in (OUTPUT_NAMESPACE,GUARD_PATH,AUTHORIZATION_PATH,ledger,cache)): raise RuntimeError("F4 run1 namespace already exists")
    active=_tree(ACTIVE)
    if _tree(SNAP)!=active: raise RuntimeError("active/snapshot source differ")
    publications={BUDGET_PUBLICATION:post_stage0_f4_budget_v1(),SCOPE_PUBLICATION:post_stage0_f4_scope_publication_v1(),PARENT_AUTHORIZATION:post_stage0_f4_parent_authorization_v1()}
    for p,v in publications.items():
        if not p.is_file() or json.loads(p.read_text())!=v: raise RuntimeError(f"publication changed: {p}")
    impact=json.loads(IMPACT_REVIEW.read_text())
    if impact.get("review_payload_sha256")!="ca9c3c1419a4513c849311eed904246c4784da3b36f306bcee8e9021f133e043": raise RuntimeError("impact review changed")
    source=capture_runtime_source_lock(family="F4")
    if source["snapshot"]["implementation_source_sha256"]!=active: raise RuntimeError("source hash mismatch")
    child=[str(PYTHON),"-m","controlled_multi_future.probes.post_stage0_f4_scope_runner_v1","--authorization-receipt",str(AUTHORIZATION_PATH.resolve())]
    policy=current_gpu_policy_artifact(); budget=post_stage0_f4_budget_v1(); planned=post_stage0_f4_planned_spec_v1(); parent=post_stage0_f4_parent_authorization_v1(); scope_pub=post_stage0_f4_scope_publication_v1()
    request={"schema_version":"cmf_post_stage0_f4_scope_request_v1","implementation_version":IMPLEMENTATION_VERSION,"scope":SCOPE,"family":"F4","scene_seed":SCENE_SEED,
        "planned_root_slot_spec":planned,"planned_root_slot_spec_sha256":planned["planned_scope_spec_sha256"],"scope_publication_sha256":scope_pub["scope_publication_sha256"],
        "budget_receipt_sha256":budget["budget_receipt_sha256"],"impact_review_payload_sha256":impact["review_payload_sha256"],"implementation_source_sha256":active,
        "reviewed_content_commit":head,"reviewed_content_commit_contains_current_changes":False,"uncommitted_source_bound_by_source_lock":True,
        "parent_user_authorization_sha256":parent["parent_user_authorization_sha256"],"authorized_command":child,"authorized_command_sha256":command_sha256(child),
        "output_namespace":str(OUTPUT_NAMESPACE.resolve()),"guard_receipt_path":str(GUARD_PATH.resolve()),"allowed_physical_gpu_indices":list(range(8)),
        "gpu_policy_sha256":policy["policy_sha256"],"automatic_retry":False,"recovery_attempts":0,"formal_data":False,"stage0_data":False,"stage0_authorized":False,"stage0_reopened":False,"stage1_authorized":False}
    request["scope_request_sha256"]=hash_json(request); write_runtime_source_lock(SOURCE_LOCK_PATH,source); _new(REQUEST_PATH,request)
    issued=datetime.now(timezone.utc)
    auth={"schema_version":AUTHORIZATION_SCHEMA_VERSION,"implementation_version":IMPLEMENTATION_VERSION,"approved":True,"approved_scopes":[SCOPE],"authorization_id":AUTHORIZATION_ID,
        "authorized_run_id":AUTHORIZATION_ID+"-run","issued_at":issued.isoformat(),"expires_at":(issued+timedelta(seconds=3600)).isoformat(),"family":"F4","scene_seed":SCENE_SEED,
        "max_invocations":1,"automatic_retry":False,"recovery_attempts":0,"formal_data":False,"stage0_data":False,"stage0_authorized":False,"stage0_reopened":False,"stage1_authorized":False,
        "planned_root_slot_spec":planned,"planned_root_slot_spec_sha256":planned["planned_scope_spec_sha256"],"scope_publication_path":str(SCOPE_PUBLICATION.resolve()),"scope_publication_file_sha256":_file_sha(SCOPE_PUBLICATION),
        "scope_publication_sha256":scope_pub["scope_publication_sha256"],"budget_publication_path":str(BUDGET_PUBLICATION.resolve()),"budget_publication_file_sha256":_file_sha(BUDGET_PUBLICATION),
        "budget_receipt_sha256":budget["budget_receipt_sha256"],"planner_query_limit":budget["planner_query_limit"],"controlled_action_limit":budget["canonical_prefix_reference_execution_limit"],
        "physics_step_limit":budget["physics_step_limit"],"timeout_seconds":budget["timeout_seconds"],"impact_review_path":str(IMPACT_REVIEW.resolve()),"impact_review_file_sha256":_file_sha(IMPACT_REVIEW),
        "impact_review_payload_sha256":impact["review_payload_sha256"],"source_lock_receipt_path":str(SOURCE_LOCK_PATH.resolve()),"source_lock_receipt_sha256":source["source_lock_receipt_sha256"],
        "implementation_source_sha256":active,"reviewed_content_commit":head,"reviewed_content_commit_contains_current_changes":False,"uncommitted_source_bound_by_source_lock":True,
        "parent_user_authorization_path":str(PARENT_AUTHORIZATION.resolve()),"parent_user_authorization_file_sha256":_file_sha(PARENT_AUTHORIZATION),"parent_user_authorization_sha256":parent["parent_user_authorization_sha256"],
        "approval_request_path":str(REQUEST_PATH.resolve()),"approval_request_file_sha256":_file_sha(REQUEST_PATH),"approval_request_sha256":request["scope_request_sha256"],"authorized_command":child,
        "authorized_command_sha256":command_sha256(child),"output_namespace":str(OUTPUT_NAMESPACE.resolve()),"guard_receipt_path":str(GUARD_PATH.resolve()),"consumption_ledger_directory":CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        "gpu_lease_directory":CANONICAL_GPU_LEASE_DIRECTORY,"job_cache_root_directory":CANONICAL_JOB_CACHE_DIRECTORY,
        **{k:policy[k] for k in ("gpu_policy_version","allowed_physical_gpu_indices","dynamic_fresh_idle_selection","parallel_different_cards_authorized","one_project_job_per_gpu","one_root_one_gpu","root_sharding_authorized","share_busy_gpu_authorized","atomic_guard_recheck_before_launch","automatic_gpu0_fallback")}}
    auth["receipt_sha256"]=authorization_receipt_sha256(auth); _new(AUTHORIZATION_PATH,auth)
    validate_post_stage0_f4_authorization_v1(auth,requested_scope=SCOPE,now=issued+timedelta(seconds=1),expected_family="F4",expected_seed=SCENE_SEED,expected_output_namespace=str(OUTPUT_NAMESPACE.resolve()),expected_reviewed_content_commit=head)
    return {"schema_version":"cmf_post_stage0_f4_bundle_receipt_v1","implementation_version":IMPLEMENTATION_VERSION,"scope":SCOPE,"reviewed_content_commit":head,
        "implementation_source_sha256":active,"scope_publication_sha256":scope_pub["scope_publication_sha256"],"budget_receipt_sha256":budget["budget_receipt_sha256"],
        "parent_user_authorization_sha256":parent["parent_user_authorization_sha256"],"source_lock_receipt_sha256":source["source_lock_receipt_sha256"],"scope_request_sha256":request["scope_request_sha256"],
        "authorization_receipt_sha256":auth["receipt_sha256"],"authorization_path":str(AUTHORIZATION_PATH.resolve()),"guard_path":str(GUARD_PATH.resolve()),"output_namespace":str(OUTPUT_NAMESPACE.resolve()),
        "child_command":child,"timeout_seconds":budget["timeout_seconds"],"physical_gpu_indices":list(range(8)),"uncommitted_source_bound_by_source_lock":True}
