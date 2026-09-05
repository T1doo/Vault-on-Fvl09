"""Run3 admission: exact immutable review and parent scientific contract."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path("/nfs_share/lijunhui")
AUDIT = ROOT / "Vault-on-Fvl09/数据构造/实现审计"
HERE = Path(__file__).resolve().parent
DECISION = AUDIT / "EXTERNAL_EXECUTION_DECISION_20260905_V1.json"
DECISION_SHA = "42543182b246c472ce9daa52281e7fd64b1086e767f91f4930e2de9ef6575058"
PROPOSAL = AUDIT / "PROPOSED_F2_SHORT_TMPDIR_INFRASTRUCTURE_RECOVERY_RUN3_MANIFEST_V1.json"
PROPOSAL_SHA = "82e0527ccf5cd945694b726034c6d0028ff0300ae480e62d002046675346c2fc"
PARENT = AUDIT / "F2_CONTROLLED_INSERTION_ROUTE_GATE_ADMISSION_REISSUE_RUN2_MANIFEST_V1.json"
PARENT_SHA = "210dd17071c1f5b89aee6fb8f7451cb14949a2948c663cbc2e86c2824725ccd0"
TERMINAL = AUDIT / "F2_CONTROLLED_INSERTION_ROUTE_GATE_ADMISSION_REISSUE_RUN2_TERMINAL_PUBLICATION_V1.json"
TERMINAL_SHA = "c486c0489c0830e8280a0d6919be4a35855d72adb523ce4a3cae6d7d1b2a08d9"
TOKEN = "APPROVE_ONE_F2_SHORT_TMPDIR_INFRASTRUCTURE_RECOVERY_RUN3"
JOB = "f2-controlled-insertion-route-gate-run1"
CACHE_DIRS = {"CONDA_PKGS_DIRS":"conda_pkgs", "CUDA_CACHE_PATH":"cuda", "HOME":"home",
 "MPLCONFIGDIR":"matplotlib", "NUMBA_CACHE_DIR":"numba", "TMPDIR":"tmp",
 "TORCH_EXTENSIONS_DIR":"torch_extensions", "TORCH_HOME":"torch", "XDG_CACHE_HOME":"xdg"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(d):
    return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def read(path, key="receipt_sha256", expected=None):
    p=Path(path)
    check(p.resolve().is_relative_to(ROOT), "outside workspace")
    if expected is not None: check(sha(p)==expected, "file hash mismatch: "+p.name)
    d=json.loads(p.read_text())
    check(isinstance(d,dict), "expected object")
    check(d.get(key)==canonical({k:v for k,v in d.items() if k!=key}), "self hash mismatch")
    return d


def module(path, name, digest):
    check(sha(path)==digest, "module hash changed")
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def validate_values(m, parent, proposal, decision):
    check(decision["f2"]["decision"] == TOKEN and decision["f2"]["authorized"] is True, "not exact F2 approval")
    check(decision["f2"]["maximum_dispatches"] == 1, "decision budget")
    check(m.get("dispatch_ordinal")==3 and type(m["dispatch_ordinal"]) is int, "dispatch ordinal")
    check(m.get("scientific_attempt_ordinal")==1 and type(m["scientific_attempt_ordinal"]) is int, "scientific ordinal")
    for k in ("approved","third_dispatch_authorized","gpu_execution_authorized","planner_execution_authorized","scene_execution_authorized"):
        check(m.get(k) is True, "required authority "+k)
    for k in ("physical_execution_authorized","root_execution_authorized","formal_data","stage0_reopened",
              "stage1_authorized","formal_360_authorized","training_authorized","h_reveal_authorized","compression_authorized","pi05_authorized",
              "automatic_retry","fourth_dispatch_authorized"):
        check(m.get(k) is False, "forbidden authority "+k)
    check(m["allowed_physical_gpu_indices"]==list(range(8)), "GPU scope")
    check(len(m["jobs"])==1 and m["jobs"][0]["job_id"]==JOB,"job")
    before=dict(parent["jobs"][0]); after=dict(m["jobs"][0])
    before.pop("output_namespace"); after.pop("output_namespace")
    check(before==after,"scientific job changed")
    for k in ("runner_script_path","runner_script_sha256","guard_script_path","guard_script_sha256",
              "implementation_source_sha256","asset_hashes_by_family","robotwin_tracked_head",
              "external_review_decision_path","external_review_decision_file_sha256","one_job_per_gpu","root_sharding"):
        check(m[k]==parent[k], "parent contract changed "+k)
    for k,v in parent.items():
        if k.startswith("sealed_"): check(m.get(k)==v,"sealed evidence changed")
    delta=proposal["future_approved_manifest_delta"]
    for k in ("run_id","guard_directory","cache_directory"): check(m[k]==delta[k], "path changed "+k)
    check(m["jobs"][0]["output_namespace"]==delta["jobs[0].output_namespace"], "output path")
    lengths={k:len(str(Path(m["cache_directory"])/JOB/v).encode("utf-8")) for k,v in CACHE_DIRS.items()}
    check(max(lengths.values())<=100, "cache path exceeds 100 UTF-8 bytes")
    return lengths


def validate(path, *, before_launch=True):
    m=read(path,"manifest_sha256")
    decision=read(DECISION,expected=DECISION_SHA)
    proposal=read(PROPOSAL,"manifest_sha256",PROPOSAL_SHA)
    parent=read(PARENT,"manifest_sha256",PARENT_SHA)
    terminal=read(TERMINAL,expected=TERMINAL_SHA)
    for key,p,digest,selfkey in (
        ("decision",DECISION,DECISION_SHA,"receipt_sha256"),
        ("proposal",PROPOSAL,PROPOSAL_SHA,"manifest_sha256"),
        ("parent_terminal",TERMINAL,TERMINAL_SHA,"receipt_sha256")):
        bound=m["admission_bindings"][key]
        check(bound["path"]==str(p) and bound["file_sha256"]==digest,"admission binding")
        value={"decision":decision,"proposal":proposal,"parent_terminal":terminal}[key]
        check(bound["content_sha256"]==value[selfkey],"content binding")
    msg=decision["authoritative_message"]
    check(sha(msg["path"])==msg["file_sha256"], "review Markdown changed")
    for name in ("admission_contract.py","authorized_launcher.py","auditor_v1_2.py"):
        bound=m["admission_sources"][name]
        check(Path(bound["path"]).resolve()==HERE/name and sha(HERE/name)==bound["sha256"],"admission source identity")
    lengths=validate_values(m,parent,proposal,decision)
    runner=module(m["runner_script_path"],"f2_run3_original_runner",m["runner_script_sha256"])
    if before_launch:
        # Original loader rechecks source, assets, evidence, all budgets and new paths.
        runner.load_manifest(Path(path),JOB,phase="guard")
    return m,lengths
