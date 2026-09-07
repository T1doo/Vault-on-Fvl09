"""Check every actual planner sample against native box materials."""
import numpy as np
from .spec import matrix,checked_pose,digest

def screen_actor_path(poses,box_pose,verifier,*,actual_start_can_pose,require_support=False):
    p=np.asarray(poses,dtype=float)
    if p.ndim!=2 or p.shape[1:]!=(7,) or len(p)<2 or not np.isfinite(p).all():raise ValueError('complete native actor path required')
    B=matrix(checked_pose(box_pose));start=matrix(checked_pose(actual_start_can_pose))
    if np.max(abs(matrix(checked_pose(p[0]))-start))>1e-4:raise ValueError('actual FK path does not start at bound actual can')
    failures=[];eps=verifier.c['native_boundary_epsilon_m'];pairs=0
    for i,cp in enumerate(p):
        relative=np.linalg.inv(B)@matrix(checked_pose(cp))
        for bs,bm in verifier.box:
            idx=int(bs['name'].split('__')[1]);boxT=matrix(bs['shape_local_pose']);bv=np.asarray(bs['vertices'])@boxT[:3,:3].T+boxT[:3,3]
            for cs,cm in verifier.can:
                T=relative@matrix(cs['shape_local_pose']);cv=np.asarray(cs['vertices'])@T[:3,:3].T+T[:3,3]
                if np.any(cv.max(0)<bv.min(0)) or np.any(bv.max(0)<cv.min(0)):continue
                pairs+=1
                if not verifier._material_intersection(cs,cm,T,bs,bm,boxT):continue
                if idx!=9:failures.append({'sample':i,'shape':bs['name'],'reason':'noncertified_material_intersection'});continue
                raised=T.copy();raised[1,3]+=eps
                if verifier._material_intersection(cs,cm,raised,bs,bm,boxT):failures.append({'sample':i,'shape':bs['name'],'reason':'floor_penetration'})
    end=verifier.evaluate(p[-1].tolist(),box_pose,binding_sha256=verifier.c['binding_sha256']) if require_support else None
    result={'schema_version':'f2_controlled_inside_all_native_samples_v2','pass':not failures and (not require_support or end['pass']),
      'samples':len(p),'narrow_native_pairs':pairs,'failures':failures,'endpoint_support':end,'poses_sha256':digest(p.tolist()),
      'continuous_sweep_proven':False,'physical_success':False,'robot_and_other_world_checked_by_actual_planner':True}
    result['receipt_sha256']=digest(result);return result
