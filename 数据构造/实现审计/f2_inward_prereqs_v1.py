"""Actual native support and moving-pair geometry for the single new layout."""
import copy,json,sys,hashlib
from pathlib import Path
import numpy as np
import transforms3d as t3d
from scipy.spatial import ConvexHull
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';D=W/'Robotwin2/datasets';P=W/'Robotwin2/project/RoboTwin'
sys.path.insert(0,str(A/'f2_f3_model_bridge_v1_1'));sys.path.insert(1,str(A/'f3_model_replay_v1'));sys.path.insert(2,str(A));sys.path.append(str(A/'f2_bounded_transit_runtime_v1'))
from geometry import matrix,exact_shape_pairs
from kinematics_cpu import link_world,collision_description
from semantic_target import corrected_contract,old
from realization_utf8_io_v1 import write_new
def run():
    c,geom=corrected_contract();p=json.loads((A/'F2_ENDPOINT_DIAGNOSIS_AND_ONE_LAYOUT_PROPOSAL_V1_20260906.json').read_text(encoding='utf-8'))['one_proposal'];capture=json.loads((D/'f2_endpoint_constraint_remaining_v1_1/live_model_capture.json').read_text(encoding='utf-8'));world=json.loads((D/'f2_endpoint_constraint_remaining_v1_1/world_geometry.json').read_text(encoding='utf-8'))['shapes'];base=capture['actual_base_world_pose'];B=matrix(base)
    def world_vertices(s):
        T=B@matrix(s['solver_pose']);return np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3]
    def move(shapes,pose):
        out=[]
        for s in shapes:
            n=copy.deepcopy(s);T=np.linalg.inv(B)@matrix(pose)@matrix(s['shape_local_pose']);n['solver_pose']=np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist();out.append(n)
        return out
    stand=move([s for s in world if s['role']=='stand'],p['new_stand_actor_pose']);can=move(capture['can_shapes'],p['new_can_actor_pose'])
    initial_pose=[*c['binding']['layout_payload']['main_object_pose_xyz'],*c['binding']['layout_payload']['main_object_orientation_wxyz']];initialcan=move(capture['can_shapes'],initial_pose)
    tables=[s for s in world if s['role']=='table'];table=max(tables,key=lambda s:(world_vertices(s).max(0)-world_vertices(s).min(0))[:2].prod());tv=world_vertices(table);top=float(tv[:,2].max());topverts=tv[np.abs(tv[:,2]-top)<1e-5,:2];hull=ConvexHull(topverts);support=[]
    for name,shapes in [('stand',stand),('final_can',can)]:
        v=np.concatenate([world_vertices(s) for s in shapes]);inside=bool(np.all(v[:,:2]@hull.equations[:,:2].T+hull.equations[:,2]<=1e-6));gap=float(v[:,2].min()-top)
        support.append({'role':name,'footprint_all_native_vertices_in_real_table_top':inside,'bottom_gap_m':gap,'numeric_support_tolerance_m':.0001,'pass':inside and abs(gap)<=.0001})
    finalpair=exact_shape_pairs(stand,can);initialpair=exact_shape_pairs(stand,initialcan);heldpair=exact_shape_pairs(stand,capture['can_shapes']);robotrows=[]
    with np.load(old.SEALED_TRACE,allow_pickle=False) as z:initialq=z['joint_qpos'][0]
    for label,q in [('initial',initialq),('diagnostic_held',capture['joint_qpos'])]:
        named=dict(zip(capture['joint_names'],q));shapes=[]
        for prefix in ('fl','fr'):
            for i in range(1,9):
                left=prefix+'_link'+str(i);right='fr_link'+str(i);assert collision_description(left)==collision_description(right)
                for s in world:
                    if s['role']!=right:continue
                    n=copy.deepcopy(s);n['name']=left+'__'+s['name'].rsplit('__',1)[-1];T=np.linalg.inv(B)@link_world(left,named,base)@matrix(s['shape_local_pose']);n['solver_pose']=np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist();shapes.append(n)
        robotrows.append({'state':label,'pairs':exact_shape_pairs(stand,shapes)})
    pairs=finalpair+initialpair+heldpair+[p for r in robotrows for p in r['pairs']];pairpass=not any(p['mesh_intersection'] and p['physical_collision_filter_enabled'] for p in pairs)
    # Semantic predicates use metadata-centre semantics, separately from mesh
    # safety. Region disjointness is a sufficient negative inside/on witness.
    target=np.array(p['new_target_geometry_xy_m']);layout=c['binding']['layout_payload'];half=np.array(geom['half_extents_m']);R=matrix(p['new_can_actor_pose'])[:3,:3];extent=np.abs(R)@half
    inside_disjoint=bool(np.any(np.abs(target-np.array(layout['inside_region_center_xy_m']))>extent[:2]+np.array(layout['inside_region_half_xy_m'])))
    on_disjoint=bool(np.any(np.abs(target-np.array(layout['on_region_center_xy_m']))>extent[:2]+np.array(layout['on_region_half_xy_m'])))
    # Both centres receive identical translation; exact old semantic radial
    # remains the sealed radial, so no dependence on guessed stand metadata.
    radial=float(c['beside_radial_distance_m']);beside=.12<=radial<=.23 and p['new_can_actor_pose'][2]<=.83 and inside_disjoint and on_disjoint
    result={'schema_version':'cmf_f2_inward_complete_cpu_prerequisites_v1','support':support,'stand_final_can_pairs':finalpair,'stand_initial_can_pairs':initialpair,'stand_diagnostic_can_pairs':heldpair,'stand_robot_pairs':robotrows,
        'semantics':{'beside':beside,'inside':not inside_disjoint,'on':not on_disjoint,'inside_on_false_by_disjoint_regions':inside_disjoint and on_disjoint,'radial_m':radial},
        'all_cpu_geometric_prerequisites_pass':all(r['pass'] for r in support) and pairpass and beside,'new_layout_version':'f2_beside_inward_layout_v1','beside_candidate_coordinates_policy':'translate all three retained coordinates by the same declared XY; only index2 active',
        'new_root_current_anchor_required':True,'new_GPU_scene_count':0,'IK_queries':0,'physical_attempts':0,'support_check_not_dynamic_stability_proof':True}
    write_new(A/'F2_INWARD_COMPLETE_CPU_PREREQUISITES_V1_20260906.json',result);print(json.dumps({'support':support,'pairpass':pairpass,'semantic':result['semantics'],'pass':result['all_cpu_geometric_prerequisites_pass']}))
if __name__=='__main__':run()
