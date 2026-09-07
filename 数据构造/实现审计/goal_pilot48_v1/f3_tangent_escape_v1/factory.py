"""Unexecuted GPU integration proposal; invoke only in a separately bound Guard."""
import copy,sys
from pathlib import Path
from types import SimpleNamespace
from .policy import PairFilteredWorld

def build_support_aware_motiongen(robot_config,world_export,witness,*,tensor_args,lease,batch=False):
    from .integrity import verify_factory_inputs
    verify_factory_inputs(robot_config,world_export,witness)
    # Imports and device construction deliberately occur only inside this
    # function. CPU policy tests do not initialize any CuRobo/CUDA object.
    from curobo.types.robot import RobotConfig
    from curobo.geom.sdf.world import WorldCollisionConfig,CollisionCheckerType,CollisionQueryBuffer
    from curobo.geom.sdf.utils import create_collision_checker
    from curobo.wrap.reacher.motion_gen import MotionGen,MotionGenConfig
    A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');sys.path.insert(0,str(A/'f2_f3_model_bridge_v1_1'))
    from geometry import make_world,digest
    from model_apply import verify_actual_world_cache
    cfg=RobotConfig.from_dict(copy.deepcopy(robot_config),tensor_args)
    kin=cfg.kinematics.kinematics_config;reverse={v:k for k,v in kin.link_name_to_idx_map.items()}
    names=[reverse[int(i)] for i in kin.link_sphere_idx_map.detach().cpu().numpy().reshape(-1)]
    subset={**world_export,'shapes':[s for s in world_export['shapes'] if s['name']!='pad__0']};subset['geometry_sha256']=digest(subset['shapes'])
    if len(world_export['shapes'])-len(subset['shapes'])!=1:raise ValueError('exactly one frozen pad mesh is required')
    def checker(export):return create_collision_checker(WorldCollisionConfig(tensor_args=tensor_args,world_model=make_world(export),checker_type=CollisionCheckerType.MESH,cache={'mesh':len(export['shapes']),'obb':1}))
    full=checker(world_export);reduced=checker(subset)
    split=PairFilteredWorld(full,reduced,sphere_link_names=names,attached_link_name='attached_bottle',support_name='pad__0',witness=witness,
        buffer_factory=lambda q:CollisionQueryBuffer.initialize_from_shape(q.shape,tensor_args,reduced.collision_types),lease=lease)
    kwargs={'interpolation_dt':.004,'num_trajopt_seeds':1,'use_cuda_graph':False,'world_coll_checker':split,'tensor_args':tensor_args,'collision_checker_type':CollisionCheckerType.MESH}
    if batch:kwargs['num_graph_seeds']=1
    mg=MotionGen(MotionGenConfig.load_from_robot_config(cfg,make_world(world_export),**kwargs))
    if mg.world_coll_checker is not split:raise ValueError('actual MotionGen did not retain split checker')
    callback_audit=[]
    for rollout in [mg.rollout_fn]+mg.get_all_rollout_instances():
        for name in ('primitive_collision_cost','primitive_collision_constraint'):
            cost=getattr(rollout,name,None)
            if cost is None:continue
            for field in ('coll_check_fn','sweep_check_fn'):
                fn=getattr(cost,field)
                if getattr(fn,'__self__',None) is not split:raise ValueError('cached collision callback bypasses pair-aware checker')
                callback_audit.append({'cost':name,'callback':field,'bound_to_pair_checker':True})
    caches={'full':verify_actual_world_cache(SimpleNamespace(world_coll_checker=full),world_export),'attached_except_pad':verify_actual_world_cache(SimpleNamespace(world_coll_checker=reduced),subset)}
    return mg,{'source_status':'TANGENT_CERTIFICATE_NEW_FACTORY_REQUIRES_REAL_GPU_CONFORMANCE','cache_audit':caches,'callback_audit':callback_audit,'attached_sphere_count':names.count('attached_bottle'),
        'table_retained_in_both_views':True,'pad_retained_for_all_robot_spheres':True,'planned_escape_geometry_gate_required_before_execution':True,'new_physical_authorization':False}
