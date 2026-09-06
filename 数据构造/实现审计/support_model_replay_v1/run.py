"""Four fixed start-state checks, then at most one non-executed lift plan."""
import copy,json,sys,time,traceback
from pathlib import Path
import numpy as np
import transforms3d as t3d
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计'
sys.path.insert(1,str(A));sys.path.insert(2,str(A/'f2_f3_model_bridge_v1_1'));sys.path.insert(3,str(A/'new_recipe_prereqs_v1'));sys.path.insert(4,str(A/'f3_model_replay_v1'))
from realization_utf8_io_v1 import write_new
from geometry import make_world,matrix
from model_apply import query_state,verify_actual_world_cache
from goal_mapping import cpu_views,reported_command_to_actual_solver_goal
from kinematics_cpu import link_world
from support_pair_collision_v1.factory import build_support_aware_motiongen
from support_pair_collision_v1.policy import audit_lift_escape

def execute(m,out):
    from curobo.types.base import TensorDeviceType
    from curobo.types.math import Pose
    from curobo.types.state import JointState
    from curobo.wrap.reacher.motion_gen import MotionGen,MotionGenConfig,MotionGenPlanConfig
    from curobo.geom.sdf.world import CollisionCheckerType
    import torch
    d=json.loads(Path(m['state_input_path']).read_text(encoding='utf-8'));cfg=d['robot_config'];world=d['world_export'];args=TensorDeviceType();models={};records=[]
    robot,planner=cpu_views(d['world_base_pose']);goal=reported_command_to_actual_solver_goal(robot,planner,d['reported_command'])
    assert np.allclose(matrix(goal),np.linalg.inv(matrix(d['world_base_pose']))@matrix(d['desired_actual_goal']),atol=1e-7,rtol=0)
    for batch in (False,True):
        label='batch' if batch else 'single'
        kw={'interpolation_dt':.004,'num_trajopt_seeds':1,'use_cuda_graph':False,'collision_checker_type':CollisionCheckerType.MESH,'collision_cache':{'mesh':len(world['shapes']),'obb':1},'tensor_args':args}
        if batch:kw['num_graph_seeds']=1
        full=MotionGen(MotionGenConfig.load_from_robot_config(copy.deepcopy(cfg),make_world(world),**kw));verify_actual_world_cache(full,world)
        for kind in ('full','pair'):
            if kind=='full':mg=full
            else:
                mg,application=build_support_aware_motiongen(cfg,world,d['support_witness'],tensor_args=args,batch=batch);write_new(out/(label+'.application.json'),application);models[label]=mg
            name=label+'_'+kind;write_new(out/'checks'/(name+'.start.json'),{'kind':name,'high_level_constraint_call':1})
            result,_=query_state(mg,d['actual_qpos'],d['actual_joint_names']);result['expected_valid']=kind=='pair';result['expectation_pass']=result['valid']==(kind=='pair')
            write_new(out/'checks'/(name+'.json'),result);records.append(result);print(name,result['valid'],result['status'],flush=True)
    if not all(r['expectation_pass'] for r in records):return {'checks':records,'conformance_pass':False,'plan':None,'scientific_status':'START_STATE_CONFORMANCE_FAILED'}
    mg=models['single'];mg.reset(reset_seed=True);torch.manual_seed(1531);np.random.seed(1531)
    names=mg.kinematics.joint_names;q=[round(d['named_qpos'][n],5) for n in names];start=JointState.from_position(args.to_device(q).reshape(1,-1),joint_names=names)
    write_new(out/'lift.plan.start.json',{'trajectory_problem':1,'actual_goal':d['desired_actual_goal'],'solver_goal':goal.tolist(),'max_attempts':10})
    began=time.monotonic();r=mg.plan_single(start,Pose.from_list(goal.tolist()),MotionGenPlanConfig(max_attempts=10));passed=bool(r.success.item())
    plan={'success':passed,'status':str(r.status),'valid_query':bool(r.valid_query) if r.valid_query is not None else None,'elapsed_s':time.monotonic()-began,'executed':False}
    if passed:
        controls=r.interpolated_plan;position=controls.position.detach().cpu().numpy();velocity=controls.velocity.detach().cpu().numpy()
        with (out/'lift.controls.npz').open('xb') as f:np.savez_compressed(f,position=position,velocity=velocity)
        actor_frames=[];vertices=[];relative=np.asarray(d['eef_to_actor_matrix']);local=np.asarray(d['native_actor_vertices'])
        for values in position:
            named=dict(d['named_qpos']);named.update(dict(zip(names,values)));actor=link_world('fl_link6',named,d['world_base_pose'])@relative
            actor_frames.append(np.r_[actor[:3,3],t3d.quaternions.mat2quat(actor[:3,:3])]);vertices.append(local@actor[:3,:3].T+actor[:3,3])
        geometry=audit_lift_escape(vertices,actor_frames,support_plane_z=d['pad_top_world_z_m'],witness=d['support_witness']);plan['native_escape_audit']=geometry
        with (out/'lift.native_geometry.npz').open('xb') as f:np.savez_compressed(f,actor_world_poses=actor_frames,native_world_vertices=vertices)
    plan['checker_method_calls']=dict(mg.world_coll_checker.calls);write_new(out/'lift.plan.json',plan)
    return {'checks':records,'conformance_pass':True,'plan':plan,'scientific_status':'PLAN_AND_NATIVE_ESCAPE_PASS' if passed and plan['native_escape_audit']['pass'] else 'LIFT_PLAN_OR_GEOMETRY_FAILED'}

def run(m):
    out=Path(m['jobs'][0]['output_namespace']);out.mkdir(parents=True,exist_ok=False);result=error=None
    try:result=execute(m,out)
    except BaseException as exc:error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    starts=list((out/'checks').glob('*.start.json'));done=[p for p in (out/'checks').glob('*.json') if not p.name.endswith('.start.json')]
    planned=(out/'lift.plan.start.json').exists();plan_done=(out/'lift.plan.json').exists();known=len(starts)==len(done) and planned==plan_done
    return {'schema_version':'cmf_support_model_replay_terminal_v1','manifest_sha256':m['manifest_sha256'],'result':result,'error':error,'constraint_checks':len(starts),'constraint_completions':len(done),'trajectory_queries':int(planned),'accounting_complete':known,
        'scene_attempts':0,'physical_attempts':0,'IK_problems':0,'new_raw':0,'new_roots':0,'pass':error is None and known,'physical_execution':False}
