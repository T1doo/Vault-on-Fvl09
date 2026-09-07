"""Pure data/document skeleton. No simulator, RNG sampling, budget or writes."""
from collections import Counter
from copy import deepcopy
import hashlib
from pathlib import Path

CANONICAL=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/数据构造方案.md')
CANONICAL_SHA='5b24d53718c44fb2a67e79b817c6c4904b82bacf62d4e642ce49470e980b32f9'
FAMILIES=('F1','F2','F3','F4')
QUOTAS={'train':{'clear':1,'medium':3,'crowded':1},'validation':{'clear':0,'medium':2,'crowded':0},'test':{'clear':1,'medium':1,'crowded':1}}
GENERATORS={
 'F1':{'scientific_variable':'one_of_three_nearby_same_class_objects',
       'required_parameters':['active_object_instance_pool','common_container_binding','two_similar_distractors','background_obstacle','identity_position_rotation','executing_arm_schedule','camera_visibility_contract','path_and_motion_variation_procedures'],
       'development_basis':'existing F1 development roots; formal role/difficulty grid and all9 realization qualification pending'},
 'F2':{'scientific_variable':'same_object_target_relation_bundle',
       'required_parameters':['main_object_asset','box_scale_pot_or_stand_bindings','three_mutually_exclusive_success_regions','facility_position_rotation','two_similar_distractors','background_obstacle','held_and_released_collision_models','controlled_inside_and_beside_physical_qualification'],
       'development_basis':'bounded planner-only inward-layout evidence exists; new-layout complete physical root/formal generator pending'},
 'F3':{'scientific_variable':'VVHH_VHVH_VHHV_order_only',
       'required_parameters':['bottle_asset_and_native_geometry','original_pad','two_similar_bottles','one_or_two_ordinary_distractors','common_central_pose','qualified_grasp_and_lift','table_z_V_table_x_H','realized_event_detector','same_rest_release_state','shared_first_V_and_boundary_contract'],
       'development_basis':'grasp/support-model development evidence only; stable complete temporal roots and formal generator pending'},
 'F4':{'scientific_variable':'common_X_then_ABC_ACB_BAC',
       'required_parameters':['common_X_and_tray','three_operated_instances','three_target_slots','one_or_two_distractors','role_symbol_object_slot_permutation','branch_neutral_pose_and_velocity','completion_stability_and_tie_rule','noninterference_and_final_state_equivalence'],
       'development_basis':'development planner/physical-template evidence; ten-root balanced formal generator and9-cell qualification pending'},
}

def build():
    actual=hashlib.sha256(CANONICAL.read_bytes()).hexdigest()
    if actual!=CANONICAL_SHA:raise ValueError('canonical source changed; re-review before updating draft')
    slots=[]
    for family in FAMILIES:
        rank=0
        for split,difficulties in QUOTAS.items():
            for difficulty,count in difficulties.items():
                for _ in range(count):
                    rank+=1
                    slots.append(dict(root_slot_id=f'draft_formal360_v1_{family}_P{rank:02d}',family_id=family,
                        formal_dataset_role='phase_1_formal_mechanism_dataset',root_slot_type='primary',origin='fresh_formal',slot_rank=rank,
                        split=split,layout_difficulty=difficulty,scene_seed=None,generator_version=None,
                        generator_profile_ref=family,slot_status='draft_pending_stage2_review',candidate_freeze_status='required_before_active',
                        attempt_budget_version=None,stop_condition_version=None,identity_status='proposed_not_allocated_or_sealed'))
        for rank in range(1,5):
            slots.append(dict(root_slot_id=f'draft_formal360_v1_{family}_R{rank:02d}',family_id=family,
                formal_dataset_role='phase_1_formal_mechanism_dataset',root_slot_type='reserve',origin='reserve',slot_rank=rank,reserve_rank=rank,
                split='inherit_failed_slot',layout_difficulty='inherit_failed_slot',scene_seed=None,generator_version=None,
                generator_profile_ref=family,slot_status='reserve_pending_activation',candidate_freeze_status='pending_activation',
                replacement_for_primary_slot=None,replacement_policy='inherit_failed_slot_split_and_layout_difficulty',
                attempt_budget_version=None,stop_condition_version=None,identity_status='proposed_not_allocated_or_sealed'))
    generators=deepcopy(GENERATORS)
    for g in generators.values():g.update(executable_generator_version=None,formal_generator_qualification='pending',formal_success_rate=None,
        numerical_threshold_registry=None,scene_seed_procedure='pending_review_then_freeze_before_any_formal_feasibility',scene_seed_values_generated=False)
    return dict(schema_version='cmf_formal360_nonexecuting_draft_v1',status='DRAFT_STAGE2_REVIEW_REQUIRED_NOT_SEALED',
        canonical_source=dict(path=str(CANONICAL),file_sha256=actual,sections=['D2-D5','D6-D10','D12-D17','D18-D20','M2-M3','M10']),
        design_version='controlled_multi_future_f1_f4_v1_2',
        design_counts=dict(primary_planned_slots=40,ordered_inactive_reserve_slots=16,target_accepted_roots=40,intents_per_root=3,
            realizations_per_intent=3,trajectories_per_accepted_root=9,target_formal_trajectories=360),
        split_difficulty_quotas_per_family=deepcopy(QUOTAS),
        realizations=['r_pc','r_inv_path','r_inv_motion'],primary_action_stream=dict(version='controller_effective_setpoint_v1',frequency_hz=250,dimensions=26,alignment='N_actions_N_plus_1_states'),
        authorizations=dict(stage2_sealed=False,formal_collection_authorized=False,training_authorized=False,h_reveal_authorized=False,compression_authorized=False,pi05_authorized=False),
        scientific_gates=dict(future_content='not_evaluated_by_this_draft',temporal_identifiability_F3='pending',temporal_identifiability_F4='pending',H_P='pending',compression='unauthorized',policy_transfer='unauthorized'),
        generated_state=dict(scenes=0,raw_trajectories=0,accepted_formal_roots=0,candidate_frozen_specs=0,activated_reserves=0),
        generators=generators,slots=slots)

def validate_structure(draft):
    if draft.get('schema_version')!='cmf_formal360_nonexecuting_draft_v1':raise ValueError('wrong draft schema')
    if draft.get('status')!='DRAFT_STAGE2_REVIEW_REQUIRED_NOT_SEALED':raise ValueError('draft must not claim seal')
    if draft.get('split_difficulty_quotas_per_family')!=QUOTAS:raise ValueError('quota registry disagrees')
    if set(draft['authorizations'])!={'stage2_sealed','formal_collection_authorized','training_authorized','h_reveal_authorized','compression_authorized','pi05_authorized'}:raise ValueError('authorization fields incomplete')
    if any(type(v) is not bool for v in draft['authorizations'].values()):raise ValueError('authority flags must be explicit false booleans')
    if set(draft['generated_state'])!={'scenes','raw_trajectories','accepted_formal_roots','candidate_frozen_specs','activated_reserves'} or any(type(v) is not int for v in draft['generated_state'].values()):raise ValueError('generated counters must be explicit integers')
    if any(draft['authorizations'].values()) or any(draft['generated_state'].values()):raise ValueError('draft cannot grant authority or fabricate generated evidence')
    if draft['realizations']!=['r_pc','r_inv_path','r_inv_motion']:raise ValueError('R=3 real realization contract changed')
    if draft['design_counts']!=dict(primary_planned_slots=40,ordered_inactive_reserve_slots=16,target_accepted_roots=40,intents_per_root=3,realizations_per_intent=3,trajectories_per_accepted_root=9,target_formal_trajectories=360):raise ValueError('denominator changed')
    slots=draft['slots']
    if len(slots)!=56 or len({s['root_slot_id'] for s in slots})!=56:raise ValueError('exact56 unique planned draft identities required')
    forbidden={'object_instances','object_roles','candidate_programs','candidate_universe_hash','candidate_universe_sha256','current','current_sha256','anchor','anchor_sha256','task_tree_hash','prefix_contract_hash','prefix_sha256','candidate_frozen_root_spec'}
    for s in slots:
        if forbidden&set(s):raise ValueError('no generated scene/candidate/current/hash fields in draft slots')
        if s['scene_seed'] is not None or s['generator_version'] is not None or s['attempt_budget_version'] is not None or s['stop_condition_version'] is not None:raise ValueError('unapproved seed/generator/numerical budget freeze')
        common={'root_slot_id','family_id','formal_dataset_role','root_slot_type','origin','slot_rank','split','layout_difficulty','scene_seed','generator_version','generator_profile_ref','slot_status','candidate_freeze_status','attempt_budget_version','stop_condition_version','identity_status'}
        allowed=common|({'reserve_rank','replacement_for_primary_slot','replacement_policy'} if s['root_slot_type']=='reserve' else set())
        if set(s)!=allowed:raise ValueError('unexpected slot fields may fabricate generation/qualification')
    for family in FAMILIES:
        primary=[s for s in slots if s['family_id']==family and s['root_slot_type']=='primary']
        reserve=[s for s in slots if s['family_id']==family and s['root_slot_type']=='reserve']
        if len(primary)!=10 or len(reserve)!=4:raise ValueError('family slot counts')
        if [s['slot_rank'] for s in primary]!=list(range(1,11)):raise ValueError('primary rank sequence changed')
        for split,row in QUOTAS.items():
            observed=Counter(s['layout_difficulty'] for s in primary if s['split']==split)
            if any(observed[k]!=v for k,v in row.items()) or set(observed)-set(row):raise ValueError('split by difficulty quota changed')
        if [s['reserve_rank'] for s in reserve]!=[1,2,3,4]:raise ValueError('ordered reserves changed')
        for s in reserve:
            if s['split']!='inherit_failed_slot' or s['layout_difficulty']!='inherit_failed_slot' or s['candidate_freeze_status']!='pending_activation' or s['replacement_for_primary_slot'] is not None:raise ValueError('inactive reserve preassigned or activated')
        g=draft['generators'][family]
        if g['formal_generator_qualification']!='pending' or g['formal_success_rate'] is not None or g['executable_generator_version'] is not None or g['numerical_threshold_registry'] is not None:raise ValueError('unverified formal generator/rate claim')
    if draft['scientific_gates']!=dict(future_content='not_evaluated_by_this_draft',temporal_identifiability_F3='pending',temporal_identifiability_F4='pending',H_P='pending',compression='unauthorized',policy_transfer='unauthorized'):raise ValueError('scientific Gate not proved by structure')
    return dict(structure_check_passed=True,scope='document_structure_only_not_stage2_seal_or_scientific_gate',primary_slots=40,inactive_reserves=16,
        roots_by_split={'train':20,'validation':8,'test':12},target_trajectories_by_split={'train':180,'validation':72,'test':108})

def assert_executable(_draft):
    raise ValueError('DRAFT_ONLY: seed/generator/thresholds/budgets/candidate seals and separate collection approval pending')

if __name__=='__main__':
    import json
    value=build();validate_structure(value);print(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2))
