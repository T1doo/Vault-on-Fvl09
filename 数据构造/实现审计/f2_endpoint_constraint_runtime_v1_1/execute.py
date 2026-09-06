"""At most15 fixed IK problems plus one four-target planner-only route."""
import copy,json,sys
from pathlib import Path
import numpy as np
import transforms3d as t3d
from panel import W,A,P,world_and_can,configure_solvers,run_problem,corrected_contract,derive_live_targets,old,write_new,digest

def yaw_targets(contract,angle):
    from controlled_multi_future.geometry import actor_target_to_eef_pose,world_axis_offset_pose
    from controlled_multi_future.f2_asset_bound_runtime_v3 import _actor_pose_centered_on_support
    data=json.loads((P/'assets/objects/071_can/model_data0.json').read_text());center=np.asarray(data['center'])*.05;half=np.asarray(data['extents'])*.05/2
    original=np.asarray(contract['beside_template_actor_pose']);R=t3d.axangles.axangle2mat([0,0,1],np.deg2rad(angle))@t3d.quaternions.quat2mat(original[3:])
    actor=_actor_pose_centered_on_support(target_geometry_xy=np.asarray(contract['beside_candidate_xy_m']),support_plane_z_m=float(contract['binding']['layout_payload']['table_plane_z_m']),orientation_wxyz=t3d.quaternions.mat2quat(R),local_geometry_center_m=center,half_extents_m=half)
    D=actor_target_to_eef_pose(contract['sealed_prefix_end_eef_pose'],contract['sealed_prefix_end_actor_pose'],actor);U=world_axis_offset_pose(D,.08)
    return {'U':U.tolist(),'D':D.tolist(),'actor_pose':actor.tolist(),'yaw_degrees':angle,'geometry_center_xy_unchanged':True}

def run_panel(scene,contract,directory):
    from controlled_multi_future.family_runners_v3_1 import _plan_chain,_planner_reset
    _,binding=derive_live_targets(scene,contract);planner=scene.robot.left_planner
    if scene.robot.communication_flag:raise ValueError('unverified worker path')
    export,can=world_and_can(scene,planner);write_new(directory/'world_geometry.json',export)
    from model_apply import runtime_joint_state
    names,q=runtime_joint_state(scene)
    write_new(directory/'live_model_capture.json',{'joint_names':names,'joint_qpos':q.tolist(),'can_shapes':can,'actual_base_world_pose':planner._cmf_solver_base_world_pose,'live_binding':binding})
    solvers,configs,bank,start,robot_cfg,attachment=configure_solvers(scene,export,can)
    write_new(directory/'carried_can_model.json',attachment);write_new(directory/'derived_robot_config.json',robot_cfg)
    write_new(directory/'constraint_profiles.json',configs)
    with (directory/'seed_bank.npz').open('xb') as f:np.savez_compressed(f,seeds=bank.detach().cpu().numpy())
    goals={'C':contract['sealed_prefix_end_eef_pose'].tolist(),'U':contract['beside_targets'][1]['pose'],'D':contract['beside_targets'][2]['pose'],'N':contract['neutral_eef_pose'].tolist()}
    records=[];selected=None;counter=0
    def problem(label,profile,goal):
        nonlocal counter
        counter+=1
        if counter>15:raise ValueError('IK problem cap')
        row=run_problem(scene,solvers,bank,start,label,profile,goal,directory/'problems',counter);records.append(row)
        if row['error'] is not None:raise RuntimeError('IK infrastructure: '+str(row['error']))
        return row
    def full_pass(rows):return any(r['result']['full_valid_solution_found'] for r in rows)
    by={}
    for goal in ('C','U','D'):
        by[goal]=[problem(goal+'_'+k,k,goals[goal]) for k in ('K0','K1','K2')]
        if goal=='C' and not full_pass(by['C']):
            return {'problems':records,'positive_control_pass':False,'diagnosis':'CURRENT_POSE_MODEL_OR_ADAPTER_GATE_FAILED','selected_yaw':None,'route':None,'live_binding':binding}
    if full_pass(by['U']) and full_pass(by['D']):selected={'yaw_degrees':0,'U':goals['U'],'D':goals['D']}
    else:
        for angle in (90,-90,180):
            targets=yaw_targets(contract,angle)
            rows=[problem('yaw_'+str(angle)+'_'+k,'K2',targets[k]) for k in ('U','D')]
            if all(r['result']['full_valid_solution_found'] for r in rows):selected=targets;break
    route=None
    if selected is not None:
        from curobo.wrap.reacher.motion_gen import MotionGen,MotionGenConfig
        from curobo.geom.sdf.world import CollisionCheckerType
        from geometry import make_world
        from model_apply import verify_actual_world_cache
        for name in ('motion_gen','motion_gen_batch'):
            kwargs={'interpolation_dt':.004,'num_trajopt_seeds':1,'use_cuda_graph':False,'collision_checker_type':CollisionCheckerType.MESH,'collision_cache':{'mesh':len(export['shapes']),'obb':1}}
            if name=='motion_gen_batch':kwargs['num_graph_seeds']=1
            mg=MotionGen(MotionGenConfig.load_from_robot_config(copy.deepcopy(robot_cfg),make_world(export),**kwargs));setattr(planner,name,mg);verify_actual_world_cache(mg,export)
        _planner_reset(scene,planner_seed=2026090402,variant_id='F2_first_full_constraint_pair_route',arm='left')
        before=scene.planner_query_count;targets=[{'segment_id':'route_'+str(i)+'_'+k,'pose':selected[k] if k in selected else goals[k]} for i,k in enumerate(('U','D','U','N'))]
        r=_plan_chain(scene,targets,query_limit=before+4,arm='left');after=scene.planner_query_count
        arrays={f'{i}_{k}':np.asarray(c[k]) for i,c in enumerate(r.get('controls',[])) for k in ('position','velocity')}
        with (directory/'route_controls.npz').open('xb') as f:np.savez_compressed(f,**arrays)
        route={'pass':r['pass'],'targets':targets,'segments':r['segment_receipts'],'before':before,'after':after,'query_delta':after-before,'executed':False}
        write_new(directory/'route.json',route)
    return {'problems':records,'positive_control_pass':True,'selected_yaw':None if selected is None else selected['yaw_degrees'],'selected_targets':selected,'route':route,
        'live_binding':binding,'diagnosis':'FULL_CONSTRAINT_ENDPOINT_PAIR_AND_ROUTE_FOUND' if route and route['pass'] else 'NO_COMPLETE_FULL_CONSTRAINT_ROUTE_WITHIN_FIXED_BUDGET'}

def run_job(manifest):
    from controlled_multi_future.f2_asset_bound_runtime_v3 import RoboTwinRealSapienF2AssetBoundAdapterV3
    from controlled_multi_future.real_sapien_adapter_high_level_v1 import _PinnedSapienRenderDeviceContextV1
    out=Path(manifest['jobs'][0]['output_namespace']);out.mkdir(parents=True,exist_ok=False);contract,_=corrected_contract()
    adapter=RoboTwinRealSapienF2AssetBoundAdapterV3(output_root=out/'adapter',expected_implementation_source_sha256=manifest['implementation_source_sha256'],binding=contract['binding'],planner_only=True)
    context=_PinnedSapienRenderDeviceContextV1(adapter.scene(contract['planned'],phase='F2_ENDPOINT_CONSTRAINT_DIAGNOSIS',program=None));scene=None;before=after=None;result=None;error=None
    try:
        with context as handle:
            scene=handle.scene
            if not hasattr(scene,'planner_query_count'):scene.planner_query_count=0
            before=scene.planner_query_count
            try:result=run_panel(scene,contract,out)
            finally:after=getattr(scene,'planner_query_count',None)
    except BaseException as exc:error={'type':type(exc).__name__,'message':str(exc),'traceback':__import__('traceback').format_exc()}
    starts=list((out/'problems').glob('*.start.json'));done=list((out/'problems').glob('*.json'));done=[p for p in done if not p.name.endswith('.start.json')]
    known=type(before) is int and type(after) is int and after>=before and len(starts)==len(done)
    cleanup=context.cleanup_receipt;safe=known and error is None and cleanup is not None and cleanup.get('cleanup_safety_pass') is True
    value={'schema_version':'cmf_f2_endpoint_constraint_terminal_v1','manifest_sha256':manifest['manifest_sha256'],'result':result,'error':error,'cleanup':cleanup,
        'ik_problem_attempts':len(starts),'ik_problem_receipts':len(done),'trajectory_queries':after-before if known else None,'total_solver_problems':len(starts)+after-before if known else None,
        'fresh_scene_attempts':1,'accounting_complete':known,'physical_execution_count':0,'new_raw_trajectories':0,'new_roots':0,'pass':safe,
        'status':'DIAGNOSIS_COMPLETED_WITH_FINDINGS' if safe else 'DIAGNOSIS_INFRASTRUCTURE_STOP','render_binding':None if scene is None else getattr(scene,'_cmf_render_device_binding_v1',None)}
    value['receipt_sha256']=digest(value);write_new(out/'job_terminal.json',value);return value
