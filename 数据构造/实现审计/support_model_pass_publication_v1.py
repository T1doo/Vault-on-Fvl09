"""Publish real saved-state GPU conformance and planned native escape only."""
import json,hashlib,sys
from pathlib import Path
import numpy as np
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';D=W/'Robotwin2/datasets/f3_support_model_replay_v1';G=D.parent/'f3_support_model_replay_v1_guard'
sys.path.insert(0,str(A));from realization_utf8_io_v1 import write_new
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def checked(p):
    d=json.loads(Path(p).read_text(encoding='utf-8'));v=dict(d);h=v.pop('receipt_sha256');assert digest(v)==h;return d
def main():
    t=checked(D/'job_terminal.json');g=checked(G/'model1.terminal.json');assert t['pass'] and t['constraint_checks']==4 and t['trajectory_queries']==1 and t['scene_attempts']==0 and t['physical_attempts']==0
    assert t['result']['scientific_status']=='PLAN_AND_NATIVE_ESCAPE_PASS' and g['task_owned_cleanup_pass'] and g['child_exit_code']==0
    with np.load(D/'lift.controls.npz',allow_pickle=False) as z:shape=z['position'].shape;assert shape==(109,6) and np.isfinite(z['position']).all() and np.isfinite(z['velocity']).all()
    with np.load(D/'lift.native_geometry.npz',allow_pickle=False) as z:
        poses=z['actor_world_poses'];v=z['native_world_vertices'];low=v[:,:,2].min(1);metrics={'planned_actor_rise_m':float(poses[-1,2]-poses[0,2]),'native_min_z_start_m':float(low[0]),'native_min_z_end_m':float(low[-1]),'minimum_native_height_step_m':float(np.diff(low).min())}
    files={str(p):sha(p) for folder in (D,G) for p in sorted(folder.rglob('*')) if p.is_file()}
    evidence={'schema_version':'cmf_support_model_gpu_and_single_lift_plan_pass_publication_v1','terminal':t,'guard_receipt_sha256':g['receipt_sha256'],'file_sha256':files,'planned_control_shape':list(shape),'planned_geometry_metrics':metrics,
        'GPU_factory_and_cached_callbacks_verified_on_frozen_state':True,'actual_physical_lift_executed':False,'cuda_kernel_launch_count':None,'kernel_launch_count_note':'not profiled; reported checker counters are method invocations, not kernel launches',
        'scope_delta':{'scenes':0,'physical_attempts':0,'IK_problems':0,'start_state_checks':4,'trajectory_queries':1,'raw':0,'roots':0},'task_GPU_release_verified':True,
        'projection_metadata_overlay_path':str(A/'SUPPORT_MODEL_PROJECTION_METADATA_OVERLAY_V1_20260906.json'),'projection_metadata_overlay_sha256':sha(A/'SUPPORT_MODEL_PROJECTION_METADATA_OVERLAY_V1_20260906.json')}
    evidence['receipt_sha256']=digest(evidence);write_new(A/'SUPPORT_MODEL_GPU_LIFT_PLAN_PASS_PUBLICATION_V1_20260906.json',evidence)
    prior=json.loads((A/'STAGE1_READINESS_R3063_SUPPORTED_GRASP_LIFT_MODEL_BLOCKED_20260906.json').read_text(encoding='utf-8'))
    r={'schema_version':'cmf_readiness_support_model_lift_plan_pass_v1','status':'F3_SAVED_STATE_MODEL_AND_LIFT_PLAN_PASS_PHYSICAL_LIFT_PENDING','accepted_development':prior['accepted_development'],'stage1':prior['stage1'],'formal':prior['formal'],'current_task_GPU_jobs':0,'F2':prior['F2'],'F4_B':prior['F4_B'],
        'F3':{'pregrasp_grasp_and_supported_hold_observed':True,'support_pair_GPU_verified_for_saved_state':True,'single_lift_plan_pass':True,'native_109_point_escape_pass':True,'actual_lift_executed':False,'micro_pass':False,'r1401_pregrasp_qualified':False,'physical_validation_proposal':'F3_SUPPORT_AWARE_PHYSICAL_VALIDATION_PROPOSAL_V1_20260906.json','new_physical_execution_authorized':False},
        'cumulative_since_new_topdown_review':{'scenes':4,'IK_problems':6,'trajectory_queries':5,'physical_attempt_slots':2,'actual_arm_execution_scenes':1,'new_training_raw':0,'new_roots':0},
        'latest_scope_delta':evidence['scope_delta'],'publication_receipt_sha256':evidence['receipt_sha256'],'handoff':'GPT_HANDOFF_SUPPORT_MODEL_AND_LIFT_PLAN_PASS_20260906.md'}
    r['receipt_sha256']=digest(r);write_new(A/'STAGE1_READINESS_SUPPORT_MODEL_LIFT_PLAN_PASS_20260906.json',r);print(json.dumps({'files':len(files),'publication':evidence['receipt_sha256'],'readiness':r['receipt_sha256']}))
if __name__=='__main__':main()
