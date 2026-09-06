"""Two existing assets, five preregistered states each; no planner trajectory/action."""
import copy,importlib.util,json,sys
from pathlib import Path
import numpy as np
from geometry import capture_scene_collision_geometry,capture_actor_geometry,closest_pairs,exact_shape_pairs,digest
from model_apply import rebuild_actual_motiongens,update_world_and_locks,runtime_joint_state,query_state,link_conformance
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计'
if str(A) not in sys.path:sys.path.insert(1,str(A))
from realization_utf8_io_v1 import write_new,load_json
SOURCE_SHA='3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7'
H=W/'Robotwin2/production_micro_gate_v1/job_runner.py'

def helper():
    import hashlib
    if hashlib.sha256(H.read_bytes()).hexdigest()!='376ddfbe07b1c9ae3e6e3b2d1975344a8605c6e81e49f27e92241c88a851a1d4':raise ValueError('scene helper changed')
    spec=importlib.util.spec_from_file_location('model_conformance_scene_helper',H);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def candidates():
    rows=load_json(A/'F3_DETERMINISTIC_CANDIDATE_FREEZE_RESOLVED_V1.json')['ordered_candidates']
    return [r for name in ('f3-final-pose-v3-r3063','f3-final-pose-v3-r1401') for r in rows if r['recipe_id']==name]

def candidate_spec(recipe):
    from controlled_multi_future.f3_asset_grasp_qualification_v2 import build_f3_asset_grasp_qualification_v2
    from controlled_multi_future.high_level_runtime_specs_v1 import build_f3_runtime_spec_v1
    tuples=build_f3_asset_grasp_qualification_v2()['grasp_tuples'];t=next(t for t in tuples if t['asset']==recipe['asset'] and t['arm']==recipe['arm'])
    return build_f3_runtime_spec_v1(t['tuple_id'],purpose='f3_level1_planner')

def old_states(recipe,names):
    i=0 if recipe['recipe_id'].endswith('r3063') else 2
    base=W/'Robotwin2/datasets/cmf_f3_micro_authorized_v1_1'/str(i)/'physical';receipt=load_json(base/'scene_receipt.json')
    with np.load(base/'physical_trace.npz',allow_pickle=False) as z:
        q=z['joint_qpos'];obj=z['object_pose'];commands=z['controller_effective_setpoint']
        if q.shape[1]!=len(names):raise ValueError('historical/live articulation size differs')
        windows=receipt['result']['windows'];pre=windows[0]['end_inclusive'];failure=windows[1]['first_failure']['row_index'];end=windows[1]['end_inclusive']
        moved=np.flatnonzero(np.linalg.norm(obj[:,:3]-obj[0,:3],axis=1)>1e-6);before=max(0,int(moved[0])-1) if len(moved) else 0
        indices=[names.index('fl_joint'+str(j)) for j in range(1,7)]
        if indices!=[6,14,18,22,26,30]:raise ValueError('historical source joint-name order changed')
        goal=q[0].copy();goal[indices]=commands[end,:6]
        rows=[{'label':label,'trace_row':int(idx),'qpos':q[idx].tolist(),'bottle_pose':obj[idx].tolist()} for label,idx in [('initial_clear',0),('pregrasp_endpoint',pre),('first_failure',failure),('before_bottle_motion',before)]]
        rows.append({'label':'planned_grasp_endpoint','trace_row':None,'qpos':goal.tolist(),'bottle_pose':obj[0].tolist(),
            'source':'exact last grasp effective setpoint by joint name; non-arm state and bottle reset to pre-action state'})
    return rows

def project_state(scene,state):
    import sapien.core as sapien
    q=np.asarray(state['qpos'],dtype=np.float32);scene.robot.left_entity.set_qpos(q);scene.robot.left_entity.set_qvel(np.zeros_like(q))
    p=state['bottle_pose'];actor=scene.bottle.actor if hasattr(scene.bottle,'actor') else scene.bottle
    actor.set_pose(sapien.Pose(p[:3],p[3:]))

def run_scene(recipe,directory):
    from controlled_multi_future.planner_qualification_manifests_v2_3 import _f3_scene_binding
    from controlled_multi_future.real_sapien_adapter_high_level_v1 import _PinnedSapienRenderDeviceContextV1
    h=helper();legacy=candidate_spec(recipe);adapter=h.adapter_for('F3',legacy,directory/'adapter',SOURCE_SHA)
    context=_PinnedSapienRenderDeviceContextV1(adapter.scene(legacy,phase='F3_MODEL_NON_ACTION_CONFORMANCE',program=None))
    before=after=None;scene=None;error=None;rows=[];application=None;binding=None
    try:
        with context as handle:
            scene=handle.scene
            if not hasattr(scene,'planner_query_count'):scene.planner_query_count=0
            before=scene.planner_query_count
            try:
                binding=h.prepare_f3_scene(scene,adapter,recipe,_f3_scene_binding(recipe))
                names,_=runtime_joint_state(scene);states=old_states(recipe,names)
                project_state(scene,states[0]);initial=capture_scene_collision_geometry(scene,scene.robot.left_planner)
                write_new(directory/'initial_geometry.json',initial)
                planner,old,derived,application=rebuild_actual_motiongens(scene,initial)
                write_new(directory/'model_application.json',application);write_new(directory/'derived_robot_config.json',derived)
                links={l.get_name():l for l in scene.robot.left_entity.get_links()}
                for state in states:
                    project_state(scene,state);export=capture_scene_collision_geometry(scene,planner)
                    locks=update_world_and_locks(planner,export,derived,names,np.asarray(state['qpos']))
                    result={'state':state,'locked_joints':locks,'geometry_sha256':export['geometry_sha256'],'old_models':{},'new_models':{}}
                    for attr in ('motion_gen','motion_gen_batch'):
                        old_result,_=query_state(old[attr],state['qpos'],names);mg=getattr(planner,attr);new_result,tensor=query_state(mg,state['qpos'],names)
                        model_locks=dict(zip(new_result['full_model_joint_names'],new_result['full_model_qpos']))
                        if any(abs(model_locks[n]-v)>1e-6 for n,v in locks.items()):raise ValueError('actual solver locked joint state differs')
                        new_result['link_conformance']=link_conformance(scene,planner,mg,tensor)
                        new_result['nearest_robot_sphere_world_pairs']=closest_pairs(mg.kinematics,tensor,export)
                        result['old_models'][attr]=old_result;result['new_models'][attr]=new_result
                    fingers=[]
                    for name in ('fl_link6','fl_link7','fl_link8'):fingers+=capture_actor_geometry(links[name],name,planner)
                    result['exact_sapien_shape_pairs']=exact_shape_pairs(fingers,[s for s in export['shapes'] if s['role'] in ('table','pad','bottle')])
                    result['exact_geometry_intersection']=any(x['mesh_intersection'] and x['physical_collision_filter_enabled'] for x in result['exact_sapien_shape_pairs'])
                    write_new(directory/(state['label']+'.geometry.json'),export);write_new(directory/(state['label']+'.result.json'),result);rows.append(result)
                    print(recipe['recipe_id'],state['label'],{k:v['valid'] for k,v in result['new_models'].items()},'exact_intersection',result['exact_geometry_intersection'],flush=True)
            finally:after=getattr(scene,'planner_query_count',None)
    except BaseException as exc:error={'type':type(exc).__name__,'message':str(exc)}
    cleanup=context.cleanup_receipt;known=type(before) is int and type(after) is int and after>=before
    clear=next((r for r in rows if r['state']['label']=='initial_clear'),None);pre=next((r for r in rows if r['state']['label']=='pregrasp_endpoint'),None);endpoint=next((r for r in rows if r['state']['label']=='planned_grasp_endpoint'),None)
    conforms=bool(clear and pre) and all(r['new_models'][n]['valid'] for r in (clear,pre) for n in ('motion_gen','motion_gen_batch'))
    conforms=conforms and all(x['position_error_m']<=.005 and x['orientation_error_rad']<=.05 for r in rows for n in ('motion_gen','motion_gen_batch') for x in r['new_models'][n]['link_conformance'])
    if endpoint and endpoint['exact_geometry_intersection']:decision='EXACT_ENDPOINT_GEOMETRY_INVALID_NO_PHYSICAL'
    elif not conforms:decision='MODEL_CONFORMANCE_INCOMPLETE'
    elif endpoint and all(v['valid'] for v in endpoint['new_models'].values()):decision='ENDPOINT_VALID_MICRO_PREREQUISITES_PENDING'
    else:decision='MODEL_REJECTED_ENDPOINT_GEOMETRY_REVIEW_REQUIRED'
    result={'schema_version':'cmf_f3_model_conformance_scene_v1','recipe_id':recipe['recipe_id'],'recipe_sha256':recipe['recipe_sha256'],'scene_binding':binding,
        'render_device_binding':None if scene is None else getattr(scene,'_cmf_render_device_binding_v1',None),
        'model_application':application,'states':rows,'error':error,'cleanup':cleanup,'accounting_complete':known,'planner_before':before,'planner_after':after,
        'trajectory_queries':after-before if known else None,'physical_attempts':0,'physical_actions_executed':False,'model_conformance':bool(conforms),'decision':decision,
        'global_stop':not known or (known and after!=before) or error is not None or not isinstance(cleanup,dict) or cleanup.get('cleanup_safety_pass') is not True}
    write_new(directory/'scene_receipt.json',result);return result
