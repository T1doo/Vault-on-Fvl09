"""Fresh open/static and postclose/attached prefix model bridge; GPU pending."""
import copy,sys
from pathlib import Path
import numpy as np
import yaml
from goal_pilot48_v1.f2_inward_runtime_v1.contract import A,digest

def imports():
    from goal_pilot48_v1.f2_inward_runtime_v1.runtime import dependencies,install_motiongens,prepare_carried_config
    parent=dependencies()
    return parent,install_motiongens,prepare_carried_config

def save(scene,name,value):
    from realization_utf8_io_v1 import write_new
    write_new(Path(scene._cmf_goal_prefix_output)/name,value)

def native_escape_checks(native_world_vertices,support_plane):
    vertices=np.asarray(native_world_vertices,dtype=float)
    if vertices.ndim!=3 or vertices.shape[0]<2 or vertices.shape[-1]!=3 or not np.isfinite(vertices).all():raise ValueError('incomplete native prefix escape samples')
    bottom=vertices[:,:,2].min(axis=1)
    checks={'not_deeper_than_initial':bool(bottom.min()>=bottom[0]-1e-4),
      'non_descending_lower_envelope':bool(np.all(np.diff(bottom)>=-1e-4)),
      'initial_support_within_numeric_band':bool(abs(bottom[0]-support_plane)<=1e-4),
      'final_native_geometry_off_table':bool(bottom[-1]>support_plane+1e-4)}
    return {'checks':checks,'pass':all(checks.values()),'sample_count':len(bottom),'initial_bottom_z_m':float(bottom[0]),'final_bottom_z_m':float(bottom[-1]),
      'minimum_bottom_z_m':float(bottom.min()),'numeric_geometry_tolerance_m':1e-4,'physical_lift_proven':False,'continuous_sweep_proven':False}

def preplan(scene,targets):
    parent,install,_=imports()
    from model_apply import runtime_joint_state
    from controlled_multi_future.family_runners_v3_1 import _plan_chain
    export,can=parent.world_and_can(scene,scene.robot.left_planner)
    static={**export,'shapes':export['shapes']+can};static['geometry_sha256']=digest(static['shapes'])
    names,q=runtime_joint_state(scene);cfg=yaml.safe_load(Path(scene.robot.left_planner.yml_path).read_text(encoding='utf-8'))['robot_cfg']
    cfg['kinematics']['lock_joints']={n:float(q[names.index(n)]) for n in cfg['kinematics']['lock_joints']}
    cfg['kinematics']['link_names']=['fl_link6','fl_link7','fl_link8']
    audits=install(scene,cfg,static)
    save(scene,'prefix_open_model.json',{'world':static,'config':cfg,'audits':audits,'can_static':True,'physical_Gates_changed':False})
    if scene.planner_query_count!=0:raise ValueError('prefix setup consumed unexpected solver queries')
    return _plan_chain(scene,targets[:2],query_limit=3,arm='left')

def postclose_plan(scene,planned,targets):
    parent,install,prepare=imports()
    from controlled_multi_future.family_runners_v3_1 import _plan_chain
    from controlled_multi_future.family_runners_v3_3 import _pose
    from goal_pilot48_v1.f2_inward_runtime_v1.collision import support_witness,native_can_screen
    if scene.planner_query_count!=2 or len(planned['controls'])!=2:raise ValueError('prefix two-stage accounting changed')
    export,can=parent.world_and_can(scene,scene.robot.left_planner)
    base=scene.robot.left_planner._cmf_solver_base_world_pose
    # Geometric applicability only; physical support/grasp success must still
    # be established by the unchanged original prefix acceptance gate.
    witness=support_witness(export,can,_pose(scene.can),base)
    cfg,_,_,_,native,_=prepare(scene,can)
    audits=install(scene,cfg,export,witness)
    save(scene,'prefix_postclose_model.json',{'world':export,'config':cfg,'witness':witness,'audits':audits,'actual_postclose':True})
    lift=_plan_chain(scene,[targets[2]],query_limit=3,arm='left')
    if not lift['pass']:raise RuntimeError('actual postclose lift planning failed')
    geometry=native_can_screen(scene.robot.left_planner.motion_gen.kinematics,lift['controls'][0]['position'],native,base,witness)
    from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix
    mg=scene.robot.left_planner.motion_gen;states=mg.kinematics.get_state(mg.tensor_args.to_device(np.asarray(lift['controls'][0]['position'],dtype=np.float32)))
    positions=states.ee_position.detach().cpu().numpy();rotations=states.ee_quaternion.detach().cpu().numpy();B=matrix(base);samples=[]
    for p,q in zip(positions,rotations):
        T=B@matrix([*p,*q]);samples.append(native@T[:3,:3].T+T[:3,3])
    escape=native_escape_checks(samples,witness['support_plane_z_m']);geometry['upward_native_escape']=escape;geometry['pass']=geometry['pass'] and escape['pass']
    save(scene,'prefix_lift_native_plan_gate.json',geometry)
    if not geometry['pass']:raise RuntimeError('native prefix lift geometry failed before execution')
    return {**lift,'controls':planned['controls']+lift['controls'],'segment_receipts':planned['segment_receipts']+lift['segment_receipts']}

def restore_fullworld(scene):
    parent,install,prepare=imports()
    from model_apply import runtime_joint_state,query_state
    export,can=parent.world_and_can(scene,scene.robot.left_planner);cfg,_,_,_,_,_=prepare(scene,can)
    audits=install(scene,cfg,export,witness=None);names,q=runtime_joint_state(scene)
    checks={key:query_state(getattr(scene.robot.left_planner,key),q,names)[0] for key in ('motion_gen','motion_gen_batch')}
    save(scene,'prefix_postlift_fullworld_restored.json',{'audits':audits,'checks':checks,'support_pair_exception_active':False,'all_robot_and_attached_can_world_checks_restored':True})
    if not all(row['valid'] for row in checks.values()):raise RuntimeError('actual postlift fullworld model invalid before prefix acceptance')
