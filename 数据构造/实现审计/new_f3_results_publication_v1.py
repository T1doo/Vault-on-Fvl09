"""Publish actual new qualification and pre-action micro failure, without retry."""
import json,hashlib,sys,unittest,io
from pathlib import Path
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';D=W/'Robotwin2/datasets'
sys.path.insert(0,str(A));from realization_utf8_io_v1 import write_new
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def checked(p):
    d=json.loads(Path(p).read_text(encoding='utf-8'));v=dict(d);h=v.pop('receipt_sha256');assert canonical(v)==h;return d
def main():
    q=checked(D/'f3_new_topdown_qualification_v1/job_terminal.json');m=checked(D/'f3_new_topdown_r3063_micro_v1/job_terminal.json');gq=checked(D/'f3_new_topdown_qualification_v1_guard_idle_wave1/qual2.terminal.json');gm=checked(D/'f3_new_topdown_r3063_micro_v1_guard/micro1.terminal.json')
    assert q['pass'] and q['IK_problems']==6 and q['scene_attempts']==2
    assert m['trajectory_queries']==1 and m['scene_attempts']==1 and m['physical_attempts']==1 and not m['pass']
    assert gq['task_owned_cleanup_pass'] and gm['task_owned_cleanup_pass']
    assert "has no attribute 'trace'" in m['error']['traceback'] and "has no attribute 'markers'" in m['error']['traceback']
    assert not (D/'f3_new_topdown_r3063_micro_v1/physical_trace.npz').exists()
    sys.path.insert(0,str(A/'f3_topdown_micro_runtime_v1_1'));import test_lifecycle
    stream=io.StringIO();tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(test_lifecycle.Tests));assert tests.wasSuccessful() and tests.testsRun==4
    files={}
    for name in ('f3_new_topdown_qualification_v1','f3_new_topdown_qualification_v1_guard_idle_wave1','f3_new_topdown_r3063_micro_v1','f3_new_topdown_r3063_micro_v1_guard'):
        for p in sorted((D/name).rglob('*')):
            if p.is_file():files[str(p)]=sha(p)
    value={'schema_version':'cmf_new_f3_qualification_micro_failure_publication_v1','qualification':q,'micro_original_terminal':m,'qualification_guard_sha256':gq['receipt_sha256'],'micro_guard_sha256':gm['receipt_sha256'],'file_sha256':files,
        'cumulative_new_scope':{'scenes':3,'IK_problems':6,'trajectory_queries':1,'physical_attempt_slots':1,'actual_arm_control_execution_reached':False,'raw':0,'roots':0},
        'no_arm_execution_evidence':'first line len(scene.trace) in locked _execute_planned_segment raised before _execute_control; source/plan/error preserved; scene initialization/settling is not arm-control execution',
        'bootstrap_fix_CPU_tests':{'tests_run':4,'success':True,'output':stream.getvalue(),'file_sha256':sha(A/'f3_topdown_micro_runtime_v1_1/test_lifecycle.py')},'original_failed_artifacts_preserved':True,'replacement_authorized':False,'task_GPU_cleanup_verified':True}
    value['receipt_sha256']=canonical(value);write_new(A/'NEW_F3_QUALIFICATION_MICRO_FAILURE_PUBLICATION_V1_20260906.json',value)
    prior=json.loads((A/'STAGE1_READINESS_NEW_SCOPES_CPU_READY_GPU_BUSY_20260906.json').read_text(encoding='utf-8'))
    r={'schema_version':'cmf_readiness_after_new_f3_qualification_micro_failure_v1','status':'F3_ONE_RECIPE_QUALIFIED_MICRO_BOOTSTRAP_FAILED_REPLACEMENT_DECISION_NEEDED','accepted_development':prior['accepted_development'],'stage1':prior['stage1'],'formal':prior['formal'],'current_task_GPU_jobs':0,
        'new_scope_consumption':value['cumulative_new_scope'],'F2':prior['F2'],'F3':{'Stage_A_consumed':True,'qualified_recipe':'f3-final-pose-v3-r3063-topdown-geometry-v1','r1401_pregrasp_qualified':False,'r3063_micro_consumed':True,'r3063_physical_grasp_success_proven':False,'bootstrap_CPU_fix_tests_pass':4,'automatic_retry_authorized':False,'replacement_requires_explicit_decision':True},'F4_B':prior['F4_B'],'publication_receipt_sha256':value['receipt_sha256'],'handoff':'GPT_HANDOFF_F3_NEW_IK_AND_MICRO_BOOTSTRAP_FAILURE_20260906.md'}
    r['receipt_sha256']=canonical(r);write_new(A/'STAGE1_READINESS_AFTER_NEW_F3_QUALIFICATION_MICRO_FAILURE_20260906.json',r);print(json.dumps({'files':len(files),'CPU_lifecycle_tests':tests.testsRun,'publication':value['receipt_sha256'],'readiness':r['receipt_sha256']}))
if __name__=='__main__':main()
