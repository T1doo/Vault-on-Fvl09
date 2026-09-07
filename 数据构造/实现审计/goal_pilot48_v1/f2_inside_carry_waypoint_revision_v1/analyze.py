"""CPU necessary-condition audit of the consumed repeated lift failure."""
import copy,json,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import yaml
from goal_pilot48_v1.f2_controlled_inside_runtime_v2.spec import A,W,digest,matrix,sha
P=W/'Robotwin2/project/RoboTwin';D=W/'Robotwin2/datasets/p48_f2_inside_qualification_001'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def vertices(shape,base):
    T=matrix(base)@matrix(shape['solver_pose']);return np.asarray(shape['vertices'])@T[:3,:3].T+T[:3,3]

def target_from_actual(spec):
    eef=np.asarray(spec['source_actual_state']['eef']);can=np.asarray(spec['source_actual_state']['can']);target=np.asarray(spec['target_actor_pose'])
    shifted=eef.copy();shifted[:2]+=target[:2]-can[:2]
    return {'segment_id':'carry_at_qualified_prefix_height_to_inside_xy','pose':shifted.tolist()}

def bound_against_world(lo,hi,world,base):
    rows=[]
    for shape in world['shapes']:
        v=vertices(shape,base);a=v.min(0);b=v.max(0);separation=np.maximum(a-hi,lo-b);gap=float(separation.max())
        rows.append({'name':shape['name'],'role':shape['role'],'axis_separation_m':separation.tolist(),'separating_axis':int(np.argmax(separation)),
          'minimum_axis_gap_m':gap,'swept_aabb_disjoint':gap>0,'world_z_max_m':float(b[2])})
    return {'pass':all(r['swept_aabb_disjoint'] for r in rows),'world_shapes':rows,'minimum_separating_axis_gap_m':min(r['minimum_axis_gap_m'] for r in rows)}

def sphere_clearance(model,spec,new_target):
    kin=model['config']['kinematics'];spheres=kin['collision_spheres']['attached_can']
    F=matrix(model['can'][0]['actor_world_pose'])@np.linalg.inv(np.asarray(model['T_solver_eef_can']))
    centers=np.asarray([s['center'] for s in spheres])@F[:3,:3].T+F[:3,3]
    radius=np.asarray([s['radius'] for s in spheres])+kin['collision_sphere_buffer']
    if not np.isfinite(radius).all() or not np.all(radius>0):raise ValueError('invalid fitted can spheres')
    shift=np.asarray(new_target['pose'][:3])-spec['source_actual_state']['eef'][:3]
    lower=np.minimum((centers-radius[:,None]).min(0),(centers-radius[:,None]+shift).min(0))
    upper=np.maximum((centers+radius[:,None]).max(0),(centers+radius[:,None]+shift).max(0))
    result=bound_against_world(lower,upper,model['world'],model['base'])
    result.update(schema_version='f2_actual_profile_sphere_buffer_straight_carry_bound_v1',fitted_spheres=len(spheres),unchanged_world_buffer_m=kin['collision_sphere_buffer'],
      buffered_swept_bounds_world=[lower.tolist(),upper.tolist()],robot_arm_kinematics_not_proven=True,actual_fitting_model_receipt_sha256=model['receipt_sha256'])
    result['receipt_sha256']=digest(result);return result

def clearance(world,can,base,spec,new_target):
    initial=np.concatenate([vertices(s,base) for s in can]);shift=np.asarray(new_target['pose'][:3])-spec['source_actual_state']['eef'][:3]
    if shift[2]!=0 or new_target['pose'][3:]!=spec['source_actual_state']['eef'][3:]:raise ValueError('carry revision cannot guess a new height/rotation')
    swept=np.vstack([initial,initial+shift]);lo=swept.min(0);hi=swept.max(0);rows=[]
    for shape in world['shapes']:
        v=vertices(shape,base);a=v.min(0);b=v.max(0)
        separation=np.maximum(a-hi,lo-b);gap=float(separation.max())
        rows.append({'name':shape['name'],'role':shape['role'],'axis_separation_m':separation.tolist(),'separating_axis':int(np.argmax(separation)),
          'minimum_native_axis_gap_m':gap,'native_swept_aabb_disjoint':gap>0,'world_z_max_m':float(b[2])})
    result={'schema_version':'f2_prefix_height_linear_carry_native_swept_bound_v1','pass':all(r['native_swept_aabb_disjoint'] for r in rows),
      'initial_native_bounds_world':[initial.min(0).tolist(),initial.max(0).tolist()],'whole_translation_swept_bounds_world':[lo.tolist(),hi.tolist()],
      'translation_world':shift.tolist(),'world_shapes':rows,'minimum_separating_axis_gap_m':min(r['minimum_native_axis_gap_m'] for r in rows),
      'all_continuous_translations_covered_by_conservative_AABB':True,'robot_arm_clearance_proven':False,
      'arbitrary_planner_path_not_certified_by_this_straight_bound':True,'new_height_chosen':False}
    result['receipt_sha256']=digest(result);return result

def analyze():
    r=load(D/'inside_result.json');m=load(D/'model_005_carried_full.json');spec=r['spec'];new=target_from_actual(spec)
    geometry=clearance(m['world'],m['can'],m['base'],spec,new)
    sys.path.insert(0,str(A/'f2_f3_model_bridge_v1_1'));sys.path.insert(0,str(A/'f3_model_replay_v1'))
    from transforms import planner_view,reported_eef_goal_to_solver_goal
    from kinematics_cpu import root_transform,origin,JOINTS
    robotcfg=yaml.safe_load((P/'assets/embodiments/aloha-agilex/config.yml').read_text(encoding='utf-8'));pcfg=yaml.safe_load((P/'assets/embodiments/aloha-agilex/curobo_left.yml').read_text(encoding='utf-8'))
    robot=SimpleNamespace(left_gripper_bias=robotcfg['gripper_bias'],left_inv_delta_matrix=np.linalg.inv(robotcfg['delta_matrix']))
    planner=planner_view(robotcfg['robot_pose'][0],pcfg['planner']['frame_bias'],'aloha-agilex/curobo_left.yml')
    names=m['checks']['motion_gen']['full_model_joint_names'];q=m['checks']['motion_gen']['full_model_qpos'];named=dict(zip(names,q))
    F=np.linalg.inv(root_transform('fl_base_link',named))@root_transform('fl_link6',named)
    lengths=[float(np.linalg.norm(origin(JOINTS['fl_link'+str(i)])[:3,3])) for i in range(1,7)]
    goals={key:reported_eef_goal_to_solver_goal(robot,planner,value).tolist() for key,value in [('actual',spec['source_actual_state']['eef']),('failed_extra_lift',spec['targets'][0]['pose']),('revised',new['pose'])]}
    reach={key:{'solver_goal':g,'norm_from_base_m':float(np.linalg.norm(g[:3])),'triangle_chain_length_upper_bound_m':sum(lengths),
      'excluded_by_general_triangle_bound':bool(np.linalg.norm(g[:3])>sum(lengths))} for key,g in goals.items()}
    replay_error=float(np.linalg.norm(np.asarray(goals['actual'][:3])-F[:3,3]))
    inputs=[D/'inside_result.json',D/'model_005_carried_full.json',D/'qualification_trace.npz',D/'actual_replay.json',D/'job_terminal.json',
      P/'envs/robot/robot.py',P/'envs/robot/planner.py',P/'assets/embodiments/aloha-agilex/config.yml',P/'assets/embodiments/aloha-agilex/curobo_left.yml',P/'assets/embodiments/aloha-agilex/urdf/arx5_description_isaac.urdf',
      A/'f2_f3_model_bridge_v1_1/transforms.py',A/'f3_model_replay_v1/kinematics_cpu.py']
    result={'schema_version':'f2_inside_repeated_lift_failure_and_unique_carry_revision_v1','parent_job':'p48_f2_inside_qualification_001',
      'observed_error':r['error'],'old_target':spec['targets'][0],'new_target':new,'other_targets_unchanged':spec['targets'][1:],
      'native_continuous_straight_carry':geometry,'actual_fitted_buffered_sphere_straight_carry':sphere_clearance(m,spec,new),'exact_goal_transform_replay_position_error_m':replay_error,
      'URDF_necessary_reach_bounds':reach,'original_full_single_batch_start_valid':all(v['valid'] for v in m['checks'].values()),
      'FK_current_solver_pose':F.tolist(),'asset_layout_or_final_inside_changed':False,'height_scan_performed':False,
      'finite_IK_failure_is_not_mathematical_infeasibility':True,'new_IK_or_planner_or_scene_calls':0,
      'files':{str(p):sha(p) for p in inputs}}
    result['receipt_sha256']=digest(result);return result

if __name__=='__main__':
    r=analyze()
    print(json.dumps({k:v for k,v in r.items() if k not in ('files','native_continuous_straight_carry','FK_current_solver_pose')},ensure_ascii=False,indent=2))
    print(json.dumps(r['native_continuous_straight_carry'],ensure_ascii=False,indent=2))
