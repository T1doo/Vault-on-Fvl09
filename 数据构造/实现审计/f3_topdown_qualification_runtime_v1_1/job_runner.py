import argparse,json
from pathlib import Path
from manifest_contract import load_manifest,canonical_hash
from realization_utf8_io_v1 import write_new
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True,type=Path);p.add_argument('--job-id');p.add_argument('--preflight-only',action='store_true');args=p.parse_args(argv)
    m=load_manifest(args.manifest,runner=not args.preflight_only)
    if args.preflight_only:
        import ast
        ast.parse(Path(__file__).with_name('qualification.py').read_text(encoding='utf-8'))
        d=json.loads((Path(__file__).parents[1]/'F3_TOPDOWN_CLOSURE_AND_GOAL_MAPPING_V1_20260906.json').read_text(encoding='utf-8'));assert all(r['CPU_necessary_gate_pass'] for r in d['results']);print('CPU closure and original-entry roundtrip prerequisites passed');return 0
    from qualification import run
    value=run(m);value['receipt_sha256']=canonical_hash(value);write_new(Path(m['jobs'][0]['output_namespace'])/'job_terminal.json',value);return 0 if value['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
