"""Saved F2 postclose pose: demonstrate support-pair applicability without GPU."""
import copy,json,sys
from pathlib import Path
import numpy as np
import transforms3d as t3d
from .spec import A,W,digest
from .prefix_models import native_escape_checks
sys.path.insert(0,str(A/'f3_model_replay_v1'))
from kinematics_cpu import link_world
from goal_pilot48_v1.f2_inward_failure_review_v1.analyze import matrix,model_collision_audit
from goal_pilot48_v1.f2_inward_runtime_v1.collision import support_witness

def audit():
    base=W/'Robotwin2/datasets/p48_f2_u_route_001'
    read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
    cap=read(base/'live_capture.json');cfg=read(base/'carried_robot_config.json')['kinematics'];export=read(base/'world_geometry.json');B=matrix(cap['base'])
    root=W/'Robotwin2/datasets/controlled_multi_future_f2_top_contact_root_v1/f2-top-contact-development-rpc-root-v1-run1/root'
    prefix=read(root/'canonical_prefix_artifact/canonical_prefix_artifact.json');index=prefix['reference_event_boundaries']['post_close']
    with np.load(root/'canonical_prefix_reference_trace.npz',allow_pickle=False) as z:
        q=np.asarray(z['joint_qpos'][index]);actor=np.asarray(z['role_object_pose__main_can'][index]);eef=np.asarray(z['eef_pose'][index])
    n0=dict(zip(cap['joint_names'],cap['qpos']));n=dict(zip(cap['joint_names'],q))
    EC=link_world('fl_link6',n0,cap['base']);EP=link_world('fl_link6',n,cap['base']);AC=matrix(cap['can_shapes'][0]['actor_world_pose']);AP=matrix(actor)
    if np.linalg.norm(EP[:3,3]-eef[:3])>2e-6:raise ValueError('F2 saved EEF disagrees with URDF')
    cfg=copy.deepcopy(cfg);T=np.linalg.inv(EP)@AP@np.linalg.inv(AC)@EC
    for sphere in cfg['collision_spheres']['attached_can']:
        sphere['center']=(T[:3,:3]@sphere['center']+T[:3,3]).tolist()
    cfg['lock_joints']={key:float(n[key]) for key in cfg['lock_joints']}
    can=copy.deepcopy(cap['can_shapes']);points=[]
    for s in can:
        M=np.linalg.inv(B)@AP@matrix(s['shape_local_pose']);s['solver_pose']=np.r_[M[:3,3],t3d.quaternions.mat2quat(M[:3,:3])].tolist()
        M=AP@matrix(s['shape_local_pose']);points.extend(np.asarray(s['vertices'])@M[:3,:3].T+M[:3,3])
    witness=support_witness(export,can,actor,cap['base'])
    full=model_collision_audit(cfg,n,export,{'support_name':'NO_FILTER'})
    pair=model_collision_audit(cfg,n,export,witness)
    points=np.asarray(points);sampled=np.asarray([points+[0,0,z] for z in np.linspace(0,.12,31)])
    escape=native_escape_checks(sampled,witness['support_plane_z_m'])
    # Translate actual grasp+can by12cm only to verify the end support distance;
    # no hypothetical arm qpos or collision-free arm plan is fabricated.
    value={'schema_version':'f2_saved_postclose_support_pair_CPU_v1','saved_trace_postclose_index':index,'source_is_historical_F2_not_new_scene':True,
      'native_support_witness':witness,'full_model_CPU_nearest':full['world_nearest'],'pair_model_CPU_nearest':pair['world_nearest'],
      'pair_model_CPU_self_overlaps':pair['self_buffered_overlaps'],'straight_up_12cm_native_geometry':escape,
      'full_vs_pair_support_conflict_reproduced':full['world_nearest'][0]['buffered_clearance_m']<0 and full['world_nearest'][0]['link']=='attached_can' and full['world_nearest'][0]['obstacle']==witness['support_name'],
      'filtered_model_other_world_pairs_clear':all(r['buffered_clearance_m']>=0 for r in pair['world_nearest']),
      'actual_new_prefix_plan_or_execution_verified':False,'new_solver_problems':0,'new_scenes':0,'physical_Gates_changed':False}
    value['receipt_sha256']=digest(value);return value

if __name__=='__main__':
    r=audit()
    from realization_utf8_io_v1 import write_new
    write_new(Path(__file__).parent/'postclose_cpu_audit.json',r);print(json.dumps(r,ensure_ascii=False,indent=2))
