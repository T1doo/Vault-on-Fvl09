"""CPU-wired physical validation proposal; no execution authorization or manifest."""
import copy,json,sys,importlib.util,traceback
from pathlib import Path
import numpy as np
import yaml
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计'
sys.path.insert(1,str(A/'f2_f3_model_bridge_v1_1'));sys.path.insert(2,str(A/'new_recipe_prereqs_v1'));sys.path.insert(3,str(A/'f3_model_replay_v1'));sys.path.insert(4,str(A));sys.path.append(str(A/'f3_preclose_candidate_micro_runtime_v1_1'))
from f3_conformance import helper,candidates,candidate_spec,SOURCE_SHA
from geometry import capture_scene_collision_geometry,capture_actor_geometry,make_world,digest
from model_apply import bind_actual_solver_base,rebuild_actual_motiongens,verify_actual_world_cache,runtime_joint_state
from lock_compat import update_locked_state
from goal_mapping import actual_flange_goal_to_reported_command
from realization_utf8_io_v1 import write_new
from candidate_executor import online_window
from post_lift_audit import audit_micro_lift_trace

def refresh_open_model(scene,derived):
    planner=scene.robot.left_planner;world=capture_scene_collision_geometry(scene,planner);names,q=runtime_joint_state(scene)
    locks={n:float(q[names.index(n)]) for n in derived['robot_cfg']['kinematics']['lock_joints']}
    for key in ('motion_gen','motion_gen_batch'):
        mg=getattr(planner,key);mg.update_world(make_world(world));update_locked_state(mg,locks,derived);verify_actual_world_cache(mg,world)
    return world

def _build_full_attached_bottle_model(scene,out):
    import torch
    from curobo.geom.types import Mesh
    from curobo.geom.sphere_fit import SphereFitType
    from curobo.geom.sdf.world import CollisionCheckerType
    from curobo.wrap.reacher.motion_gen import MotionGen,MotionGenConfig
    planner=scene.robot.left_planner;export=capture_scene_collision_geometry(scene,planner);bottle=[s for s in export['shapes'] if s['role']=='bottle'];rest={**export,'shapes':[s for s in export['shapes'] if s['role']!='bottle']};rest['geometry_sha256']=digest(rest['shapes'])
    names,q=runtime_joint_state(scene);cfg=yaml.safe_load(Path(planner.yml_path).read_text(encoding='utf-8'))['robot_cfg'];kin=cfg['kinematics'];kin['lock_joints']={n:float(q[names.index(n)]) for n in kin['lock_joints']};kin['link_names']=['fl_link6','fl_link7','fl_link8']
    np.random.seed(1531);torch.manual_seed(1531)
    mg=planner.motion_gen;values=mg.tensor_args.to_device([q[names.index(n)] for n in mg.kinematics.joint_names]).reshape(1,-1);ee=mg.kinematics.get_state(values).ee_pose;spheres=[]
    for s in bottle:
        obj=Mesh(name=s['name'],pose=s['solver_pose'],vertices=s['vertices'],faces=s['faces'])
        fits=obj.get_bounding_spheres(max(8,128//len(bottle)),.001,pre_transform_pose=ee.inverse(),tensor_args=mg.tensor_args,fit_type=SphereFitType.VOXEL_VOLUME_SAMPLE_SURFACE)
        spheres.extend({'center':[float(x) for x in p.position],'radius':float(p.radius)} for p in fits)
    if not spheres:raise ValueError('missing attached bottle collision geometry')
    data=yaml.safe_load(Path(kin['collision_spheres']).read_text(encoding='utf-8'))['collision_spheres'];data['attached_bottle']=spheres;kin['collision_spheres']=data;kin['collision_link_names']+=['attached_bottle'];kin['extra_links']=dict(kin.get('extra_links') or {})
    kin['extra_links']['attached_bottle']={'parent_link_name':'fl_link6','link_name':'attached_bottle','fixed_transform':[0,0,0,1,0,0,0],'joint_type':'FIXED','joint_name':'attached_bottle_fixed'}
    for link in ('fl_link6','fl_link7','fl_link8'):kin['self_collision_ignore'].setdefault(link,[]).append('attached_bottle')
    for key in ('motion_gen','motion_gen_batch'):
        kwargs={'interpolation_dt':.004,'num_trajopt_seeds':1,'use_cuda_graph':False,'collision_checker_type':CollisionCheckerType.MESH,'collision_cache':{'mesh':len(rest['shapes']),'obb':1}}
        if key=='motion_gen_batch':kwargs['num_graph_seeds']=1
        new=MotionGen(MotionGenConfig.load_from_robot_config(copy.deepcopy(cfg),make_world(rest),**kwargs));setattr(planner,key,new);verify_actual_world_cache(new,rest)
    receipt={'kind':'planner_only_attachment_from_actual_postclose_FK','actual_joint_names':names,'actual_qpos':q.tolist(),'sphere_count':len(spheres),'native_bottle_shapes':bottle,'robot_config':cfg,
        'physical_weld':False,'static_bottle_removed_only_because_attached':True,'table_and_pad_remain_enabled_for_robot_and_attached_bottle':True,'original_collision_sphere_buffer_unchanged':True,
        'normal_grasp_ignore_links':['fl_link6','fl_link7','fl_link8'],'support_contact_model_rejection_must_be_reported_not_bypassed':True}
    write_new(out/'postclose_attached_model.json',receipt);return receipt

def attach_closed_bottle_model(scene,out):
    from goal_pilot48_v1.runtime.support_witness import hold_witness,model_overlap_witness,bind_exact_pad
    from support_pair_collision_v1.factory import build_support_aware_motiongen
    from controlled_multi_future.family_runners_v3_1 import _entity
    receipt=_build_full_attached_bottle_model(scene,out)
    export=capture_scene_collision_geometry(scene,scene.robot.left_planner);export['shapes']=[s for s in export['shapes'] if s['role']!='bottle'];export['geometry_sha256']=digest(export['shapes'])
    mg=scene.robot.left_planner.motion_gen;names,q=runtime_joint_state(scene);tensor=mg.tensor_args.to_device([q[names.index(n)] for n in mg.kinematics.joint_names]).reshape(1,-1)
    witness=model_overlap_witness(mg,tensor,export)
    witness['hold']=hold_witness(scene.trace[-250:],selected_links=scene.selected_gripper_links(),bottle_name=_entity(scene.bottle).get_name(),pad_name=_entity(scene.pad).get_name())
    bind_exact_pad(witness,export,_entity(scene.pad).get_name())
    write_new(out/'fresh_support_witness.json',witness);applications=[]
    for name in ('motion_gen','motion_gen_batch'):
        new,application=build_support_aware_motiongen(receipt['robot_config'],export,witness,tensor_args=mg.tensor_args,batch=name=='motion_gen_batch')
        setattr(scene.robot.left_planner,name,new);applications.append(application)
    write_new(out/'support_pair_applications.json',applications)
    scene._cmf_fresh_support_witness=witness;scene._cmf_fresh_bottle_shapes=receipt['native_bottle_shapes'];scene._cmf_fresh_support_world=export
    return receipt

def native_plan_gate(scene,controls,out):
    from support_pair_collision_v1.escape import evaluate_controls
    from geometry import matrix
    from controlled_multi_future.family_runners_v3_1 import _pose
    names,q=runtime_joint_state(scene);planner=scene.robot.left_planner;pad=next(s for s in scene._cmf_fresh_support_world['shapes'] if s['name']=='pad__0')
    T=matrix(planner._cmf_solver_base_world_pose)@matrix(pad['solver_pose']);vertices=np.asarray(pad['vertices'])@T[:3,:3].T+T[:3,3]
    value=evaluate_controls(controls['position'],solver_joint_names=planner.motion_gen.kinematics.joint_names,actual_joint_names=names,actual_qpos=q,base_pose=planner._cmf_solver_base_world_pose,
        actor_pose=_pose(scene.bottle),bottle_shapes=scene._cmf_fresh_bottle_shapes,pad_top=float(vertices[:,2].max()),witness=scene._cmf_fresh_support_witness)
    write_new(out/'lift_native_preexecution_gate.json',value);return value

def execute(scene,proposal,out):
    from controlled_multi_future.family_runners_v3_1 import _plan_chain,_planner_reset,_arm_eef_pose,_must_action,_arm_tag,_wait_and_record,_entity
    from controlled_multi_future.high_level_physical_runner_v1 import _execute_planned_segment
    planner=scene.robot.left_planner;bind_actual_solver_base(scene,planner);initial=capture_scene_collision_geometry(scene,planner)
    _,_,derived,application=rebuild_actual_motiongens(scene,initial);write_new(out/'initial_model_application.json',application)
    targets={'grasp':np.array(proposal['desired_actual_flange_world_pose'])};targets['pregrasp']=targets['grasp'].copy();targets['pregrasp'][2]+=.12
    events=[];windows=[];plans=[];close_executed=False
    def plan_and_execute(stage,actual):
        command=actual_flange_goal_to_reported_command(scene.robot,scene.robot.left_planner,actual)
        name='f3_micro_'+stage;request=[{'segment_id':name,'pose':command.tolist()}]
        before=scene.planner_query_count
        if before>=3:raise ValueError('three trajectory query cap')
        write_new(out/(stage+'.plan.start.json'),{'actual_goal':actual.tolist(),'reported_command':command.tolist(),'query_counter_before':before})
        planned=_plan_chain(scene,request,query_limit=before+1,arm='left');after=scene.planner_query_count
        row={k:v for k,v in planned.items() if k!='controls'};row.update(query_before=before,query_after=after,actual_goal=actual.tolist(),reported_command=command.tolist());plans.append(row);write_new(out/(stage+'.plan.json'),row)
        if not planned['pass']:return None,planned
        with (out/(stage+'.controls.npz')).open('xb') as f:np.savez_compressed(f,position=planned['controls'][0]['position'],velocity=planned['controls'][0]['velocity'])
        if stage=='lift25':
            gate=native_plan_gate(scene,planned['controls'][0],out)
            if not gate['pass']:
                planned['native_preexecution_gate']=gate
                return None,planned
        # Execute exactly planned joint controls, but evaluate tracking against
        # pre-frozen actual flange pose, not legacy reported command coordinates.
        receipt=_execute_planned_segment(scene,planned['controls'],[{'segment_id':name,'pose':actual.tolist()}],0,'left');events.append(stage);return receipt,planned
    _planner_reset(scene,planner_seed=2026090603,variant_id=proposal['proposal_id'],arm='left')
    for stage in ('pregrasp','grasp'):
        refresh_open_model(scene,derived);receipt,plan=plan_and_execute(stage,targets[stage])
        if receipt is None:return {'pass':False,'earliest_failed_stage':stage+'_planner','events':events,'windows':windows,'plans':plans,'close_executed':False}
        gate=online_window(scene,receipt,{'segment_id':'f3_micro_'+stage,'pose':targets[stage].tolist()},plan['segment_receipts'][0],'left');windows.append(gate);write_new(out/(stage+'.full_window.json'),gate)
        if not gate['pass']:return {'pass':False,'earliest_failed_stage':stage+'_physical_gate','events':events,'windows':windows,'plans':plans,'close_executed':False}
    _must_action(scene,scene.close_gripper(_arm_tag('left'),pos=.50),'f3_micro_close');close_executed=True;events.append('close_0.50');_wait_and_record(scene,250);events.append('hold250');baseline=len(scene.trace)-1
    attach_closed_bottle_model(scene,out);_planner_reset(scene,planner_seed=2026090603,variant_id=proposal['proposal_id']+':actual_postclose',arm='left')
    actual=np.asarray(_arm_eef_pose(scene,'left'));lift=actual.copy();lift[2]+=.025
    receipt,plan=plan_and_execute('lift25',lift)
    if receipt is None:return {'pass':False,'earliest_failed_stage':'lift_native_preexecution_gate' if 'native_preexecution_gate' in plan else 'actual_postclose_lift_planner','events':events,'windows':windows,'plans':plans,'close_executed':True,'post_close_baseline_row':baseline}
    _wait_and_record(scene,50)
    checked=audit_micro_lift_trace(scene.trace,baseline_row=baseline,lift_receipt=receipt,arm='left',selected_links=list(scene.selected_gripper_links()),bottle_name=_entity(scene.bottle).get_name(),support_names=['table',_entity(scene.pad).get_name()])
    return {'pass':checked['pass'],'earliest_failed_stage':None if checked['pass'] else 'post_lift_gate','events':events,'windows':windows,'plans':plans,'close_executed':True,'post_lift':checked,'shared_v_executed':False}

def run(manifest):
    from controlled_multi_future.planner_qualification_manifests_v2_3 import _f3_scene_binding
    from controlled_multi_future.real_sapien_adapter_high_level_v1 import _PinnedSapienRenderDeviceContextV1
    out=Path(manifest['jobs'][0]['output_namespace']);out.mkdir(parents=True,exist_ok=False);recipe=candidates()[0];proposal=json.loads(Path(manifest['recipe_spec_path']).read_text(encoding='utf-8'))
    h=helper();legacy=candidate_spec(recipe);adapter=h.adapter_for('F3',legacy,out/'adapter',SOURCE_SHA);ctx=_PinnedSapienRenderDeviceContextV1(adapter.scene(legacy,phase='NEW_TOPDOWN_MICRO',program=None))
    result=error=trace=trace_error=None;before=after=None;trace_initialized=False
    try:
        with ctx as handle:
            scene=handle.scene
            if not hasattr(scene,'planner_query_count'):scene.planner_query_count=0
            before=scene.planner_query_count
            try:
                binding=h.prepare_f3_scene(scene,adapter,recipe,_f3_scene_binding(recipe));write_new(out/'scene_binding.json',binding)
                from goal_pilot48_v1.f3_com_revision_v1.live_mass_properties import capture_mass_properties
                mass=capture_mass_properties(scene.bottle);write_new(out/'actual_mass_properties.json',mass)
                actual_y=float(mass['cmass_local_pose'][1]);old_station=.09735;proposed_station=old_station+.0131
                if abs(actual_y-proposed_station)>=abs(actual_y-old_station):raise ValueError('actual COM contradicts the frozen direction of grasp-station improvement')
                current=adapter.capture_current(scene);anchor=adapter.capture_anchor(scene)
                write_new(out/'diagnostic_current_anchor.json',{'current':current,'anchor':anchor,'training_raw':False})
                scene.initialize_trace(scene.bottle,'left',role_actors=scene.role_actors)
                if not hasattr(scene,'trace') or not scene.trace or not hasattr(scene,'markers'):raise ValueError('trace bootstrap incomplete before any plan/action')
                trace_initialized=True
                result=execute(scene,proposal,out)
            except BaseException as exc:
                error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
            finally:
                after=getattr(scene,'planner_query_count',None)
                if trace_initialized:
                    try:
                        trace=h.save_trace(scene,out/'physical_trace.npz');write_new(out/'diagnostic_trace_receipt.json',trace)
                    except BaseException as exc:
                        trace_error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    except BaseException as exc:
        error=error or {'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    cleanup=ctx.cleanup_receipt;known=type(before)is int and type(after)is int and 0<=after-before<=3
    return {'schema_version':'cmf_f3_topdown_one_qualified_micro_terminal_v1_1','manifest_sha256':manifest['manifest_sha256'],'proposal_id':proposal['proposal_id'],'result':result,'error':error,'trace_save_error':trace_error,'trace_initialized_before_planning':trace_initialized,'cleanup':cleanup,'trace':trace,
        'scene_attempts':1,'physical_attempts':1,'IK_problems':0,'trajectory_queries':after-before if known else None,'accounting_complete':known,'new_raw':0,'new_roots':0,
        'pass':known and error is None and trace_error is None and cleanup is not None and cleanup.get('cleanup_safety_pass')is True,'micro_pass':result is not None and result['pass']}
