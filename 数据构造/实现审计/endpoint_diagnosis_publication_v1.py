"""Seal durable index and readiness from completed bounded diagnostics."""
import json,sys,hashlib
from pathlib import Path
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';D=W/'Robotwin2/datasets'
sys.path.insert(0,str(A));from realization_utf8_io_v1 import write_new
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def seal(d):d['receipt_sha256']=hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest();return d
def checked(p):
    d=json.loads(p.read_text(encoding='utf-8'));v=dict(d);h=v.pop('receipt_sha256');assert seal(v)['receipt_sha256']==h;return d
def main():
    jobs=[('F3','f3_model_conformance_v1','model2'),('F3','f3_remaining_model_scene_v1_1','remain1'),('F3','f3_zero_scene_solver_replay_v1','replay0'),('F2','f2_endpoint_constraint_v1','ik1'),('F2','f2_endpoint_constraint_remaining_v1_1','ik2')];rows=[];files={}
    for family,name,job in jobs:
        root=D/name;guard=D/(name+'_guard');t=checked(root/'job_terminal.json');g=checked(guard/(job+'.terminal.json'))
        assert g['task_owned_cleanup_pass'] and (g['child_exit_code']==0)==t['pass']
        rows.append({'family':family,'output':str(root),'job_terminal_receipt_sha256':t['receipt_sha256'],'pass':t['pass'],'error':t.get('error'),'guard_receipt_sha256':g['receipt_sha256'],'guard_pid':g['guard_pid'],'child_pid':g['child_pid'],'task_owned_cleanup_pass':g['task_owned_cleanup_pass'],'elapsed_seconds':g['elapsed_seconds']})
        for folder in (root,guard):
            for p in sorted(folder.rglob('*')):
                if p.is_file():files[str(p)]=sha(p)
    assert [r['pass'] for r in rows]==[False,False,True,False,True]
    publication=seal({'schema_version':'cmf_endpoint_model_completed_publication_v1','jobs':rows,'file_sha256':files,'fresh_scenes':4,'F3_non_action_scenes':2,'F2_planner_only_scenes':2,'F3_model_constraint_API_checks_completed':40,'F2_IK_problems':15,'task_trajectory_queries':0,'physical_attempts':0,'new_raw':0,'new_roots':0,'all_task_GPUs_released':True,'all_prior_failures_retained':True})
    write_new(A/'ENDPOINT_MODEL_COMPLETED_PUBLICATION_V1_20260906.json',publication)
    prior=json.loads((A/'STAGE1_READINESS_AFTER_NINE_REALIZATIONS_20260906.json').read_text(encoding='utf-8'))
    readiness=seal({'schema_version':'cmf_stage1_readiness_after_endpoint_model_diagnosis_v1','status':'NOT_READY_F2_NEW_LAYOUT_AND_F3_NEW_GRASP_REQUIRE_REVIEW',
        'accepted_development':prior['accepted_development'],'stage1':prior['stage1'],'formal':prior['formal'],'current_GPU_jobs':0,'publication_receipt_sha256':publication['receipt_sha256'],
        'F2':{'endpoint_diagnosis_completed':True,'C_positive_control_pass':True,'U_D_and_registered_yaws_full_valid_solutions':0,'mathematical_infeasibility_proven':False,'scene_cap_consumed':2,'IK_cap_consumed':15,'conditional_route_queries_unused':4,'old_job_rerun_allowed':False,'next':'one proposed 100mm inward stand/target layout; CPU no box/scale/wall intersection; new current/root and exact review required'},
        'F3':{'model_conformance_completed':True,'old_endpoints_exact_geometry_invalid':2,'old_micro_condition_satisfied':False,'non_action_scene_cap_consumed':2,'conditional_trajectory_queries_unused':6,'physical_attempts_unused':2,'next':'two parent-bound analytical top-down CPU proposals; open geometry clear, IK/closed retention/full-arm/postlift not validated; new recipe review required'},
        'F4_B':{'status':'CPU_NEW_SEED_LAYOUT_PROPOSAL_ONLY','GPU_authorized':False,'potential_new_pilot_cells':6},
        'pilot_remaining_structure_if_later_authorized':{'F2_A_B':12,'F3_A_B':12,'F4_B':6,'total':30},'prohibited':prior['prohibited'],
        'review_entrypoint':str(A/'GPT_HANDOFF_F2_ENDPOINT_F3_GEOMETRY_DECISIONS_20260906.md')})
    write_new(A/'STAGE1_READINESS_AFTER_ENDPOINT_MODEL_DIAGNOSIS_20260906.json',readiness);print(json.dumps({'publication_files':len(files),'publication_receipt':publication['receipt_sha256'],'readiness_receipt':readiness['receipt_sha256']}))
if __name__=='__main__':main()
