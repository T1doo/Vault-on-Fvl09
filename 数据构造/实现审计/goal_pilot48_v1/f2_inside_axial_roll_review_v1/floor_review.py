"""Necessary floor-height review of the one already frozen analytic roll."""
import json
from pathlib import Path
import numpy as np,trimesh
from goal_pilot48_v1.f2_inside_preinsert_failure_review_v1.analyze import context,matrix,hand_parts,goal_solver,sha,digest

def approved_profile_checks(r):
    model=r['full_actual_profile_and_native_hand_necessary_conditions'];pairs=model['configured_buffer']['attached_can']['groups']
    native=r['native_final_five_boundaries_and_floor'];actual=r['actual_solver_implied_native_final']
    return {'native_five_boundaries_floor':bool(native['pass'] and actual['pass']),
      'only_box9_native_support':native['floor_geometry_candidate_indices']==[9] and actual['floor_geometry_candidate_indices']==[9],
      'no_can_pair_outside_approved_box9':not any(k!='attached_can/box__9' for k in pairs),
      'no_hand_world_buffered_collision':model['configured_buffer']['hand']['count']==0,
      'no_hand_native_surface_intersection':model['native_hand']['pass_surface_test']}

def review():
    path=Path(__file__).with_name('ANALYSIS_001.json');r=json.loads(path.read_text(encoding='utf-8'));payload=dict(r);h=payload.pop('receipt_sha256')
    if digest(payload)!=h:raise ValueError('single-roll report changed')
    for p,h in r['sources'].items():
        if sha(p)!=h:raise ValueError('single-roll source binding changed')
    c=context();verifier=c['verifier'];B=matrix(c['box']);relative=np.linalg.inv(B)@matrix(r['proposed_actor_pose'])
    bs,bm=next((s,m) for s,m in verifier.box if s['name']=='box__9');bo=verifier._object(bm,matrix(bs['shape_local_pose']))
    distances=[verifier.fcl.distance(verifier._object(m,relative@matrix(s['shape_local_pose'])),bo,verifier.fcl.DistanceRequest(enable_nearest_points=True)) for s,m in verifier.can]
    nearest=min(distances,key=lambda x:x.min_distance);point=np.asarray(nearest.nearest_points)
    if point.shape!=(3,) or not np.isfinite(point).all():raise ValueError('frozen MPLib nearest-points API differs')
    point=B[:3,:3]@point+B[:3,3];T=B@matrix(bs['shape_local_pose']);vertices=np.asarray(bs['vertices'])@T[:3,:3].T+T[:3,3]
    triangles=vertices[np.asarray(bs['faces'],dtype=int)];closest=trimesh.triangles.closest_point(triangles,np.tile(point,(len(triangles),1)));index=int(np.linalg.norm(closest-point,axis=1).argmin());tri=triangles[index]
    n=np.cross(tri[1]-tri[0],tri[2]-tri[0]);n/=np.linalg.norm(n);n*=1 if n[2]>=0 else -1
    G=goal_solver(c,r['actual_grasp_derived_eef_goal']);worldB=matrix(c['model']['base']);parts=[]
    for link,s,T in hand_parts(c,G):
        T=worldB@T;p=np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3];i=int(p[:,2].argmin())
        parts.append({'link':link,'lowest_world_point':p[i].tolist(),'minimum_signed_support_facet_plane_distance_m':float(((p-tri[0])@n).min())})
    checks=approved_profile_checks(r)
    result={'schema_version':'f2_one_roll_floor_height_necessary_condition_review_v1','source_roll_receipt_sha256':r['receipt_sha256'],
      'new_pose_candidates_or_solver_scene_calls':0,'nearest_can_box9_gap_m':float(nearest.min_distance),'native_support_facet_index':index,
      'native_support_surface_point_world':closest[index].tolist(),'native_support_upward_normal_world':n.tolist(),
      'maximin_lowest_hand_world_z_m':r['maximum_lowest_native_hand_world_z_m'],
      'best_lowest_hand_below_support_point_z_m':float(closest[index,2]-r['maximum_lowest_native_hand_world_z_m']),
      'individual_hand_parts':parts,'approved_box9_aware_necessary_checks':checks,'necessary_conditions_pass':all(checks.values()),
      'original_full_world_report_pass_was_conservative_not_an_override_of_box9_approval':True,
      'floor_is_sloped_not_a_global_constant_z_plane':True,'native_floor_contacts_are_geometry_only_not_measured_physical_support':True,
      'pure_wall_widening_with_existing_floor_does_not_remove_observed_native_floor_intersections':True,
      'arbitrary_larger_or_deeper_container_impossibility_proven':False,
      'sources':{str(path):sha(path),str(Path(__file__)):sha(__file__)}}
    result['receipt_sha256']=digest(result);return result

if __name__=='__main__':
    r=review()
    with Path(__file__).with_name('FLOOR_REVIEW_001.json').open('x',encoding='utf-8') as f:json.dump(r,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print({'receipt_sha256':r['receipt_sha256'],'hand_deficit_m':r['best_lowest_hand_below_support_point_z_m'],'checks':r['approved_box9_aware_necessary_checks']})
