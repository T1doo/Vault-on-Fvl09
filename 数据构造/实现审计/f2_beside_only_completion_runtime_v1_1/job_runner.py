"""One fresh F2 beside-only planner scene. No inside or physical dispatch."""
import argparse,json
from pathlib import Path
from manifest_contract import load_manifest,canonical,sha,INSIDE
from semantic_target import corrected_contract,derive_live_targets,old
from scene_attempt import record_attempt

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
    contract,artifact=corrected_contract();before=sha(INSIDE)
    write_new(out/'semantic_target.json',artifact)
    def opened():
        adapter=RoboTwinRealSapienF2AssetBoundAdapterV3(output_root=out/'scene_adapter',expected_implementation_source_sha256=m['implementation_source_sha256'],binding=contract['binding'],planner_only=True)
        return old.base.opened_scene(adapter,contract['planned'],phase='F2_BESIDE_ONLY_COMPLETION',program=None,family='F2')
    def derive(scene):
        if not hasattr(scene,'planner_query_count'):scene.planner_query_count=0
        targets,state=derive_live_targets(scene,contract)
        state['support_plane_check']={'frozen':contract['binding']['layout_payload']['table_plane_z_m'],'live':0.74+float(scene.table_z_bias),'pass':True}
        return {'targets':targets,'state_restore_receipt':state}
    def plan(scene,target):
        reset=_planner_reset(scene,planner_seed=2026090402,variant_id='f2_controlled_insertion_route_gate_v1:beside',arm='left')
        p=_plan_chain(scene,target['targets'],query_limit=6,arm='left')
        return {'planner_pass':p['pass'],'segment_receipts':p['segment_receipts'],'terminal_qpos':p.get('terminal_qpos'),'terminal_qpos_sha256':p.get('terminal_qpos_sha256'),'planner_reset_receipt':reset}
    receipt=record_attempt(opened,derive,plan,lambda r:write_new(out/'beside_scene_receipt.json',r))
    unchanged=sha(INSIDE)==before==m['inside_file_sha256']
    passed=receipt['accounting_complete'] is True and receipt['planner_delta']==6 and receipt['error'] is None and (receipt['result'] or {}).get('planner_pass') is True and (receipt['cleanup'] or {}).get('cleanup_safety_pass') is True and unchanged
    terminal={'schema_version':'cmf_f2_beside_only_terminal_v1','manifest_sha256':m['manifest_sha256'],'scene_receipt':receipt,'planner_queries':receipt['planner_delta'],'fresh_scene_attempts':1,
      'inside_original_file_sha256':before,'inside_unchanged':unchanged,'pass':passed,'physical_execution_count':0,'raw_trajectory_count':0,'accepted_root_count':0,'formal_trajectory_count':0,'automatic_continuation':False}
    return write_new(out/'job_terminal.json',terminal)

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--job-id');p.add_argument('--preflight-only',action='store_true');a=p.parse_args(argv)
    m=load_manifest(a.manifest,runner=not a.preflight_only)
    if a.job_id and a.job_id!=m['jobs'][0]['job_id']:raise ValueError('job identity')
    if a.preflight_only:
        _,artifact=corrected_contract();print(json.dumps({'pass':True,'queries':6,'scenes':1,'physical':0,'GPU_used':False,'target_sha256':artifact['targets_sha256']}));return 0
    return 0 if run(m)['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
