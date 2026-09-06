"""Bounded C/U/D constraint diagnosis with a carried-can collision model."""
import copy,json,sys,time
from pathlib import Path
import numpy as np
import yaml
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';P=W/'Robotwin2/project/RoboTwin'
sys.path.insert(1,str(A/'f2_f3_model_bridge_v1_1'));sys.path.insert(2,str(A));sys.path.append(str(A/'f2_bounded_transit_runtime_v1'))
from geometry import capture_actor_geometry,make_world,digest,closest_pairs
from model_apply import bind_actual_solver_base,runtime_joint_state,verify_actual_world_cache
from transforms import reported_eef_goal_to_solver_goal,full_joint_state_to_solver_joint_state
from realization_utf8_io_v1 import write_new
from semantic_target import corrected_contract,derive_live_targets,old
from ik_config import profile_config

def world_and_can(scene,planner):
    bind_actual_solver_base(scene,planner);world=[]
    actors=[('table',scene.table),('wall',scene.wall)]+[(name,actor) for name,actor in scene.role_actors.items() if name!='main_can']
    actors += [(l.get_name(),l) for l in scene.robot.right_entity.get_links() if l.get_name().startswith('fr_link')]
    for name,actor in actors:world+=capture_actor_geometry(actor,name,planner)
    can=capture_actor_geometry(scene.can,'held_can',planner)
    return {'shapes':world,'geometry_sha256':digest(world)},can

def configure_solvers(scene,export,can):
    import torch
    from curobo.types.math import Pose as CuroboPose
    from curobo.wrap.reacher.ik_solver import IKSolver,IKSolverConfig
    from curobo.geom.sdf.world import CollisionCheckerType
    from curobo.geom.types import Mesh
    from curobo.geom.sphere_fit import SphereFitType
    planner=scene.robot.left_planner;names,q=runtime_joint_state(scene);cfg=yaml.safe_load(open(planner.yml_path,encoding='utf-8'))['robot_cfg']
    active=list(planner.motion_gen.kinematics.joint_names);start=full_joint_state_to_solver_joint_state(q,names,active)
    tensor=planner.motion_gen.tensor_args.to_device(start).reshape(1,-1);ee=planner.motion_gen.kinematics.get_state(tensor).ee_pose
    np.random.seed(1531);torch.manual_seed(1531)
    spheres=[];per_shape=max(8,128//len(can))
    for s in can:
        obj=Mesh(name=s['name'],pose=s['solver_pose'],vertices=s['vertices'],faces=s['faces'])
        fitted=obj.get_bounding_spheres(per_shape,.001,pre_transform_pose=ee.inverse(),tensor_args=planner.motion_gen.tensor_args,fit_type=SphereFitType.VOXEL_VOLUME_SAMPLE_SURFACE)
        spheres += [{'center':[float(x) for x in p.position],'radius':float(p.radius)} for p in fitted]
    if not spheres:raise ValueError('carried can geometry missing')
    kin=cfg['kinematics'];kin['lock_joints']={n:float(q[names.index(n)]) for n in kin['lock_joints']}
    kin['link_names']=['fl_link6','fl_link7','fl_link8']
    sphere_data=yaml.safe_load(Path(kin['collision_spheres']).read_text())['collision_spheres'] if isinstance(kin['collision_spheres'],str) else kin['collision_spheres']
    sphere_data=copy.deepcopy(sphere_data);sphere_data['attached_can']=spheres;kin['collision_spheres']=sphere_data
    kin['collision_link_names']=list(kin['collision_link_names'])+['attached_can']
    kin['extra_links']=dict(kin.get('extra_links') or {})
    kin['extra_links']['attached_can']={'parent_link_name':'fl_link6','link_name':'attached_can','fixed_transform':[0,0,0,1,0,0,0],'joint_type':'FIXED','joint_name':'attached_can_fixed'}
    for link in ('fl_link6','fl_link7','fl_link8'):kin['self_collision_ignore'].setdefault(link,[]).append('attached_can')
    world=make_world(export);solvers={};configs={}
    for name in ('K0','K1','K2'):
        spec=profile_config(name);kwargs=copy.deepcopy(spec['kwargs']);kwargs.update(copy.deepcopy(spec['configs']))
        kwargs.update(collision_checker_type=CollisionCheckerType.MESH,collision_cache={'mesh':len(export['shapes']),'obb':1})
        solvers[name]=IKSolver(IKSolverConfig.load_from_robot_config(copy.deepcopy(cfg),world if name=='K2' else None,**kwargs));configs[name]=spec
    # Same configured Halton generator, same initial-state seed, same frozen bank.
    solvers['K0'].reset_seed();dummy=CuroboPose.from_list(reported_eef_goal_to_solver_goal(scene.robot,planner,scene.robot.get_left_ee_pose()).tolist())
    bank=solvers['K0'].get_seed(32,dummy,False,seed_config=tensor.reshape(1,1,-1)).reshape(1,32,-1).clone()
    audit={}
    for profile,solver in solvers.items():
        rows=[]
        for rollout in solver.get_all_rollout_instances():
            terms={}
            for term in ('primitive_collision_cost','primitive_collision_constraint','robot_self_collision_cost','robot_self_collision_constraint'):
                obj=getattr(rollout,term,None)
                terms[term]=None if obj is None else {'enabled':bool(obj.enabled),'weight':obj.weight.detach().cpu().numpy().tolist()}
                disabled=(profile=='K0') or (profile=='K1' and term.startswith('primitive'))
                if disabled and obj is not None and obj.enabled:raise ValueError('actual collision term remained enabled: '+profile+term)
            rows.append(terms)
        audit[profile]=rows
    audit['K2_actual_world_cache']=verify_actual_world_cache(solvers['K2'],export)
    from model_apply import link_conformance
    audit['actual_link_FK']=link_conformance(scene,planner,solvers['K2'],tensor)
    if any(x['position_error_m']>.005 or x['orientation_error_rad']>.05 for x in audit['actual_link_FK']):raise ValueError('actual model FK mismatch')
    for solver in solvers.values():solver._cmf_export=export
    attachment={'schema_version':'cmf_f2_carried_can_model_v1','actual_constraint_audit':audit,'sphere_count':len(spheres),'sphere_fit':'native VOXEL_VOLUME_SAMPLE_SURFACE, 1mm surface spheres',
        'can_is_static_world_obstacle':False,'can_is_robot_attached_collision_geometry':True,'physical_weld_created':False,
        'normal_grasp_ignore_links':['fl_link6','fl_link7','fl_link8'],'other_environment_collisions_checked':True,
        'parent_link':'fl_link6','relative_pose_from_actual_current_model_FK':True,'native_geometry_file_shapes':can,'robot_config_sha256':digest(cfg)}
    return solvers,configs,bank,start,cfg,attachment

def cross_validate(solvers,solution,solver_goal):
    import torch
    from curobo.types.state import JointState
    values=solution.reshape(-1,solution.shape[-1])
    if not bool(torch.isfinite(values).all()):raise ValueError('nonfinite IK solution; refusing FK/constraint interpretation')
    model=solvers['K2'].kinematics;state=model.get_state(values)
    pos=state.ee_position.detach().cpu().numpy();quat=state.ee_quaternion.detach().cpu().numpy();goal=np.asarray(solver_goal);gq=goal[3:]/np.linalg.norm(goal[3:])
    position=np.linalg.norm(pos-goal[:3],axis=1);dots=np.clip(np.abs((quat/np.linalg.norm(quat,axis=1)[:,None])@gq),0,1)
    angle=2*np.arccos(dots);rotation_metric=np.sqrt(np.maximum(0,1-dots*dots))
    constraints={}
    js=JointState.from_position(values,joint_names=model.joint_names)
    for name,solver in solvers.items():constraints[name]=solver.check_constraints(js).feasible.detach().cpu().numpy().reshape(-1).astype(bool)
    limits=model.get_joint_limits().position.detach().cpu().numpy();q=values.detach().cpu().numpy();margins=np.minimum(q-limits[0],limits[1]-q)
    return [{'qpos':q[i].tolist(),'FK_position_error_m':float(position[i]),'FK_orientation_angle_rad':float(angle[i]),'FK_rotation_metric_sin_half_angle':float(rotation_metric[i]),
        'joint_limit_min_margin_rad':float(margins[i].min()),'constraint_checks':{k:bool(v[i]) for k,v in constraints.items()},
        'full_valid':bool(position[i]<=.005 and rotation_metric[i]<=.05 and all(v[i] for v in constraints.values()))} for i in range(len(q))]

def run_problem(scene,solvers,bank,start,label,profile,goal,output,ordinal):
    from curobo.types.math import Pose as CuroboPose
    solver_goal=reported_eef_goal_to_solver_goal(scene.robot,scene.robot.left_planner,goal)
    write_new(output/(label+'.start.json'),{'ordinal':ordinal,'profile':profile,'reported_goal':goal,'solver_goal':solver_goal.tolist(),'seed_count':32,'grad_iters':100})
    solver=solvers[profile];began=time.monotonic();error=None;result=None
    try:
        r=solver.solve_single(CuroboPose.from_list(solver_goal.tolist()),retract_config=solver.tensor_args.to_device(start).reshape(1,-1),seed_config=bank.clone(),return_seeds=32,num_seeds=32,use_nn_seed=False)
        solutions=cross_validate(solvers,r.solution,solver_goal)
        for i,s in enumerate(solutions):
            if i==0 or s['full_valid']:
                s['nearest_robot_or_carried_can_world_pairs']=closest_pairs(solvers['K2'].kinematics,r.solution.reshape(-1,r.solution.shape[-1])[i:i+1],solver._cmf_export)
        result={'reported_solver_success':r.success.detach().cpu().numpy().reshape(-1).tolist(),'solutions':solutions,'solver_solve_time_s':float(r.solve_time),
            'full_valid_solution_found':any(s['full_valid'] for s in solutions)}
    except BaseException as exc:error={'type':type(exc).__name__,'message':str(exc)}
    receipt={'problem_id':label,'profile':profile,'ordinal':ordinal,'reported_goal':goal,'solver_goal':solver_goal.tolist(),'result':result,'error':error,
        'elapsed_seconds':time.monotonic()-began,'problem_calls':1,'physical_execution':False,'seed_bank_unchanged':True}
    write_new(output/(label+'.json'),receipt);return receipt
