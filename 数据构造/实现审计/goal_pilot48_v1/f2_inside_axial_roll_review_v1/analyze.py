"""One analytic maximin-height axial roll, not a pose/angle sweep."""
import json
from pathlib import Path
import numpy as np,transforms3d as t3d
from scipy.spatial import ConvexHull
from goal_pilot48_v1.f2_inside_preinsert_failure_review_v1.analyze import context,hand_parts,goal_audit,goal_solver,matrix,pose,A,D,sha,digest

def highest_lowest_point_roll(points):
    """Exact polygon support construction, no candidate pose evaluation.

    For origin inside P, max_|u|=1 min_p(p.u) = -min support-edge distance.
    For origin outside P, the closest point projection supplies the direction.
    """
    p=np.asarray(points,dtype=float)
    if p.ndim!=2 or p.shape[1]!=2 or not np.isfinite(p).all():raise ValueError('finite two-dimensional hand cross-section required')
    hull=ConvexHull(p);equations=hull.equations;inside=bool(np.all(equations[:,2]<=1e-12))
    if inside:
        distance=-equations[:,2];minimum=float(distance.min());ids=np.flatnonzero(abs(distance-minimum)<=1e-10)
        candidates=[(-equations[i,:2],int(i)) for i in ids]
        u,index=min(candidates,key=lambda item:(abs(float(np.arctan2(item[0][1],item[0][0]))),item[1]))
        proof={'method':'nearest_supporting_edge_to_axis_origin','axis_origin_inside_convex_hull':True,'support_edge':index,'distance_m':minimum,'tied_optimal_edges':len(ids)}
    else:
        vertices=p[hull.vertices];closest=[]
        for i,a in enumerate(vertices):
            b=vertices[(i+1)%len(vertices)];d=b-a;t=float(np.clip(-np.dot(a,d)/np.dot(d,d),0,1));point=a+t*d;closest.append((float(np.dot(point,point)),point,i))
        norm2,point,index=min(closest,key=lambda x:(x[0],x[2]));u=point/np.sqrt(norm2)
        proof={'method':'closest_convex_polygon_point_projection','axis_origin_inside_convex_hull':False,'support_edge':index,'distance_m':float(np.sqrt(norm2))}
    theta=float(np.arctan2(u[1],u[0]));minimum_height=float((p@u).min())
    return {'roll_rad':theta,'roll_deg':float(np.degrees(theta)),'minimum_hand_height_relative_to_axis_m':minimum_height,
      'unrotated_minimum_hand_height_relative_to_axis_m':float(p[:,0].min()),'direction':u.tolist(),'proof':proof,
      'pose_angles_evaluated_by_search':0,'geometric_cross_section_points':len(p)}

def analyze():
    c=context();cert=c['certificate'];R0=matrix(c['spec']['target_actor_pose'])[:3,:3];center=np.asarray(cert['can_native_center_m']);half=np.asarray(cert['can_native_half_extents_m']);axis=int(np.argmax(half));vaxis=np.eye(3)[axis]
    if axis!=1 or abs(float((R0@vaxis)[2]))>1e-10:raise ValueError('review assumes the existing horizontal native long axis, not another axis')
    C0=matrix(c['spec']['target_actor_pose']);world_center=C0[:3,:3]@center+C0[:3,3]
    can_from_flange=np.linalg.inv(np.asarray(c['model']['T_solver_eef_can']));vertices=[]
    for link,shape,T in hand_parts(c,np.eye(4)):
        T=can_from_flange@T;vertices.extend(np.asarray(shape['vertices'])@T[:3,:3].T+T[:3,3]-center)
    vertices=np.asarray(vertices);w=R0.T@np.array([0.,0.,1.]);a=vertices@w;b=np.cross(vaxis,vertices)@w;roll=highest_lowest_point_roll(np.c_[a,b])
    R=R0@t3d.axangles.axangle2mat(vaxis,roll['roll_rad']);candidate=np.eye(4);candidate[:3,:3]=R;candidate[:3,3]=world_center-R@center
    grasp=np.linalg.inv(matrix(c['eef']))@matrix(c['can']);EEF=candidate@np.linalg.inv(grasp);actor=pose(candidate);goal=pose(EEF)
    native=c['verifier'].evaluate(actor,c['box'],binding_sha256=cert['binding_sha256']);model=goal_audit(c,goal)
    implied=matrix(c['model']['base'])@goal_solver(c,goal)@np.asarray(c['model']['T_solver_eef_can']);actual_native=c['verifier'].evaluate(pose(implied),c['box'],binding_sha256=cert['binding_sha256'])
    # This is the sole proposed orientation. No additional roll/height is
    # attempted when the fixed-center candidate fails a necessary condition.
    passes=bool(native['pass'] and actual_native['pass'] and model['configured_buffer']['attached_can']['count']==0 and model['configured_buffer']['hand']['count']==0 and model['native_hand']['pass_surface_test'])
    paths=[Path(__file__),A/'goal_pilot48_v1/f2_inside_preinsert_failure_review_v1/analyze.py',A/'goal_pilot48_v1/f2_inside_preinsert_failure_review_v1/DIAGNOSIS_001.json',
      D/'inside_result.json',D/'model_010_carried_full.json',D/'qualification_trace.npz']
    old_diagnosis=json.loads(paths[2].read_text(encoding='utf-8'))
    sources={**old_diagnosis['sources'],**{str(p):sha(p) for p in paths}}
    result={'schema_version':'f2_inside_single_analytic_axial_roll_necessary_condition_review_v1','CPU_only':True,'new_solver_scene_action_calls':0,
      'orientation_design_is_not_pure_path_revision':True,'old_final_actor_orientation':c['spec']['target_actor_pose'][3:],
      'native_long_axis_index':axis,'fixed_world_long_axis':(R0@vaxis).tolist(),'fixed_world_native_geometry_center':world_center.tolist(),
      'roll_derivation':roll,'proposed_actor_pose':actor,'actual_grasp_derived_eef_goal':goal,
      'axis_preservation_error':float(np.linalg.norm(R@vaxis-R0@vaxis)),
      'center_preservation_error_m':float(np.linalg.norm(R@center+candidate[:3,3]-world_center)),
      'maximum_lowest_native_hand_world_z_m':float(world_center[2]+roll['minimum_hand_height_relative_to_axis_m']),
      'native_final_five_boundaries_and_floor':native,'actual_solver_implied_native_final':actual_native,
      'full_actual_profile_and_native_hand_necessary_conditions':model,'necessary_conditions_pass':passes,
      'only_one_orientation_evaluated':True,'native_axial_symmetry_assumed':False,'numerical_Gates_or_collision_masks_changed':False,
      'physical_or_full_arm_IK_success_proven':False,'sources':sources}
    result['receipt_sha256']=digest(result);return result

if __name__=='__main__':
    r=analyze()
    with Path(__file__).with_name('ANALYSIS_001.json').open('x',encoding='utf-8') as f:json.dump(r,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print({'receipt_sha256':r['receipt_sha256'],'roll':r['roll_derivation'],'native_checks':r['native_final_five_boundaries_and_floor']['checks'],
      'hand_native':r['full_actual_profile_and_native_hand_necessary_conditions']['native_hand']['surface_intersections'],'necessary_pass':r['necessary_conditions_pass']})
