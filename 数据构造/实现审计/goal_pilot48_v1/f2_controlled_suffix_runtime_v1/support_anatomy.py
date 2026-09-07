"""CPU native shape/floor audit. No planner, scene or physical execution."""
import copy,json,hashlib,sys
from pathlib import Path
import numpy as np
import transforms3d as t3d
from goal_pilot48_v1.f2_inward_runtime_v3.contract import A,P,W,build_contract,digest
from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix
OUT=Path(__file__).parent;D=W/'Robotwin2/datasets/p48_f2_u_route_001'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def audit():
    from mplib import Pose
    from mplib.collision_detection import fcl
    from controlled_multi_future.geometry import compose_pose,obb_inside_local_cavity
    cap=load(D/'live_capture.json');world=load(D/'world_geometry.json');B=matrix(cap['base']);c=build_contract()
    def vertices(s):
        T=B@matrix(s['solver_pose']);return np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3]
    anatomy=[]
    for s in world['shapes']:
        if s['role'] not in ('box','scale'):continue
        v=vertices(s);anatomy.append({'shape':s['name'],'role':s['role'],'min_world_xyz':v.min(0).tolist(),'max_world_xyz':v.max(0).tolist(),
          'z_thickness_m':float(np.ptp(v[:,2])),'source_geometry_sha256':s['geometry_sha256']})
    def bv(s):
        geom=fcl.BVHModel();v=np.asarray(s['vertices']);f=np.asarray(s['faces'],dtype=np.int32);geom.begin_model(len(f),len(v));geom.add_sub_model(v,f);geom.end_model();return geom
    boxes=[]
    for s in world['shapes']:
        if s['role']!='box':continue
        T=B@matrix(s['solver_pose']);boxes.append((s['name'],fcl.CollisionObject(bv(s),Pose(T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])))))
    can=[(s,bv(s)) for s in cap['can_shapes']]
    target=np.asarray(c['frozen_strict_cavity_target_actor_pose']).copy()
    native_test_calls=0
    def hits(drop):
        nonlocal native_test_calls
        native_test_calls+=1
        pose=target.copy();pose[2]-=drop;result=[]
        for s,geom in can:
            T=matrix(pose)@matrix(s['shape_local_pose']);obj=fcl.CollisionObject(geom,Pose(T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])))
            for name,box in boxes:
                r=fcl.collide(obj,box,fcl.CollisionRequest())
                if r.is_collision():result.append(name)
        return sorted(set(result))
    if hits(0) or not hits(.04):raise ValueError('native vertical contact bracket unexpected')
    lo,hi=0.,.04
    for _ in range(18):
        mid=(lo+hi)/2
        if hits(mid):hi=mid
        else:lo=mid
    contact=target.copy();contact[2]-=hi;metadata=load(P/'assets/objects/071_can/model_data0.json');center=np.asarray(metadata['center'])*.05;half=np.asarray(metadata['extents'])*.025
    box_shape=next(s for s in world['shapes'] if s['role']=='box');boxpose=box_shape['actor_world_pose'];cavity=c['binding']['strict_cavity_contract']
    fit=obb_inside_local_cavity(compose_pose(contact,[*center,1,0,0,0]),half,boxpose,cavity['lower_m'],cavity['upper_m'])
    strict_floor=compose_pose(boxpose,[0,cavity['lower_m'][1],0,1,0,0,0])[2]
    floor_ids=[r['shape'] for r in anatomy if r['role']=='box' and r['max_world_xyz'][2]<=strict_floor+1e-6]
    wall_ids=[r['shape'] for r in anatomy if r['role']=='box' and r['shape'] not in floor_ids]
    # Scale's highest shape is a cap; classify, don't silently enable a mask.
    scale_rows=[r for r in anatomy if r['role']=='scale'];top=max(scale_rows,key=lambda r:r['max_world_xyz'][2])
    result={'schema_version':'F2_native_support_anatomy_CPU_v1','shapes':anatomy,
      'inside':{'original_target_actor_pose':target.tolist(),'first_native_contact_drop_interval_m':[lo,hi],'first_contact_actor_pose':contact.tolist(),
        'first_contact_shape_ids':hits(hi),'strict_cavity_floor_world_z_m':float(strict_floor),'low_floor_shape_ids':floor_ids,'sidewall_shape_ids_must_retain':wall_ids,
        'strict_inside_at_first_native_contact':fit,'controlled_target_is_not_native_supported':True,
        'support_target_revision_implemented':False,'blanket_box_collision_disable_allowed':False,
        'execution_ready':False,'blocker':'original mid-cavity target has no support; contact-height pose must satisfy unchanged strict verifier before any physical suffix'},
      'on':{'highest_native_shape':top,'other_scale_shapes_retained':True,'single_cap_shape_identified':True,'support_pair_mask_enabled':False,
        'execution_ready':False,'remaining_gate':'top-face footprint, fresh supported target and released/open-gripper model must be bound before execution'},
      'native_geometry_queries':{'vertical_contact_tests':native_test_calls,'fixed_bisection_steps':18,'solver_problems':0,'scenes':0,'actions':0},
      'input_files':{str(p):sha(p) for p in (D/'live_capture.json',D/'world_geometry.json',P/'assets/objects/071_can/model_data0.json')},
      'physical_Gates_or_tolerances_changed':False}
    result['receipt_sha256']=digest(result);return result

if __name__=='__main__':
    r=audit()
    from realization_utf8_io_v1 import write_new
    write_new(OUT/'anatomy.json',r);print(json.dumps({'inside':r['inside'],'on':r['on'],'receipt':r['receipt_sha256']},ensure_ascii=False,indent=2))
