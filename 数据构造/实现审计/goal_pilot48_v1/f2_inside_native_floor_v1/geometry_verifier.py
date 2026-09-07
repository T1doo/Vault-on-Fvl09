"""Native geometry boundary verifier, separate from real support/stability."""
import itertools,copy
import numpy as np
import transforms3d as t3d
from .certificate import validate_certificate,matrix,VERSION,digest

class GeometryVerifier:
    def __init__(self,certificate):
        validate_certificate(certificate);self.c=certificate
        from mplib import Pose
        from mplib.collision_detection import fcl
        from scipy.spatial import ConvexHull
        self.Pose=Pose;self.fcl=fcl;self.box=[];self.can=[];self.hulls={}
        for target,shapes in ((self.box,certificate['box_shapes']),(self.can,certificate['can_shapes'])):
            for s in shapes:
                mesh=fcl.BVHModel();vertices=np.asarray(s['vertices']);faces=np.asarray(s['faces'],dtype=np.int32)
                mesh.begin_model(len(faces),len(vertices));mesh.add_sub_model(vertices,faces);mesh.end_model()
                self.hulls[s['name']]=ConvexHull(vertices).equations
                target.append((s,mesh))
        self.cache={}

    def _object(self,mesh,T):return self.fcl.CollisionObject(mesh,self.Pose(T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])))

    def _material_intersection(self,cs,cm,canT,bs,bm,boxT):
        co=self._object(cm,canT);bo=self._object(bm,boxT)
        if self.fcl.collide(co,bo).is_collision():return True
        # BVH surface collision alone misses one closed convex part wholly
        # contained in the other. Check both volume-containment directions.
        for first,T1,second,T2 in ((cs,canT,bs,boxT),(bs,boxT,cs,canT)):
            T=np.linalg.inv(T2)@T1;points=np.asarray(first['vertices'])@T[:3,:3].T+T[:3,3];eq=self.hulls[second['name']]
            if np.any(np.all(points@eq[:,:3].T+eq[:,3]<-1e-10,axis=1)):return True
        return False

    def evaluate(self,can_world_pose,box_world_pose,*,binding_sha256,frame='world',can_scale=(.05,.05,.05),box_scale=(.1,.1,.1)):
        if frame!='world':raise ValueError('world actor poses required; implicit frame conversion prohibited')
        if binding_sha256!=self.c['binding_sha256']:raise ValueError('wrong current/layout binding')
        if not np.array_equal(can_scale,[.05]*3) or not np.array_equal(box_scale,[.1]*3):raise ValueError('wrong asset scale')
        p=np.asarray(can_world_pose,dtype=float);b=np.asarray(box_world_pose,dtype=float)
        if p.shape!=(7,) or b.shape!=(7,) or not np.isfinite(np.r_[p,b]).all() or abs(np.linalg.norm(p[3:])-1)>1e-5 or abs(np.linalg.norm(b[3:])-1)>1e-5:raise ValueError('invalid actor pose')
        key=tuple(np.r_[p,b])
        if key in self.cache:return copy.deepcopy(self.cache[key])
        relative=np.linalg.inv(matrix(b))@matrix(p);center=np.asarray(self.c['can_native_center_m']);half=np.asarray(self.c['can_native_half_extents_m'])
        corners=np.asarray([center+half*np.asarray(sign) for sign in itertools.product((-1,1),repeat=3)])
        local=corners@relative[:3,:3].T+relative[:3,3];lo=local.min(0);hi=local.max(0)
        lower=np.asarray(self.c['unchanged_strict_lower_m']);upper=np.asarray(self.c['unchanged_strict_upper_m'])
        checks={'X_sides':bool(lo[0]>=lower[0] and hi[0]<=upper[0]),'Z_sides':bool(lo[2]>=lower[2] and hi[2]<=upper[2]),'top':bool(hi[1]<=upper[1])}
        eps=self.c['native_boundary_epsilon_m'];near=set();floor_penetration=set();wall_hit=set();raw_hits=set();nearest=[]
        for bs,bm in self.box:
            index=int(bs['name'].split('__')[1]);boxT=matrix(bs['shape_local_pose']);bo=self._object(bm,boxT)
            for cs,cm in self.can:
                T=relative@matrix(cs['shape_local_pose']);co=self._object(cm,T)
                hit=self._material_intersection(cs,cm,T,bs,bm,boxT)
                if index in self.c['wall_shape_indices']:
                    if hit:wall_hit.add(index)
                    continue
                if hit:
                    raw_hits.add(index);near.add(index)
                    raised=T.copy();raised[1,3]+=eps
                    if self._material_intersection(cs,cm,raised,bs,bm,boxT):floor_penetration.add(index)
                else:
                    gap=float(self.fcl.distance(co,bo).min_distance)
                    if gap>=0 and gap<=eps:
                        near.add(index)
                        # Near the underside is not supporting contact. This
                        # must also be checked for positive-gap manifolds,
                        # not just already intersecting surface pairs.
                        raised=T.copy();raised[1,3]+=eps
                        if self._material_intersection(cs,cm,raised,bs,bm,boxT):floor_penetration.add(index)
        checks.update(no_sidewall_material_intersection=not wall_hit,no_floor_penetration_beyond_native_numeric_band=not floor_penetration,near_actual_floor_surface=bool(near))
        result={'schema_version':'f2_inside_native_piecewise_floor_geometry_result_v1','verifier_version':VERSION,'certificate_sha256':self.c['receipt_sha256'],
          'checks':checks,'pass':all(checks.values()),'local_native_envelope_lower':lo.tolist(),'local_native_envelope_upper':hi.tolist(),
          'floor_geometry_candidate_indices':sorted(near),'floor_intersection_indices':sorted(raw_hits),'floor_penetration_indices':sorted(floor_penetration),'wall_intersection_indices':sorted(wall_hit),
          'floor_penetration_test':'native intersections must clear under box-local +Y numerical epsilon; not sphere-buffer removal',
          'physical_support_proven':False,'can_world_pose':p.tolist(),'box_world_pose':b.tolist()}
        result['receipt_sha256']=digest(result);self.cache[key]=copy.deepcopy(result);return result

    def synthetic_contact_geometry(self,can_world_pose,box_world_pose):
        """CPU-test contact location only, never a real simulator contact receipt."""
        R=np.linalg.inv(matrix(box_world_pose))@matrix(can_world_pose)
        for bs,bm in self.box:
            index=int(bs['name'].split('__')[1])
            if index not in self.c['floor_shape_indices']:continue
            bo=self._object(bm,matrix(bs['shape_local_pose']))
            for ci,(cs,cm) in enumerate(self.can):
                result=self.fcl.collide(self._object(cm,R@matrix(cs['shape_local_pose'])),bo,self.fcl.CollisionRequest(enable_contact=True))
                if result.is_collision() and result.num_contacts():
                    contact=result.get_contacts()[0];B=matrix(box_world_pose)
                    return {'can_shape_index':ci,'box_shape_index':index,'position_world':(B[:3,:3]@contact.pos+B[:3,3]).tolist(),'normal_world':(B[:3,:3]@contact.normal).tolist(),'synthetic_CPU_fixture':True}
        raise ValueError('no native boundary contact for CPU fixture')
