"""Guarded-only actual solver replacement and collision-model conformance."""
import copy
import numpy as np
from transforms import full_joint_state_to_solver_joint_state,world_obstacle_to_solver_frame
from geometry import make_world,pose7,matrix,digest

def bind_actual_solver_base(scene,planner):
    import yaml
    cfg=yaml.safe_load(open(planner.yml_path,encoding='utf-8'))
    name=cfg['robot_cfg']['kinematics']['base_link']
    links={l.get_name():l for l in scene.robot.left_entity.get_links()}
    if name not in links:raise ValueError('solver base link missing from physical articulation')
    planner._cmf_solver_base_world_pose=pose7(links[name]).tolist()
    return {'base_link':name,'base_link_world_pose':planner._cmf_solver_base_world_pose,
        'world_geometry_rule':'original WORLD routine with actual configured solver base link pose; no gripper tool or empirical goal correction',
        'reported_goal_rule':'unchanged full Robot->CuroboPlanner legacy goal chain'}

def verify_actual_world_cache(mg,export):
    checker=mg.world_coll_checker;records=[]
    for shape in export['shapes']:
        index=checker.get_mesh_idx(shape['name']);cached=checker._wp_mesh_cache[shape['name']]
        vertices=np.asarray(cached.vertices.numpy());faces=np.asarray(cached.faces.numpy()).reshape(-1,3)
        expected=np.asarray(shape['vertices'],dtype=np.float32)
        if not np.array_equal(vertices,expected) or not np.array_equal(faces,np.asarray(shape['faces'])):raise ValueError('actual Warp mesh geometry differs')
        pose=checker._mesh_tensor_list[1][0,index,:7].detach().cpu().numpy()
        error=float(np.max(np.abs(matrix(pose)-np.linalg.inv(matrix(shape['solver_pose'])))))
        if error>1e-5 or int(checker._mesh_tensor_list[2][0,index].item())!=1:raise ValueError('actual solver mesh pose/enabled flag differs')
        records.append({'name':shape['name'],'geometry_equal_float32':True,'inverse_pose_matrix_max_error':error,'enabled':True})
    return records

def runtime_joint_state(scene,arm='left'):
    entity=getattr(scene.robot,arm+'_entity');names=[j.get_name() for j in entity.get_active_joints()]
    q=np.asarray(entity.get_qpos(),dtype=float)
    if len(names)!=len(q) or len(set(names))!=len(names):raise ValueError('live joint enumeration')
    return names,q

def rebuild_actual_motiongens(scene,export,arm='left'):
    import yaml
    from curobo.geom.sdf.world import CollisionCheckerType
    from curobo.wrap.reacher.motion_gen import MotionGen,MotionGenConfig
    robot=scene.robot
    if robot.communication_flag:raise RuntimeError('worker RPC binding required; refusing inprocess-only update')
    planner=getattr(robot,arm+'_planner');names,q=runtime_joint_state(scene,arm)
    cfg=yaml.safe_load(open(planner.yml_path,encoding='utf-8'));kin=cfg['robot_cfg']['kinematics']
    locked={name:float(q[names.index(name)]) for name in kin['lock_joints']}
    derived=copy.deepcopy(cfg);derived['robot_cfg']['kinematics']['lock_joints']=locked
    derived['robot_cfg']['kinematics']['link_names']=['fl_link6','fl_link7','fl_link8']
    world=make_world(export);old={name:getattr(planner,name) for name in ('motion_gen','motion_gen_batch')};records=[]
    for name in old:
        kwargs={'interpolation_dt':1/250,'num_trajopt_seeds':1,'use_cuda_graph':False,'collision_checker_type':CollisionCheckerType.MESH,
            'collision_cache':{'mesh':max(1,len(export['shapes'])),'obb':1}}
        if name=='motion_gen_batch':kwargs['num_graph_seeds']=1
        mg=MotionGen(MotionGenConfig.load_from_robot_config(copy.deepcopy(derived['robot_cfg']),world,**kwargs))
        setattr(planner,name,mg)
        mg.update_world(world)
        actual=set(x for x in mg.world_coll_checker.get_obstacle_names() if x)
        expected={s['name'] for s in export['shapes']}
        if actual!=expected:raise RuntimeError('actual solver obstacle names differ')
        records.append({'attribute':name,'old_object_id':id(old[name]),'new_object_id':id(mg),'checker_type':type(mg.world_coll_checker).__name__,
            'obstacle_names':sorted(actual),'geometry_sha256':export['geometry_sha256'],'actual_cache_audit':verify_actual_world_cache(mg,export),'locked_joints':locked,'use_cuda_graph':False})
    return planner,old,derived,{'actual_robot_planner_instance_id':id(planner),'instances':records,'derived_robot_config_sha256':digest(derived),'pass':True}

def update_world_and_locks(planner,export,derived,names,full_q):
    world=make_world(export);locks={name:float(full_q[names.index(name)]) for name in derived['robot_cfg']['kinematics']['lock_joints']}
    for attr in ('motion_gen','motion_gen_batch'):
        mg=getattr(planner,attr);mg.update_world(world);mg.update_locked_joints(locks,copy.deepcopy(derived))
        expected={s['name'] for s in export['shapes']};actual=set(x for x in mg.world_coll_checker.get_obstacle_names() if x)
        if actual!=expected:raise RuntimeError('solver world update not acknowledged')
        verify_actual_world_cache(mg,export)
    return locks

def query_state(mg,full_q,names):
    import torch
    from curobo.types.state import JointState
    ordered=full_joint_state_to_solver_joint_state(full_q,names,mg.kinematics.joint_names)
    tensor=torch.as_tensor(ordered,device=mg.tensor_args.device,dtype=mg.tensor_args.dtype).reshape(1,-1)
    js=JointState.from_position(tensor,joint_names=mg.kinematics.joint_names)
    # The locked version returns on world collision before restoring its self
    # constraint; restore both explicitly for independent conformance states.
    try:valid,status=mg.check_start_state(js)
    finally:
        mg.rollout_fn.primitive_collision_constraint.enable_cost()
        mg.rollout_fn.robot_self_collision_constraint.enable_cost()
    full=mg.kinematics.get_full_js(js)
    return {'valid':bool(valid),'status':None if status is None else str(status),'solver_joint_names':list(js.joint_names),
        'solver_qpos':ordered.tolist(),'full_model_joint_names':list(full.joint_names),'full_model_qpos':full.position.detach().cpu().numpy().reshape(-1).tolist()},tensor

def link_conformance(scene,planner,mg,tensor):
    names=['fl_link6','fl_link7','fl_link8'];poses=mg.kinematics.get_link_poses(tensor,names)
    positions=poses.position.detach().cpu().numpy()[0];quats=poses.quaternion.detach().cpu().numpy()[0]
    links={l.get_name():l for l in scene.robot.left_entity.get_links()};rows=[]
    for i,name in enumerate(names):
        expected=world_obstacle_to_solver_frame(planner,pose7(links[name]))
        angular=2*np.arccos(np.clip(abs(np.dot(expected[3:]/np.linalg.norm(expected[3:]),quats[i]/np.linalg.norm(quats[i]))),0,1))
        rows.append({'link':name,'position_error_m':float(np.linalg.norm(expected[:3]-positions[i])),'orientation_error_rad':float(angular),
            'sapien_link_solver_pose':expected.tolist(),'model_link_solver_pose':np.r_[positions[i],quats[i]].tolist()})
    return rows
