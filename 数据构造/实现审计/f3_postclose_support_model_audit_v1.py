"""CPU audit of saved hold contacts and literal attached-model world clearance."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
import trimesh
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';D=W/'Robotwin2/datasets/f3_r3063_bootstrap_replacement_v1'
sys.path.insert(0,str(A/'f3_model_replay_v1'));sys.path.insert(1,str(A/'f2_f3_model_bridge_v1_1'));sys.path.insert(2,str(A))
from kinematics_cpu import link_world
from geometry import matrix
from controlled_multi_future.geometry import relative_pose
from controlled_multi_future.anchor import quaternion_angular_error
from controlled_multi_future.f3_physical_contact_signal_v8 import classify_contact_pair_physical_hit_v8
from realization_utf8_io_v1 import write_new
def run():
    terminal=json.loads((D/'job_terminal.json').read_text(encoding='utf-8'));model=json.loads((D/'postclose_attached_model.json').read_text(encoding='utf-8'))
    base=json.loads((W/'Robotwin2/datasets/f3_remaining_model_scene_v1_1/remaining_scene/f3-final-pose-v3-r3063/initial_geometry.json').read_text())['solver_base_binding']['base_link_world_pose'];B=matrix(base)
    named=dict(zip(model['actual_joint_names'],model['actual_qpos']));T=link_world('fl_link6',named,base)
    with np.load(D/'physical_trace.npz',allow_pickle=False) as z:
        assert len(z['timestamp'])==terminal['result']['post_close_baseline_row']+1
        assert np.linalg.norm(T[:3,3]-z['eef_pose'][-1,:3])<1e-5
        selected=set(json.loads(str(z['selected_gripper_links_json'].item())));stats=[];poses=z['object_pose'][-250:];eef=z['eef_pose'][-250:];start=relative_pose(eef[0],poses[0]);td=[];rd=[]
        contacts=z['contact_pairs_json']
        for i in range(len(z['timestamp'])-250,len(z['timestamp'])):
            hits=[];finger=set();support=False;forbidden=False;complete=True
            for pair in json.loads(str(contacts[i])):
                c=classify_contact_pair_physical_hit_v8(pair);complete &= c['evidence_complete'] is True
                if not c['physical_hit_for_gate']:continue
                bodies={pair['body_a'],pair['body_b']};arm={b for b in bodies if b.startswith('fl_')}
                is_bottle='f3_main_bottle' in bodies
                if is_bottle:finger|=bodies&selected;support|=bool(bodies&{'table','f3_original_pad','f3_pad','original_pad'})
                if len(arm)==2 or (arm and bodies&{'table','f3_original_pad','f3_pad','original_pad'}) or (is_bottle and arm and not arm.issubset(selected)):forbidden=True
                hits.append(sorted(bodies))
            stats.append({'row':i,'physical_pairs':hits,'selected_contact':bool(finger),'both_selected_fingers':len(finger)==len(selected),'bottle_support_contact':support,'forbidden':forbidden,'complete':complete})
        for a,b in zip(eef,poses):
            p=relative_pose(a,b);td.append(float(np.linalg.norm(p[:3]-start[:3])));rd.append(float(quaternion_angular_error(p[3:],start[3:])))
        hold={'frames':250,'all_selected_contact':all(r['selected_contact'] for r in stats),'all_both_fingers':all(r['both_selected_fingers'] for r in stats),'forbidden_count':sum(r['forbidden'] for r in stats),'support_contact_frames':sum(r['bottle_support_contact'] for r in stats),'all_signal_complete':all(r['complete'] for r in stats),'max_relative_translation_drift_m':max(td),'max_relative_orientation_drift_rad':max(rd),'object_endpoint_displacement_m':float(np.linalg.norm(poses[-1,:3]-poses[0,:3])),'actual_gripper_qpos_final':z['realized_left_gripper_joint_qpos'][-1].tolist(),'commanded_gripper_drive_target_final':z['left_gripper_joint_drive_target'][-1].tolist(),'first_physical_pairs':stats[0]['physical_pairs'],'last_physical_pairs':stats[-1]['physical_pairs']}
    world=json.loads((W/'Robotwin2/datasets/f3_new_topdown_qualification_v1/f3-final-pose-v3-r3063-topdown-geometry-v1/geometry.json').read_text(encoding='utf-8'))['shapes']
    cfg=model['robot_config']['kinematics'];buffer=float(cfg['collision_sphere_buffer']);centers=[];radii=[];links=[]
    for name,spheres in cfg['collision_spheres'].items():
        if name not in cfg['collision_link_names']:continue
        frame=T if name=='attached_bottle' else link_world(name,named,base)
        for s in spheres:
            if float(s['radius'])+buffer<=0:continue
            centers.append(frame[:3,:3]@np.asarray(s['center'])+frame[:3,3]);radii.append(float(s['radius'])+buffer);links.append(name)
    centers=np.asarray(centers);radii=np.asarray(radii);pairs=[]
    for shape in world:
        if shape['role']=='bottle':continue
        actor=link_world(shape['role'],named,base) if shape['role'].startswith('fr_link') else matrix(shape['actor_world_pose'])
        m=trimesh.Trimesh(vertices=shape['vertices'],faces=shape['faces'],process=True);m.apply_transform(actor@matrix(shape['shape_local_pose']));signed=trimesh.proximity.signed_distance(m,centers);gap=-signed-radii
        for index in np.flatnonzero(gap<0):pairs.append({'robot_link':links[index],'obstacle':shape['name'],'role':shape['role'],'buffered_sphere_clearance_m':float(gap[index]),'without_4mm_buffer_clearance_m':float(gap[index]+buffer),'sphere_world_xyz':centers[index].tolist(),'sphere_radius_with_buffer_m':float(radii[index])})
    native=[]
    for s in model['native_bottle_shapes']:
        frame=matrix(s['actor_world_pose'])@matrix(s['shape_local_pose']);v=np.asarray(s['vertices'])@frame[:3,:3].T+frame[:3,3];native.append(v)
    native_min=float(np.concatenate(native)[:,2].min());pad=next(s for s in world if s['role']=='pad');pm=matrix(pad['actor_world_pose'])@matrix(pad['shape_local_pose']);pv=np.asarray(pad['vertices'])@pm[:3,:3].T+pm[:3,3];pad_top=float(pv[:,2].max())
    result={'schema_version':'cmf_f3_postclose_support_model_cpu_audit_v1','trace_sha256':hashlib.sha256((D/'physical_trace.npz').read_bytes()).hexdigest(),'postclose_model_sha256':hashlib.sha256((D/'postclose_attached_model.json').read_bytes()).hexdigest(),'hold':hold,
        'literal_config_sphere_world_overlap_pairs':sorted(pairs,key=lambda x:x['buffered_sphere_clearance_m']),'native_bottle_min_world_z_m':native_min,'pad_top_world_z_m':pad_top,'native_bottle_pad_height_gap_m':native_min-pad_top,
        'only_attached_bottle_support_pairs_overlap':bool(pairs) and all(p['robot_link']=='attached_bottle' and p['role'] in ('table','pad') for p in pairs),
        'solver_reported_status':'MotionGenStatus.INVALID_START_STATE_WORLD_COLLISION','GPU_check_reexecuted':False,'new_scene_count':0,'new_IK_or_trajectory_queries':0,'physical_lift_executed':False}
    write_new(A/'F3_POSTCLOSE_SUPPORT_MODEL_CPU_AUDIT_V1_20260906.json',result);print(json.dumps({'hold':hold,'sphere_overlap_pairs':len(pairs),'only_bottle_support':result['only_attached_bottle_support_pairs_overlap'],'native_pad_gap':native_min-pad_top}))
if __name__=='__main__':run()
