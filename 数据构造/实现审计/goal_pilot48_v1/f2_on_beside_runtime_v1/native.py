"""All discrete native can/world samples, no global obstacle toggle."""
import numpy as np
from scipy.spatial import ConvexHull
from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix,pose

class NativeWorld:
    def __init__(self,export,can,base):
        from mplib import Pose
        from mplib.collision_detection import fcl
        self.Pose,self.fcl=Pose,fcl;self.world=[];self.can=[]
        for entries,shapes in ((self.world,export['shapes']),(self.can,can)):
            for s in shapes:
                v=np.asarray(s['vertices']);faces=np.asarray(s['faces'],dtype=np.int32)
                mesh=fcl.BVHModel();mesh.begin_model(len(faces),len(v));mesh.add_sub_model(v,faces);mesh.end_model()
                T=matrix(base)@matrix(s['solver_pose']) if entries is self.world else matrix(s['shape_local_pose'])
                entries.append((s,mesh,ConvexHull(v).equations,T))

    def intersect(self,a,Ta,b,Tb):
        sa,ma,ha,_=a;sb,mb,hb,_=b
        pa,pb=pose(Ta),pose(Tb)
        if self.fcl.collide(self.fcl.CollisionObject(ma,self.Pose(pa[:3],pa[3:])),self.fcl.CollisionObject(mb,self.Pose(pb[:3],pb[3:]))).is_collision():return True
        for s,T1,T2,h in ((sa,Ta,Tb,hb),(sb,Tb,Ta,ha)):
            T=np.linalg.inv(T2)@T1;p=np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3]
            if np.any(np.all(p@h[:,:3].T+h[:,3]<-1e-10,axis=1)):return True
        return False

    def screen(self,poses,*,table_support):
        failures=[];count=0
        for i,p in enumerate(poses):
            for a in self.can:
                Ta=matrix(p)@a[3];av=np.asarray(a[0]['vertices'])@Ta[:3,:3].T+Ta[:3,3]
                for b in self.world:
                    Tb=b[3];bv=np.asarray(b[0]['vertices'])@Tb[:3,:3].T+Tb[:3,3]
                    if np.any(av.max(0)<bv.min(0)) or np.any(bv.max(0)<av.min(0)):continue
                    count+=1
                    if not self.intersect(a,Ta,b,Tb):continue
                    if table_support and b[0]['name']=='table__0':
                        lifted=Ta.copy();lifted[2,3]+=1e-4
                        if not self.intersect(a,lifted,b,Tb):continue
                    failures.append({'sample':i,'can_shape':a[0]['name'],'obstacle':b[0]['name']})
        return {'pass':bool(poses) and not failures,'samples':len(poses),'narrow_pair_checks':count,'failures':failures,
          'only_native_table_support_numeric_band':table_support,'scale_exception':False,'continuous_sweep_proven':False,'physical_success':False}
