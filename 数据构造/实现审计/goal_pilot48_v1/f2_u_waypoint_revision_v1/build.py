"""Single endpoint-route revision from saved IK; CPU geometry, no new solve."""
import copy
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import transforms3d as t3d
W=Path('/nfs_share/lijunhui'); A=W/'Vault-on-Fvl09/数据构造/实现审计'
D=W/'Robotwin2/datasets/p48_f2_revision1_001'; OUT=Path(__file__).parent
sys.path.insert(0,str(A/'f3_model_replay_v1'))
from kinematics_cpu import root_transform,link_world,collision_description
sys.path.insert(0,str(A/'f2_f3_model_bridge_v1_1'))
from geometry import exact_shape_pairs,matrix,digest
from realization_utf8_io_v1 import write_new

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build():
    cap=load(D/'live_capture.json'); ex=load(D/'world_geometry.json'); wit=load(D/'support_witness.json')
    u=load(D/'IK/U_new.start.json'); dg=load(D/'IK/D_new.start.json'); rows=load(D/'IK/U_new.done.json')['result']['solutions']
    choices=[(i,r) for i,r in enumerate(rows) if r['constraint_checks']['K2'] and r['FK_rotation_metric_sin_half_angle']<=.05]
    index,r=min(choices,key=lambda pair:pair[1]['FK_position_error_m'])
    if index!=15:raise ValueError('saved selected endpoint changed')
    B=matrix(cap['base']); ib=np.linalg.inv(B); n0=dict(zip(cap['joint_names'],cap['qpos'])); E0=ib@link_world('fl_link6',n0,cap['base'])
    named=dict(n0); named.update({f'fl_joint{j+1}':v for j,v in enumerate(r['qpos'])})
    F=ib@link_world('fl_link6',named,cap['base']); e=F[:3,3]-np.asarray(u['solver_goal'][:3]); norm=float(np.linalg.norm(e))
    if e[2]>=0:raise ValueError('no evidence for a downward-only revision')
    lower=(norm+.005)*norm/(-e[2]); old_h=u['reported_goal'][2]-dg['reported_goal'][2]; height=old_h-lower
    if not 0<height<old_h:raise ValueError('one local height revision outside bracket')
    new=np.asarray(u['reported_goal']).copy(); new[2]-=lower
    shapes=[]
    for j in (6,7,8):
        left=f'fl_link{j}';right=f'fr_link{j}'
        if collision_description(left)!=collision_description(right):raise ValueError('unsupported native hand reuse')
        for s in ex['shapes']:
            if s['role']!=right:continue
            sh=copy.deepcopy(s);sh['role']=left;sh['name']=left+'__'+s['name'].rsplit('__',1)[-1]
            T=ib@link_world(left,n0,cap['base'])@matrix(s['shape_local_pose']);sh['relative_to_flange']=np.linalg.inv(E0)@T;shapes.append(sh)
    for s in cap['can_shapes']:
        sh=copy.deepcopy(s);sh['relative_to_flange']=np.linalg.inv(E0)@matrix(s['solver_pose']);shapes.append(sh)
    checks=[]
    for t in np.linspace(0,1,11):
        goal=np.asarray(dg['solver_goal']).copy();goal[2]+=height*(1-t);EE=matrix(goal);hand=[];can=[];vertices=[]
        for s in shapes:
            sh=copy.deepcopy(s);T=EE@sh.pop('relative_to_flange');sh['solver_pose']=np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist()
            if s['role']=='held_can':
                can.append(sh);TW=B@T;vertices.extend(np.asarray(s['vertices'])@TW[:3,:3].T+TW[:3,3])
            else:hand.append(sh)
        pairs=exact_shape_pairs(hand,ex['shapes'])+exact_shape_pairs(can,[s for s in ex['shapes'] if s['name']!=wit['support_name']])
        forbidden=[x for x in pairs if x['mesh_intersection'] and x['physical_collision_filter_enabled']]
        bottom=float(np.asarray(vertices)[:,2].min()-wit['support_plane_z_m'])
        checks.append({'interpolation_t':float(t),'exact_pair_count':len(pairs),'forbidden_pairs':forbidden,'native_can_bottom_gap_m':bottom,'pass':not forbidden and bottom>=-1e-4})
    paths=[D/'live_capture.json',D/'world_geometry.json',D/'support_witness.json',D/'carried_robot_config.json',D/'runtime_revision1_lineage.json',*sorted((D/'IK').glob('*.json'))]
    source=[Path(__file__),A/'f3_model_replay_v1/kinematics_cpu.py',A/'f2_f3_model_bridge_v1_1/geometry.py',A/'f2_f3_model_bridge_v1_1/transforms.py',W/'Robotwin2/project/RoboTwin/assets/embodiments/aloha-agilex/urdf/arx5_description_isaac.urdf']
    result={'schema_version':'f2_U_waypoint_local_revision1_cpu_v1','parent_job_id':'p48_f2_revision1_001','revision_class':'endpoint_route','revision_index':1,
      'layout_revision_count_unchanged':True,'selected_saved_U_solution_index':index,'selected_saved_K2':True,'selected_saved_orientation_metric':r['FK_rotation_metric_sin_half_angle'],
      'CPU_FK_error_solver_xyz_m':e.tolist(),'CPU_FK_error_norm_m':norm,'recorded_GPU_FK_error_norm_m':r['FK_position_error_m'],
      'derivation':'downward crossing of local residual-normal plane, plus one original5mm position-tolerance normal margin; not a certified boundary',
      'formula':'lower=(norm(e)+0.005)*norm(e)/(-e_z)','original_approach_height_m':float(old_h),'lowering_m':float(lower),'new_approach_height_m':float(height),
      'old_U_reported_goal':u['reported_goal'],'new_U_reported_goal':new.tolist(),'unchanged_D_reported_goal':dg['reported_goal'],
      'native_geometry_checks':checks,'exact_pair_count':sum(x['exact_pair_count'] for x in checks),'native_geometry_pass':all(x['pass'] for x in checks),
      'input_files':{str(p):sha(p) for p in paths},'source_files':{str(p):sha(p) for p in source},
      'physical_Gates_changed':False,'layout_D_XY_orientation_seed_changed':False,'full_arm_new_U_IK_verified':False,'continuous_or_planned_path_verified':False,
      'new_solver_problems':0,'new_scenes':0,'new_physical_actions':0,'new_collection_attempts':0}
    result['receipt_sha256']=digest(result);return result

if __name__=='__main__':
    r=build();write_new(OUT/'proposal.json',r);print(json.dumps({k:r[k] for k in ('receipt_sha256','new_approach_height_m','new_U_reported_goal','exact_pair_count','native_geometry_pass')},indent=2))
