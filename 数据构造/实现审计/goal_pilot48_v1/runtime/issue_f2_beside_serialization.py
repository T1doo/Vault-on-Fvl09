"""Only future untouched beside; no on recollection or qualification adoption."""
from pathlib import Path
from goal_pilot48_v1.runtime.issue_f2_single_relation import build_beside_manifest as old,ROOT,sha,digest,merge_checked,checked
def build_manifest(job_id,reservation):
    m=old(job_id,reservation);m.pop('manifest_sha256')
    root=ROOT/'f2_on_beside_runtime_v2'
    sources=[*root.glob('*.py'),Path(__file__).resolve(),ROOT/'f2_on_final_serialization_review_v1/recover.py',ROOT/'f2_on_final_serialization_review_v1/recover_v2.py']
    merge_checked(m['source_files'],{str(p):sha(p) for p in sources})
    proof=ROOT/'f2_on_final_serialization_review_v1/RECOVERY_REVIEW_002.json'
    merge_checked(m['input_files'],{str(proof):sha(proof)})
    merge_checked(m['input_files'],checked(proof)['files'])
    job=m['jobs'][0];job.update(runtime_module='goal_pilot48_v1.f2_on_beside_runtime_v2.runner_bridge',runtime_file=str(root/'runner_bridge.py'),test_module='goal_pilot48_v1.f2_on_beside_runtime_v2.test_all')
    m['serialization_only_implementation_revision']=2;m['on_original_failed_terminal_unchanged']=True
    m['manifest_sha256']=digest(m);return m
