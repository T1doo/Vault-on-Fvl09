"""Shared Goal lifecycle dispatcher; no sub-agent can reserve or launch GPU."""
import argparse,importlib,json,sys,traceback,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from goal_pilot48_v1.runtime_v3.manifest_contract import load_manifest,canonical_hash
from goal_pilot48_v1.runtime_v3.meter import Meter
from realization_utf8_io_v1 import write_new
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True,type=Path);p.add_argument('--job-id');p.add_argument('--preflight-only',action='store_true');a=p.parse_args(argv);m=load_manifest(a.manifest,runner=not a.preflight_only);job=m['jobs'][0]
    if a.job_id and a.job_id!=job['job_id']:raise ValueError('wrong job')
    if a.preflight_only:
        tests=importlib.import_module(job['test_module']);suite=unittest.defaultTestLoader.loadTestsFromModule(tests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    # Initialize meter before importing any runtime that constructs models.
    if job.get('family')=='F1':raise ValueError('runtime_v2 rejects new F1 jobs until namespaced action coverage is audited')
    out=Path(job['output_namespace']);meter=Meter(out.parent/(out.name+'_meter'),job['resource_caps']);result=error=close_error=None
    try:
        meter.configure_collection_contract(m);meter.install();runtime=importlib.import_module(job['runtime_module'])
        result=runtime.run(m,meter=meter) if job.get('requires_live_meter') is True else runtime.run(m)
    except BaseException as exc:error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        try:meter.close()
        except BaseException as exc:close_error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    known=result is not None and result.get('accounting_complete') is True
    if result is not None:
        if result.get('scene_attempts',result.get('fresh_scene_attempts'))!=meter.counts['fresh_scenes']:known=False
        if job['kind']=='F3_MICRO' and result.get('trajectory_queries')!=meter.counts['solver_problems']:known=False
        if job.get('requires_live_meter') is True:
            if result.get('collection_attempts')!=meter.counts['collection_attempts']:known=False
            if job['resource_caps']['collection_attempts']>0 and not meter.collection_hooks:known=False
    if close_error is not None:known=False
    terminal={'schema_version':'cmf_goal_job_terminal_v1','manifest_sha256':m['manifest_sha256'],'job_id':job['job_id'],'issuance':'ISSUED_UNDER_USER_GOAL','runtime_result':result,'error':error,
        'resource_counts':dict(meter.counts),'setup_action_calls':meter.setup_action_calls,'model_constructions':meter.model_constructions,'dummy_warmups_skipped':meter.warmups_skipped,
        'collection_hook_count':len(meter.collection_hooks),'meter_close_error':close_error,
        'accounting_complete':known,'pass':error is None and close_error is None and known and result.get('pass') is True}
    terminal['receipt_sha256']=canonical_hash(terminal);out.mkdir(parents=True,exist_ok=True);write_new(out/'goal_terminal.json',terminal)
    return 0 if terminal['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
