"""Deterministic replay of saved target geometry, no IK/scene/GPU."""
import copy,itertools,json,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np,yaml,transforms3d as t3d
from mplib import Pose
from mplib.collision_detection import fcl
from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix,pose
from goal_pilot48_v1.f2_prefix_clearance_runtime_v2.certificate import negative_pairs
from goal_pilot48_v1.f2_inside_native_floor_v1.certificate import build_certificate,sha,digest
from goal_pilot48_v1.f2_inside_native_floor_v1.geometry_verifier import GeometryVerifier
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';P=W/'Robotwin2/project/RoboTwin';D=W/'Robotwin2/datasets/p48_f2_inside_carry_revision1_002'
sys.path.insert(0,str(A/'f2_f3_model_bridge_v1_1'));sys.path.insert(0,str(A/'f3_model_replay_v1'))
from transforms import planner_view,reported_eef_goal_to_solver_goal
from kinematics_cpu import root_transform,collision_description,URDF

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def context():
    r=load(D/'inside_result.json');m=load(D/'model_010_carried_full.json');s=r['spec'];k=m['config']['kinematics'];box=next(x for x in m['world']['shapes'] if x['role']=='box')['actor_world_pose']
    with np.load(D/'qualification_trace.npz',allow_pickle=False) as z:E=z['eef_pose'][-1].copy();C=z['role_object_pose__main_can'][-1].copy();queries=json.loads(str(z['planner_queries_json'].item()))
    cfg=yaml.safe_load((P/'assets/embodiments/aloha-agilex/config.yml').read_text());pcfg=yaml.safe_load((P/'assets/embodiments/aloha-agilex/curobo_left.yml').read_text())
    robot=SimpleNamespace(left_gripper_bias=cfg['gripper_bias'],left_inv_delta_matrix=np.linalg.inv(cfg['delta_matrix']));planner=planner_view(cfg['robot_pose'][0],pcfg['planner']['frame_bias'],'aloha-agilex/curobo_left.yml')
    check=m['checks']['motion_gen'];named=dict(zip(check['full_model_joint_names'],check['full_model_qpos']));rootE=root_transform('fl_link6',named)
    c=build_certificate(m['can'],[x for x in m['world']['shapes'] if x['role']=='box'],binding_sha256=s['binding_sha256'])
    return dict(result=r,model=m,spec=s,kin=k,box=box,eef=E,can=C,queries=queries,robot=robot,planner=planner,named=named,rootE=rootE,certificate=c,verifier=GeometryVerifier(c))

def goal_solver(c,goal):return matrix(reported_eef_goal_to_solver_goal(c['robot'],c['planner'],goal))
def summarize(pairs):
    groups={}
    for p in pairs:
        key=p['link']+'/'+p['obstacle'];v=groups.setdefault(key,{'count':0,'minimum_clearance_m':0.});v['count']+=1;v['minimum_clearance_m']=min(v['minimum_clearance_m'],p['clearance_m'])
    return {'count':len(pairs),'groups':groups}

def hand_parts(c,G):
    parts=[]
    for i in (6,7,8):
        left='fl_link'+str(i);right='fr_link'+str(i)
        if collision_description(left)!=collision_description(right):raise ValueError('left/right native collision definitions differ')
        shape=next(s for s in c['model']['world']['shapes'] if s['role']==right)
        T=G@np.linalg.inv(c['rootE'])@root_transform(left,c['named'])@matrix(shape['shape_local_pose']);parts.append((left,shape,T))
    return parts

def collision_object(s,T):
    vertices=np.asarray(s['vertices']);faces=np.asarray(s['faces'],dtype=np.int32);mesh=fcl.BVHModel();mesh.begin_model(len(faces),len(vertices));mesh.add_sub_model(vertices,faces);mesh.end_model()
    return fcl.CollisionObject(mesh,Pose(T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])))

def hand_native(c,G):
    world=[(s,collision_object(s,matrix(s['solver_pose']))) for s in c['model']['world']['shapes']];hits=[]
    for link,shape,T in hand_parts(c,G):
        hand=collision_object(shape,T)
        for target,other in world:
            if fcl.collide(hand,other).is_collision():hits.append(link+'/'+target['name'])
    return {'surface_intersections':hits,'pass_surface_test':not hits,'equal_left_right_native_URDF_templates_verified':True,
      'live_right_body_local_native_templates_used_for_equal_left_geometry':True,'whole_arm_or_GPU_candidate_check':False}

def goal_audit(c,goal):
    G=goal_solver(c,goal);kin=c['kin'];result={}
    for label,pad in (('configured_buffer',kin['collision_sphere_buffer']),('zero_buffer_CPU_diagnostic',0.)):
        attached=np.asarray([[*(G[:3,:3]@np.asarray(s['center'])+G[:3,3]),s['radius']+pad] for s in kin['collision_spheres']['attached_can']]);hand=[];links=[]
        for link in ('fl_link6','fl_link7','fl_link8'):
            if link not in kin['collision_link_names']:continue
            T=G@np.linalg.inv(c['rootE'])@root_transform(link,c['named'])
            for s in kin['collision_spheres'][link]:hand.append([*(T[:3,:3]@np.asarray(s['center'])+T[:3,3]),s['radius']+pad]);links.append(link)
        result[label]={'attached_can':summarize(negative_pairs(attached,['attached_can']*len(attached),c['model']['world'])),
          'hand':summarize(negative_pairs(np.asarray(hand),links,c['model']['world']))}
    result['native_hand']=hand_native(c,G);result['solver_goal']=pose(G);return result

def upright_top_bound(c):
    cert=c['certificate'];T=matrix(c['can']);T[:2,3]=c['spec']['target_actor_pose'][:2];B=matrix(c['box']);relative=np.linalg.inv(B)@T
    center=np.asarray(cert['can_native_center_m']);half=np.asarray(cert['can_native_half_extents_m']);corners=np.asarray([center+half*np.asarray(sign) for sign in itertools.product((-1,1),repeat=3)])
    local=corners@relative[:3,:3].T+relative[:3,3];T[:3,3]+=B[:3,1]*(cert['unchanged_strict_upper_m'][1]-local[:,1].max())
    E=T@np.linalg.inv(np.linalg.inv(matrix(c['eef']))@matrix(c['can']))
    return {'actor_pose':pose(T),'eef_pose':pose(E),'preserves_actual_grasp_orientation':True,'analytical_highest_legal_top_pose_not_height_scan':True,
      'box_Y_native_envelope_span_m':float(np.ptp(local[:,1])),'native_geometry':c['verifier'].evaluate(pose(T),c['box'],binding_sha256=cert['binding_sha256'])}

def analyze():
    c=context();g=c['spec']['targets'][1]['pose'];E=matrix(c['eef']);C=matrix(c['can']);G=goal_solver(c,g);implied=matrix(c['model']['base'])@G@np.asarray(c['model']['T_solver_eef_can']);nominal=matrix(g)@np.asarray(c['spec']['actual_eef_to_can']);grasp=np.linalg.inv(E)@C
    rotation=E[:3,:3].T@matrix(g)[:3,:3];up=upright_top_bound(c);up['hand_and_model']=goal_audit(c,up['eef_pose'])
    paths=[D/'inside_result.json',D/'qualification_trace.npz',D/'model_005_carried_full.json',D/'model_010_carried_full.json',URDF,
      P/'envs/robot/robot.py',P/'envs/robot/planner.py',P/'assets/embodiments/aloha-agilex/config.yml',P/'assets/embodiments/aloha-agilex/curobo_left.yml',
      A/'f2_f3_model_bridge_v1_1/transforms.py',A/'f3_model_replay_v1/kinematics_cpu.py',A/'goal_pilot48_v1/f2_controlled_inside_runtime_v2/spec.py',
      A/'goal_pilot48_v1/f2_inside_native_floor_v1/saved_contact_geometry.json',W/'Vault-on-Fvl09/数据构造/数据构造方案.md',Path(__file__)]
    paths+=list((A/'goal_pilot48_v1/f2_inside_native_floor_v1').glob('*.py'))
    r={'schema_version':'f2_inside_preinsert_endpoint_geometry_diagnosis_v1','CPU_only':True,'new_solver_scene_action_calls':0,
      'actual_queries':[{k:q[k] for k in ('source','start_step','end_step','status','motiongen_result_side_channel')} for q in c['queries']],
      'plan0_actual_execution':next(e['receipt']['original_execution_receipt'] for e in c['result']['events'] if e['stage']=='execute_0'),
      'actual_model_start_valid':{k:v['valid'] for k,v in c['model']['checks'].items()},'current_eef':c['eef'].tolist(),'old_preinsert_eef':g,
      'translation_delta_m':(np.asarray(g[:3])-c['eef'][:3]).tolist(),'rotation_delta_deg':float(np.degrees(np.arccos(np.clip((np.trace(rotation)-1)/2,-1,1)))),
      'actual_grasp_translation_drift_m':float(np.linalg.norm(grasp[:3,3]-np.asarray(c['spec']['actual_eef_to_can'])[:3,3])),
      'actual_implied_minus_nominal_can_xyz_m':(implied[:3,3]-nominal[:3,3]).tolist(),'old_goal_necessary_conditions':goal_audit(c,g),
      'single_preserved_orientation_necessary_condition':up,'executable_replacement_found':False,'sources':{str(p):sha(p) for p in paths}}
    r['receipt_sha256']=digest(r);return r

if __name__=='__main__':
    r=analyze();out=Path(__file__).with_name('DIAGNOSIS_001.json')
    with out.open('x',encoding='utf-8') as f:json.dump(r,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print({'receipt_sha256':r['receipt_sha256'],'old_hand_native':r['old_goal_necessary_conditions']['native_hand']['surface_intersections'],
      'upright_native_pass':r['single_preserved_orientation_necessary_condition']['native_geometry']['pass']})
