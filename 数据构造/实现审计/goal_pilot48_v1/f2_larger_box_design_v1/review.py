"""Check only the one analytically selected bigger-box candidate."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from goal_pilot48_v1.f2_inside_preinsert_failure_review_v1.analyze import collision_object,hand_parts,goal_solver,matrix,pose,negative_pairs,sha,digest,A,W,D
from .design import derive,body_vertices,world_vertices,FLOORS

def record(name,vertices,faces):return {'name':name,'vertices':np.asarray(vertices),'faces':np.asarray(faces,dtype=int)}
def intersects(first,second):
    from mplib.collision_detection import fcl
    if np.any(first['vertices'].max(0)<second['vertices'].min(0)) or np.any(second['vertices'].max(0)<first['vertices'].min(0)):return False
    if fcl.collide(collision_object(first,np.eye(4)),collision_object(second,np.eye(4))).is_collision():return True
    for a,b in ((first,second),(second,first)):
        equations=ConvexHull(b['vertices']).equations
        if np.any(np.all(a['vertices']@equations[:,:3].T+equations[:,3]<-1e-10,axis=1)):return True
    return False
def swept(shape,height):
    vertices=np.vstack([shape['vertices'],shape['vertices']+[0,0,height]]);hull=ConvexHull(vertices)
    return record(shape['name'],vertices,hull.simplices)

def review():
    d=derive();c=d['context'];m=c['model'];target=d['can_target'];box=[record(*x) for x in d['box_pieces']]
    others=[record(s['name'],world_vertices(s,m['base']),s['faces']) for s in m['world']['shapes'] if s['role']!='box'];world=others+box
    # Keep actual grasp orientation; first-contact height was solved from
    # triangle equations, not by evaluating candidate heights.
    reported_grasp=np.linalg.inv(matrix(c['eef']))@matrix(c['can']);goal=target@np.linalg.inv(reported_grasp);G=goal_solver(c,pose(goal));B=matrix(m['base'])
    hand=[]
    for link,s,T in hand_parts(c,G):
        T=B@T;hand.append(record(link,np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3],s['faces']))
    can=[record(s['name'],body_vertices(s)@target[:3,:3].T+target[:3,3],s['faces']) for s in c['certificate']['can_shapes']]
    hand_hits=[];can_forbidden=[];floor_band_pairs=[]
    for shape in hand:
        extrusion=swept(shape,.03)
        for other in world:
            if intersects(extrusion,other):hand_hits.append(shape['name']+'/'+other['name'])
    for shape in can:
        extrusion=swept(shape,.03);raised=record(extrusion['name'],extrusion['vertices']+[0,0,1e-4],extrusion['faces'])
        for other in world:
            if not intersects(extrusion,other):continue
            isfloor=other['name'].startswith('box__') and int(other['name'].split('__')[1]) in FLOORS
            if isfloor and not intersects(raised,other):floor_band_pairs.append(shape['name']+'/'+other['name'])
            else:can_forbidden.append(shape['name']+'/'+other['name'])
    initial_anchor=W/'Robotwin2/datasets/p48_f2_prefix_clearance_001/reference_anchor.json';initial_pose=matrix(json.loads(initial_anchor.read_text())['actor_states']['main_can']['pose']);initial=[]
    for shape in c['certificate']['can_shapes']:
        initial.append(record(shape['name'],body_vertices(shape)@initial_pose[:3,:3].T+initial_pose[:3,3],shape['faces']))
    initial_hits=[s['name']+'/'+b['name'] for s in initial for b in box if intersects(s,b)]
    box_facility_hits=[s['name']+'/'+o['name'] for s in box for o in others if (o['name'].startswith('scale__') or o['name'].startswith('stand__')) and intersects(s,o)]
    # Original actually fitted sphere profile, mapped to this sole goal.
    from goal_pilot48_v1.f2_inside_preinsert_failure_review_v1.analyze import root_transform,summarize
    balls=[];links=[]
    for link in ('fl_link6','fl_link7','fl_link8','attached_can'):
        T=B@G if link=='attached_can' else B@G@np.linalg.inv(c['rootE'])@root_transform(link,c['named'])
        for sphere in c['kin']['collision_spheres'][link]:balls.append([*(T[:3,:3]@np.asarray(sphere['center'])+T[:3,3]),sphere['radius']+c['kin']['collision_sphere_buffer']]);links.append(link)
    export={'shapes':[{'name':s['name'],'vertices':s['vertices'].tolist(),'faces':s['faces'].tolist(),'solver_pose':[0,0,0,1,0,0,0]} for s in world]}
    pairs=negative_pairs(np.asarray(balls),links,export);robot_pairs=[p for p in pairs if p['link']!='attached_can'];can_pairs=[p for p in pairs if p['link']=='attached_can']
    raw_files=[D/'inside_result.json',D/'model_010_carried_full.json',D/'qualification_trace.npz',initial_anchor,
      A/'goal_pilot48_v1/f2_inside_preinsert_failure_review_v1/DIAGNOSIS_001.json']
    source_files=list(Path(__file__).parent.glob('*.py'))+[A/'goal_pilot48_v1/f2_inside_preinsert_failure_review_v1/analyze.py',A/'f3_model_replay_v1/kinematics_cpu.py',A/'f2_f3_model_bridge_v1_1/transforms.py']
    r={'schema_version':'f2_one_uniform_larger_box_CPU_design_review_v1',**d['report'],'new_current_or_scene_generated':False,
      'predicted_uniform_box_native_vertices_not_fresh_Sapien_capture':True,'upright_eef_target':pose(goal),
      'whole_30mm_vertical_insertion_hand_native_intersections':hand_hits,'whole_30mm_vertical_insertion_can_forbidden_intersections':can_forbidden,
      'can_native_floor_endpoint_numeric_band_pairs':floor_band_pairs,'initial_can_new_box_intersections':initial_hits,
      'new_box_other_facility_native_intersections':box_facility_hits,'unchanged_buffered_hand_endpoint_pairs':summarize(robot_pairs),
      'unchanged_buffered_can_endpoint_pairs':summarize(can_pairs),'new_model_support_pair_design_required':True,
      'old_box9_contact_certificate_not_reused':True,'native_necessary_checks_pass':bool(all(d['report']['can_five_boundaries'].values()) and d['report']['table_xy_footprint_pass'] and not hand_hits and not can_forbidden and not initial_hits and not box_facility_hits),
      'robot_endpoint_model_necessary_check_pass':not robot_pairs,'whole_arm_IK_or_path_proven':False,
      'new_solver_scene_action_GPU_calls':0,'sources':{str(p):sha(p) for p in source_files+raw_files}}
    r['receipt_sha256']=digest(r);return r

if __name__=='__main__':
    r=review()
    with Path(__file__).with_name('CPU_REVIEW_001.json').open('x',encoding='utf-8') as f:json.dump(r,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print({k:r[k] for k in ('receipt_sha256','uniform_factor','native_necessary_checks_pass','robot_endpoint_model_necessary_check_pass','whole_30mm_vertical_insertion_hand_native_intersections','whole_30mm_vertical_insertion_can_forbidden_intersections','unchanged_buffered_hand_endpoint_pairs','unchanged_buffered_can_endpoint_pairs')})
