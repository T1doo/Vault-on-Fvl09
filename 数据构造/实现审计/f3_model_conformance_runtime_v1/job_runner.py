"""Run only two reserved non-action model scenes, not a micro/root retry."""
import argparse,sys
from pathlib import Path
from manifest_contract import load_manifest,canonical_hash,BRIDGE,A
from realization_utf8_io_v1 import write_new
from f3_conformance import candidates,candidate_spec,run_scene

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True,type=Path);p.add_argument('--job-id');p.add_argument('--preflight-only',action='store_true');args=p.parse_args(argv)
    m=load_manifest(args.manifest,runner=not args.preflight_only);job=m['jobs'][0]
    if args.job_id and args.job_id!=job['job_id']:raise ValueError('job identity')
    recipes=candidates()
    if [r['recipe_id'] for r in recipes]!=m['candidate_ids']:raise ValueError('candidate freeze')
    if args.preflight_only:
        import unittest
        from test_cpu import BridgeTests
        for r in recipes:candidate_spec(r)
        return 0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BridgeTests)).wasSuccessful() else 1
    output=Path(job['output_namespace']);output.mkdir(parents=True,exist_ok=False);rows=[];error=None;attempts=0
    try:
        for recipe in recipes:
            attempts+=1
            write_new(output/(recipe['recipe_id']+'.start.json'),{'recipe':recipe,'manifest_sha256':m['manifest_sha256'],'scene_ordinal':attempts})
            r=run_scene(recipe,output/recipe['recipe_id']);rows.append(r)
            if r['global_stop']:break
    except BaseException as exc:error={'type':type(exc).__name__,'message':str(exc)}
    complete=len(rows)==attempts and all(r['accounting_complete'] for r in rows)
    good=complete and error is None and len(rows)==2 and all(not r['global_stop'] for r in rows)
    result={'schema_version':'cmf_f3_model_conformance_terminal_v1','manifest_sha256':m['manifest_sha256'],'scene_attempts':attempts,'scene_receipts':rows,
        'error':error,'accounting_complete':complete,'trajectory_queries':sum(r['trajectory_queries'] for r in rows) if complete else None,
        'physical_attempts':0,'new_raw_trajectories':0,'new_roots':0,'pass':good,
        'status':'MODEL_AUDIT_COMPLETED_WITH_FINDINGS' if good else 'MODEL_AUDIT_INFRASTRUCTURE_STOP',
        'reserved_physical_scenes_unconsumed':2,'reserved_trajectory_queries_unconsumed':6}
    result['receipt_sha256']=canonical_hash(result);write_new(output/'job_terminal.json',result)
    return 0 if good else 1

if __name__=='__main__':raise SystemExit(main())
