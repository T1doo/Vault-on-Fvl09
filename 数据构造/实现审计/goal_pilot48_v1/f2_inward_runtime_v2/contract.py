import copy
import hashlib
import json
import numpy as np
from goal_pilot48_v1.f2_inward_runtime_v1.contract import A, P, W, digest, build_contract as parent_contract

PROPOSAL = A / 'goal_pilot48_v1/f2_inward_failure_review_v1/proposal_revision1.json'
PROPOSAL_SHA = '1060352374547715c7d2b88eab97d3d56061a16c891d45cf1ea69d9bcbe7a3b1'
LAYOUT = 'f2_goal_inward_endpoint_revision1'
SLOT = 'f2-goal-inward-endpoint-revision1-planner-only-20260907'

def proposal():
    if hashlib.sha256(PROPOSAL.read_bytes()).hexdigest() != PROPOSAL_SHA:
        raise ValueError('frozen revision1 proposal bytes changed')
    p = json.loads(PROPOSAL.read_text(encoding='utf-8'))
    if p['parent_job_id'] != 'p48_f2_inward_001' or p['evidence_based_revision'] != 1 or p['new_layout_id'] != LAYOUT or not p['geometry_audit']['pass']:
        raise ValueError('unexpected revision source')
    return p

def build_contract():
    c = copy.deepcopy(parent_contract())
    p = proposal()
    prior_b = c['binding']['binding_sha256']
    prior_p = c['planned']['planned_root_slot_spec_sha256']
    b = c['binding']
    b.pop('binding_sha256')
    layout = b['layout_payload']
    layout['layout_version'] = LAYOUT
    layout['facility_pose_xyz']['beside_reference'] = list(p['new_stand_actor_pose'][:3])
    layout['beside_candidate_xy_m'] = copy.deepcopy(p['all_beside_candidate_xy_m'])
    b.update(layout_version=LAYOUT, layout_payload_sha256=digest(layout), parent_binding_sha256=prior_b,
             new_layout_dynamic_qualification_status='pending', selected=False, provisional_dynamic_candidate=True,
             development_execution_authorized=False, source_proposal_file_sha256=PROPOSAL_SHA,
             old_inside_qualification_inherited=False, selection_decision_source='user_goal_evidence_based_endpoint_revision1')
    b['binding_sha256'] = digest(b)
    planned = c['planned']
    planned.pop('planned_root_slot_spec_sha256')
    planned.update(slot_id=SLOT, f2_asset_layout_binding_v3=copy.deepcopy(b), parent_planned_spec_sha256=prior_p,
                   purpose='goal_unique_revision1_planner_only_gate', source_proposal_file_sha256=PROPOSAL_SHA,
                   new_current_anchor_lineage_required=True, old_current_anchor_reuse_allowed=False)
    # Keep the deterministic scene seed: only the registered layout changes.
    planned['planned_root_slot_spec_sha256'] = digest(planned)
    c['beside_candidate_xy_m'] = list(p['new_target_geometry_xy_m'])
    c['beside_template_actor_pose'] = np.asarray(p['new_can_actor_pose'])
    goals = copy.deepcopy(c['inward_goals'])
    goals['U_new'] = list(p['new_U_reported_goal'])
    goals['D_new'] = list(p['new_D_reported_goal'])
    U = np.asarray(goals['U_new']); D = np.asarray(goals['D_new']); N = np.asarray(goals['N'])
    hub = U.copy(); hub[:2] = (np.asarray(goals['C'])[:2] + U[:2]) / 2; hub[2] = max(goals['C'][2], U[2])
    c['beside_targets'] = [dict(t, pose=v.tolist()) for t, v in zip(c['beside_targets'], (hub,U,D,U,hub,N))]
    c['beside_targets_sha256'] = digest(c['beside_targets'])
    c['inward_goals'] = goals
    n = copy.deepcopy(c['inward_contract'])
    n.update(schema_version='cmf_f2_goal_revision1_route_contract_v2', planned=copy.deepcopy(planned), binding=copy.deepcopy(b), goals=copy.deepcopy(goals),
             source_proposal_file_sha256=PROPOSAL_SHA, parent_job_id='p48_f2_inward_001', execution_ready=True,
             remaining_implementation_gate='actual GPU revision1 endpoint and route qualification pending',
             old_inside_success_is_historical_only=True)
    c['inward_contract'] = n
    validate_contract(c)
    return c

def validate_contract(c):
    from controlled_multi_future.f2_official_asset_compatibility_matrix_v3 import validate_frozen_asset_layout_binding_v3
    p = proposal(); b = c['binding']; n = c['inward_contract']
    validate_frozen_asset_layout_binding_v3(b)
    if b['layout_version'] != LAYOUT or c['planned']['slot_id'] != SLOT:
        raise ValueError('old layout/planned slot cannot enter revision1')
    if c['planned']['f2_asset_layout_binding_v3'] != b or n['binding'] != b or n['planned'] != c['planned']:
        raise ValueError('three-relation shared layout lineage mismatch')
    planned = dict(c['planned']); h = planned.pop('planned_root_slot_spec_sha256')
    if digest(planned) != h:
        raise ValueError('planned hash mismatch')
    if b['program_ids'] != ['F2-inside', 'F2-on', 'F2-beside'] or b['old_inside_qualification_inherited'] is not False:
        raise ValueError('three-relation semantics or old-inside claim changed')
    if c['inward_goals'] != n['goals'] or c['inward_goals']['U_new'] != p['new_U_reported_goal'] or c['inward_goals']['D_new'] != p['new_D_reported_goal']:
        raise ValueError('old dispatch targets or mutable proposal')
    if b['layout_payload']['beside_candidate_xy_m'] != p['all_beside_candidate_xy_m'] or b['layout_payload']['facility_pose_xyz']['beside_reference'] != p['new_stand_actor_pose'][:3]:
        raise ValueError('stand/target translation not bound together')
    if c['beside_candidate_xy_m'] != p['new_target_geometry_xy_m'] or not np.array_equal(c['beside_template_actor_pose'], p['new_can_actor_pose']):
        raise ValueError('wrong selected candidate geometry')
    if digest(c['beside_targets']) != c['beside_targets_sha256']:
        raise ValueError('geometry target hash mismatch')
    for i, key in ((1, 'U_new'), (2, 'D_new'), (3, 'U_new'), (5, 'N')):
        if c['beside_targets'][i]['pose'] != c['inward_goals'][key]:
            raise ValueError('old target under revised binding')
    if [n[k] for k in ('IK_cap', 'trajectory_query_cap', 'scene_cap', 'physical_cap', 'raw_cap')] != [3,4,1,0,0]:
        raise ValueError('revision budget changed')
    return True

def manifest_lineage(c=None):
    c = build_contract() if c is None else c
    return {'f2_revision1_binding_sha256': c['binding']['binding_sha256'],
            'f2_revision1_planned_sha256': c['planned']['planned_root_slot_spec_sha256'],
            'f2_revision1_goals_sha256': digest(c['inward_goals']),
            'f2_revision1_proposal_file_sha256': PROPOSAL_SHA}
