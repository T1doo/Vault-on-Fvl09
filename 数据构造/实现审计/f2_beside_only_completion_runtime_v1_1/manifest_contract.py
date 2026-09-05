"""Exact F2 beside-only conditional execution contract."""
import hashlib,json
from pathlib import Path
ROOT=Path("/nfs_share/lijunhui")
AUDIT=Path(__file__).resolve().parent.parent
GUARD_ENTRY="GUARD_ENTRY"
POST_CHILD="POST_CHILD"
AUTH=AUDIT/"EXTERNAL_EXECUTION_DECISION_F4_ADOPTION_F2_F3_20260905_V1.json"
INSIDE=ROOT/"Robotwin2/datasets/controlled_multi_future_f2_controlled_insertion_route_gate_v1/f2-controlled-insertion-route-gate-short-tmpdir-recovery-run3/inside_planner_receipt.json"
def canonical(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
canonical_hash=canonical
file_sha=sha
def read(p,key):
    if not Path(p).resolve().is_relative_to(ROOT):raise ValueError("outside workspace")
    d=json.loads(Path(p).read_text());v=dict(d);h=v.pop(key,None)
    if h!=canonical(v):raise ValueError("self hash")
    return d
def load_manifest(p,*,execution=True,runner=False,post=False):
    from semantic_target import corrected_contract
    m=read(p,"manifest_sha256");a=read(AUTH,"receipt_sha256");f=a["decision"]["f2"]
    if m["authorization_receipt_sha256"]!=a["receipt_sha256"] or sha(AUTH)!=m["authorization_file_sha256"]:raise PermissionError("approval binding")
    if sha(a["authoritative_message"]["path"])!=a["authoritative_message"]["file_sha256"]:raise PermissionError("review source")
    if f["decision"]!="CONFIRM_LIVE_METADATA_GEOMETRY_AND_EXISTING_BESIDE_ONLY_PERMISSION":raise PermissionError("decision")
    c,target=corrected_contract()
    if target["receipt_sha256"]!=f["target_artifact_receipt_sha256"] or target["targets_sha256"]!=f["corrected_beside_targets_sha256"]:raise ValueError("target binding")
    if target["receipt_sha256"]!=m["target_artifact_receipt_sha256"]:raise ValueError("manifest target")
    for k in ("approved","gpu_execution_authorized","planner_execution_authorized","scene_execution_authorized"):
        if m.get(k) is not True:raise PermissionError(k)
    for k in ("physical_execution_authorized","root_execution_authorized","stage1_authorized","formal_360_authorized","training_authorized","h_reveal_authorized","compression_authorized","pi05_authorized","automatic_retry","inside_rerun","full_11_query_rerun"):
        if m.get(k) is not False:raise PermissionError(k)
    if m["allowed_physical_gpu_indices"]!=list(range(8)):raise ValueError("GPU scope")
    runtime=Path(__file__).resolve().parent
    names=("manifest_contract.py","guarded_launcher.py","job_runner.py","semantic_target.py","scene_attempt.py")
    if set(m["source_files"])!={str(runtime/n) for n in names}:raise ValueError("source set")
    for source,digest in m["source_files"].items():
        if sha(source)!=digest:raise ValueError("source changed")
    for role,n in (("guard","guarded_launcher.py"),("runner","job_runner.py")):
        if m[role+"_script_path"]!=str(runtime/n) or m[role+"_script_sha256"]!=sha(runtime/n):raise ValueError("dispatch source")
    if m["implementation_source_sha256"]!="3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7":raise ValueError("active source")
    inside=read(INSIDE,"receipt_sha256")
    if sha(INSIDE)!=m["inside_file_sha256"] or inside["planner_pass"] is not True or inside["planner_query_count"]!=5 or inside["cleanup"]["cleanup_safety_pass"] is not True:raise ValueError("inside retained evidence")
    if len(m["jobs"])!=1:raise ValueError("one job")
    job=m["jobs"][0]
    expected={"family":"F2","mode":"F2_BESIDE_ONLY_COMPLETION_V1","planner_query_cap":6,"fresh_scene_cap":1,"physical_execution_cap":0,"raw_trajectory_cap":0,"accepted_root_cap":0,"formal_trajectory_cap":0,"timeout_seconds":3600,"planner_seed":2026090402}
    if any(job.get(k)!=v for k,v in expected.items()):raise ValueError("job exact caps/seed")
    for v in (job["output_namespace"],m["guard_directory"],m["cache_directory"]):
        if not Path(v).resolve().is_relative_to(ROOT):raise ValueError("path")
    cache=Path(m["cache_directory"])/job["job_id"]
    if len(str(cache/"tmp").encode())>100:raise ValueError("TMPDIR")
    if not post and Path(job["output_namespace"]).exists():raise ValueError("output used")
    if not runner and not post and (Path(m["guard_directory"]).exists() or cache.exists()):raise ValueError("used Guard/cache")
    if runner:verify_runner_lease(m)
    return m
def validate_terminal(t):
    r=t["scene_receipt"];q=r["planner_delta"]
    if q is not None and (type(q) is not int or q<0 or q>6):raise ValueError("query cap")
    if t["planner_queries"]!=q:raise ValueError("query accounting")
    for k in ("physical_execution_count","raw_trajectory_count","accepted_root_count","formal_trajectory_count"):
        if type(t[k]) is not int or t[k]!=0:raise ValueError("zero caps")
    passed=r["accounting_complete"] is True and r["error"] is None and q==6 and (r["result"] or {}).get("planner_pass") is True and (r["cleanup"] or {}).get("cleanup_safety_pass") is True and t["inside_unchanged"] is True
    if t["pass"] is not passed:raise ValueError("success classification")
    return passed

def verify_runner_lease(m):
    import os,fcntl
    job=m["jobs"][0]; path=Path(m["guard_directory"])/(job["job_id"]+".start.json")
    start=read(path,"receipt_sha256")
    index=start["physical_gpu_index"];uuid=start["gpu_uuid"]
    expected=ROOT/"Robotwin2/gpu_leases/production_micro_gate_v1"/f"physical_gpu_{index}.lock"
    if index not in range(8) or start.get("manifest_sha256")!=m["manifest_sha256"] or start.get("job_id")!=job["job_id"]:raise PermissionError("Guard start identity")
    if start.get("family")!="F2" or start.get("guard_pid")!=os.getppid():raise PermissionError("Guard parent identity")
    if os.environ.get("CUDA_VISIBLE_DEVICES")!=uuid or "LD_LIBRARY_PATH" in os.environ:raise PermissionError("Guard device environment")
    if os.environ.get("CMF_GPU_LEASE_PATH")!=str(expected) or start.get("lease_path")!=str(expected):raise PermissionError("Guard lease binding")
    if os.environ.get("CMF_F2_GUARD_START_RECEIPT")!=str(path):raise PermissionError("Guard receipt environment")
    with expected.open("r+") as f:
        try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return True
        fcntl.flock(f.fileno(),fcntl.LOCK_UN)
    raise PermissionError("lease not held by Guard")

def load_and_validate_manifest_job(path,job_id,*,phase,require_execution_authorized,executable_role,executable_path):
    if require_execution_authorized is not True:raise PermissionError("real Guard requires exact approval")
    m=load_manifest(path,execution=True,post=phase==POST_CHILD);job=m["jobs"][0]
    if job_id!=job["job_id"] or executable_role!="guard" or str(Path(executable_path).resolve())!=m["guard_script_path"]:raise ValueError("dispatch identity")
    guard=Path(m["guard_directory"]);cache=Path(m["cache_directory"])/job_id
    paths={"guard_directory":str(guard),"start_receipt":str(guard/(job_id+".start.json")),
      "guard_terminal":str(guard/(job_id+".terminal.json")),"stdout_log":str(guard/(job_id+".stdout.log")),
      "stderr_log":str(guard/(job_id+".stderr.log")),"output":job["output_namespace"],"cache_job":str(cache)}
    if phase==GUARD_ENTRY:
        import subprocess,importlib.util
        base=ROOT/"Robotwin2/production_micro_gate_v1/guarded_launcher.py"
        if sha(base)!="d666db0b9059c0abed5473024873919531dfff60d8f56346067909c357597210":raise ValueError("Guard primitives")
        s=importlib.util.spec_from_file_location("f3_source_check",base);b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
        project=ROOT/"Robotwin2/project/RoboTwin"
        if b.python_tree_sha(project/"controlled_multi_future")!=m["implementation_source_sha256"]:raise ValueError("active tree")
        def git(*args):return subprocess.check_output(["git","-C",str(project),*args],text=True,timeout=20).strip()
        if git("rev-parse","HEAD")!=m["robotwin_tracked_head"] or git("status","--porcelain","--untracked-files=no"):raise ValueError("official worktree")
        for relative,digest in m["asset_hashes_by_family"]["F2"].items():
            if sha(project/relative)!=digest:raise ValueError("asset source")
    elif phase==POST_CHILD:
        g=read(paths["guard_terminal"],"receipt_sha256")
        if g["manifest_sha256"]!=m["manifest_sha256"] or g["task_owned_cleanup_pass"] is not True or cache.exists():raise ValueError("Guard cleanup")
        t=read(Path(job["output_namespace"])/"job_terminal.json","receipt_sha256")
        if t["manifest_sha256"]!=m["manifest_sha256"]:raise ValueError("terminal manifest")
        success=validate_terminal(t)
        if (g["child_exit_code"]==0)!=success:raise ValueError("exit propagation")
        paths["phase_validation"]={"job_succeeded":success}
    else:raise ValueError("unknown phase")
    return {"manifest":m,"job":job,"paths":paths,"phase":phase}
