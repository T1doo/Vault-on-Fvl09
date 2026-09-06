import argparse,ast,unittest,sys
from pathlib import Path
from manifest_contract import load_manifest,canonical_hash
from realization_utf8_io_v1 import write_new
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True,type=Path);p.add_argument('--job-id');p.add_argument('--preflight-only',action='store_true');a=p.parse_args(argv);m=load_manifest(a.manifest,runner=not a.preflight_only)
    if a.preflight_only:
        ast.parse(Path(__file__).with_name('run.py').read_text(encoding='utf-8'))
        sys.path.insert(0,str(Path(__file__).parents[1]/'support_pair_collision_v1'));from test_policy import Tests
        return 0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful() else 1
    from run import run
    value=run(m);value['receipt_sha256']=canonical_hash(value);write_new(Path(m['jobs'][0]['output_namespace'])/'job_terminal.json',value);return 0 if value['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
