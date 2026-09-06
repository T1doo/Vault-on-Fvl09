"""Actual SAPIEN collision shapes, never metadata-centre AABB substitution."""
import hashlib,json
import numpy as np
import transforms3d as t3d
from transforms import world_obstacle_to_solver_frame

def pose7(obj):
    p=obj.get_pose();return np.r_[np.asarray(p.p),np.asarray(p.q)].astype(float)
def matrix(p):return t3d.affines.compose(p[:3],t3d.quaternions.quat2mat(p[3:]),[1,1,1])
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()

def capture_actor_geometry(actor,role,planner,arm='left'):
    import trimesh
    entity=actor.actor if hasattr(actor,'actor') else actor
    bodies=[entity] if hasattr(entity,'get_collision_shapes') else [c for c in entity.get_components() if hasattr(c,'get_collision_shapes')]
    actor_pose=pose7(entity);world_to_solver=matrix(world_obstacle_to_solver_frame(planner,[0,0,0,1,0,0,0],arm))
    shapes=[]
    for body in bodies:
        body_vertices=[];body_shapes=[]
        for shape in body.get_collision_shapes():
            kind=type(shape).__name__;local=shape.get_local_pose();local_pose=np.r_[local.p,local.q].astype(float)
            if kind=='PhysxCollisionShapeBox':
                mesh=trimesh.creation.box(extents=2*np.asarray(shape.get_half_size(),dtype=float));vertices=np.asarray(mesh.vertices);faces=np.asarray(mesh.faces);scale=np.ones(3)
            elif kind in ('PhysxCollisionShapeConvexMesh','PhysxCollisionShapeTriangleMesh'):
                vertices=np.asarray(shape.get_vertices(),dtype=float);faces=np.asarray(shape.get_triangles(),dtype=np.int64);scale=np.asarray(shape.get_scale(),dtype=float)
            else:raise ValueError('unsupported actual collision shape: '+kind)
            if vertices.ndim!=2 or vertices.shape[1]!=3 or faces.ndim!=2 or faces.shape[1]!=3:raise ValueError('collision mesh shape')
            transform=world_to_solver@matrix(actor_pose)@matrix(local_pose)
            scaled_vertices=vertices*scale
            world_transform=matrix(actor_pose)@matrix(local_pose)
            body_vertices.append((world_transform[:3,:3]@scaled_vertices.T).T+world_transform[:3,3])
            solver_pose=np.r_[transform[:3,3],t3d.quaternions.mat2quat(transform[:3,:3])]
            value={'name':role+'__'+str(len(shapes)),'role':role,'actor_name':entity.get_name(),'kind':kind,
                'actor_world_pose':actor_pose.tolist(),'shape_local_pose':local_pose.tolist(),'shape_scale':scale.tolist(),
                'source_vertices_sha256':hashlib.sha256(vertices.tobytes()).hexdigest(),'source_faces_sha256':hashlib.sha256(faces.tobytes()).hexdigest(),
                'vertices':scaled_vertices.tolist(),'faces':faces.tolist(),'solver_pose':solver_pose.tolist(),
                'contact_offset':float(shape.get_contact_offset()),'rest_offset':float(shape.get_rest_offset()),'collision_groups':list(shape.get_collision_groups()),
                'transform_rule':'solver_from_world @ actor_world @ shape_local @ scaled_vertex; no gripper tool transform'}
            body_shapes.append(value)
        if body_vertices:
            points=np.vstack(body_vertices);computed=np.stack((points.min(axis=0),points.max(axis=0)))
            actual=np.asarray(body.compute_global_aabb_tight(),dtype=float)
            error=float(np.max(np.abs(computed-actual)))
            if error>1e-4:raise ValueError('collision scale/local-pose/AABB mismatch for '+role+': '+str(error))
            for value in body_shapes:
                value['body_global_aabb_max_error_m']=error;value['body_global_aabb_source']='SAPIEN compute_global_aabb_tight'
                value['geometry_sha256']=digest(value);shapes.append(value)
    return shapes

def capture_scene_collision_geometry(scene,planner,*,include_right_arm=True):
    actors=[('table',scene.table),('pad',scene.pad),('bottle',scene.bottle)]
    if include_right_arm:
        actors += [(link.get_name(),link) for link in scene.robot.right_entity.get_links() if link.get_name().startswith('fr_link')]
    shapes=[]
    for role,actor in actors:
        captured=capture_actor_geometry(actor,role,planner)
        if role in ('table','pad','bottle') and not captured:raise ValueError('missing mandatory collision geometry: '+role)
        shapes.extend(captured)
    return {'schema_version':'cmf_actual_collision_mesh_export_v1','shapes':shapes,'geometry_sha256':digest(shapes)}

def make_world(export):
    from curobo.geom.types import Mesh,WorldConfig
    return WorldConfig(mesh=[Mesh(name=s['name'],pose=s['solver_pose'],vertices=s['vertices'],faces=s['faces']) for s in export['shapes']])

def closest_pairs(model,q,export):
    import trimesh
    spheres=model.get_state(q).get_link_spheres().detach().cpu().numpy()[0]
    cfg=model.kinematics_config;indices=cfg.link_sphere_idx_map.detach().cpu().numpy();names={v:k for k,v in cfg.link_name_to_idx_map.items()}
    valid=spheres[:,3]>0;rows=[]
    for shape in export['shapes']:
        mesh=trimesh.Trimesh(vertices=shape['vertices'],faces=shape['faces'],process=True)
        mesh.apply_transform(matrix(shape['solver_pose']))
        signed=trimesh.proximity.signed_distance(mesh,spheres[valid,:3]);clearance=-signed-spheres[valid,3]
        selected=int(np.argmin(clearance));idx=int(np.flatnonzero(valid)[selected]);value=float(clearance[selected])
        rows.append({'obstacle':shape['name'],'role':shape['role'],'robot_link':names[int(indices[idx])],'sphere_index':idx,
            'sphere_to_mesh_clearance_m':value,'sphere_radius_includes_configured_buffer':True,
            'obstacle_contact_offset_m':shape['contact_offset'],'within_physics_contact_offset':value<=shape['contact_offset']})
    return sorted(rows,key=lambda x:x['sphere_to_mesh_clearance_m'])

def exact_shape_pairs(robot_shapes,world_shapes):
    import mplib
    from mplib.collision_detection import fcl
    def collision_object(shape):
        mesh=fcl.BVHModel();mesh.begin_model(len(shape['faces']),len(shape['vertices']))
        mesh.add_sub_model(np.asarray(shape['vertices'],dtype=float),np.asarray(shape['faces'],dtype=np.int32));mesh.end_model()
        pose=shape['solver_pose'];return fcl.CollisionObject(mesh,mplib.Pose(pose[:3],pose[3:]))
    robots=[(s,collision_object(s)) for s in robot_shapes];world=[(s,collision_object(s)) for s in world_shapes]
    rows=[]
    for left,a in robots:
        for right,b in world:
            ga,gb=left['collision_groups'],right['collision_groups']
            enabled=bool((ga[0]&gb[1] or ga[1]&gb[0]) and not(ga[2]&gb[2] and (ga[3]&65535)==(gb[3]&65535)))
            hit=bool(fcl.collide(a,b).is_collision());distance=float(fcl.distance(a,b).min_distance)
            rows.append({'robot_shape':left['name'],'obstacle_shape':right['name'],'role':right['role'],'physical_collision_filter_enabled':enabled,
                'mesh_intersection':hit,'surface_distance_m':distance,'negative_distance_is_collision_sentinel_not_penetration_depth':distance<0,
                'combined_contact_offset_m':left['contact_offset']+right['contact_offset'],
                'contact_offset_is_not_itself_physical_impulse':True})
    return sorted(rows,key=lambda x:x['surface_distance_m'])
