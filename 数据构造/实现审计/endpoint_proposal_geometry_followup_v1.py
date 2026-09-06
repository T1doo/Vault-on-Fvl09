"""One-shot CPU clearance for the sole F2 proposal; no alternative search."""
import copy,json,sys,hashlib
from pathlib import Path
import numpy as np
import transforms3d as t3d
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';D=W/'Robotwin2/datasets/f2_endpoint_constraint_remaining_v1_1'
sys.path.insert(0,str(A/'f2_f3_model_bridge_v1_1'));sys.path.insert(1,str(A))
from geometry import matrix,exact_shape_pairs
from realization_utf8_io_v1 import write_new
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=A/'F2_ENDPOINT_DIAGNOSIS_AND_ONE_LAYOUT_PROPOSAL_V1_20260906.json';proposal=json.loads(p.read_text(encoding='utf-8'))['one_proposal'];capture=json.loads((D/'live_model_capture.json').read_text(encoding='utf-8'));world=json.loads((D/'world_geometry.json').read_text(encoding='utf-8'))['shapes'];B=matrix(capture['actual_base_world_pose'])
    moving=[]
    for role,originals,target in [('stand',[s for s in world if s['role']=='stand'],proposal['new_stand_actor_pose']),('can',capture['can_shapes'],proposal['new_can_actor_pose'])]:
        for s in originals:
            n=copy.deepcopy(s);T=np.linalg.inv(B)@matrix(target)@matrix(s['shape_local_pose']);n['solver_pose']=np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist();n['role']=role;moving.append(n)
    obstacles=[s for s in world if s['role'] in ('box','scale','wall')]
    pairs=exact_shape_pairs(moving,obstacles)
    overlaps=[x for x in pairs if x['mesh_intersection'] and x['physical_collision_filter_enabled']]
    support=[]
    for s in moving:
        T=B@matrix(s['solver_pose']);v=np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3];support.append({'shape':s['name'],'role':s['role'],'world_min_z_m':float(v[:,2].min()),'world_max_z_m':float(v[:,2].max())})
    out={'schema_version':'cmf_f2_single_inward_proposal_cpu_geometry_v1','parent_proposal_file_sha256':sha(p),'exact_native_mesh_pairs':pairs,'no_box_scale_wall_intersection':not overlaps,
        'supported_geometry_z':support,'supported_z_unchanged_by_xy_translation':True,'table_footprint_and_robot_path_not_certified':True,'GPU_queries':0,'physical_attempts':0,'other_proposals_generated':0}
    write_new(A/'F2_INWARD_PROPOSAL_CPU_GEOMETRY_V1_20260906.json',out)
    f4={'schema_version':'cmf_f4_B_prospective_budget_derivation_v1','proposal_file_sha256':sha(A/'F4_PILOT_B_NEW_LAYOUT_CPU_PROPOSAL_V1_20260906.json'),
        'not_an_execution_manifest':True,'GPU_authorized':False,'proposed_caps':{'new_independent_roots':1,'r_pc':3,'r_inv_motion':3,'raw_trajectories':6,'fresh_scenes':14,'planner_queries':136,'wall_timeout_seconds':32400,'automatic_retry':False},
        'derivation':{'r_pc_original_runner_lifecycle_scenes':11,'motion_fresh_replays':3,'prefix_queries':10,'suffix_queries':{'programs':3,'target_construction_each':12,'chain_each':30},'motion_queries':0},
        'conditions':['new layout must pass all original prereq gates; prior A qualification not inherited','motion uses its own newly successful B controls and real execution, not A trajectories','derive and validate actual new runner accounting before any approval/launch','if additional prerequisite probes are required this prospective cap must be revised and reviewed before execution']}
    write_new(A/'F4_PILOT_B_PROSPECTIVE_BUDGET_V1_20260906.json',f4);print(json.dumps({'F2_no_box_scale_wall_intersection':not overlaps,'F4_prospective_queries':136}))
if __name__=='__main__':main()
