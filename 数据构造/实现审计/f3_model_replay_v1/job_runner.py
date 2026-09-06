"""Guarded solver replay only: zero fresh simulator scenes and zero actions."""
import argparse
from pathlib import Path
from manifest_contract import load_manifest,canonical_hash
from realization_utf8_io_v1 import write_new
from replay import run

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True,type=Path);p.add_argument('--job-id');p.add_argument('--preflight-only',action='store_true');args=p.parse_args(argv)
    m=load_manifest(args.manifest,runner=not args.preflight_only);job=m['jobs'][0]
    if args.job_id and args.job_id!=job['job_id']:raise ValueError('job identity')
    if args.preflight_only:
        import unittest
        from test_cpu import ReplayTests
        return 0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReplayTests)).wasSuccessful() else 1
    out=Path(job['output_namespace']);result=None;error=None
    try:result=run(out)
    except BaseException as exc:error={'type':type(exc).__name__,'message':str(exc)}
    starts=list((out/'check_ledger').glob('*.start.json'));done=list((out/'check_ledger').glob('*.done.json'))
    terminal={'schema_version':'cmf_f3_zero_scene_model_replay_terminal_v1','manifest_sha256':m['manifest_sha256'],'scene_attempts':0,'previous_scene_attempts':2,
        'cumulative_non_action_scenes':2,'trajectory_queries':0,'physical_attempts':0,'new_raw_trajectories':0,'new_roots':0,
        'model_check_attempts':len(starts),'model_check_completions':len(done),'accounting_complete':len(starts)==len(done),'error':error,'result':result,
        'pass':error is None and result is not None and result['pass'] and len(starts)==len(done)==40,
        'reserved_physical_scenes_unconsumed':2,'reserved_trajectory_queries_unconsumed':6}
    terminal['receipt_sha256']=canonical_hash(terminal);write_new(out/'job_terminal.json',terminal);return 0 if terminal['pass'] else 1

if __name__=='__main__':raise SystemExit(main())
