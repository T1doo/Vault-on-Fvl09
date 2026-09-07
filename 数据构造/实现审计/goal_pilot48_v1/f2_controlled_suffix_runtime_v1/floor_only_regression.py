"""Hypothetical one-axis decision regression, NOT a new acceptance verifier."""
import copy,json
import numpy as np
from .support_anatomy import A,P,D,OUT,load,sha
from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix
from goal_pilot48_v1.f2_inward_runtime_v3.contract import digest

def audit():
    from controlled_multi_future.geometry import compose_pose,obb_inside_local_cavity
    a=load(OUT/'anatomy.json');l=load(OUT/'cavity_lineage.json');cap=load(D/'live_capture.json');world=load(D/'world_geometry.json')
    pts=[]
    for s in cap['can_shapes']:
        T=matrix(s['shape_local_pose']);pts.extend(np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3])
    pts=np.asarray(pts);center=(pts.min(0)+pts.max(0))/2;half=np.ptp(pts,axis=0)/2
    pose=a['inside']['first_contact_actor_pose'];box=next(s['actor_world_pose'] for s in world['shapes'] if s['role']=='box')
    strict_lo=np.asarray(l['frozen_lower_m']);strict_hi=np.asarray(l['frozen_upper_m']);floor_only_lo=strict_lo.copy();floor_only_lo[1]=l['raw_lower_m'][1]
    native=compose_pose(pose,[*center,1,0,0,0]);fit=obb_inside_local_cavity(native,half,box,floor_only_lo,strict_hi)
    lo=np.asarray(fit['local_corner_min']);hi=np.asarray(fit['local_corner_max'])
    checks={'both_X_side_bounds_unchanged':bool(np.array_equal(floor_only_lo[[0]],strict_lo[[0]])),
      'both_Z_side_bounds_unchanged':bool(np.array_equal(floor_only_lo[[2]],strict_lo[[2]])),
      'all_upper_bounds_including_top_unchanged':True,
      'X_sides_pass':bool(lo[0]>=strict_lo[0] and hi[0]<=strict_hi[0]),'Z_sides_pass':bool(lo[2]>=strict_lo[2] and hi[2]<=strict_hi[2]),'top_pass':bool(hi[1]<=strict_hi[1]),
      'native_first_contact_only_registered_low_floor':set(a['inside']['first_contact_shape_ids']).issubset(set(a['inside']['low_floor_shape_ids']))}
    negative={}
    M=matrix(box)
    for axis,label in ((0,'X_side_escape'),(2,'Z_side_escape'),(1,'top_escape')):
        shifted=np.asarray(pose).copy();delta=float(strict_hi[axis]-hi[axis]+.001);shifted[:3]+=M[:3,axis]*delta
        f=obb_inside_local_cavity(compose_pose(shifted,[*center,1,0,0,0]),half,box,floor_only_lo,strict_hi)
        negative[label]={'pass_true_cavity_obb':f['pass_true_cavity_obb'],'expected_rejection':not f['pass_true_cavity_obb']}
    result={'schema_version':'F2_native_only_floor_uninset_decision_regression_v1','NOT_IMPLEMENTED_AS_ACCEPTANCE':True,'NO_NEW_PHYSICAL_GATE_EXECUTED':True,
      'candidate_actor_pose':pose,'native_center_m':center.tolist(),'native_half_extents_m':half.tolist(),
      'original_lower_m':strict_lo.tolist(),'one_axis_only_hypothetical_lower_m':floor_only_lo.tolist(),'unchanged_upper_m':strict_hi.tolist(),
      'one_axis_only_hypothetical_fit':fit,'checks':checks,'negative_side_top_cases':negative,
      'unchanged_side_margins_m':{'X_min':float(lo[0]-strict_lo[0]),'X_max':float(strict_hi[0]-hi[0]),'Z_min':float(lo[2]-strict_lo[2]),'Z_max':float(strict_hi[2]-hi[2]),'top':float(strict_hi[1]-hi[1])},
      'floor_contact_shape_ids':a['inside']['first_contact_shape_ids'],'contact_height_bracket_m':a['inside']['first_native_contact_drop_interval_m'],
      'geometric_combination_is_sufficient_for_saved_candidate':bool(fit['pass_true_cavity_obb'] and all(checks.values()) and all(v['expected_rejection'] for v in negative.values())),
      'actual_physical_support_stability_proven':False,
      'production_floor_rule_must_be_actual_piecewise_native_contact_not_raw_grid_plane':True,
      'remaining_negative_regressions_before_adoption':['native floor penetration','floating without real floor support','wrong shape identity','contact-offset-only/no-force false support','wrong frame or scale'],
      'source_files':{str(p):sha(p) for p in (OUT/'anatomy.json',OUT/'cavity_lineage.json',D/'live_capture.json',D/'world_geometry.json')},'GPU_or_solver_calls':0}
    result['receipt_sha256']=digest(result);return result

if __name__=='__main__':
    r=audit()
    from realization_utf8_io_v1 import write_new
    write_new(OUT/'floor_only_regression.json',r);print(json.dumps({k:r[k] for k in ('receipt_sha256','one_axis_only_hypothetical_fit','checks','negative_side_top_cases','unchanged_side_margins_m','geometric_combination_is_sufficient_for_saved_candidate')},ensure_ascii=False,indent=2))
