import argparse
from pathlib import Path
from manifest_contract import load_manifest

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True,type=Path);p.add_argument('--job-id');p.add_argument('--preflight-only',action='store_true');args=p.parse_args(argv)
    m=load_manifest(args.manifest,runner=not args.preflight_only)
    if args.job_id and args.job_id!=m['jobs'][0]['job_id']:raise ValueError('job id')
    if args.preflight_only:
        import unittest
        from test_cpu import Tests
        return 0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful() else 1
    from execute import run_job
    return 0 if run_job(m)['pass'] else 1

if __name__=='__main__':raise SystemExit(main())
