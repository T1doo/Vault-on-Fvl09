"""New recipe current/pregrasp/grasp full-constraint IK, no physical actions."""
import copy,json,sys,traceback
from pathlib import Path
import numpy as np
import yaml
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计'
sys.path.insert(1,str(A/'f2_f3_model_bridge_v1_1'));sys.path.insert(2,str(A/'new_recipe_prereqs_v1'));sys.path.insert(3,str(A));sys.path.append(str(A/'f2_endpoint_constraint_runtime_v1_1'))
from f3_conformance import helper,candidates,candidate_spec,SOURCE_SHA
from geometry import capture_scene_collision_geometry,make_world,closest_pairs,matrix
from model_apply import bind_actual_solver_base,runtime_joint_state,verify_actual_world_cache,link_conformance
from transforms import full_joint_state_to_solver_joint_state
from goal_mapping import actual_flange_goal_to_reported_command,reported_command_to_actual_solver_goal
from realization_utf8_io_v1 import write_new
from ik_config import profile_config

def run_scene(recipe,proposal,out):
    import torch
    from curobo.types.math import Pose
    from curobo.types.state import JointState
    from curobo.wrap.reacher.ik_solver import IKSolver,IKSolverConfig
    from curobo.geom.sdf.world import CollisionCheckerType
    from controlled_multi_future.planner_qualification_manifests_v2_3 import _f3_scene_binding
    from controlled_multi_future.real_sapien_adapter_high_level_v1 import _PinnedSapienRenderDeviceContextV1
    from controlled_multi_future.family_runners_v3_1 import _arm_eef_pose
    h=helper();legacy=candidate_spec(recipe);adapter=h.adapter_for('F3',legacy,out/'adapter',SOURCE_SHA)
    ctx=_PinnedSapienRenderDeviceContextV1(adapter.scene(legacy,phase='NEW_TOPDOWN_FULL_CONSTRAINT_IK',program=None));rows=[];error=None;before=after=None
    try:
        with ctx as handle:
            scene=handle.scene
            if not hasattr(scene,'planner_query_count'):scene.planner_query_count=0
            before=scene.planner_query_count
            try:
                binding=h.prepare_f3_scene(scene,adapter,recipe,_f3_scene_binding(recipe));planner=scene.robot.left_planner;bind_actual_solver_base(scene,planner)
                export=capture_scene_collision_geometry(scene,planner);write_new(out/'geometry.json',export);write_new(out/'scene_binding.json',binding)
                names,q=runtime_joint_state(scene);cfg=yaml.safe_load(Path(planner.yml_path).read_text(encoding='utf-8'))['robot_cfg'];kin=cfg['kinematics']
                kin['lock_joints']={n:float(q[names.index(n)]) for n in kin['lock_joints']};kin['link_names']=['fl_link6','fl_link7','fl_link8']
                profile=profile_config('K2');kw=copy.deepcopy(profile['kwargs']);kw.update(copy.deepcopy(profile['configs']));kw.update(collision_checker_type=CollisionCheckerType.MESH,collision_cache={'mesh':len(export['shapes']),'obb':1})
                solver=IKSolver(IKSolverConfig.load_from_robot_config(cfg,make_world(export),**kw));start=full_joint_state_to_solver_joint_state(q,names,solver.kinematics.joint_names);tensor=solver.tensor_args.to_device(start).reshape(1,-1)
                application={'actual_cache':verify_actual_world_cache(solver,export),'actual_FK':link_conformance(scene,planner,solver,tensor),'locked_joints':kin['lock_joints'],'profile':profile}
                if any(r['position_error_m']>.005 or r['orientation_error_rad']>.05 for r in application['actual_FK']):raise ValueError('model FK conformance')
                write_new(out/'model_application.json',application)
                actual=np.asarray(_arm_eef_pose(scene,'left'));grasp=np.asarray(proposal['desired_actual_flange_world_pose']);pre=grasp.copy();pre[2]+=.12
                solver.reset_seed();bank=solver.get_seed(32,Pose.from_list([0,0,0,1,0,0,0]),False,seed_config=tensor.reshape(1,1,-1)).reshape(1,32,-1).clone()
                with (out/'seed_bank.npz').open('xb') as f:np.savez_compressed(f,seeds=bank.cpu().numpy())
                for label,target in [('current_control',actual),('pregrasp',pre),('grasp',grasp)]:
                    command=actual_flange_goal_to_reported_command(scene.robot,planner,target);goal=reported_command_to_actual_solver_goal(scene.robot,planner,command)
                    expected=np.linalg.inv(matrix(planner._cmf_solver_base_world_pose))@matrix(target)
                    if not np.allclose(matrix(goal),expected,atol=1e-7,rtol=0):raise ValueError('live roundtrip target mapping mismatch')
                    write_new(out/(label+'.start.json'),{'label':label,'actual_world_goal':target.tolist(),'reported_command':command.tolist(),'solver_goal':goal.tolist(),'IK_problem_count':1})
                    r=solver.solve_single(Pose.from_list(goal.tolist()),retract_config=tensor,seed_config=bank.clone(),return_seeds=32,num_seeds=32,use_nn_seed=False)
                    values=r.solution.reshape(-1,6)
                    if not bool(torch.isfinite(values).all()):raise ValueError('nonfinite IK solution')
                    js=JointState.from_position(values,joint_names=solver.kinematics.joint_names);feasible=solver.check_constraints(js).feasible.cpu().numpy().reshape(-1).astype(bool)
                    state=solver.kinematics.get_state(values);pos=state.ee_position.cpu().numpy();quat=state.ee_quaternion.cpu().numpy();error_pos=np.linalg.norm(pos-goal[:3],axis=1)
                    dots=np.clip(np.abs((quat/np.linalg.norm(quat,axis=1)[:,None])@(goal[3:]/np.linalg.norm(goal[3:]))),0,1);rot=np.sqrt(np.maximum(0,1-dots*dots));valid=feasible&(error_pos<=.005)&(rot<=.05)
                    row={'goal':label,'desired_actual_world_pose':target.tolist(),'reported_command':command.tolist(),'solver_goal':goal.tolist(),'solver_reported_success':r.success.cpu().numpy().reshape(-1).tolist(),
                        'solutions':[{'qpos':values[i].cpu().numpy().tolist(),'position_error_m':float(error_pos[i]),'orientation_angle_rad':float(2*np.arccos(dots[i])),'sin_half_angle_metric':float(rot[i]),'full_constraint_feasible':bool(feasible[i]),'valid':bool(valid[i])} for i in range(len(values))],
                        'nearest_pairs_first_solution':closest_pairs(solver.kinematics,values[0:1],export),'full_valid_count':int(valid.sum()),'pass':bool(valid.any())}
                    write_new(out/(label+'.json'),row);rows.append(row);print(proposal['proposal_id'],label,row['full_valid_count'],flush=True)
            finally:after=scene.planner_query_count
    except BaseException as exc:error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    starts=list(out.glob('*.start.json'));known=type(before)is int and type(after)is int and before==after and len(starts)==len(rows)
    cleanup=ctx.cleanup_receipt;safe=known and error is None and cleanup is not None and cleanup.get('cleanup_safety_pass')is True
    result={'proposal_id':proposal['proposal_id'],'parent_recipe_id':recipe['recipe_id'],'results':rows,'error':error,'cleanup':cleanup,'IK_problem_attempts':len(starts),'IK_completions':len(rows),
        'trajectory_queries':after-before if type(before)is int and type(after)is int else None,'accounting_complete':known,'physical_attempts':0,'scene_attempts':1,'global_stop':not safe,
        'all_three_goals_pass':len(rows)==3 and all(r['pass'] for r in rows)}
    write_new(out/'scene_receipt.json',result);return result

def run(manifest):
    out=Path(manifest['jobs'][0]['output_namespace']);out.mkdir(parents=True,exist_ok=False)
    proposals=json.loads((A/'F3_GEOMETRY_TOPDOWN_PROPOSAL_V1_20260906.json').read_text(encoding='utf-8'))['proposals'];rows=[]
    for recipe,proposal in zip(candidates(),proposals):
        d=out/proposal['proposal_id'];d.mkdir();r=run_scene(recipe,proposal,d);rows.append(r)
        if r['global_stop']:break
    return {'schema_version':'cmf_f3_topdown_qualification_terminal_v1','manifest_sha256':manifest['manifest_sha256'],'scenes':rows,'scene_attempts':len(rows),'IK_problems':sum(r['IK_problem_attempts'] for r in rows),
        'trajectory_queries':0 if all(r['trajectory_queries']==0 for r in rows) else None,'physical_attempts':0,'accounting_complete':all(r['accounting_complete'] for r in rows),
        'qualified_recipes':[r['proposal_id'] for r in rows if r['all_three_goals_pass']],'pass':len(rows)==2 and all(not r['global_stop'] for r in rows),'new_raw':0,'new_roots':0}
