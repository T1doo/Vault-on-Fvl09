"""Unique approved native-floor support target, bound to an actual grasp."""
import copy
import numpy as np
import transforms3d as t3d
from goal_pilot48_v1.f2_inside_native_floor_v1.certificate import A,W,load,sha,digest,matrix,validate_certificate
from goal_pilot48_v1.f2_inside_native_floor_v1.geometry_verifier import GeometryVerifier

REFERENCE=W/'Robotwin2/datasets/p48_f2_prefix_clearance_001'
CONTACT=A/'goal_pilot48_v1/f2_inside_native_floor_v1/saved_contact_geometry.json'
CAPS={'solver_problems':5,'independent_ik_problems':0,'fresh_scene_attempts':1,'action_attempts':1,'collection_attempts':0}

def pose(T):return np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist()
def checked_pose(p):
    p=np.asarray(p,dtype=float)
    if p.shape!=(7,) or not np.isfinite(p).all() or abs(np.linalg.norm(p[3:])-1)>1e-5:raise ValueError('actual finite unit-quaternion world pose required')
    return p

def prefix_lineage():
    terminal=load(REFERENCE/'job_terminal.json');payload=dict(terminal);claimed=payload.pop('receipt_sha256')
    if digest(payload)!=claimed or terminal['pass'] is not True or terminal['prefix_physical_pass'] is not True or terminal['scientific_route_pass'] is not True:raise ValueError('real prefix qualification required')
    r=load(REFERENCE/'prefix_result.json')
    files=['job_terminal.json','goal_terminal.json','prefix_result.json','reference_anchor.json','reference_current_hashes.json','prefix_trace.npz','canonical_prefix_artifact/canonical_prefix_artifact.json','canonical_prefix_artifact/prefix_arrays.npz']
    return {'reference_job':'p48_f2_prefix_clearance_001','qualified_prefix_receipt_sha256':claimed,
      'reference_current':load(REFERENCE/'reference_current_hashes.json'),'initial_anchor_sha256':load(REFERENCE/'reference_anchor.json')['anchor_sha256'],
      'acceptance_anchor_sha256':r['acceptance_prefix_end_anchor']['anchor_sha256'],
      'files':{str(REFERENCE/f):sha(REFERENCE/f) for f in files},'reference_is_not_fresh_scene_replay':True}

def build_targets(*,actual_eef_pose,actual_can_pose,actual_box_pose,neutral_eef_pose,certificate,lineage):
    validate_certificate(certificate)
    if lineage!=prefix_lineage():raise ValueError('qualified prefix/current/anchor lineage changed')
    E,C,B,N=[matrix(checked_pose(p)) for p in (actual_eef_pose,actual_can_pose,actual_box_pose,neutral_eef_pose)]
    contact=load(CONTACT)
    if contact['certificate_sha256']!=certificate['receipt_sha256']:
        # Fresh certificates have changed world transforms but identical native
        # local signatures; the approved reference certificate still binds the
        # saved target, not a fabricated fresh success.
        from goal_pilot48_v1.f2_inside_native_floor_v1.certificate import reference_certificate
        if contact['certificate_sha256']!=reference_certificate()['receipt_sha256']:raise ValueError('approved contact reference changed')
    target=B@np.linalg.inv(matrix(contact['box_world_pose']))@matrix(contact['can_world_pose'])
    grasp=np.linalg.inv(E)@C;goal=target@np.linalg.inv(grasp)
    geometry=GeometryVerifier(certificate).evaluate(pose(target),pose(B),binding_sha256=certificate['binding_sha256'])
    if not geometry['pass'] or geometry['floor_geometry_candidate_indices']!=[9]:raise ValueError('unique native box__9 support geometry not satisfied')
    pre=goal.copy();pre[:3,3]+=.03*B[:3,1]
    lift=E.copy();lift[2,3]+=.12
    targets=[{'segment_id':name,'pose':pose(T)} for name,T in zip(('lift','preinsert_30mm','controlled_descend_to_support','retreat_to_preinsert','neutral'),(lift,pre,goal,pre,N))]
    state={'eef':pose(E),'can':pose(C),'box':pose(B),'neutral':pose(N)}
    result={'schema_version':'f2_controlled_inside_actual_grasp_spec_v2','source_actual_state':state,'source_state_sha256':digest(state),
      'actual_eef_to_can':grasp.tolist(),'target_actor_pose':pose(target),'targets':targets,'target_geometry':geometry,
      'certificate_sha256':certificate['receipt_sha256'],'binding_sha256':certificate['binding_sha256'],'prefix_lineage':lineage,
      'approved_contact_source_sha256':sha(CONTACT),'caps':CAPS,'allowed_support_shape_names':['box__9'],
      'support_frames':50,'slow_release':[[x,10] for x in (.2,.4,.6,.8,1.)],'settle_frames':250,'rest_frames':75,
      'primary_gravity_drop':False,'old_inside_success_inherited':False,'physical_execution_authorized':False}
    result['receipt_sha256']=digest(result);return result

def validate_spec(spec):
    value=copy.deepcopy(spec);claimed=value.pop('receipt_sha256',None)
    if digest(value)!=claimed or spec['caps']!=CAPS or spec['support_frames']!=50 or spec['settle_frames']!=250 or spec['rest_frames']!=75 or spec['slow_release']!=[[x,10] for x in (.2,.4,.6,.8,1.)] or spec['allowed_support_shape_names']!=['box__9']:raise ValueError('controlled inside contract/budget changed')
    if spec['prefix_lineage']!=prefix_lineage() or spec['approved_contact_source_sha256']!=sha(CONTACT):raise ValueError('source lineage changed')
    return True
