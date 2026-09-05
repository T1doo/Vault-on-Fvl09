"""Stage-specific structural/evidence matrix; never grants collection authority."""
from .io import canonical,seal

LEVELS={'development_rpc':('r_pc',),'pilot_A':('r_pc','r_inv_path'),
        'pilot_B':('r_pc','r_inv_motion'),'formal':('r_pc','r_inv_path','r_inv_motion')}
EVIDENCE=('raw_integrity_pass','video_integrity_pass','family_verifier_pass','same_current_pass',
          'anchor_equivalence_pass','fresh_scene_pass','cleanup_pass','failure_history_complete')

def finalize_matrix(root_id,programs,rows,*,level,family,authorization=None):
    if level not in LEVELS or family not in ('F1','F2','F3','F4') or len(programs)!=3:raise ValueError('matrix specification')
    expected={(p,r) for p in programs for r in LEVELS[level]};observed=[];errors=[]
    raw_ids=[];rollout_ids=[];currents=[];universes=[]
    for row in rows:
        key=(row.get('program_id'),row.get('realization'));observed.append(key)
        if row.get('root_id')!=root_id:errors.append('mixed_root')
        if key not in expected:errors.append('unexpected_cell')
        if row.get('program_semantic_sha256')!=programs.get(row.get('program_id')):errors.append('program_mismatch')
        if row.get('origin_kind')!='real_rollout' or row.get('derived_from_raw_id') is not None:errors.append('derived_view_is_not_realization')
        if any(row.get(k) is not True for k in EVIDENCE) or row.get('orphan_process_count')!=0:errors.append('evidence_incomplete')
        if family in ('F3','F4') and row.get('final_state_equivalence_pass') is not True:errors.append('final_state_incomplete')
        raw_ids.append(row.get('raw_id'));rollout_ids.append(row.get('rollout_id'));currents.append(row.get('current_sha256'));universes.append(row.get('candidate_universe_sha256'))
    if set(observed)!=expected or len(observed)!=len(expected):errors.append('matrix_incomplete_or_duplicate')
    if None in raw_ids or len(set(raw_ids))!=len(raw_ids):errors.append('duplicate_or_missing_raw_id')
    if None in rollout_ids or len(set(rollout_ids))!=len(rollout_ids):errors.append('duplicate_or_missing_real_rollout')
    if None in currents or len(set(currents))!=1 or None in universes or len(set(universes))!=1:errors.append('current_or_universe_mismatch')
    complete=not errors
    # An external signed/hash-bound stage decision is required; CPU fixtures never accept.
    authorized=False
    if authorization is not None:
        a=dict(authorization);h=a.pop('receipt_sha256',None)
        authorized=h==canonical(a) and a.get('authorized') is True and a.get('root_id')==root_id and a.get('level')==level
    accepted=complete and authorized and all(row.get('evidence_scope')=='real_simulator_verified' for row in rows)
    return seal({'schema_version':'cmf_stage_specific_matrix_v1','root_id':root_id,'family':family,'level':level,
       'scientific_protocol':'controlled_multi_future_f1_f4_v1_2','acceptance_profile_version':'stage_profiles_v1',
       'expected_trajectory_count':len(expected),'observed_trajectory_count':len(rows),'required_realizations':list(LEVELS[level]),
       'matrix_complete':complete,'accepted':accepted,'stage_authorized':authorized,'errors':sorted(set(errors)),
       'formal_9_of_9_required':level=='formal','rows_sha256':canonical(rows)})

def check_split_atomicity(rows):
    seen={}
    for r in rows:
        for identity in (r['root_id'],r.get('super_root_id',r['root_id'])):
            if identity in seen and seen[identity]!=r['split']:raise ValueError('root/super-root split leakage')
            seen[identity]=r['split']
    return True
