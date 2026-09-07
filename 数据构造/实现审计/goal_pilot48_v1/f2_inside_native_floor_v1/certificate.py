import copy,hashlib,json
from pathlib import Path
import numpy as np
import trimesh
from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix
from goal_pilot48_v1.f2_inward_runtime_v3.contract import A,P,W,build_contract,digest

VERSION='f2_inside_native_envelope_piecewise_floor_v1'
APPROVAL=A/'goal_pilot48_v1/F2_INSIDE_NATIVE_FLOOR_DESIGN_APPROVAL_V1_20260907.md'
APPROVAL_SHA='87fd4deb878eb88f504b2f03330bd5f19b848bc672b03909a3b130a625b37464'
APPROVED_PROPOSAL=A/'goal_pilot48_v1/f2_controlled_suffix_runtime_v1/INSIDE_GEOMETRY_DECISION_REQUEST.md'
APPROVED_PROPOSAL_SHA='55af088c5e1fc4b7870a2d1a15897f252e3bf848a64228eb67be1c7347c89fa9'
REFERENCE=W/'Robotwin2/datasets/p48_f2_u_route_001'
FLOOR_INDICES=(4,5,7,9,12,13,14)
WALL_INDICES=(0,1,2,3,6,8,10,11)
# Numerical native-mesh boundary band, inherited from the already used F2
# native support screen. It does not alter V10 contact/speed/rest thresholds.
NATIVE_GEOMETRY_EPS_M=1e-4

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def local_signature(s):
    return digest({k:s[k] for k in ('name','role','kind','shape_local_pose','shape_scale','vertices','faces','collision_groups','contact_offset','rest_offset')})
def local_vertices(shapes):
    result=[]
    for s in shapes:
        T=matrix(s['shape_local_pose']);result.extend(np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3])
    return np.asarray(result)

def build_certificate(can_shapes,box_shapes,*,binding_sha256):
    if sha(APPROVAL)!=APPROVAL_SHA:raise ValueError('direct user design approval changed')
    if sha(APPROVED_PROPOSAL)!=APPROVED_PROPOSAL_SHA:raise ValueError('user-approved detailed proposal changed')
    if not isinstance(binding_sha256,str) or len(binding_sha256)!=64:raise ValueError('binding hash required')
    ref=load(REFERENCE/'live_capture.json')['can_shapes']
    boxref=[s for s in load(REFERENCE/'world_geometry.json')['shapes'] if s['role']=='box']
    for label,values,expected,scale in (('can',can_shapes,ref,.05),('box',box_shapes,boxref,.1)):
        if [s['name'] for s in values]!=[s['name'] for s in expected]:raise ValueError('wrong '+label+' ordered shape registry')
        by={s['name']:s for s in expected}
        for s in values:
            if not np.allclose(s['shape_scale'],[scale]*3,atol=1e-7,rtol=0):raise ValueError('wrong native scale')
            if local_signature(s)!=local_signature(by[s['name']]):raise ValueError('changed native geometry/frame/shape identity')
    if sorted(s['name'] for s in box_shapes)!=sorted('box__'+str(i) for i in range(15)):raise ValueError('expected exact15 box pieces')
    native=local_vertices(can_shapes);visual_path=P/'assets/objects/071_can/visual/base0.glb';visual=trimesh.load(visual_path,force='scene');vv=[]
    for name in visual.graph.nodes_geometry:
        T,g=visual.graph[name];m=visual.geometry[g].copy();m.apply_transform(T);m.apply_scale([.05]*3);vv.extend(m.vertices)
    vv=np.asarray(vv);lo=native.min(0);hi=native.max(0)
    visual_covered=bool(np.all(vv>=lo-1e-6) and np.all(vv<=hi+1e-6))
    if not visual_covered:raise ValueError('native envelope would omit visible can geometry')
    old=build_contract()['binding']['strict_cavity_contract']
    for s in box_shapes:
        if int(s['name'].split('__')[1]) in FLOOR_INDICES and local_vertices([s])[:,1].max()>old['lower_m'][1]:
            raise ValueError('designated floor contains material above old lower boundary; possible compound wall')
    files=[APPROVAL,APPROVED_PROPOSAL,visual_path,P/'assets/objects/071_can/collision/base0.glb',P/'assets/objects/071_can/model_data0.json',
           P/'assets/objects/062_plasticbox/collision/base2.glb',P/'assets/objects/062_plasticbox/model_data2.json',REFERENCE/'live_capture.json',REFERENCE/'world_geometry.json']
    result={'schema_version':'f2_inside_native_floor_support_shape_certificate_v1','verifier_version':VERSION,'approval_file_sha256':APPROVAL_SHA,
      'binding_sha256':binding_sha256,'can_actor_name':can_shapes[0]['actor_name'],'box_actor_name':box_shapes[0]['actor_name'],
      'can_shapes':copy.deepcopy(can_shapes),'box_shapes':copy.deepcopy(box_shapes),'can_native_center_m':((lo+hi)/2).tolist(),'can_native_half_extents_m':((hi-lo)/2).tolist(),
      'native_envelope_contains_visual':visual_covered,'native_bounds_m':[lo.tolist(),hi.tolist()],
      'unchanged_strict_lower_m':old['lower_m'],'unchanged_strict_upper_m':old['upper_m'],'floor_lower_inset_used_as_acceptance':False,
      'floor_shape_indices':list(FLOOR_INDICES),'wall_shape_indices':list(WALL_INDICES),'frame':'actor_world_poses_and_body_local_shapes',
      'native_boundary_epsilon_m':NATIVE_GEOMETRY_EPS_M,'all_robot_and_sidewall_collision_checks_must_remain':True,'blanket_box_disable_allowed':False,
      'certificate_is_not_physical_success':True,'physical_thresholds_changed':False,'files':{str(p):sha(p) for p in files}}
    result['receipt_sha256']=digest(result);return result

def reference_certificate():
    cap=load(REFERENCE/'live_capture.json');world=load(REFERENCE/'world_geometry.json')
    return build_certificate(cap['can_shapes'],[s for s in world['shapes'] if s['role']=='box'],binding_sha256=build_contract()['binding']['binding_sha256'])

def validate_certificate(c):
    v=copy.deepcopy(c);h=v.pop('receipt_sha256')
    if digest(v)!=h or c['verifier_version']!=VERSION or c['approval_file_sha256']!=APPROVAL_SHA or sha(APPROVAL)!=APPROVAL_SHA:raise ValueError('certificate/approval identity mismatch')
    if c['floor_shape_indices']!=list(FLOOR_INDICES) or c['wall_shape_indices']!=list(WALL_INDICES) or c['blanket_box_disable_allowed'] is not False:raise ValueError('floor/wall partition changed')
    old=build_contract()['binding']['strict_cavity_contract']
    if c['unchanged_strict_lower_m']!=old['lower_m'] or c['unchanged_strict_upper_m']!=old['upper_m']:raise ValueError('five original side/top bounds changed')
    if c['native_boundary_epsilon_m']!=NATIVE_GEOMETRY_EPS_M or c['physical_thresholds_changed'] is not False:raise ValueError('unapproved tolerance change')
    for p,h in c['files'].items():
        if sha(p)!=h:raise ValueError('certificate input changed')
    refs=[load(REFERENCE/'live_capture.json')['can_shapes'],[s for s in load(REFERENCE/'world_geometry.json')['shapes'] if s['role']=='box']]
    for values,reference in zip((c['can_shapes'],c['box_shapes']),refs):
        by={s['name']:local_signature(s) for s in reference}
        if [s['name'] for s in values]!=[s['name'] for s in reference] or any(local_signature(s)!=by[s['name']] for s in values):raise ValueError('certificate native geometry does not match approved ordered asset capture')
    vertices=local_vertices(c['can_shapes']);center=(vertices.min(0)+vertices.max(0))/2;half=np.ptp(vertices,axis=0)/2
    if not np.array_equal(center,c['can_native_center_m']) or not np.array_equal(half,c['can_native_half_extents_m']):raise ValueError('native envelope was altered')
    return True

def build_live_certificate(scene):
    from goal_pilot48_v1.f2_inward_runtime_v1.runtime import dependencies
    parent=dependencies()
    for actor,count in ((scene.can,26),(scene.box,15)):
        entity=actor.actor if hasattr(actor,'actor') else actor
        bodies=[entity] if hasattr(entity,'get_collision_shapes') else [v for v in entity.get_components() if hasattr(v,'get_collision_shapes')]
        if len(bodies)!=1 or len(bodies[0].get_collision_shapes())!=count:raise ValueError('ambiguous live body-local shape index registry')
    export,can=parent.world_and_can(scene,scene.robot.left_planner)
    binding=scene._cmf_f2_asset_binding_v3
    return build_certificate(can,[s for s in export['shapes'] if s['role']=='box'],binding_sha256=binding['binding_sha256'])
