"""One fresh-idle wave; never dispatch any Guard when all cards are busy."""
import argparse,importlib.util,json,subprocess,sys
from pathlib import Path
W=Path('/nfs_share/lijunhui');BASE=W/'Robotwin2/production_micro_gate_v1/guarded_launcher.py'
spec=importlib.util.spec_from_file_location('idle_wave_base',BASE);base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
def eligible(snapshot):
    return [g for g in snapshot['gpus'] if g['index'] in range(8) and base.idle(g)]
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--test-busy-fixture',type=Path);a=p.parse_args()
    if a.test_busy_fixture:
        snapshot=json.loads(a.test_busy_fixture.read_text(encoding='utf-8'))['pre_snapshot'];assert not eligible(snapshot);print('busy fixture: zero eligible, zero Guard dispatch');return 0
    snapshot=base.nvidia_snapshot();cards=eligible(snapshot)
    if not cards:print(json.dumps({'status':'WAITING_NO_FRESH_IDLE_GPU','snapshot':snapshot,'job_launched':False,'execution_budget_consumed':False}));return 75
    m=json.loads(a.manifest.read_text(encoding='utf-8'));g=cards[0]
    return subprocess.call([str(W/'Robotwin2/env/bin/python'),m['guard_script_path'],'--manifest',str(a.manifest),'--physical-index',str(g['index']),'--expected-uuid',g['uuid']])
if __name__=='__main__':raise SystemExit(main())
