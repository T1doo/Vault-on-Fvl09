"""Run3 admission entry point. Always audit after the unchanged Guard returns."""
import argparse
import json
import sys
from pathlib import Path
from admission_contract import validate, module, JOB, HERE, check
from auditor_v1_2 import audit


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--preflight-only",action="store_true")
    p.add_argument("--physical-index",type=int,choices=range(8))
    p.add_argument("--expected-uuid")
    a=p.parse_args(argv)
    m,lengths=validate(a.manifest)
    check(Path(__file__).resolve()==HERE/"authorized_launcher.py","launcher path")
    if a.preflight_only:
        original=module(m["runner_script_path"],"f2_run3_preflight_runner",m["runner_script_sha256"])
        print(json.dumps({"pass":True,"admission_pass":True,"cache_lengths":lengths,
              "original_preflight":original.preflight(a.manifest,JOB),"gpu_used":False,"authorization_consumed":False}))
        return 0
    check(a.physical_index is not None and a.expected_uuid,"GPU binding required")
    # The original wrapper imports sibling job_runner by name.
    runtime=str(Path(m["guard_script_path"]).parent)
    sys.path.insert(0,runtime)
    guard=module(m["guard_script_path"],"f2_run3_original_guard",m["guard_script_sha256"])
    guard_error=None
    try:
        guard.main(["--manifest",str(a.manifest),"--job-id",JOB,
                    "--physical-index",str(a.physical_index),"--expected-uuid",a.expected_uuid])
    except BaseException as e:
        guard_error={"type":type(e).__name__,"message":str(e)}
    result=audit(a.manifest)
    print(json.dumps({"guard_error":guard_error,"audit":result},ensure_ascii=False))
    return 0 if guard_error is None and result["pass"] else 1


if __name__ == "__main__": raise SystemExit(main())
