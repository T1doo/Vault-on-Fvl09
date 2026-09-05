"""Frozen C/U/D/N/H route construction and cumulative-count planner ledger."""
import copy
from semantic_target import corrected_contract,canonical

DIAGNOSTICS=[('D0_current_pose_positive_control',['C']),('D1_direct_preplace',['U']),('D2_direct_release',['D'])]
ROUTES=[('R0',['U','D','U','N']),('R1',['H_low','U','D','U','H_low','N']),('R2',['H_current_orientation','U','D','U','H_current_orientation','N'])]

def build_transit_spec():
    c,a=corrected_contract();t=a['six_targets']
    poses={'C':c['sealed_prefix_end_eef_pose'].tolist(),'U':t[1]['pose'],'D':t[2]['pose'],'N':c['neutral_eef_pose'].tolist(),'H':t[0]['pose']}
    poses=copy.deepcopy(poses);poses['H_low']=poses['H'].copy();poses['H_low'][2]=poses['U'][2]
    poses['H_current_orientation']=poses['H'][:3]+poses['C'][3:]
    def rows(items):return [{'test_id':name,'symbols':symbols,'query_cap':len(symbols),
        'targets':[{'segment_id':name+'_'+str(i)+'_'+symbol,'pose':poses[symbol]} for i,symbol in enumerate(symbols)]} for name,symbols in items]
    s={'schema_version':'cmf_f2_bounded_transit_spec_v1','pose_source_artifact_receipt_sha256':a['receipt_sha256'],
       'final_actor_pose':a['corrected_actor_pose'],'poses':poses,'pose_hashes':{k:canonical(v) for k,v in poses.items()},
       'diagnostics':rows(DIAGNOSTICS),'routes':rows(ROUTES),'planner_seed':2026090402,
       'reset_rule':'same original MotionGen.reset(reset_seed=True) before each independent test; no numeric seed search',
       'caps':{'planner_queries':19,'fresh_planner_scenes':2,'physical_executions':0,'branch_executions':0,'accepted_raw_trajectories':0,'accepted_roots':0,'formal_trajectories':0}}
    for row in s['diagnostics']+s['routes']:row['targets_sha256']=canonical(row['targets'])
    s['spec_sha256']=canonical(s);return s

def plan_test(scene,test,*,restore,reset,plan,save_controls):
    before=scene.planner_query_count
    if type(before) is not int or before<0:raise ValueError('invalid live before counter')
    if test['targets_sha256']!=canonical(test['targets']) or len(test['targets'])!=test['query_cap']:raise ValueError('test targets')
    error=None;planned=None;after=None;controls=None;state=None;reset_receipt=None
    try:
        state=restore(scene)
        if scene.planner_query_count!=before:raise ValueError('restore reset query counter')
        reset_receipt=reset(scene,test['test_id'])
        if scene.planner_query_count!=before:raise ValueError('planner reset changed counter')
        planned=plan(scene,test['targets'],query_limit=before+len(test['targets']),arm='left')
        controls=save_controls(test['test_id'],planned.get('controls',[]))
    except Exception as exc:error={'type':type(exc).__name__,'message':str(exc)}
    finally:
        value=getattr(scene,'planner_query_count',None)
        after=value if type(value) is int and value>=before else None
    delta=None if after is None else after-before
    complete=delta is not None and delta<=test['query_cap']
    result={'test_id':test['test_id'],'symbols':test['symbols'],'targets_sha256':test['targets_sha256'],'targets':test['targets'],
      'before':before,'after':after,'absolute_limit':before+len(test['targets']),'delta':delta,'accounting_complete':complete,
      'restore_receipt':state,'reset_receipt':reset_receipt,'controls_artifact':controls,'error':error,
      'segment_receipts':[] if planned is None else planned['segment_receipts'],
      'pass':error is None and complete and planned is not None and planned['pass'] is True and delta==len(test['targets'])}
    if planned is not None and planned.get('planner_query_count')!=after:result['accounting_complete']=False;result['pass']=False
    result['receipt_sha256']=canonical(result);return result

def run_ordered(scene,tests,*,diagnostic,dispatch):
    rows=[]
    for t in tests:
        r=dispatch(scene,t);rows.append(r)
        if r['error'] is not None or not r['accounting_complete']:break
        if diagnostic and t['test_id'].startswith('D0') and not r['pass']:break
        if not diagnostic and r['pass']:break
    return rows
