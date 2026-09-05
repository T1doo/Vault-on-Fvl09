"""Bounded F2 endpoint diagnosis and transit comparison. Controls never executed."""
import argparse,json
from pathlib import Path
import numpy as np
from manifest_contract import load_manifest,canonical,sha,INSIDE
from semantic_target import corrected_contract,derive_live_targets,old
from scene_attempt import record_attempt
from transit import build_transit_spec,plan_test,run_ordered

def write_new(p,d):
    from controlled_multi_future.canonical_artifact import canonical_jsonable
    d=canonical_jsonable(d);d.pop('receipt_sha256',None);d['receipt_sha256']=canonical(d)
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(d,f,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)
    return d

def run(m):
    from controlled_multi_future.f2_asset_bound_runtime_v3 import RoboTwinRealSapienF2AssetBoundAdapterV3
    from controlled_multi_future.family_runners_v3_1 import _plan_chain,_planner_reset
    job=m['jobs'][0];out=Path(job['output_namespace']);out.mkdir(parents=True,exist_ok=False)
    contract,artifact=corrected_contract();spec=build_transit_spec();before_inside=sha(INSIDE)
    write_new(out/'transit_spec.json',{'schema_version':'cmf_f2_transit_spec_copy_v1','frozen_spec':spec})
    scenes=[]
    def scene_attempt(phase,tests,diagnostic):
        directory=out/phase
        def opened():
            adapter=RoboTwinRealSapienF2AssetBoundAdapterV3(output_root=directory/'adapter',expected_implementation_source_sha256=m['implementation_source_sha256'],binding=contract['binding'],planner_only=True)
            return old.base.opened_scene(adapter,contract['planned'],phase='F2_BOUNDED_TRANSIT_'+phase,program=None,family='F2')
        def initialize(scene):
            if not hasattr(scene,'planner_query_count'):scene.planner_query_count=0
            return {'phase':phase,'spec_sha256':spec['spec_sha256']}
        def restore(scene):
            _,state=derive_live_targets(scene,contract);return state
        def reset(scene,test_id):return _planner_reset(scene,planner_seed=2026090402,variant_id='f2_bounded_transit:'+test_id,arm='left')
        def save_controls(test_id,controls):
            arrays={}
            for i,c in enumerate(controls):
                for k,v in c.items():
                    try:a=np.asarray(v)
                    except (TypeError,ValueError):continue
                    if a.dtype.kind in 'biufc' and a.size:arrays[str(i)+'__'+k]=a
            p=directory/(test_id+'.planner_controls.npz');p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as f:np.savez_compressed(f,**arrays)
            return {'path':str(p),'file_sha256':sha(p),'array_keys':sorted(arrays),'executed':False}
        def dispatch(scene,test):
            r=plan_test(scene,test,restore=restore,reset=reset,plan=_plan_chain,save_controls=save_controls)
            write_new(directory/(test['test_id']+'.json'),r);return r
        def plan(scene,unused):return {'phase':phase,'tests':run_ordered(scene,tests,diagnostic=diagnostic,dispatch=dispatch)}
        r=record_attempt(opened,initialize,plan,lambda r:write_new(directory/'scene_receipt.json',r));scenes.append(r)
        return r
    first=scene_attempt('diagnostics',spec['diagnostics'],True)
    tests=(first['result'] or {}).get('tests',[])
    positive=bool(tests) and tests[0]['pass'] is True
    safe=first['error'] is None and first['accounting_complete'] and (first['cleanup'] or {}).get('cleanup_safety_pass') is True and all(t['error'] is None and t['accounting_complete'] for t in tests)
    selected=None
    if positive and safe:
        route_scene=scene_attempt('routes',spec['routes'],False)
        route_tests=(route_scene['result'] or {}).get('tests',[])
        selected=next((r['test_id'] for r in route_tests if r['pass']),None)
    all_tests=[t for r in scenes for t in (r['result'] or {}).get('tests',[])]
    complete=all(r['accounting_complete'] for r in scenes) and all(t['accounting_complete'] for t in all_tests)
    total=sum(r['planner_delta'] for r in scenes) if complete else None
    safe=complete and all(r['error'] is None and (r['cleanup'] or {}).get('cleanup_safety_pass') is True for r in scenes) and all(t['error'] is None for t in all_tests)
    unchanged=sha(INSIDE)==before_inside==m['inside_file_sha256']
    passed=safe and unchanged and selected is not None and total<=19
    if passed:
        chosen=next(t for t in all_tests if t['test_id']==selected)
        write_new(out/'selected_route.json',{'schema_version':'cmf_f2_selected_transit_route_v1','transit_spec_sha256':spec['spec_sha256'],'first_complete_route':selected,'test_receipt':chosen,'root_execution_authorized':False})
    terminal={'schema_version':'cmf_f2_bounded_transit_terminal_v1','manifest_sha256':m['manifest_sha256'],'transit_spec_sha256':spec['spec_sha256'],'scene_receipts':scenes,
      'planner_queries':total,'fresh_scene_attempts':len(scenes),'accounting_complete':complete,'positive_control_pass':positive,'selected_route':selected,'inside_unchanged':unchanged,'inside_file_sha256':before_inside,
      'pass':passed,'physical_execution_count':0,'raw_trajectory_count':0,'accepted_root_count':0,'formal_trajectory_count':0,'automatic_continuation':False}
    return write_new(out/'job_terminal.json',terminal)

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--job-id');p.add_argument('--preflight-only',action='store_true');a=p.parse_args(argv)
    m=load_manifest(a.manifest,runner=not a.preflight_only)
    if a.job_id and a.job_id!=m['jobs'][0]['job_id']:raise ValueError('job identity')
    if a.preflight_only:
        s=build_transit_spec();print(json.dumps({'pass':True,'queries_cap':19,'scenes_cap':2,'physical':0,'GPU_used':False,'transit_spec_sha256':s['spec_sha256']}));return 0
    return 0 if run(m)['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
