"""CPU-reviewed candidate manifest contract; execution still needs a new exact decision."""
import hashlib,json
from pathlib import Path
AUDIT=Path(__file__).resolve().parent.parent
ROOT=Path("/nfs_share/lijunhui")
FREEZE=AUDIT/"F3_DETERMINISTIC_CANDIDATE_FREEZE_RESOLVED_V1.json"
EXPECTED=[
("f3-final-pose-v3-r3063","e612c0a829559966bae718bd3a995fe4d87b731de2680c38a56f325cedf2fb79"),
("f3-final-pose-v3-r0861","546859c30a0d068f1ca8103e5def09a450a84016980d766d479949d908ceadbd"),
("f3-final-pose-v3-r1401","599934ea0592589f4daa7b9daffc72c42a5a527ce2bd50911fd3b85a80ee883d"),
("f3-final-pose-v3-r2526","2b9c30ea466d6350b04add4102eda9aa004f22f9589224284ed5851dd681b5ae")]
CAPS={"candidate_cap":4,"qualification_query_cap":40,"physical_query_cap":12,"planner_query_cap":52,
      "planner_scene_cap":8,"physical_scene_cap":4,"scene_cap":12,"physical_attempt_cap":4,
      "shared_v":0,"no_suffix":0,"root":0,"raw":0,"formal":0}
def canonical(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p,key):
    p=Path(p).resolve()
    if not p.is_relative_to(ROOT):raise ValueError("outside workspace")
    d=json.loads(p.read_text());v=dict(d);h=v.pop(key,None)
    if h!=canonical(v):raise ValueError("self hash mismatch")
    return d
def candidates():
    d=read(FREEZE,"manifest_sha256")
    rows=d["ordered_candidates"]
    if [(r["recipe_id"],r["recipe_sha256"]) for r in rows]!=EXPECTED:raise ValueError("candidate identity/order")
    for r in rows:
        payload=dict(r);h=payload.pop("recipe_sha256")
        if canonical(payload)!=h:raise ValueError("recipe payload hash")
    return rows
def check_budget(queries,planner_scenes,physical_scenes,physical_attempts):
    values=[queries,planner_scenes,physical_scenes,physical_attempts]
    if any(type(v) is not int or v<0 for v in values):raise ValueError("invalid count")
    if queries>52 or planner_scenes>8 or physical_scenes>4 or planner_scenes+physical_scenes>12 or physical_attempts>4:
        raise ValueError("budget exceeded")
    return True
def load_manifest(p,*,execution=False,runner=False,post=False):
    m=read(p,"manifest_sha256"); candidates()
    from post_lift_audit import CONTRACT
    if m.get("post_lift_contract")!=CONTRACT:raise ValueError("post-lift contract changed")
    if m["caps"]!=CAPS:raise ValueError("caps changed")
    if m["candidate_freeze_sha256"]!=read(FREEZE,"manifest_sha256")["manifest_sha256"]:raise ValueError("freeze binding")
    if m.get("approved") is not execution or m.get("gpu_execution_authorized") is not execution:raise PermissionError("authority")
    for k in ("shared_v_authorized","no_suffix_authorized","root_execution_authorized","raw_collection_authorized","formal_360_authorized","stage1_authorized","training_authorized","h_reveal_authorized","compression_authorized","pi05_authorized"):
        if m.get(k) is not False:raise PermissionError(k)
    if m.get("allowed_physical_gpu_indices")!=list(range(8)):raise ValueError("GPU scope")
    expected_sources={str(Path(__file__).resolve().parent/n) for n in ("manifest_contract.py","guarded_launcher.py","job_runner.py","candidate_executor.py","post_lift_audit.py")}
    expected_sources.add(str(AUDIT/"f3_preclose_physical_consistency_gate_v1_1/gate.py"))
    if set(m["source_files"])!=expected_sources:raise ValueError("incomplete runtime source bindings")
    if m.get("implementation_source_sha256")!="3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7":raise ValueError("active source contract")
    if m.get("robotwin_tracked_head")!="c3ddfa8b97d5519efa828b075999bd0006778e5e":raise ValueError("official source contract")
    for path,digest in m["source_files"].items():
        if sha(path)!=digest:raise ValueError("source changed")
    for role in ("runner","guard"):
        expected=str(Path(__file__).resolve().parent/("job_runner.py" if role=="runner" else "guarded_launcher.py"))
        if m.get(role+"_script_path")!=expected or m.get(role+"_script_sha256")!=m["source_files"][expected]:raise ValueError("executable identity")
    if execution:
        d=read(m["execution_decision_path"],"receipt_sha256")
        if sha(m["execution_decision_path"])!=m["execution_decision_file_sha256"]:raise ValueError("decision file")
        if d.get("decision")!="F3_PRECLOSE_CANDIDATE_MICRO_EXECUTION_V1" or d.get("authorized") is not True:raise PermissionError("exact decision")
        if d.get("candidate_freeze_sha256")!=m["candidate_freeze_sha256"] or d.get("caps")!=CAPS:raise ValueError("decision scope")
        if d.get("source_files")!=m["source_files"]:raise ValueError("decision source binding")
    job=m["jobs"][0]
    if len(m["jobs"])!=1 or job["family"]!="F3":raise ValueError("job")
    if job.get("timeout_seconds")!=21600 or job.get("mode")!="F3_PRECLOSE_CANDIDATE_MICRO_V1":raise ValueError("job runtime contract")
    for p in (job["output_namespace"],m["guard_directory"],str(Path(m["cache_directory"])/job["job_id"])):
        if not Path(p).resolve().is_relative_to(ROOT):raise ValueError("path boundary")
    if not post and Path(job["output_namespace"]).exists():raise ValueError("output exists")
    if not runner and not post and (Path(m["guard_directory"]).exists() or (Path(m["cache_directory"])/job["job_id"]).exists()):raise ValueError("used run")
    if runner and (not Path(m["guard_directory"]).is_dir() or not (Path(m["cache_directory"])/job["job_id"]).is_dir()):raise ValueError("missing Guard paths")
    if len(str(Path(m["cache_directory"])/job["job_id"]/"tmp").encode())>100:raise ValueError("TMPDIR length")
    if m.get("physical_planner_seed")!=20260829:raise ValueError("physical seed changed")
    if runner:verify_runner_lease(m)
    return m

def verify_runner_lease(m):
    import os,fcntl
    job=m["jobs"][0]; path=Path(m["guard_directory"])/(job["job_id"]+".start.json")
    start=read(path,"receipt_sha256")
    index=start["physical_gpu_index"];uuid=start["gpu_uuid"]
    expected=ROOT/"Robotwin2/gpu_leases/production_micro_gate_v1"/f"physical_gpu_{index}.lock"
    if index not in range(8) or start.get("manifest_sha256")!=m["manifest_sha256"] or start.get("job_id")!=job["job_id"]:raise PermissionError("Guard start identity")
    if start.get("family")!="F3" or start.get("guard_pid")!=os.getppid():raise PermissionError("Guard parent identity")
    if os.environ.get("CUDA_VISIBLE_DEVICES")!=uuid or "LD_LIBRARY_PATH" in os.environ:raise PermissionError("Guard device environment")
    if os.environ.get("CMF_GPU_LEASE_PATH")!=str(expected) or start.get("lease_path")!=str(expected):raise PermissionError("Guard lease binding")
    if os.environ.get("CMF_F3_GUARD_START_RECEIPT")!=str(path):raise PermissionError("Guard receipt environment")
    with expected.open("r+") as f:
        try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return True
        fcntl.flock(f.fileno(),fcntl.LOCK_UN)
    raise PermissionError("lease not held by Guard")

GUARD_ENTRY="GUARD_ENTRY"
POST_CHILD="POST_CHILD"
canonical_hash=canonical
file_sha=sha

def validate_terminal(t):
    check_budget(t["planner_queries"],t["planner_scenes"],t["physical_scenes"],t["physical_attempts"])
    receipts=t["scene_receipts"]
    for r in receipts:
        if canonical({k:v for k,v in r.items() if k!="receipt_sha256"})!=r.get("receipt_sha256"):raise ValueError("scene hash")
    known=[r["planner_delta"] for r in receipts if r["planner_delta"] is not None]
    if sum(known)!=t["planner_queries"]:raise ValueError("query accounting")
    if len(receipts)!=t["planner_scenes"]+t["physical_scenes"]:raise ValueError("scene accounting")
    pq=t["phase_queries"]
    if pq["qualification"]>40 or pq["physical"]>12 or sum(pq.values())!=t["planner_queries"]:raise ValueError("phase accounting")
    for k in ("shared_v","no_suffix","root","raw","formal"):
        if type(t.get(k)) is not int or t[k]!=0:raise ValueError("forbidden output")
    scientific=(t["error"] is None and t["accounting_complete"] is True
       and all(r["error"] is None and (r["cleanup"] or {}).get("cleanup_safety_pass") is True for r in receipts)
       and sum(r["result"].get("pass") is True for r in t["physical_rows"])>=2)
    if t.get("pass") is not scientific:raise ValueError("terminal success inconsistent")
    return scientific

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
        for relative,digest in m["asset_hashes_by_family"]["F3"].items():
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
