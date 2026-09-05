"""Read-only Run3 auditor: transport, evidence and scientific truth are distinct."""
import json
from pathlib import Path
from admission_contract import validate, module, read, canonical, sha, check, JOB, AUDIT

BASE_PATH = AUDIT / "f2_controlled_insertion_route_gate_postrun_auditor_v1/auditor.py"
BASE_SHA = "a76aee0674ff641da41f5951d221d28547dc92db87e7a5c0f41558ced047251d"


def audit(path):
    report={"schema_version":"cmf_f2_run3_auditor_v1_2",
            "evidence_integrity_pass":False,"scientific_gate_pass":False,
            "infrastructure_failure":False,"cleanup_pass":False,"errors":[]}
    try:
        m,_=validate(path,before_launch=False)
        b=module(BASE_PATH,"f2_run3_auditor_base",BASE_SHA)
        b.EXPECTED_MANIFEST_PATH=Path(path).resolve()
        b.EXPECTED_MANIFEST_FILE_SHA256=sha(path)
        b.EXPECTED_MANIFEST_SHA256=m["manifest_sha256"]
        b.EXPECTED_RUN_ID=m["run_id"]
        output=Path(m["jobs"][0]["output_namespace"]); gd=Path(m["guard_directory"])
        gt=read(gd/(JOB+".terminal.json"))
        report["manifest_sha256"]=m["manifest_sha256"]
        check(gt["manifest_sha256"]==m["manifest_sha256"] and gt["job_id"]==JOB and gt["run_id"]==m["run_id"],"Guard binding")
        idx=gt["physical_gpu_index"]; uuid=gt["gpu_uuid"]
        check(type(idx) is int and idx in range(8) and uuid==b.GPU_UUIDS[idx],"GPU identity")
        pre=b.selected_gpu(gt["pre_snapshot"],idx,uuid,"pre")
        post=b.selected_gpu(gt["post_snapshot"],idx,uuid,"post")
        report["cleanup_pass"]=bool(gt["cleanup_errors"]==[] and gt["cache_removed"] is True and
           gt["lease_released"] is True and gt["task_owned_cleanup_pass"] is True and
           gt["gpu_returned_to_idle_baseline"] is True and
           post["memory_used_mib"]<=max(64,pre["memory_used_mib"]+32) and
           post["utilization_gpu_percent"]==0 and post["pstate"] in ("P8","P12") and
           post["compute_processes"]==[] and not (Path(m["cache_directory"])/JOB).exists())
        jt=read(output/"job_terminal.json")
        check(jt["manifest_sha256"]==m["manifest_sha256"] and jt["job_id"]==JOB,"job binding")
        check(jt["schema_version"]=="cmf_f2_controlled_insertion_route_gate_terminal_v1","terminal schema")
        for k in ("physical_execution_count","accepted_root_count","formal_trajectory_count"):
            check(type(jt[k]) is int and jt[k]==0,"forbidden counts")
        check(jt["formal_data"] is False and jt["stage1_authorized"] is False and jt["automatic_continuation"] is False,"terminal scope")
        gs=read(gd/(JOB+".start.json"))
        check(gs["manifest_sha256"]==m["manifest_sha256"] and gs["gpu_uuid"]==uuid and
              gs["physical_gpu_index"]==idx and gs["run_id"]==m["run_id"] and gs["job_id"]==JOB,"start binding")
        report["infrastructure_failure"]=jt.get("error") is not None
        report["job_terminal_receipt_sha256"]=jt["receipt_sha256"]
        report["guard_terminal_receipt_sha256"]=gt["receipt_sha256"]
        try:
            strict=b.audit_from_disk(Path(path))
        except Exception as e:
            strict={"pass":False,"failure":str(e)}
        report["strict_scientific_audit"]=strict
        report["scientific_gate_pass"]=bool(strict["pass"] and report["cleanup_pass"])
        # Integrity of an infrastructure terminal can hold despite no scientific rows.
        if report["infrastructure_failure"]:
            check(jt["pass"] is False and isinstance(jt["error"],dict),"error/pass inconsistency")
            report["evidence_integrity_pass"]=True
        elif strict["pass"]:
            report["evidence_integrity_pass"]=True
        else:
            result=jt["result"]
            check(jt["pass"] is False and result["both_chains_pass"] is False,"negative result inconsistent")
            rows=result["planner_rows"]
            check(len(rows)==2 and [x["relation"] for x in rows]==["inside","beside"],"negative row order")
            total=0
            ids=[]
            for row,relation,segments in zip(rows,("inside","beside"),(b.INSIDE_SEGMENTS,b.BESIDE_SEGMENTS)):
                disk=read(output/(relation+"_planner_receipt.json"))
                check(disk==row,"negative receipt differs from terminal")
                receipts=row["segment_receipts"]
                n=row["planner_query_count"]
                check(type(n) is int and 1<=n<=len(segments) and n==len(receipts),"query counts")
                check([s["segment_id"] for s in receipts]==list(segments[:n]),"segment order")
                check(row["physical_execution_count"]==0,"physical count")
                check(all(s["executed"] is False for s in receipts),"unexpected physical execution")
                b.validate_scene_cleanup(row["cleanup"],relation)
                ids.append(row["cleanup"]["scene_instance_id"])
                total+=n
            check(len(set(ids))==2 and result["fresh_planner_scene_count"]==2,"scene identities")
            check(result["planner_query_count"]==total<=11,"negative total count")
            check(any(x["planner_pass"] is False for x in rows),"negative pass mismatch")
            for k in ("physical_execution_count","branch_execution_count","raw_trajectory_count","video_count","accepted_root_count","formal_trajectory_count"):
                check(type(result[k]) is int and result[k]==0,"forbidden result count")
            check(b.forbidden_output_paths(output)==([],[]),"forbidden disk artifacts")
            report["evidence_integrity_pass"]=True
        report["result_summary"]=jt.get("result")
    except Exception as e:
        report["errors"].append({"type":type(e).__name__,"message":str(e)})
    report["pass"]=report["evidence_integrity_pass"] and report["scientific_gate_pass"] and report["cleanup_pass"]
    report["receipt_sha256"]=canonical(report)
    return report
