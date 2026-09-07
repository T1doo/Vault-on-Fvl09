"""Fresh certificate construction and model transition hooks; no import-time GPU."""
import json,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from .certificate import SCHEMA,seal,validate,SinglePlanLease

def prepare(scene,out,build_full):
    from geometry import capture_scene_collision_geometry,digest,matrix
    from model_apply import runtime_joint_state,query_state
    from controlled_multi_future.family_runners_v3_1 import _entity
    from controlled_multi_future.f3_physical_contact_signal_v8 import classify_contact_pair_physical_hit_v8
    from goal_pilot48_v1.runtime.support_witness import hold_witness,model_overlap_witness,bind_exact_pad
    from support_pair_collision_v1.policy import verify_support_witness
    from support_pair_collision_v1.factory import build_support_aware_motiongen as supported_factory
    from .factory import build_support_aware_motiongen as tangent_factory
    from realization_utf8_io_v1 import write_new
    from controlled_multi_future.canonical_artifact import canonical_jsonable
    full=build_full(scene,out);planner=scene.robot.left_planner
    export=capture_scene_collision_geometry(scene,planner);export['shapes']=[s for s in export['shapes'] if s['role']!='bottle'];export['geometry_sha256']=digest(export['shapes'])
    names,q=runtime_joint_state(scene);checks={};tensor=None
    for name in ('motion_gen','motion_gen_batch'):checks[name],tensor=query_state(getattr(planner,name),q,names)
    mg=planner.motion_gen;rows=scene.trace[-250:];pad_name=_entity(scene.pad).get_name();bottle=_entity(scene.bottle).get_name()
    witness=model_overlap_witness(mg,tensor,export);witness['hold']=hold_witness(rows,selected_links=scene.selected_gripper_links(),bottle_name=bottle,pad_name=pad_name)
    old_supported=verify_support_witness(witness)
    write_new(out/'literal_old_supported_witness.json',{'witness':witness,'old_supported_hold_pass':old_supported,'full_model_checks':checks})
    lease=None;certificate=None
    if old_supported:
        bind_exact_pad(witness,export,pad_name);factory=supported_factory;factory_kwargs={};branch='old_supported'
    else:
        pads=[s for s in export['shapes'] if s['name']=='pad__0' and s['actor_name']==pad_name]
        if len(pads)!=1:raise ValueError('exact same native pad binding absent')
        pad=pads[0];T=matrix(planner._cmf_solver_base_world_pose)@matrix(pad['solver_pose']);pv=np.asarray(pad['vertices'])@T[:3,:3].T+T[:3,3];top=float(pv[:,2].max())
        local=[]
        for s in full['native_bottle_shapes']:
            T=matrix(s['shape_local_pose']);local.append(np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3])
        local=np.concatenate(local);gaps=[];table=other=0
        for row in rows:
            p=np.asarray(row['actor_pose']);v=R.from_quat(p[[4,5,6,3]]).apply(local)+p[:3];gaps.append(float(v[:,2].min()-top));t=o=False
            for pair in row['contact_pairs']:
                bodies={pair['body_a'],pair['body_b']}
                if bottle not in bodies or not classify_contact_pair_physical_hit_v8(pair)['physical_hit_for_gate']:continue
                t|='table' in bodies
                allowed={bottle,pad_name,*scene.selected_gripper_links()};o|=bool(bodies-allowed-{'table'})
            table+=int(t);other+=int(o)
        def hashed(v):return hashlib.sha256(json.dumps(canonical_jsonable(v),sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
        certificate=seal({'schema_version':SCHEMA,'old_supported_hold_pass':old_supported,'old_supported_witness':witness,
            'scene_id':str(scene._cmf_tangent_scene_id),'job_namespace':str(Path(out).resolve()),'plan_id':'fixed_lift25_once',
            'actual_joint_names':names,'actual_qpos':q.tolist(),'actual_actor_pose':list(rows[-1]['actor_pose']),'actual_eef_pose':list(rows[-1]['eef']),
            'trace_window_sha256':hashed([{'step_index':r['step_index'],'timestamp':r['timestamp'],'eef':r['eef'],'actor_pose':r['actor_pose'],'contact_pairs':r['contact_pairs']} for r in rows]),'world_sha256':digest(export['shapes']),'robot_config_sha256':hashed(full['robot_config']),
            'native_geometry_sha256':hashed(full['native_bottle_shapes']),'pad_actor_name':pad_name,'pad_shape_name':'pad__0','pad_top_m':top,
            'hold':witness['hold'],'table_contact_frames':table,'other_support_contact_frames':other,'native_gap_per_hold_frame_m':gaps,
            'hold_step_indices':[r['step_index'] for r in rows],'hold_timestamps':[r['timestamp'] for r in rows],
            'overlap_pairs':witness['pairs'],'full_model_checks':checks,'target_delta_world_m':[0.,0.,.025],'target_orientation_unchanged':True})
        write_new(out/'tangent_certificate_candidate.json',certificate)
        if not validate(certificate):raise ValueError('new tangent certificate rejected; old supported condition remains failed')
        lease=SinglePlanLease(certificate);factory=tangent_factory;factory_kwargs={'lease':lease};branch='tangent_unloading'
    scene._cmf_tangent_lease=lease;scene._cmf_escape_model_branch=branch
    applications=[]
    for name in ('motion_gen','motion_gen_batch'):
        new,application=factory(full['robot_config'],export,certificate if lease else witness,tensor_args=mg.tensor_args,batch=name=='motion_gen_batch',**factory_kwargs)
        setattr(planner,name,new);applications.append(application)
    pair_checks={name:query_state(getattr(planner,name),q,names)[0] for name in ('motion_gen','motion_gen_batch')}
    write_new(out/'escape_model_conformance.json',{'branch':branch,'full_checks':checks,'pair_checks':pair_checks,'applications':applications,'high_level_state_checks':4})
    if not all(v['valid'] for v in pair_checks.values()):
        if lease:lease.invalidate()
        raise ValueError('pair model actual single/batch conformance failed')
    scene._cmf_tangent_lease=lease;scene._cmf_escape_certificate=certificate;scene._cmf_fresh_support_witness=witness
    scene._cmf_fresh_bottle_shapes=full['native_bottle_shapes'];scene._cmf_fresh_support_world=export;scene._cmf_escape_model_branch=branch
    return full

def begin_plan(scene,actual_goal):
    from controlled_multi_future.family_runners_v3_1 import _arm_eef_pose
    from geometry import digest
    actual=np.asarray(_arm_eef_pose(scene,'left'));goal=np.asarray(actual_goal)
    if not np.allclose(goal[:3]-actual[:3],[0,0,.025],rtol=0,atol=1e-12) or not np.array_equal(goal[3:],actual[3:]):raise ValueError('escape must be exact actual-state25mm upward goal')
    lease=getattr(scene,'_cmf_tangent_lease',None)
    if lease:lease.begin_plan(str(scene._cmf_tangent_scene_id),'fixed_lift25_once',digest(scene._cmf_fresh_support_world['shapes']))

def native_gate(scene,controls,out,old_gate):
    if getattr(scene,'_cmf_tangent_lease',None) is None:return old_gate(scene,controls,out)
    from .escape import evaluate_controls
    from model_apply import runtime_joint_state
    from controlled_multi_future.family_runners_v3_1 import _pose,_arm_eef_pose
    from realization_utf8_io_v1 import write_new
    lease=scene._cmf_tangent_lease;lease.check()
    if lease.state!='planning':raise ValueError('native screen outside bound single plan')
    names,q=runtime_joint_state(scene);planner=scene.robot.left_planner;c=scene._cmf_escape_certificate
    from .integrity import verify_actual_binding
    verify_actual_binding(c,native_shapes=scene._cmf_fresh_bottle_shapes,joint_names=names,qpos=q,actor_pose=_pose(scene.bottle),eef_pose=_arm_eef_pose(scene,'left'),world_shapes=scene._cmf_fresh_support_world['shapes'])
    result=evaluate_controls(controls['position'],solver_joint_names=planner.motion_gen.kinematics.joint_names,actual_joint_names=names,actual_qpos=q,
        base_pose=planner._cmf_solver_base_world_pose,actor_pose=_pose(scene.bottle),bottle_shapes=scene._cmf_fresh_bottle_shapes,pad_top=c['pad_top_m'],witness=c)
    write_new(out/'lift_native_tangent_escape_gate.json',result);return result

def restore(scene,out,build_full):
    from model_apply import runtime_joint_state,query_state
    from realization_utf8_io_v1 import write_new
    lease=getattr(scene,'_cmf_tangent_lease',None)
    prior_calls={name:dict(getattr(getattr(scene.robot.left_planner,name).world_coll_checker,'calls',{})) for name in ('motion_gen','motion_gen_batch')}
    if lease:lease.invalidate()
    directory=Path(out)/'full_world_restored';directory.mkdir(exist_ok=False)
    build_full(scene,directory);names,q=runtime_joint_state(scene)
    checks={name:query_state(getattr(scene.robot.left_planner,name),q,names)[0] for name in ('motion_gen','motion_gen_batch')}
    write_new(directory/'restoration.json',{'checks':checks,'all_robot_and_attached_pad_pairs_restored':True,'certificate_invalidated':True,'high_level_state_checks':2,
        'prior_checker_method_entry_counts_not_GPU_kernel_launch_counts':prior_calls,'GPU_kernel_launch_count':'not_profiled',
        'tangent_certificate_sha256':None if lease is None else lease.certificate['certificate_sha256'],
        'single_plan_lease_state':None if lease is None else lease.state,'single_plan_calls':None if lease is None else lease.plan_calls})
    return checks
