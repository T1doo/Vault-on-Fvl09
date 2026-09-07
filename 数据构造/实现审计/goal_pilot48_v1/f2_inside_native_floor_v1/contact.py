"""Real row-level floor contact proof using unchanged V8 physical-hit rules."""
import numpy as np
import trimesh
from .certificate import digest,matrix,VERSION

def shape_identity(shape,index,actor_name):
    identity={'available':True,'body_name':actor_name,'body_collision_shape_index':int(index),'shape_type':shape['kind'],
      'local_pose':shape['shape_local_pose'],'collision_groups':shape['collision_groups'],'contact_offset_m':shape['contact_offset'],'rest_offset_m':shape['rest_offset'],
      'identity_source':'contact.shapes entry matched by Python object identity to body.get_collision_shapes()'}
    identity['identity_sha256']=digest(identity);return identity

def identity_matches(identity,shapes,actor):
    if not isinstance(identity,dict) or identity.get('available') is not True or identity.get('body_name')!=actor:return False
    index=identity.get('body_collision_shape_index')
    if type(index) is not int or not 0<=index<len(shapes):return False
    return identity==shape_identity(shapes[index],index,actor)

def surface_distance(shape,world_position,actor_pose):
    T=np.linalg.inv(matrix(actor_pose)@matrix(shape['shape_local_pose']));point=T[:3,:3]@np.asarray(world_position)+T[:3,3]
    triangles=np.asarray(shape['vertices'])[np.asarray(shape['faces'],dtype=int)]
    closest=trimesh.triangles.closest_point(triangles,np.tile(point,(len(triangles),1)))
    return float(np.linalg.norm(closest-point,axis=1).min())

def verify_floor_contact_row(row,geometry_verifier):
    from controlled_multi_future.f3_physical_contact_signal_v8 import classify_contact_pair_physical_hit_v8
    c=geometry_verifier.c;poses=row.get('role_actor_poses',{})
    if not {'main_can','box'}.issubset(poses):raise ValueError('missing actual world actor poses')
    geom=geometry_verifier.evaluate(poses['main_can'],poses['box'],binding_sha256=c['binding_sha256'],frame=row.get('actor_pose_frame','world'))
    pairs=row.get('contact_pairs');complete=row.get('contact_signal_complete') is True
    if not isinstance(pairs,list):pairs=[];complete=False
    proofs=[];errors=[];walls=[]
    for pair in pairs:
        names=[pair.get('body_a'),pair.get('body_b')]
        if set(names)!={c['can_actor_name'],c['box_actor_name']}:continue
        signal=classify_contact_pair_physical_hit_v8(pair)
        if not signal['evidence_complete']:errors.append('incomplete_original_contact_signal');continue
        identities=pair.get('shape_identities',[])
        ci=names.index(c['can_actor_name']);bi=names.index(c['box_actor_name'])
        if len(identities)!=2 or not identity_matches(identities[ci],c['can_shapes'],c['can_actor_name']) or not identity_matches(identities[bi],c['box_shapes'],c['box_actor_name']):
            errors.append('wrong_shape_registry_identity');continue
        box_index=identities[bi]['body_collision_shape_index'];can_index=identities[ci]['body_collision_shape_index']
        if signal['physical_hit_for_gate'] and box_index in c['wall_shape_indices']:walls.append(box_index)
        if not signal['physical_hit_for_gate'] or box_index not in c['floor_shape_indices']:continue
        if box_index not in geom['floor_geometry_candidate_indices']:errors.append('reported_floor_not_near_native_contact');continue
        positions=pair.get('point_positions',[]);normals=pair.get('point_normals',[])
        if len(positions)!=pair.get('point_count') or len(normals)!=len(positions) or not positions:
            errors.append('floor_contact_point_geometry_missing');continue
        valid_points=True;distances=[]
        for point,normal in zip(positions,normals):
            p=np.asarray(point);n=np.asarray(normal)
            if p.shape!=(3,) or n.shape!=(3,) or not np.isfinite(np.r_[p,n]).all() or np.linalg.norm(n)==0:valid_points=False;break
            bs=c['box_shapes'][box_index];cs=c['can_shapes'][can_index]
            db=surface_distance(bs,p,poses['box']);dc=surface_distance(cs,p,poses['main_can'])
            # Geometric consistency with the original shape contact offsets;
            # no new physical-hit threshold replaces the original classifier.
            limit=bs['contact_offset']+cs['contact_offset']+c['native_boundary_epsilon_m']
            if max(db,dc)>limit:valid_points=False
            distances.append({'box_surface_distance_m':db,'can_surface_distance_m':dc,'existing_contact_offset_plus_numeric_band_m':limit})
        if not valid_points:errors.append('contact_position_frame_or_surface_mismatch');continue
        proofs.append({'box_shape_index':box_index,'can_shape_index':can_index,'original_signal_receipt':signal,'point_surface_audit':distances})
    # This certificate replaces generic box-contact identity with actual
    # floor-contact identity; it does not silently extend final containment
    # from the final pose to every earlier support-window pose.
    material_floor_ok=all(geom['checks'][k] for k in ('no_sidewall_material_intersection','no_floor_penetration_beyond_native_numeric_band','near_actual_floor_surface'))
    result={'schema_version':'f2_inside_native_floor_contact_row_v1','verifier_version':VERSION,'geometry':geom,
      'original_contact_signal_complete':complete,'matched_actual_floor_pairs':proofs,'reported_wall_contact_indices':walls,'errors':errors,
      'pass':bool(complete and material_floor_ok and proofs and not walls and not errors),
      'final_five_boundaries_are_applied_separately_at_final_pose':True,
      'source_kind':'caller_supplied_trace_row; provenance must be bound by collector'}
    result['receipt_sha256']=digest(result);return result

def verify_floor_contact_window(rows,geometry_verifier,*,expected_frames):
    if expected_frames not in (10,50) or len(rows)!=expected_frames:raise ValueError('preserve original10/50-frame support windows')
    results=[verify_floor_contact_row(row,geometry_verifier) for row in rows]
    return {'schema_version':'f2_inside_native_floor_contact_window_v1','frame_count':len(rows),'pass':all(r['pass'] for r in results),
      'row_receipt_sha256s':[r['receipt_sha256'] for r in results],'first_failure':next((i for i,r in enumerate(results) if not r['pass']),None)}
