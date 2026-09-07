"""Exactly three independently metered full-constraint IK problems; native filters."""
import copy,json,sys
from pathlib import Path
import numpy as np,yaml
from .native import A,Checker
sys.path[:0]=[str(A/'f2_f3_model_bridge_v1_1'),str(A/'new_recipe_prereqs_v1'),str(A/'f2_endpoint_constraint_runtime_v1_1'),str(A)]
def qualify(scene,targets,native_snapshot,out,counts):
    import torch
    from curobo.types.math import Pose
    from curobo.types.state import JointState
    from curobo.wrap.reacher.ik_solver import IKSolver,IKSolverConfig
    from curobo.geom.sdf.world import CollisionCheckerType
    from geometry import capture_scene_collision_geometry,make_world,matrix
    from model_apply import runtime_joint_state,verify_actual_world_cache,link_conformance
    from transforms import full_joint_state_to_solver_joint_state
    from goal_mapping import actual_flange_goal_to_reported_command,reported_command_to_actual_solver_goal
    from ik_config import profile_config
    from controlled_multi_future.family_runners_v3_1 import _arm_eef_pose
    from realization_utf8_io_v1 import write_new
    planner=scene.robot.left_planner;export=capture_scene_collision_geometry(scene,planner);names,q=runtime_joint_state(scene)
    cfg=yaml.safe_load(Path(planner.yml_path).read_text(encoding='utf-8'))['robot_cfg'];kin=cfg['kinematics'];kin['lock_joints']={n:float(q[names.index(n)]) for n in kin['lock_joints']};kin['link_names']=['fl_link6','fl_link7','fl_link8']
    profile=profile_config('K2');kwargs=copy.deepcopy(profile['kwargs']);kwargs.update(copy.deepcopy(profile['configs']));kwargs.update(collision_checker_type=CollisionCheckerType.MESH,collision_cache={'mesh':len(export['shapes']),'obb':1})
    solver=IKSolver(IKSolverConfig.load_from_robot_config(cfg,make_world(export),**kwargs));start=full_joint_state_to_solver_joint_state(q,names,solver.kinematics.joint_names);tensor=solver.tensor_args.to_device(start).reshape(1,-1)
    fk=link_conformance(scene,planner,solver,tensor)
    if any(v['position_error_m']>.005 or v['orientation_error_rad']>.05 for v in fk):raise ValueError('actual IK model FK mismatch')
    write_new(out/'IK_model.json',{'cache':verify_actual_world_cache(solver,export),'FK':fk,'profile':profile,'locks':kin['lock_joints']})
    solver.reset_seed();bank=solver.get_seed(32,Pose.from_list([0,0,0,1,0,0,0]),False,seed_config=tensor.reshape(1,1,-1)).reshape(1,32,-1).clone()
    with (out/'IK_seed_bank.npz').open('xb') as f:np.savez_compressed(f,seeds=bank.cpu().numpy())
    checker=Checker(native_snapshot);rows=[]
    for label,target in [('current',_arm_eef_pose(scene,'left')),('pregrasp',targets['pregrasp']),('grasp',targets['grasp'])]:
        target=np.asarray(target);command=actual_flange_goal_to_reported_command(scene.robot,planner,target);goal=reported_command_to_actual_solver_goal(scene.robot,planner,command)
        if not np.allclose(matrix(goal),np.linalg.inv(matrix(planner._cmf_solver_base_world_pose))@matrix(target),atol=1e-7,rtol=0):raise ValueError('actual/report roundtrip failed')
        write_new(out/(label+'.IK.start.json'),{'actual_goal':target.tolist(),'reported_goal':command.tolist(),'single_problem':1});counts.ik()
        result=solver.solve_single(Pose.from_list(goal.tolist()),retract_config=tensor,seed_config=bank.clone(),return_seeds=32,num_seeds=32,use_nn_seed=False)
        values=result.solution.reshape(-1,6)
        if not bool(torch.isfinite(values).all()):raise ValueError('IK nonfinite result')
        valid=solver.check_constraints(JointState.from_position(values,joint_names=solver.kinematics.joint_names)).feasible.cpu().numpy().reshape(-1).astype(bool)
        state=solver.kinematics.get_state(values);position=state.ee_position.cpu().numpy();quat=state.ee_quaternion.cpu().numpy();pe=np.linalg.norm(position-goal[:3],axis=1)
        dot=np.clip(np.abs((quat/np.linalg.norm(quat,axis=1)[:,None])@(goal[3:]/np.linalg.norm(goal[3:]))),0,1);re=np.sqrt(np.maximum(0,1-dot*dot));valid&=(pe<=.005)&(re<=.05)
        qpos=values.cpu().numpy();checks=[]
        for i in range(len(qpos)):
            native=checker.check(qpos[i:i+1],list(solver.kinematics.joint_names)) if valid[i] else None
            checks.append({'position_error_m':float(pe[i]),'sin_half_angle_metric':float(re[i]),'native':native,'valid':bool(valid[i] and native['pass']) if native else False,'qpos':qpos[i].tolist()})
        row={'target':label,'solutions':checks,'pass':any(c['valid'] for c in checks),'solver_problems':1};write_new(out/(label+'.IK.json'),row);rows.append(row)
        if not row['pass']:break
    return {'pass':len(rows)==3 and all(r['pass'] for r in rows),'results':rows,'IK_problems':counts.IK}
