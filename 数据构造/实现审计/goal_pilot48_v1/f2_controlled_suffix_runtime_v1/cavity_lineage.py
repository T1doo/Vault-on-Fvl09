"""Trace frozen cavity inset to collision geometry and independent native bounds."""
import json,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.optimize import linprog
from .support_anatomy import A,P,W,D,OUT,load,sha
from goal_pilot48_v1.f2_inward_runtime_v3.contract import build_contract,digest
from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix

def audit():
    from controlled_multi_future.f2_asset_geometry_layout_v3 import _collision_geometry,_cavity_proposal
    c=build_contract();box=_collision_geometry('062_plasticbox',2);raw=_cavity_proposal(2);bounds=c['binding']['strict_cavity_contract']
    lower=np.asarray(bounds['lower_m']);upper=np.asarray(bounds['upper_m']);margin=bounds['safety_margin_per_side_m']
    if not np.allclose(raw['raw_lower']+margin,lower,atol=1e-12,rtol=0) or not np.allclose(raw['raw_upper']-margin,upper,atol=1e-12,rtol=0):raise ValueError('frozen cavity source not reproduced')
    capture=load(D/'live_capture.json');world=load(D/'world_geometry.json');pieces=[];matches=[]
    for s in world['shapes']:
        if s['role']!='box':continue
        T=matrix(s['shape_local_pose']);v=np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3];lo=v.min(0);hi=v.max(0)
        best=min(box['pieces'],key=lambda p:max(np.max(abs(lo-p['lower'])),np.max(abs(hi-p['upper']))))
        match=max(float(np.max(abs(lo-best['lower']))),float(np.max(abs(hi-best['upper']))));matches.append(match)
        equations=ConvexHull(v).equations
        result=linprog(np.zeros(3),A_ub=equations[:,:3],b_ub=-equations[:,3],bounds=list(zip(lower,upper)),method='highs')
        if result.status not in (0,2):raise ValueError('native strict-volume intersection indeterminate')
        gaps=np.maximum(lo-upper,lower-hi)
        pieces.append({'native_shape_id':s['name'],'source_GLTF_node':best['node_name'],'source_vs_native_bounds_max_error_m':match,
          'actor_local_lower_m':lo.tolist(),'actor_local_upper_m':hi.tolist(),'AABB_axis_separation_m':gaps.tolist(),
          'AABB_proves_disjoint':bool(np.any(gaps>0)),'strict_cavity_intersects_native_piece':result.status==0})
    # Prove that the native can lies within the metadata OBB used by verifier,
    # so any strict-contained OBB cannot touch a disjoint native box volume.
    md=load(P/'assets/objects/071_can/model_data0.json');center=np.asarray(md['center'])*np.asarray(md['scale']);half=np.asarray(md['extents'])*np.asarray(md['scale'])/2
    native=[]
    for s in capture['can_shapes']:
        T=matrix(s['shape_local_pose']);native.extend(np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3])
    native=np.asarray(native);contain_lower=native.min(0)-(center-half);contain_upper=(center+half)-native.max(0)
    can_contained=bool(np.all(contain_lower>=-1e-6) and np.all(contain_upper>=-1e-6))
    boxpose=next(s['actor_world_pose'] for s in world['shapes'] if s['role']=='box');M=matrix(boxpose)
    files=[P/'controlled_multi_future/f2_asset_geometry_layout_v3.py',P/'controlled_multi_future/f2_dynamic_search_contract_v3.py',P/'controlled_multi_future/f2_asset_compatibility_v3_2.py',
      P/'controlled_multi_future/runtime_v3_2_contracts.py',P/'controlled_multi_future/f2_inside_control_search_v2.py',P/'controlled_multi_future/f2_release_gates_v10.py',
      P/'assets/objects/062_plasticbox/model_data2.json',P/'assets/objects/062_plasticbox/collision/base2.glb',P/'assets/objects/071_can/model_data0.json',D/'world_geometry.json',D/'live_capture.json']
    result={'schema_version':'F2_strict_cavity_inset_native_lineage_v1','box_asset':'062_plasticbox/base2','box_uniform_scale':load(P/'assets/objects/062_plasticbox/model_data2.json')['scale'],
      'cavity_source':'collision GLB node transforms + model_data scale; 1mm three-axis centerline empty-space grid; NOT visual mesh or model_data extents',
      'raw_lower_m':raw['raw_lower'].tolist(),'raw_upper_m':raw['raw_upper'].tolist(),'artificial_inset_per_side_m':margin,
      'frozen_lower_m':lower.tolist(),'frozen_upper_m':upper.tolist(),'native_source_bounds_max_error_m':max(matches),
      'native_box_pieces':pieces,'all_strict_volume_native_intersections_absent':all(not p['strict_cavity_intersects_native_piece'] for p in pieces),
      'native_can_contained_in_verifier_metadata_OBB':can_contained,'can_metadata_to_native_lower_margins_m':contain_lower.tolist(),'can_metadata_to_native_upper_margins_m':contain_upper.tolist(),
      'box_actor_pose':boxpose,'box_local_Y_in_world':M[:3,1].tolist(),'strict_lower_Y_world_height_m':float((M@np.r_[0,lower[1],0,1])[2]),
      'different_contact_region_cannot_fix_geometric_disjointness_if_OBB_containment_holds':can_contained and all(not p['strict_cavity_intersects_native_piece'] for p in pieces),
      'contact_offset_physics_not_proven_by_this_static_audit':True,'verifier_or_collision_modified':False,'solver_or_GPU_calls':0,
      'files':{str(p):sha(p) for p in files}}
    result['receipt_sha256']=digest(result);return result

if __name__=='__main__':
    r=audit()
    from realization_utf8_io_v1 import write_new
    write_new(OUT/'cavity_lineage.json',r)
    print(json.dumps({k:v for k,v in r.items() if k not in ('native_box_pieces','files')},ensure_ascii=False,indent=2))
