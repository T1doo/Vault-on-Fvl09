"""One remaining scene plus the previous immutable geometry capture."""
import argparse
from pathlib import Path
from manifest_contract import load_manifest,canonical_hash
from realization_utf8_io_v1 import write_new
from f3_conformance import candidate_spec,candidates,run_remaining_scene

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True,type=Path);p.add_argument('--job-id');p.add_argument('--preflight-only',action='store_true');args=p.parse_args(argv)
    m=load_manifest(args.manifest,runner=not args.preflight_only);job=m['jobs'][0]
    if args.job_id and args.job_id!=job['job_id']:raise ValueError('job identity')
    if args.preflight_only:
        import unittest
        from test_cpu import BridgeTests
        candidate_spec(candidates()[1])
        return 0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BridgeTests)).wasSuccessful() else 1
    out=Path(job['output_namespace']);out.mkdir(parents=True,exist_ok=False);rows=[];error=None
    write_new(out/'remaining_scene.start.json',{'manifest_sha256':m['manifest_sha256'],'live_scene_recipe':m['live_scene_recipe_id'],'prior_scenes':1})
    try:rows.append(run_remaining_scene(out/'remaining_scene'))
    except BaseException as exc:error={'type':type(exc).__name__,'message':str(exc)}
    known=len(rows)==1 and rows[0]['accounting_complete'];good=known and error is None and not rows[0]['global_stop'] and len(rows[0]['model_results'])==2
    result={'schema_version':'cmf_f3_remaining_scene_terminal_v1_1','manifest_sha256':m['manifest_sha256'],'scene_attempts':1,'previous_scene_attempts':1,'cumulative_non_action_scenes':2,
        'scene_receipts':rows,'error':error,'accounting_complete':known,'trajectory_queries':rows[0]['trajectory_queries'] if known else None,'physical_attempts':0,'new_raw_trajectories':0,'new_roots':0,
        'pass':good,'status':'MODEL_AUDIT_COMPLETED_WITH_FINDINGS' if good else 'MODEL_AUDIT_INFRASTRUCTURE_STOP','reserved_physical_scenes_unconsumed':2,'reserved_trajectory_queries_unconsumed':6}
    result['receipt_sha256']=canonical_hash(result);write_new(out/'job_terminal.json',result);return 0 if good else 1

if __name__=='__main__':raise SystemExit(main())
