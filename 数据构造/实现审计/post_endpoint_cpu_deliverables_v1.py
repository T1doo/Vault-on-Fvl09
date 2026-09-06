"""Read-only evidence checks and proposal generation. No simulator/solver jobs."""
import copy,json,hashlib,sys
from pathlib import Path
import numpy as np
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';D=W/'Robotwin2/datasets'
sys.path.insert(0,str(A));sys.path.insert(1,str(W/'Robotwin2/project/RoboTwin'))
from realization_utf8_io_v1 import write_new
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def seal(d):
    d['receipt_sha256']=hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest();return d
def f2():
    root=D/'f2_endpoint_constraint_remaining_v1_1';rows=[]
    for path in sorted((root/'problems').glob('*.json')):
        if path.name.endswith('.start.json'):continue
        d=json.loads(path.read_text(encoding='utf-8'));solutions=d['result']['solutions']
        rows.append({'problem_id':d['problem_id'],'profile':d['profile'],'file_sha256':sha(path),'reported_success_count':sum(d['result']['reported_solver_success']),
            'full_valid_count':sum(s['full_valid'] for s in solutions),'best_position_residual_m':min(s['FK_position_error_m'] for s in solutions),
            'best_orientation_residual_rad':min(s['FK_orientation_angle_rad'] for s in solutions),'constraint_feasible_counts':{k:sum(s['constraint_checks'][k] for s in solutions) for k in ('K0','K1','K2')}})
    assert len(rows)==15 and all(r['full_valid_count']>0 for r in rows if r['problem_id'].startswith('C_'))
    assert all(r['full_valid_count']==0 for r in rows if not r['problem_id'].startswith('C_'))
    # Import exact existing CPU target contract, not another GPU probe.
    sys.path.append(str(A/'f2_bounded_transit_runtime_v1'))
    from semantic_target import corrected_contract
    from controlled_multi_future.geometry import actor_target_to_eef_pose,world_axis_offset_pose,pose_matrix
    c,geometry=corrected_contract();target=np.array(c['beside_candidate_xy_m']);held=c['sealed_prefix_end_actor_pose'];local=np.array(geometry['local_center_m']);T=pose_matrix(held);current=(T[:3,:3]@local+T[:3,3])[:2]
    direction=(current-target)/np.linalg.norm(current-target)
    residual=max(r['best_position_residual_m'] for r in rows if r['problem_id'] in ('U_K0','D_K0'))
    # A single proposed displacement: twice observed residual, rounded upward
    # to 1cm, plus 1cm. This is a design heuristic, not a reachability proof.
    distance=float(np.ceil((2*residual)/.01)*.01+.01);shift=direction*distance
    actor=c['beside_template_actor_pose'].copy();actor[:2]+=shift
    release=actor_target_to_eef_pose(c['sealed_prefix_end_eef_pose'],held,actor)
    world=json.loads((root/'world_geometry.json').read_text(encoding='utf-8'));stand=next(s['actor_world_pose'] for s in world['shapes'] if s['role']=='stand');newstand=np.array(stand);newstand[:2]+=shift
    out={'schema_version':'cmf_f2_endpoint_diagnosis_and_one_layout_proposal_v1','diagnosis':'NO_U_D_SOLUTION_WITHIN_FIXED_BUDGET_EVEN_K0','problems':rows,
        'task_infeasibility_proven':False,'collision_only_explanation_supported':False,'current_pose_positive_control_pass':True,
        'cumulative_scenes':2,'IK_problems':15,'trajectory_queries':0,'physical_attempts':0,'route_queries_unused':4,
        'one_proposal':{'id':'f2-beside-inward-layout-v1','status':'PROPOSED_NOT_IK_OR_PHYSICALLY_VALIDATED','translation_world_xy_m':shift.tolist(),'translation_norm_m':distance,
            'derivation':'toward sealed reachable held-can geometry centre; ceil(2 * max(best K0 U/D position residual) / 1cm) * 1cm + 1cm; heuristic, not solver feasibility',
            'old_target_geometry_xy_m':target.tolist(),'new_target_geometry_xy_m':(target+shift).tolist(),'new_can_actor_pose':actor.tolist(),
            'stand_moves_by_identical_xy_vector':True,'old_stand_actor_pose':stand,'new_stand_actor_pose':newstand.tolist(),
            'new_U_reported_goal':world_axis_offset_pose(release,.08).tolist(),'new_D_reported_goal':release.tolist(),
            'can_yaw_grasp_and_beside_relative_geometry_unchanged':True,'box_scale_unchanged':True,
            'current_layout_changes_requires_new_root_lineage':True,'old_inside_5_of_5_evidence_retained_not_revalidated_for_new_scene':True,
            'pending':['CPU stand/target versus box/scale and table exact clearance','new scene/candidate-universe impact review','exact model C/U/D endpoint Gate','controlled insertion whole-root qualification'],
            'GPU_authorized':False,'physical_authorized':False,'additional_candidates':0},
        'terminal_file':str(root/'job_terminal.json'),'terminal_file_sha256':sha(root/'job_terminal.json')}
    write_new(A/'F2_ENDPOINT_DIAGNOSIS_AND_ONE_LAYOUT_PROPOSAL_V1_20260906.json',seal(out));return out
def eligibility():
    import realization_final_audit_v1
    d=realization_final_audit_v1.run();old=json.loads((A/'REALIZATION_NINE_FINAL_AUDIT_V1_20260906.json').read_text(encoding='utf-8'))
    assert d['rows']==old['rows'] and d['pilot_candidate_cells_with_evidence']==18
    out={'schema_version':'cmf_pilot_18_cell_eligibility_readonly_recheck_v1','pass':True,'raw_video_verifier_root_and_current_checked':True,'rows':d['rows'],
        'cohorts':[{'cohort':c['cohort'],'root':c['parent_root_id'],'matrix':c['six_cell_matrix'],'final_state_equivalence':c['six_trajectory_final_state_equivalence']} for c in d['cohorts']],
        'existing_final_audit_sha256':sha(A/'REALIZATION_NINE_FINAL_AUDIT_V1_20260906.json'),'candidate_cells':18,'stage1_accepted':0,'formal_accepted':0,'source_data_edited':False}
    write_new(A/'PILOT_18_CELL_ELIGIBILITY_READONLY_RECHECK_V1_20260906.json',seal(out));return out
def f4():
    from controlled_multi_future.planner_qualification_manifests_v2_3 import build_f4_program_panel_manifest_v1_1
    from controlled_multi_future.f4_stage_b_geometry_contract_v2 import audit_f4_stage_b_candidate_geometry_v2
    p=build_f4_program_panel_manifest_v1_1();source=p['source_candidate'];candidate=p['candidates'][0]
    # New scene, not A with a new suffix. Fixed 1cm translation is chosen once.
    sources=copy.deepcopy(source['source_layout']);slots=copy.deepcopy(candidate['slot_poses'])
    for pose in list(sources.values())+list(slots.values()):pose[0]-=.01
    audit=audit_f4_stage_b_candidate_geometry_v2(source_layout=sources,slot_poses=slots,corridor_policy=candidate['corridor_policy'],arm='left')
    assert audit['construction_valid'] and audit['equal_final_world_state']
    out={'schema_version':'cmf_f4_pilot_B_genuine_new_layout_proposal_v1','status':'CPU_PROPOSAL_ONLY','planned_root_slot_spec':{
        'slot_id':'f4-pilot-B-layout-v1-20260906','family':'F4','seed':2026090604,'generator':'one_fixed_minus_1cm_table_X_translation_of_source_blocks_and_slots','origin':'new_development_pilot_B_proposal','rank':1,
        'split':'pilot_only_not_test','difficulty':'pending_approved_design_classification','retry_or_resampling':False},
        'parent_A_source_candidate_sha256':source['candidate_sha256'],'parent_A_slot_candidate_sha256':candidate['candidate_sha256'],
        'new_source_layout':sources,'new_slot_poses':slots,'common_X_tray_unchanged':True,'object_slot_mapping':candidate['object_slot_mapping'],'programs':['ABC','ACB','BAC'],
        'same_current_as_A':False,'reuse_A_current_anchor_prefix_or_controls_allowed':False,'candidate_freeze_status':'pending_new_scene_feasibility_not_frozen',
        'geometry_only_audit':audit,'robot_IK_path_and_actual_current_unverified':True,'prospective_matrix':{'r_pc':3,'r_inv_motion':3,'total':6,'independent_roots':1},
        'motion_proposal':'separate real rollout; order-preserving C1 retiming after frozen shared prefix; fixed same executing arm/program/250Hz; exact factors require freeze',
        'proposed_finite_scope':{'candidate_layouts':1,'root_attempts':1,'raw_trajectories':6,'automatic_retry':False,'planner_scene_physical_caps':'pending reviewed runner derivation; not an execution manifest'},
        'GPU_authorized':False,'stage1_authorized':False,'formal_authorized':False,'new_scenes':0,'new_trajectories':0}
    write_new(A/'F4_PILOT_B_NEW_LAYOUT_CPU_PROPOSAL_V1_20260906.json',seal(out));return out
if __name__=='__main__':
    a=f2();b=eligibility();c=f4();print(json.dumps({'F2':a['diagnosis'],'F2_shift_m':a['one_proposal']['translation_norm_m'],'eligibility':b['candidate_cells'],'F4_geometry_pass':c['geometry_only_audit']['construction_valid']}))
