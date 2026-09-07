"""Construction-time F2-only checker, no F3 certificate or global table toggle."""
import copy
from goal_pilot48_v1.f2_inward_runtime_v1.contract import A,digest
from support_pair_collision_v1.policy import PairFilteredWorld,METHODS
from .certificate import VERSION,verify_certificate

class ClearancePairWorld(PairFilteredWorld):
    def __init__(self,full,reduced,*,names,certificate,expected_binding,buffer_factory):
        verify_certificate(certificate,expected_binding)
        if certificate.get('admitted_mode')!='F2_CAN_TABLE_PADDING_UPWARD_ONLY':raise ValueError('no admitted F2 pair-mode lease')
        checks=certificate.get('full_checks',{})
        if set(checks)!={'motion_gen','motion_gen_batch'} or any(v['valid'] or 'INVALID_START_STATE_WORLD_COLLISION' not in str(v['status']) for v in checks.values()):raise ValueError('pair model lacks both original full-world failures')
        if certificate['schema_version']!=VERSION or not certificate['pass'] or certificate['table_shape_name']!='table__0':raise ValueError('F2-specific clearance certificate required')
        if {n for n in reduced.get_obstacle_names() if n}!={n for n in full.get_obstacle_names() if n}-{'table__0'}:raise ValueError('other world geometry removed')
        if 'attached_can' not in names or all(n=='attached_can' for n in names):raise ValueError('sphere partition invalid')
        self.full=full;self.without_support=reduced;self.names=list(names);self.attached='attached_can';self.buffer_factory=buffer_factory;self.buffers={};self.calls={n:0 for n in METHODS}
        self.support_pair_policy_version='F2_CLEARANCE_UPWARD_ONLY_V1'

def install(scene,cfg,export,certificate,expected_binding):
    from curobo.types.robot import RobotConfig
    from curobo.geom.sdf.world import WorldCollisionConfig,CollisionCheckerType,CollisionQueryBuffer
    from curobo.geom.sdf.utils import create_collision_checker
    from curobo.wrap.reacher.motion_gen import MotionGen,MotionGenConfig
    from geometry import make_world
    from goal_pilot48_v1.f2_inward_runtime_v1.collision import audit_checker
    from goal_pilot48_v1.f2_inward_runtime_v1.runtime import audit_locks
    planner=scene.robot.left_planner;args=planner.motion_gen.tensor_args;audits={}
    reduced={**export,'shapes':[s for s in export['shapes'] if s['name']!='table__0']};reduced['geometry_sha256']=digest(reduced['shapes'])
    for name in ('motion_gen','motion_gen_batch'):
        robot=RobotConfig.from_dict(copy.deepcopy(cfg),args);kin=robot.kinematics.kinematics_config;reverse={v:k for k,v in kin.link_name_to_idx_map.items()}
        links=[reverse[int(i)] for i in kin.link_sphere_idx_map.detach().cpu().numpy().reshape(-1)]
        def checker(e):return create_collision_checker(WorldCollisionConfig(tensor_args=args,world_model=make_world(e),checker_type=CollisionCheckerType.MESH,cache={'mesh':len(e['shapes']),'obb':1}))
        full,subset=checker(export),checker(reduced)
        pair=ClearancePairWorld(full,subset,names=links,certificate=certificate,expected_binding=expected_binding,buffer_factory=lambda q,checker=subset:CollisionQueryBuffer.initialize_from_shape(q.shape,args,checker.collision_types))
        kwargs=dict(interpolation_dt=.004,num_trajopt_seeds=1,use_cuda_graph=False,tensor_args=args,collision_checker_type=CollisionCheckerType.MESH,world_coll_checker=pair)
        if name=='motion_gen_batch':kwargs['num_graph_seeds']=1
        mg=MotionGen(MotionGenConfig.load_from_robot_config(robot,make_world(export),**kwargs));setattr(planner,name,mg)
        audits[name]={'checker':audit_checker(mg,pair,export,reduced),'locks':audit_locks(mg,cfg)};mg.reset(reset_seed=True)
    return audits
