"""Independent visual/native/metadata and no-adoption predicate cross-checks."""
import json
import numpy as np
import trimesh
from .support_anatomy import A,P,D,OUT,load,sha
from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix
from goal_pilot48_v1.f2_inward_runtime_v3.contract import build_contract,digest

def audit():
    from controlled_multi_future.geometry import compose_pose,obb_inside_local_cavity
    records=[];files=[]
    for name,index in (('071_can',0),('062_plasticbox',2)):
        folder=P/'assets/objects'/name;mdpath=folder/f'model_data{index}.json';md=load(mdpath);files.append(mdpath)
        row={'asset':name+f'/base{index}','scale':md['scale'],'metadata_center_m':(np.asarray(md['center'])*md['scale']).tolist(),'metadata_extents_m':(np.asarray(md['extents'])*md['scale']).tolist()}
        for kind in ('collision','visual'):
            path=folder/kind/f'base{index}.glb';files.append(path);scene=trimesh.load(path,force='scene');vertices=[]
            for node in scene.graph.nodes_geometry:
                T,geometry=scene.graph[node];m=scene.geometry[geometry].copy();m.apply_transform(T);m.apply_scale(md['scale']);vertices.extend(m.vertices)
            v=np.asarray(vertices);row[kind+'_center_m']=((v.min(0)+v.max(0))/2).tolist();row[kind+'_extents_m']=np.ptp(v,axis=0).tolist()
        records.append(row)
    cap=load(D/'live_capture.json');anatomy=load(OUT/'anatomy.json');lineage=load(OUT/'cavity_lineage.json');c=build_contract()
    world=load(D/'world_geometry.json');boxpose=next(s['actor_world_pose'] for s in world['shapes'] if s['role']=='box')
    points=[]
    for s in cap['can_shapes']:
        T=matrix(s['shape_local_pose']);points.extend(np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3])
    points=np.asarray(points);native_center=(points.min(0)+points.max(0))/2;native_half=np.ptp(points,axis=0)/2
    meta_center=np.asarray(records[0]['metadata_center_m']);meta_half=np.asarray(records[0]['metadata_extents_m'])/2
    contact=anatomy['inside']['first_contact_actor_pose'];variants={}
    for geometry,center,half in (('frozen_metadata',meta_center,meta_half),('native_bounds_hypothetical',native_center,native_half)):
        for region,lower,upper in (('frozen_5mm_inset',lineage['frozen_lower_m'],lineage['frozen_upper_m']),('raw_grid_hypothetical',lineage['raw_lower_m'],lineage['raw_upper_m'])):
            variants[geometry+'__'+region]=obb_inside_local_cavity(compose_pose(contact,[*center,1,0,0,0]),half,boxpose,lower,upper)
    inventory=A/'F2_GEOMETRY_CERTIFICATE_INVENTORY_V4.json';inv=load(inventory);files.append(inventory)
    result={'schema_version':'F2_support_vs_strict_inside_independent_regression_v1','assets':records,'contact_pose_predicate_variants':variants,
      'hypothetical_variants_are_not_adopted_or_execution_authority':True,
      'preaudited_asset_inventory':{'certificate_count':inv['certificate_count'],'distinct_pair_count':inv['distinct_pair_count'],'runtime_qualified_pair_count':inv['runtime_qualified_pair_count'],
        'certificate_failures':inv['certificate_failures'],'planner_execution_authorized':inv['planner_execution_authorized'],'physical_execution_authorized':inv['physical_execution_authorized'],
        'actual_supported_strict_inside_alternative_already_proven':False},
      'no_new_asset_or_layout_trials':True,'no_GPU_or_solver_calls':True,'files':{str(p):sha(p) for p in files}}
    result['receipt_sha256']=digest(result);return result

if __name__=='__main__':
    r=audit()
    from realization_utf8_io_v1 import write_new
    write_new(OUT/'regression.json',r);print(json.dumps({'assets':r['assets'],'variants':{k:v['pass_true_cavity_obb'] for k,v in r['contact_pose_predicate_variants'].items()},'inventory':r['preaudited_asset_inventory']},ensure_ascii=False,indent=2))
