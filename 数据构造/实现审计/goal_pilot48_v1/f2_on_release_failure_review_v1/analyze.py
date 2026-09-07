"""Read sealed target/model/trace; no IK, planner, simulator or GPU calls."""
import copy,json,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import yaml
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';P=W/'Robotwin2/project/RoboTwin'
D=W/'Robotwin2/datasets/p48_f2_on_beside_qualification_001/on';OUT=Path(__file__).parent
sys.path.insert(0,str(A/'f2_f3_model_bridge_v1_1'));sys.path.insert(1,str(A/'f3_model_replay_v1'))
from transforms import planner_view,reported_eef_goal_to_solver_goal
from kinematics_cpu import link_world,named_state
from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix,pose
from goal_pilot48_v1.f2_prefix_clearance_runtime_v2.certificate import negative_pairs
from goal_pilot48_v1.f2_on_beside_runtime_v1.native import NativeWorld
from goal_pilot48_v1.f2_on_beside_runtime_v1.spec import load,sha,digest

def run():
    spec=load(D/'suffix_spec.json');model=load(D/'model_014_on_full.json');first=load(D/'model_005_on_full.json')
    failed=load(D/'model_016_plan_1_done.json');export=model['world'];cfg=model['config'];kin=cfg['kinematics']
    capture=W/'Robotwin2/datasets/p48_f2_u_route_001/live_capture.json';can=load(capture)['can_shapes']
    with np.load(D/'qualification_trace.npz',allow_pickle=False) as trace:
        last=named_state(trace,-1);actual_can=trace['object_pose'][-1].copy();actual_eef=trace['eef_pose'][-1].copy()
        fullq=trace['joint_qpos'][-1].copy();grip=trace['realized_left_gripper_joint_qpos'][-1].copy()
        endstep=int(trace['step_index'][-1]);prefix_row=load(D/'model_009_execute_0.json')['start_trace_row']
        prefix_actual_can=trace['object_pose'][prefix_row].copy();prefix_actual_eef=trace['eef_pose'][prefix_row].copy()
    bases=[matrix(s['actor_world_pose'])@matrix(s['shape_local_pose'])@np.linalg.inv(matrix(s['solver_pose'])) for s in export['shapes']]
    B=bases[0];base_error=max(float(np.max(abs(b-B))) for b in bases)
    if base_error>1e-5:raise ValueError('inconsistent actual solver base capture')
    base=pose(B);E=link_world('fl_link6',last,base);attachment=np.linalg.inv(E)@matrix(actual_can)
    robotcfg=yaml.safe_load((P/'assets/embodiments/aloha-agilex/config.yml').read_text(encoding='utf-8'))
    pcfg=yaml.safe_load((P/'assets/embodiments/aloha-agilex/curobo_left.yml').read_text(encoding='utf-8'))
    robot=SimpleNamespace(left_gripper_bias=robotcfg['gripper_bias'],left_inv_delta_matrix=np.linalg.inv(robotcfg['delta_matrix']))
    planner=planner_view(robotcfg['robot_pose'][0],pcfg['planner']['frame_bias'],'aloha-agilex/curobo_left.yml')
    goal=np.asarray(spec['targets'][1]['pose']);solvergoal=reported_eef_goal_to_solver_goal(robot,planner,goal)
    desiredE=B@matrix(solvergoal);implied_actor=desiredE@attachment
    nominal_actor=matrix(spec['target_actor_pose']);prefix_grasp=np.asarray(spec['actual_eef_to_can'])
    identity_error=float(np.max(abs(matrix(goal)@prefix_grasp-nominal_actor)))
    native=[]
    for s in can:
        T=matrix(s['shape_local_pose']);native.extend(np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3])
    native=np.asarray(native)
    def bounds(T):
        v=native@T[:3,:3].T+T[:3,3];return {'lower':v.min(0).tolist(),'upper':v.max(0).tolist()}
    entries=kin['collision_spheres']['attached_can'];buffer=float(kin['collision_sphere_buffer']);spherechecks={}
    for label,padding in (('configured_buffer',buffer),('zero_buffer_diagnostic',0.)):
        spheres=np.asarray([[*(matrix(solvergoal)[:3,:3]@np.asarray(s['center'])+matrix(solvergoal)[:3,3]),s['radius']+padding] for s in entries])
        rows=negative_pairs(spheres,['attached_can']*len(spheres),export)
        spherechecks[label]={'padding_m':padding,'count':len(rows),'pairs':rows,'minimum_clearance_m':min((r['clearance_m'] for r in rows),default=None)}
    checker=NativeWorld(export,can,base)
    nativechecks={}
    for label,T in (('nominal_target',nominal_actor),('actual_grasp_solver_implied_target',implied_actor)):
        nativechecks[label]={'bounds_world_m':bounds(T),'check':checker.screen([pose(T)],table_support=False)}
    scales=[]
    for s in export['shapes']:
        if s['role']!='scale':continue
        T=B@matrix(s['solver_pose']);v=np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3]
        scales.append({'name':s['name'],'world_lower':v.min(0).tolist(),'world_upper':v.max(0).tolist()})
    grasp_now=np.linalg.inv(matrix(actual_eef))@matrix(actual_can)
    shifted_goal=nominal_actor@np.linalg.inv(grasp_now)
    contact_names=[r['obstacle'] for r in spherechecks['configured_buffer']['pairs']]
    files=[D/'suffix_spec.json',D/'model_014_on_full.json',D/'model_005_on_full.json',D/'model_016_plan_1_done.json',D/'model_009_execute_0.json',D/'qualification_trace.npz',capture,
      P/'envs/robot/robot.py',P/'envs/robot/planner.py',P/'assets/embodiments/aloha-agilex/config.yml',P/'assets/embodiments/aloha-agilex/curobo_left.yml',Path(kin['urdf_path']),Path(__file__)]
    result={'schema_version':'f2_on_release_saved_target_model_review_v1','CPU_only':True,'new_solver_problems':0,'new_scenes':0,
      'source_files':{str(p):sha(p) for p in files},'last_real_step':endstep,'failure_side_channel':failed['segment_receipts'][0]['planner_query_receipt']['motiongen_result_side_channel'],
      'actual_start_full_checks':model['checks'],'actual_locks':kin['lock_joints'],'actual_gripper_qpos':grip.tolist(),
      'locks_equal_actual_qpos':all(abs(kin['lock_joints'][f'fl_joint{i+7}']-grip[i])<1e-12 for i in range(2)),
      'all_saved_rollout_locks_equal_config':all(r==kin['lock_joints'] for a in model['audits'].values() for r in a['actual_locks']),
      'planner_start_equals_last_actual_qpos':np.array_equal(fullq,failed['segment_receipts'][0]['start_qpos']),
      'actual_base_world_pose':base,'world_base_matrix_max_error':base_error,
      'URDF_actual_flange_vs_trace_matrix_max_error':float(np.max(abs(E-matrix(actual_eef)))),
      'target_actor_pose':spec['target_actor_pose'],'reported_release_goal':goal.tolist(),'analytical_solver_goal':solvergoal.tolist(),
      'original_goal_grasp_target_identity_max_error':identity_error,'actual_grasp_drift_matrix_max_error':float(np.max(abs(grasp_now-prefix_grasp))),
      'actual_grasp_recomputed_goal_translation_delta_m':(shifted_goal[:3,3]-goal[:3]).tolist(),
      'solver_implied_actual_actor_pose':pose(implied_actor),'implied_vs_nominal_translation_m':(implied_actor[:3,3]-nominal_actor[:3,3]).tolist(),
      'native_checks':nativechecks,'scale_piece_world_bounds':scales,'target_scale_point':spec['target_source']['scale_point'],
      'attached_sphere_count':len(entries),'target_attached_sphere_collisions':spherechecks,
      'all_target_buffered_negative_pairs_are_scale':bool(contact_names) and all(n.startswith('scale__') for n in contact_names),
      'mathematical_IK_infeasibility_proven':False,'actual_target_IK_candidates_saved':False,
      'beside_attempted':False,'old_manifest_consumed':True,'new_physical_success':False}
    result['receipt_sha256']=digest(result);return result

if __name__=='__main__':
    from realization_utf8_io_v1 import write_new
    result=run();write_new(OUT/'ANALYSIS_001.json',result)
    print(json.dumps({k:result[k] for k in ('locks_equal_actual_qpos','planner_start_equals_last_actual_qpos','URDF_actual_flange_vs_trace_matrix_max_error','original_goal_grasp_target_identity_max_error','actual_grasp_recomputed_goal_translation_delta_m','implied_vs_nominal_translation_m','all_target_buffered_negative_pairs_are_scale')}))
    print(json.dumps({k:{'count':v['count'],'minimum_clearance_m':v['minimum_clearance_m']} for k,v in result['target_attached_sphere_collisions'].items()}))
    print(json.dumps(result['native_checks']))
