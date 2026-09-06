"""Read-only helper for an already-created fresh SAPIEN actor; never creates a scene."""
import numpy as np
from scipy.spatial.transform import Rotation

def capture_mass_properties(actor):
    entity=getattr(actor,'actor',actor)
    candidates=[c for c in entity.get_components() if all(callable(getattr(c,n,None)) for n in
        ('get_mass','get_inertia','get_cmass_local_pose'))]
    if len(candidates)!=1:raise ValueError('expected exactly one rigid-body mass component')
    c=candidates[0];local=c.get_cmass_local_pose();pose=entity.get_pose()
    mass=float(c.get_mass());inertia=np.asarray(c.get_inertia(),dtype=float)
    position=np.asarray(local.p,dtype=float);quat=np.asarray(local.q,dtype=float)
    if mass<=0 or inertia.shape!=(3,) or np.any(inertia<=0) or not np.all(np.isfinite(np.r_[mass,inertia,position,quat])):
        raise ValueError('invalid measured rigid-body mass properties')
    world=Rotation.from_quat(np.asarray(pose.q)[[1,2,3,0]]).apply(position)+np.asarray(pose.p)
    return {'schema_version':'p48_actual_rigid_mass_properties_v1','actor_name':entity.get_name(),
        'component_type':type(c).__name__,'mass_kg':mass,'principal_inertia_kg_m2':inertia.tolist(),
        'cmass_local_pose':np.r_[position,quat].tolist(),'com_world':world.tolist(),
        'source':'actual PhysxRigidBodyComponent.get_mass/get_inertia/get_cmass_local_pose',
        'read_only':True,'new_scene_created':False,'proxy_COM_used':False}
