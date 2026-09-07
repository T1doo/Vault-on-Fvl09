"""Guard-compatible first upright qualification only; no confirmation/sharedV dispatch."""
import json,hashlib,sys,traceback
from pathlib import Path
import numpy as np
from .native import A,capture,Checker,p7,hash_value
sys.path[:0]=[str(A),str(A/'f2_f3_model_bridge_v1_1'),str(A/'new_recipe_prereqs_v1')]
from goal_pilot48_v1.f3_upright_design_v1.scene import initial_gate,derive_targets
from .context import Counts,make
from .ik import qualify
from .micro_binding import execute
from realization_utf8_io_v1 import write_new
def read_spec(manifest):
    p=Path(manifest['upright_design_spec_path']);spec=json.loads(p.read_text(encoding='utf-8'));body=dict(spec);h=body.pop('receipt_sha256')
    if hash_value(body)!=h or h!='1976ee32ab6d53fc6bfdfe2ed949c70614c96cfb7d61529d6014127a0b05436f':raise ValueError('unique selected upright B spec changed')
    if manifest.get('upright_design_spec_sha256')!=hashlib.sha256(p.read_bytes()).hexdigest():raise ValueError('spec file not bound')
    for path,value in spec['source_bindings'].items():
        if not Path(path).resolve().is_relative_to('/nfs_share/lijunhui') or hashlib.sha256(Path(path).read_bytes()).hexdigest()!=value:raise ValueError('upright design source changed')
    return spec
def snapshot(scene,adapter,spec):
    from goal_pilot48_v1.f3_com_revision_v1.live_mass_properties import capture_mass_properties
    from controlled_multi_future.probes.runtime_trace import _entity,_rigid_velocity
    from controlled_multi_future.f3_physical_contact_signal_v8 import classify_contact_pair_physical_hit_v8
    missing=object();old_actor=getattr(scene,'trace_contact_actor',missing);old_arm=getattr(scene,'trace_arm',missing)
    try:
        scene.trace_contact_actor=scene.bottle;scene.trace_arm='left';pairs=scene._contacts()[0]
    finally:
        for key,oldvalue in [('trace_contact_actor',old_actor),('trace_arm',old_arm)]:
            if oldvalue is missing:delattr(scene,key)
            else:setattr(scene,key,oldvalue)
    signals=[classify_contact_pair_physical_hit_v8(p) for p in pairs];support=any(s['physical_hit_for_gate'] and {p['body_a'],p['body_b']}=={'f3_main_bottle','f3_original_pad'} for p,s in zip(pairs,signals))
    linear,lok=_rigid_velocity(scene.bottle,'linear_velocity');angular,aok=_rigid_velocity(scene.bottle,'angular_velocity')
    asset=adapter._entity_payloads(scene)['bottle'];mass=capture_mass_properties(scene.bottle)
    materials=[]
    for c in _entity(scene.bottle).get_components():
        if hasattr(c,'get_collision_shapes'):
            for sh in c.get_collision_shapes():
                m=sh.get_physical_material();materials.append([float(m.get_static_friction()),float(m.get_dynamic_friction())])
    if not materials or any(v!=[.5,.5] for v in materials):raise ValueError('actual bottle material changed')
    return {'seed':int(scene._cmf_setup_kwargs['seed']),'scene_instance_id':scene._cmf_scene_instance_id,'canonical_settle_steps':scene._cmf_canonical_settle_steps,
        'asset_id':asset['model_id'],'scale':asset['scale'],'bottle_pose':p7(_entity(scene.bottle)),'pad_pose':p7(_entity(scene.pad)),
        'marker_pose':p7(_entity(scene.central_marker)),'mass_properties':mass,'linear_velocity':linear.tolist(),'angular_velocity':angular.tolist(),
        'pad_physical_contact':support,'contact_signal_complete':lok and aok and all(s['evidence_complete'] for s in signals),'contact_pairs':pairs,'actual_asset':asset,'actual_materials':materials}
def accounting(local,meter):
    known=type(local.IK)is int and type(local.MG)is int
    expected={'solver_problems':local.IK+local.MG if known else None,'fresh_scenes':local.scenes,'action_scenes':local.actions,'collection_attempts':0}
    return expected,known and expected==dict(meter.counts) and 0<=local.IK<=3 and 0<=local.MG<=3 and local.steps<=6000
def validate_first_scope(manifest):
    if len(manifest['jobs'])!=1:raise ValueError('exact one first-qualification job required')
    job=manifest['jobs'][0];caps=dict(solver_problems=6,fresh_scenes=1,action_scenes=1,collection_attempts=0)
    if job.get('kind')!='F3_UPRIGHT_QUALIFICATION' or job.get('requires_live_meter') is not True:raise ValueError('mixed IK/MG first qualification requires its explicit live-meter kind')
    if job.get('resource_caps')!=caps or job.get('timeout_seconds')!=900 or manifest.get('reserved')!={**caps,'gpu_lease_seconds':1080}:raise ValueError('first6-only budget; conditional second17 is not this entry')
def run(manifest,*,meter):
    validate_first_scope(manifest)
    out=Path(manifest['jobs'][0]['output_namespace']);out.mkdir(parents=True,exist_ok=False);counts=Counts();scene=None;ctx=None;adapter=None;initialized=False
    error=save_error=accounting_error=None;result=None;trace=None;standing=None;IK=None;MG=None
    try:
        spec=read_spec(manifest);write_new(out/'upright_design_spec.json',spec);adapter,ctx=make(spec,out,counts)
        with ctx as handle:
            scene=handle.scene
            try:
                scene._cmf_generator_version='f3_upright13_B_qualification_v1'
                snap=snapshot(scene,adapter,spec);write_new(out/'standing_snapshot.json',snap);standing=initial_gate(snap,spec);write_new(out/'standing_gate.json',standing)
                if standing['pass']:
                    current=adapter.capture_current(scene);anchor=adapter.capture_anchor(scene);write_new(out/'current_anchor.json',{'current':current,'anchor':anchor,'upright_new_current_not_old_lineage':True})
                    scene.initialize_trace(scene.bottle,'left',role_actors=scene.role_actors);initialized=True
                    from model_apply import bind_actual_solver_base,runtime_joint_state
                    bind_actual_solver_base(scene,scene.robot.left_planner);names,q=runtime_joint_state(scene)
                    native=capture(scene,scene.robot.left_planner._cmf_solver_base_world_pose,names,q);write_new(out/'initial_native_inventory.json',native)
                    active=list(scene.robot.left_planner.motion_gen.kinematics.joint_names);row=np.asarray([[q[names.index(n)] for n in active]])
                    initial_native=Checker(native).check(row,active);write_new(out/'initial_native_gate.json',initial_native)
                    if initial_native['pass']:
                        targets=derive_targets(spec,snap['bottle_pose']);write_new(out/'actual_fixed_targets.json',targets)
                        IK=qualify(scene,targets,native,out,counts)
                        if IK['pass']:MG=execute(scene,targets,spec,out)
                        result={'qualified':bool(IK['pass'] and MG is not None and MG['pass']),'IK':IK,'micro':MG}
                    else:result={'qualified':False,'stage':'initial_native_full_robot_world'}
                else:result={'qualified':False,'stage':'standing_support_or_identity'}
            except BaseException as exc:
                error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
            finally:
                value=getattr(scene,'planner_query_count',0)
                if type(value)is not int:accounting_error={'message':'unknown local MG count'};counts.MG=None
                else:counts.MG=value
                if initialized:
                    try:
                        path=out/'physical_trace.npz';scene.save_trace(path);trace={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sample_count':len(scene.trace)};write_new(out/'trace_receipt.json',trace)
                    except BaseException as exc:save_error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    except BaseException as exc:error=error or {'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    cleanup=None if ctx is None else ctx.cleanup_receipt;expected,known=accounting(counts,meter)
    safe=known and error is None and save_error is None and accounting_error is None and cleanup is not None and cleanup.get('cleanup_safety_pass') is True
    restored=None if MG is None else MG.get('full_world_restoration_checks')
    micro_evidence=MG is not None and MG.get('pass') is True and MG.get('native_full_arm_controls_pass') is True and MG.get('post_lift',{}).get('pass') is True and isinstance(restored,dict) and set(restored)=={'motion_gen','motion_gen_batch'} and all(v.get('valid') is True for v in restored.values())
    qualified=bool(safe and counts.IK==3 and counts.MG==3 and standing and standing['pass'] and result and result['qualified'] and micro_evidence)
    value={'schema_version':'f3_upright_first_qualification_terminal_v1','manifest_sha256':manifest['manifest_sha256'],'error':error,'trace_error':save_error,'cleanup':cleanup,
        'standing_gate':standing,'result':result,'trace':trace,'accounting_error':accounting_error,'local_counts':expected,'IK_problems':counts.IK,'trajectory_queries':counts.MG,
        'scene_attempts':counts.scenes,'action_scenes_observed':counts.actions,'collection_attempts':0,'physics_steps_after_setup_scene':counts.steps,
        'setup_scene_internal_physics_steps':'not_instrumented_unknown','after_setup_step_cap_unchanged':6000,
        'all_setup_physics_step_total_verified':False,
        'accounting_complete':known,'pass':safe,'qualified':qualified,'micro_pass':qualified,'scientific_route_pass':qualified,
        'scientific_scope':'first upright B qualification only; not two-fresh/sharedV/root acceptance',
        'first_fresh_only':True,'confirmation_or_sharedV_executed':False,'new_raw':0,'new_roots':0}
    value['receipt_sha256']=hash_value(value);write_new(out/'qualification_terminal.json',value);return value
