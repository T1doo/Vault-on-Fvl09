"""Read saved prefix001 once; native gap, real contact and model-only bounds."""
import copy,json,hashlib,sys
from pathlib import Path
import numpy as np
import transforms3d as t3d
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';D=W/'Robotwin2/datasets/p48_f2_prefix_001';OUT=Path(__file__).parent
sys.path.insert(0,str(A/'f3_model_replay_v1'))
from kinematics_cpu import link_world
from goal_pilot48_v1.f2_inward_failure_review_v1.analyze import model_collision_audit
from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix,pose
from controlled_multi_future.f3_physical_contact_signal_v8 import classify_contact_pair_physical_hit_v8

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def angle(q,r):return float(2*np.arccos(np.clip(abs(np.dot(q/np.linalg.norm(q),r/np.linalg.norm(r))),0,1)))

def audit():
    with np.load(D/'partial_prefix_trace.npz',allow_pickle=False) as z:
        fields=('joint_qpos','eef_pose','role_object_pose__main_can','contact_pairs_json','selected_gripper_contact','selected_gripper_contact_impulse',
          'realized_left_gripper_joint_qpos','role_object_linear_velocity__main_can','role_object_angular_velocity__main_can','gripper_command')
        data={k:np.array(z[k]) for k in fields}
    capture=load(D/'prefix_open_model.json');shapes=capture['world']['shapes'];can=[s for s in shapes if s['role']=='held_can'];table=[s for s in shapes if s['role']=='table']
    s=table[0];B=matrix(s['actor_world_pose'])@matrix(s['shape_local_pose'])@np.linalg.inv(matrix(s['solver_pose']))
    frame_error=max(float(np.max(abs(B@matrix(s['solver_pose'])-matrix(s['actor_world_pose'])@matrix(s['shape_local_pose'])))) for s in shapes)
    table_top=max(float((np.asarray(s['vertices'])@(matrix(s['actor_world_pose'])@matrix(s['shape_local_pose']))[:3,:3].T+(matrix(s['actor_world_pose'])@matrix(s['shape_local_pose']))[:3,3])[:,2].max()) for s in table)
    native=[]
    for s in can:
        T=matrix(s['shape_local_pose']);native.extend(np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3])
    native=np.asarray(native);gaps=[];contacts=[];rel=[]
    for i,actor in enumerate(data['role_object_pose__main_can']):
        T=matrix(actor);vertices=native@T[:3,:3].T+T[:3,3];gaps.append(float(vertices[:,2].min()-table_top))
        if i>=len(data['eef_pose'])-50:
            pairs=json.loads(str(data['contact_pairs_json'][i]));summary={'row':i,'table':False,'left_finger':False,'right_finger':False,'all_relevant_complete':True,'table_impulse':0.,'selected_finger_impulse':0.}
            for pair in pairs:
                names={pair['body_a'],pair['body_b']}
                if can[0]['actor_name'] not in names:continue
                signal=classify_contact_pair_physical_hit_v8(pair)
                if 'table' in names or names&{'fl_link7','fl_link8'}:
                    summary['all_relevant_complete'] &= signal['evidence_complete']
                hit=signal['physical_hit_for_gate']
                if 'table' in names:summary['table'] |=hit;summary['table_impulse']+=pair['impulse_norm_sum']
                if 'fl_link7' in names:summary['left_finger'] |=hit
                if 'fl_link8' in names:summary['right_finger'] |=hit
                if names&{'fl_link7','fl_link8'}:summary['selected_finger_impulse']+=pair['impulse_norm_sum']
            contacts.append(summary);rel.append(np.linalg.inv(matrix(data['eef_pose'][i]))@T)
    q0=t3d.quaternions.mat2quat(rel[0][:3,:3]);relative_translation=max(float(np.linalg.norm(r[:3,3]-rel[0][:3,3])) for r in rel)
    relative_angle=max(angle(t3d.quaternions.mat2quat(r[:3,:3]),q0) for r in rel)
    reference=W/'Robotwin2/datasets/p48_f2_u_route_001';ref=load(reference/'live_capture.json');cfg=copy.deepcopy(load(reference/'carried_robot_config.json')['kinematics'])
    names=ref['joint_names'];n=dict(zip(names,data['joint_qpos'][-1]));nr=dict(zip(names,ref['qpos']))
    base=pose(B);EP=link_world('fl_link6',n,base);ER=link_world('fl_link6',nr,ref['base'])
    AP=matrix(data['role_object_pose__main_can'][-1]);AR=matrix(ref['can_shapes'][0]['actor_world_pose']);transfer=np.linalg.inv(EP)@AP@np.linalg.inv(AR)@ER
    for sphere in cfg['collision_spheres']['attached_can']:sphere['center']=(transfer[:3,:3]@sphere['center']+transfer[:3,3]).tolist()
    cfg['lock_joints']={k:float(n[k]) for k in cfg['lock_joints']}
    export={'shapes':[s for s in shapes if s['role']!='held_can']}
    model=model_collision_audit(cfg,n,export,{'support_name':'NO_FILTER'})
    physical_table_count=sum(x['table'] for x in contacts);both=sum(x['left_finger'] and x['right_finger'] for x in contacts)
    result={'schema_version':'f2_prefix001_postclose_native_contact_CPU_review_v1','source_scene_rows':len(gaps),'table_top_world_z_m':table_top,
      'frame_reconstruction_max_error':frame_error,'initial_native_gap_m':gaps[0],'terminal_native_gap_m':gaps[-1],
      'last50_native_gap_range_m':[min(gaps[-50:]),max(gaps[-50:])],'last50_contacts':contacts,'last50_physical_table_frames':physical_table_count,
      'last50_both_fingers_physical_frames':both,'last10_table_frames':sum(x['table'] for x in contacts[-10:]),'last10_both_fingers_frames':sum(x['left_finger'] and x['right_finger'] for x in contacts[-10:]),
      'last50_all_relevant_contact_evidence_complete':all(x['all_relevant_complete'] for x in contacts),
      'last50_grasp_relative_translation_drift_m':relative_translation,'last50_grasp_relative_orientation_drift_rad':relative_angle,
      'last50_linear_speed_max_mps':float(np.linalg.norm(data['role_object_linear_velocity__main_can'][-50:],axis=1).max()),
      'last50_angular_speed_max_rps':float(np.linalg.norm(data['role_object_angular_velocity__main_can'][-50:],axis=1).max()),
      'terminal_finger_qpos_m':data['realized_left_gripper_joint_qpos'][-1].tolist(),'terminal_gripper_command':data['gripper_command'][-1].tolist(),
      'terminal_can_rotation_from_initial_rad':angle(data['role_object_pose__main_can'][-1,3:],data['role_object_pose__main_can'][0,3:]),
      'CPU_transferred_literal_sphere_model':model,'sphere_model_method':'rigidly transfer saved F2 can-body spheres into current actual EEF-can transform; not fresh GPU sphere fitting/kernel validation',
      'new_GPU_or_solver_calls':0,'old_sources_changed':False,'input_files':{str(p):sha(p) for p in (D/'partial_prefix_trace.npz',D/'prefix_open_model.json',D/'job_terminal.json',reference/'live_capture.json',reference/'carried_robot_config.json')}}
    from goal_pilot48_v1.f2_inward_runtime_v1.contract import digest
    result['receipt_sha256']=digest(result);return result

if __name__=='__main__':
    r=audit()
    from realization_utf8_io_v1 import write_new
    write_new(OUT/'analysis.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ('last50_contacts','input_files')},ensure_ascii=False,indent=2))
