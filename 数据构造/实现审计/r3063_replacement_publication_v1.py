"""Seal actual supported-hold result and unverified model-repair proposal."""
import json,hashlib,sys,io,unittest
from pathlib import Path
import numpy as np
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';D=W/'Robotwin2/datasets/f3_r3063_bootstrap_replacement_v1';G=D.parent/'f3_r3063_bootstrap_replacement_v1_guard'
sys.path.insert(0,str(A));from realization_utf8_io_v1 import write_new
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def checked(p):
    v=json.loads(Path(p).read_text(encoding='utf-8'));d=dict(v);h=d.pop('receipt_sha256');assert digest(d)==h;return v
def main():
    t=checked(D/'job_terminal.json');g=checked(G/'replace1.terminal.json');assert t['pass'] and not t['micro_pass'] and t['error'] is None and t['trace_save_error'] is None
    assert t['result']['events']==['pregrasp','grasp','close_0.50','hold250'];assert t['trajectory_queries']==3 and t['scene_attempts']==1 and t['physical_attempts']==1
    assert g['task_owned_cleanup_pass'] and g['child_exit_code']==0
    for name in ('pregrasp','grasp'):assert json.loads((D/(name+'.full_window.json')).read_text())['pass']
    assert sha(D/'physical_trace.npz')==t['trace']['sha256']
    with np.load(D/'physical_trace.npz',allow_pickle=False) as z:
        rows=len(z['timestamp']);assert rows==1404 and np.array_equal(z['step_index'],np.arange(rows)) and np.allclose(np.diff(z['timestamp']),.004,atol=1e-9,rtol=0)
    model=json.loads((A/'F3_POSTCLOSE_SUPPORT_MODEL_CPU_AUDIT_V1_20260906.json').read_text(encoding='utf-8'));assert model['trace_sha256']==sha(D/'physical_trace.npz') and model['only_attached_bottle_support_pairs_overlap']
    sys.path.insert(0,str(A/'support_pair_collision_v1'));import test_policy
    text=io.StringIO();tests=unittest.TextTestRunner(stream=text,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(test_policy.Tests));assert tests.wasSuccessful() and tests.testsRun==8
    files={str(p):sha(p) for folder in (D,G) for p in sorted(folder.rglob('*')) if p.is_file()}
    publication={'schema_version':'cmf_r3063_bootstrap_replacement_supported_hold_publication_v1','original_replacement_terminal':t,'guard_receipt_sha256':g['receipt_sha256'],'file_sha256':files,'trace_rows':rows,'trace_integrity_and_time_step_pass':True,
        'pregrasp_and_grasp_original_gates_pass':True,'supported_hold_observations':model['hold'],'unsupported_lift_executed':False,'micro_pass':False,'model_world_overlap_evidence':model['literal_config_sphere_world_overlap_pairs'],
        'support_pair_repair':{'implemented':True,'CPU_tests':8,'CPU_tests_success':True,'test_output':text.getvalue(),'GPU_factory_executed':False,'real_GPU_kernel_conformance_pass':False,'new_physical_execution_authorized':False},
        'cumulative_new_scope':{'scenes':4,'IK_problems':6,'trajectory_queries':4,'physical_attempt_slots':2,'actual_arm_execution_scenes':1,'new_raw':0,'new_roots':0},'task_GPU_cleanup_verified':True,'automatic_retry_authorized':False}
    publication['receipt_sha256']=digest(publication);write_new(A/'R3063_REPLACEMENT_SUPPORTED_GRASP_PUBLICATION_V1_20260906.json',publication)
    prior=json.loads((A/'STAGE1_READINESS_AFTER_NEW_F3_QUALIFICATION_MICRO_FAILURE_20260906.json').read_text(encoding='utf-8'))
    readiness={'schema_version':'cmf_readiness_r3063_supported_grasp_lift_model_blocked_v1','status':'F3_SUPPORTED_HOLD_OBSERVED_LIFT_SUPPORT_MODEL_BLOCKED','accepted_development':prior['accepted_development'],'stage1':prior['stage1'],'formal':prior['formal'],'current_task_GPU_jobs':0,'F2':prior['F2'],'F4_B':prior['F4_B'],
        'F3':{'qualified_recipes':['f3-final-pose-v3-r3063-topdown-geometry-v1'],'pregrasp_and_grasp_physical_gates_pass':True,'supported_hold250_observed':True,'unsupported_grasp_stability_proven':False,'lift_executed':False,'micro_pass':False,'replacement_budget_consumed':True,'support_pair_CPU_tests_pass':8,'support_pair_GPU_validated':False,'next':'review zero-new-scene constraint-only model conformance; no additional GPU approval created'},
        'cumulative_new_scope':publication['cumulative_new_scope'],'publication_receipt_sha256':publication['receipt_sha256'],'handoff':'GPT_HANDOFF_R3063_REPLACEMENT_SUPPORTED_GRASP_20260906.md'}
    readiness['receipt_sha256']=digest(readiness);write_new(A/'STAGE1_READINESS_R3063_SUPPORTED_GRASP_LIFT_MODEL_BLOCKED_20260906.json',readiness);print(json.dumps({'files':len(files),'trace_rows':rows,'CPU_tests':tests.testsRun,'publication_receipt':publication['receipt_sha256']}))
if __name__=='__main__':main()
