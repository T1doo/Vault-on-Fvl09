import copy,hashlib,json
import numpy as np
from goal_pilot48_v1.f2_inward_runtime_v2.contract import A,P,W,digest,build_contract as parent_contract,manifest_lineage as parent_lineage
PROPOSAL=A/'goal_pilot48_v1/f2_u_waypoint_revision_v1/proposal.json'
PROPOSAL_SHA='f97bb48c4051b38ed20a5b9e10e15b4ea10ee608bd6697009e4e03e7ba951415'

def proposal():
    if hashlib.sha256(PROPOSAL.read_bytes()).hexdigest()!=PROPOSAL_SHA:raise ValueError('fixed U proposal changed')
    p=json.loads(PROPOSAL.read_text(encoding='utf-8'));v=dict(p);h=v.pop('receipt_sha256')
    if digest(v)!=h or p['revision_class']!='endpoint_route' or p['revision_index']!=1 or not p['native_geometry_pass']:raise ValueError('U proposal not verified')
    return p

def build_contract():
    c=copy.deepcopy(parent_contract());p=proposal();old=copy.deepcopy(c['inward_goals'])
    if old['U_new']!=p['old_U_reported_goal'] or old['D_new']!=p['unchanged_D_reported_goal']:raise ValueError('qualified layout/old goals mismatch')
    goals=copy.deepcopy(old);goals['U_new']=list(p['new_U_reported_goal']);U=np.asarray(goals['U_new']);D=np.asarray(goals['D_new']);N=np.asarray(goals['N'])
    hub=U.copy();hub[:2]=(np.asarray(goals['C'])[:2]+U[:2])/2;hub[2]=max(goals['C'][2],U[2])
    c['beside_targets']=[dict(t,pose=v.tolist()) for t,v in zip(c['beside_targets'],(hub,U,D,U,hub,N))]
    c['beside_targets_sha256']=digest(c['beside_targets']);c['inward_goals']=goals
    n=copy.deepcopy(c['inward_contract']);n.update(schema_version='cmf_f2_endpoint_route_revision1_v3',goals=copy.deepcopy(goals),
      endpoint_route_revision=1,layout_revision_count_unchanged=True,approach_height_m=p['new_approach_height_m'],
      route_proposal_file_sha256=PROPOSAL_SHA,parent_endpoint_job='p48_f2_revision1_001',
      remaining_implementation_gate='fresh C/U/D and conditional four-route actual qualification pending')
    c['inward_contract']=n;validate_contract(c);return c

def validate_contract(c):
    prior=parent_contract();p=proposal()
    for key in ('binding','planned'):
        if c[key]!=prior[key]:raise ValueError('qualified D/layout/planned seed changed')
    if c['inward_contract']['binding']!=prior['binding'] or c['inward_contract']['planned']!=prior['planned']:raise ValueError('route/scene binding diverged')
    for key in ('C','D_new','N'):
        if c['inward_goals'][key]!=prior['inward_goals'][key]:raise ValueError('qualified/fixed endpoint changed')
    if c['inward_goals']['U_new']!=p['new_U_reported_goal'] or c['inward_contract']['goals']!=c['inward_goals']:raise ValueError('wrong route revision target')
    if c['beside_template_actor_pose'].tolist()!=prior['beside_template_actor_pose'].tolist() or c['beside_candidate_xy_m']!=prior['beside_candidate_xy_m']:raise ValueError('placement geometry changed')
    if digest(c['beside_targets'])!=c['beside_targets_sha256']:raise ValueError('derived route target hash mismatch')
    for i,k in ((1,'U_new'),(2,'D_new'),(3,'U_new'),(5,'N')):
        if c['beside_targets'][i]['pose']!=c['inward_goals'][k]:raise ValueError('old U in live geometry targets')
    if [c['inward_contract'][k] for k in ('IK_cap','trajectory_query_cap','scene_cap','physical_cap','raw_cap')]!=[3,4,1,0,0]:raise ValueError('budget changed')
    return True

def manifest_lineage(c=None):
    c=build_contract() if c is None else c
    return {**parent_lineage(parent_contract()),'f2_route_revision1_goals_sha256':digest(c['inward_goals']),
            'f2_route_revision1_proposal_file_sha256':PROPOSAL_SHA,'f2_route_revision1_targets_sha256':c['beside_targets_sha256']}
