"""New diagnostic lineage and explicit carry/release planner state contract."""
import copy,json,sys,hashlib
from pathlib import Path
import numpy as np
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计'
sys.path.insert(0,str(A/'f2_bounded_transit_runtime_v1'));sys.path.insert(1,str(A))
from semantic_target import corrected_contract
from realization_utf8_io_v1 import write_new
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def build():
    c,_=corrected_contract();p=json.loads((A/'F2_ENDPOINT_DIAGNOSIS_AND_ONE_LAYOUT_PROPOSAL_V1_20260906.json').read_text(encoding='utf-8'))['one_proposal'];b=copy.deepcopy(c['binding']);prior=b['binding_sha256'];shift=np.array(p['translation_world_xy_m']);layout=b['layout_payload']
    layout['layout_version']='f2_beside_inward_layout_v1';layout['facility_pose_xyz']['beside_reference']=p['new_stand_actor_pose'][:3]
    layout['beside_candidate_xy_m']=[(np.array(xy)+shift).tolist() for xy in layout['beside_candidate_xy_m']]
    assert np.allclose(layout['beside_candidate_xy_m'][2],p['new_target_geometry_xy_m'],atol=1e-12,rtol=0)
    b.update(layout_version=layout['layout_version'],layout_payload_sha256=digest(layout),selected=False,provisional_dynamic_candidate=True,development_execution_authorized=False,
        parent_binding_sha256=prior,parent_screening_is_historical_not_new_layout_qualification=True,new_layout_dynamic_qualification_status='pending',selection_decision_source='new_user_approved_inward_planner_only_design')
    b.pop('binding_sha256');b['binding_sha256']=digest(b)
    from controlled_multi_future.f2_official_asset_compatibility_matrix_v3 import validate_frozen_asset_layout_binding_v3
    validate_frozen_asset_layout_binding_v3(b)
    planned=copy.deepcopy(c['planned']);planned.pop('planned_root_slot_spec_sha256');planned.update(slot_id='f2-inward-planner-only-v1-20260906',seed=2026090602,f2_asset_layout_binding_v3=b,
        parent_planned_spec_sha256=c['planned']['planned_root_slot_spec_sha256'],purpose='one_new_inward_layout_planner_only_gate',new_current_anchor_lineage_required=True,old_current_anchor_reuse_allowed=False)
    planned['planned_root_slot_spec_sha256']=digest(planned)
    phases=[{'target':'U_new','can_state':'attached_to_actual_flange','gripper':'actual_held','world_contains_static_target_can':False},
        {'target':'D_new','can_state':'attached_until_supported_release','gripper':'actual_held','world_contains_static_target_can':False,'allowed_contact_pair':'can-table supporting contact only; never finger-table'},
        {'target':'U_new','can_state':'released_static_at_D_new','gripper':'open_target_from_real_joint_mapping','world_contains_static_target_can':True},
        {'target':'N','can_state':'released_static_at_D_new','gripper':'open_target_from_real_joint_mapping','world_contains_static_target_can':True}]
    return {'schema_version':'cmf_f2_inward_binding_and_route_state_contract_v1','planned':planned,'binding':b,'diagnostic_initial_qpos_source':'sealed old held state reconstructed for planner-only; not proof of a real new prefix',
        'goals':{'C':c['sealed_prefix_end_eef_pose'].tolist(),'U_new':p['new_U_reported_goal'],'D_new':p['new_D_reported_goal'],'N':c['neutral_eef_pose'].tolist()},
        'route_phases':phases,'release_transition_is_planner_state_change_not_physical_execution':True,'whole_table_collision_disable_allowed':False,'can_attachment_until_neutral_allowed':False,
        'CPU_layout_prerequisites_pass':True,'execution_ready':False,'remaining_implementation_gate':'audited selective can-table support handling + released-can obstacle and actual open-finger model switch integrated into real IK/route checker',
        'IK_cap':3,'trajectory_query_cap':4,'scene_cap':1,'physical_cap':0,'raw_cap':0,'actual_calls':0}
def main():
    d=build();assert d['binding']['layout_payload']['beside_candidate_xy_m'][0]!=[.2,.12]
    assert all(s['can_state']=='released_static_at_D_new' for s in d['route_phases'][2:])
    assert d['planned']['slot_id']!='f2-beside-inward-layout-v1'
    d['receipt_sha256']=digest(d);write_new(A/'F2_INWARD_NEW_BINDING_ROUTE_STATE_CONTRACT_V1_20260906.json',d);print('new binding validator, translated candidate coordinates and carry/release state contract passed; execution integration still pending')
if __name__=='__main__':main()
