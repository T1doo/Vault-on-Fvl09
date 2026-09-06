"""CPU native-mesh fl_link3/fl_link5 checker, no Scene or CUDA."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
import transforms3d as t3d
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');D=Path('/nfs_share/lijunhui/Robotwin2/datasets')
sys.path.insert(0,str(A/'f3_model_replay_v1'))
from kinematics_cpu import collision_description,root_transform,URDF
SOURCE=D/'f3_model_conformance_v1/f3-final-pose-v3-r3063/initial_geometry.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def model():
    from mplib.collision_detection import fcl
    s=json.loads(SOURCE.read_text(encoding='utf-8'));out={}
    for i in (3,5):
        assert collision_description('fl_link'+str(i))==collision_description('fr_link'+str(i))
        shapes=[x for x in s['shapes'] if x['role']=='fr_link'+str(i)];assert shapes
        out[i]=[]
        for x in shapes:
            g=fcl.BVHModel();v=np.array(x['vertices']);f=np.array(x['faces'],dtype=np.int32)
            g.begin_model(len(f),len(v));g.add_sub_model(v,f);g.end_model()
            p=x['shape_local_pose'];T=t3d.affines.compose(p[:3],t3d.quaternions.quat2mat(p[3:]),[1,1,1]);out[i].append((g,T))
    return out
def inspect_q(q,models):
    import mplib
    from mplib.collision_detection import fcl
    objects={}
    for i in (3,5):
        objects[i]=[]
        for g,local in models[i]:
            T=root_transform('fl_link'+str(i),q)@local
            objects[i].append(fcl.CollisionObject(g,mplib.Pose(T[:3,3],t3d.quaternions.mat2quat(T[:3,:3]))))
    hits=[];dist=[]
    for a in objects[3]:
        for b in objects[5]:
            hits.append(fcl.collide(a,b).is_collision());dist.append(float(fcl.distance(a,b).min_distance))
    return {'intersects':any(hits),'minimum_distance_m':min(dist),'negative_distance_not_penetration_depth':True}
def check_controls(positions,solver_joint_names,actual_names,actual_qpos):
    pos=np.asarray(positions)
    if pos.ndim!=2 or pos.shape[1]!=len(solver_joint_names) or pos.shape[0]==0:
        raise ValueError('controls must contain at least one correctly dimensioned position row')
    if set(solver_joint_names)!={'fl_joint'+str(i) for i in range(1,7)}:raise ValueError('not exact six named left arm controls')
    if len(actual_names)!=len(actual_qpos) or not np.isfinite(actual_qpos).all():raise ValueError('invalid full actual joint state')
    if not np.isfinite(pos).all():raise ValueError('nonfinite controls')
    if len(set(actual_names))!=len(actual_names):raise ValueError('ambiguous full joint names')
    named=dict(zip(actual_names,map(float,actual_qpos)));models=model();rows=[]
    for i,q in enumerate(pos):
        state={**named,**dict(zip(solver_joint_names,map(float,q)))};rows.append({'sample_index':i,**inspect_q(state,models)})
    return {'schema_version':'p48_native_fl3_fl5_controls_gate_v1','pass':not any(x['intersects'] for x in rows),'rows':rows,
        'checked_samples':len(rows),'scope':'only observed fl_link3/fl_link5 pair, discrete positions; not entire robot or continuous path',
        'source_geometry_sha256':sha(SOURCE),'URDF_sha256':sha(URDF),'thresholds_changed':False}
