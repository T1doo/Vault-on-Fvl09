"""Native asset/hand-only CPU construction, no simulator or planner creation."""
import copy,json,sys
from pathlib import Path
import numpy as np
import transforms3d as t3d
import mplib
from mplib.collision_detection import fcl
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';D=W/'Robotwin2/datasets'
sys.path.insert(0,str(A/'f3_model_replay_v1'))
from kinematics_cpu import root_transform,link_world,collision_description
def matrix(p):return t3d.affines.compose(p[:3],t3d.quaternions.quat2mat(p[3:]),[1,1,1])
def pose(T):return np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist()
def mesh(s):
    v=np.asarray(s['vertices']);f=np.asarray(s['faces'],dtype=np.int32);g=fcl.BVHModel();g.begin_model(len(f),len(v));g.add_sub_model(v,f);g.end_model();return g
def collision(a,Ta,b,Tb,contacts=False):
    ao=fcl.CollisionObject(a,mplib.Pose(Ta[:3,3],t3d.quaternions.mat2quat(Ta[:3,:3])));bo=fcl.CollisionObject(b,mplib.Pose(Tb[:3,3],t3d.quaternions.mat2quat(Tb[:3,:3])))
    if contacts:
        r=fcl.collide(ao,bo,fcl.CollisionRequest(num_max_contacts=100,enable_contact=True))
        return {'hit':r.is_collision(),'points':[{'position':np.asarray(p.pos).reshape(3).tolist(),'normal':np.asarray(p.normal).reshape(3).tolist()} for p in r.get_contacts()]}
    return fcl.collide(ao,bo).is_collision()
class Geometry:
    def __init__(self):
        self.capture_path=D/'f3_model_conformance_v1/f3-final-pose-v3-r3063/initial_geometry.json'
        self.capture=json.loads(self.capture_path.read_text(encoding='utf-8'))
        self.model_path=D/'p48_f3_one_sided_micro_001/postclose_attached_model.json'
        self.bottle_shapes=json.loads(self.model_path.read_text(encoding='utf-8'))['native_bottle_shapes']
        self.bottles=[(mesh(s),matrix(s['shape_local_pose']),s['name']) for s in self.bottle_shapes]
        self.hands={};self.arm_shapes={}
        for i in range(1,9):
            if collision_description('fl_link'+str(i))!=collision_description('fr_link'+str(i)):raise ValueError('unverified left/right native geometry alias')
            shapes=[s for s in self.capture['shapes'] if s['role']=='fr_link'+str(i)]
            self.arm_shapes[i]=[(mesh(s),matrix(s['shape_local_pose'])) for s in shapes]
        self.world=[(mesh(s),matrix(s['actor_world_pose'])@matrix(s['shape_local_pose']),s['name'],s['role']) for s in self.capture['shapes'] if s['role'] in ('table','pad')]
        self.q={f'fl_joint{i}':0. for i in range(1,9)}
        self.bottle_pose=[-.18,-.06,.75,2**-.5,2**-.5,0.,0.]
        self.B=matrix(self.bottle_pose)
    def hand(self,actual,opening):
        q={**self.q,'fl_joint7':opening,'fl_joint8':opening};F=np.linalg.inv(root_transform('fl_link6',q));T=matrix(actual);result=[]
        for i in (6,7,8):
            for g,local in self.arm_shapes[i]:result.append((g,T@F@root_transform('fl_link'+str(i),q)@local,'fl_link'+str(i)))
        return result
    def pairs(self,actual,opening):
        out=[]
        for g,T,name in self.hand(actual,opening):
            for b,local,bname in self.bottles:
                c=collision(g,T,b,self.B@local,True)
                if c['hit']:out.append({'hand':name,'bottle_shape':bname,**c})
        return out
    def first_touch(self,actual,finger):
        def hit(q):return any(p['hand']==finger for p in self.pairs(actual,q))
        if hit(.045):return {'open_clear':False}
        if not hit(.0175):return {'open_clear':True,'contact_reachable':False}
        lo,hi=.0175,.045
        for _ in range(24):
            mid=(lo+hi)/2
            if hit(mid):lo=mid
            else:hi=mid
        ps=[p for p in self.pairs(actual,lo-1e-7) if p['hand']==finger]
        points=[v for p in ps for v in p['points']]
        return {'open_clear':True,'contact_reachable':True,'joint_qpos_first_touch_m':lo,
            'bottle_shapes_at_touch':sorted({p['bottle_shape'] for p in ps}),'contacts':points,
            'contact_local_y_minmax_m':[min(v['position'][2]-.75 for v in points),max(v['position'][2]-.75 for v in points)] if points else None}
    def support_clear(self,actual,opening):
        return [{'hand':n,'world':name,'role':role} for g,T,n in self.hand(actual,opening) for b,B,name,role in self.world if collision(g,T,b,B)]
