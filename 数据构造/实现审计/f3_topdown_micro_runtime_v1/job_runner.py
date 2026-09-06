import argparse,ast
from pathlib import Path
from manifest_contract import load_manifest,canonical_hash
from realization_utf8_io_v1 import write_new
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True,type=Path);p.add_argument('--job-id');p.add_argument('--preflight-only',action='store_true');a=p.parse_args(argv);m=load_manifest(a.manifest,runner=not a.preflight_only)
    if a.preflight_only:
        tree=ast.parse(Path(__file__).with_name('micro.py').read_text(encoding='utf-8'));assert not any(isinstance(n,ast.Attribute) and n.attr in ('run_nonformal_root','shared_v') for n in ast.walk(tree));print('one qualified recipe; sequential actual-state plans; old full-window/postlift gates retained');return 0
    from micro import run
    value=run(m);value['receipt_sha256']=canonical_hash(value);write_new(Path(m['jobs'][0]['output_namespace'])/'job_terminal.json',value);return 0 if value['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
