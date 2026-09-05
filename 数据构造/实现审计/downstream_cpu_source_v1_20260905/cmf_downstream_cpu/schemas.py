"""Unapproved pilot eligibility matrix and pending formal/reserve schemas."""
from .io import seal
from .matrices import LEVELS
from controlled_multi_future.families import F1ObjectSelection,F2TargetRelation,F3MotionOrder,F4SubtaskOrder

def build_stage1(reuse_candidates):
    cells=[]
    for cls in (F1ObjectSelection,F2TargetRelation,F3MotionOrder,F4SubtaskOrder):
        programs=cls().checked_provisional_programs()
        family=programs[0]['program_id'].split('-')[0]
        for pilot in ('A','B'):
            for program in programs:
                for realization in LEVELS['pilot_'+pilot]:
                    sources=reuse_candidates.get((family,pilot,program['program_id']),[]) if realization=='r_pc' else []
                    cells.append({'family':family,'pilot_root':pilot,'intent':program['program_id'],'realization':realization,
                        'stage1_cell_id':family+'-'+pilot+'-'+program['program_id']+'-'+realization,
                        'candidate_raw_available':bool(sources),'source_evidence':sources,
                        'eligibility_status':'candidate_for_pilot_reuse' if sources else 'requires_new_collection',
                        'needs_new_collection':None if sources else True,'missing_reason':'stage_specific_reuse_review_pending' if sources else 'no_accepted_realization_for_this_pilot_cell',
                        'stage_authorized':False,'accepted_for_stage1':False,'source_debug_roots_are_not_untouched_test':True})
    assert len(cells)==48 and len({c['stage1_cell_id'] for c in cells})==48
    return seal({'schema_version':'cmf_stage1_48_cell_eligibility_v1','cells':cells,'stage1_authorized':False,
        'accepted_authorized_count':0,'required_count':48,'development_auto_promotion':False,'formal_9_before_pilot_required':False})

def build_stage2_pending():
    quota={'train':['clear']+['medium']*3+['crowded'],'validation':['medium']*2,'test':['clear','medium','crowded']}
    primary=[];reserves=[]
    for family in ('F1','F2','F3','F4'):
        rank=0
        for split,difficulties in quota.items():
            for difficulty in difficulties:
                rank+=1;primary.append({'schema_slot_id':family+'-primary-'+str(rank).zfill(2),'family':family,'split':split,'difficulty':difficulty,
                   'seed':None,'planned_root_slot_spec':None,'candidate_frozen_root_spec':None,'current_sha256':None,'candidate_universe_sha256':None,
                   'status':'pending_planned_slot_approval_not_an_operational_slot','physical_feasibility':None})
        for rank in range(1,5):reserves.append({'schema_slot_id':family+'-reserve-'+str(rank).zfill(2),'family':family,'reserve_rank':rank,'active':False,
            'split':None,'difficulty':None,'inheritance_rule':'inherit_failed_primary_split_and_difficulty_on_ordered_activation',
            'candidate_freeze_status':'pending_activation','planned_root_slot_spec':None,'current_sha256':None,'candidate_universe_sha256':None})
    return seal({'schema_version':'cmf_stage2_pending_schema_v1','primary_slots':primary,'ordered_reserves':reserves,
      'attempt_budget_schema':{'required':['planner_query_cap','fresh_scene_cap','physical_attempt_cap','timeout_seconds','recovery_policy','stop_condition'],'values':None},
      'normalization_procedure':{'fit_partition':'formal_train_only','fit_before_checkpoint_selection':True,'validation_or_test_fit_forbidden':True,'numerical_statistics':None,'procedure_frozen':False},
      'root_super_root_split_atomic':True,'formal_collection_authorized':False,'schema_only':True})
