"""One real prefix qualification, never a whole-root/collection entry."""
import json,traceback
from pathlib import Path
import numpy as np
from .spec import A,digest,build_prefix_spec
from .prefix_controller import make_controller

def run(manifest):
    from realization_utf8_io_v1 import write_new
    out=Path(manifest['jobs'][0]['output_namespace']);out.mkdir(parents=True,exist_ok=False)
    scene=context=None;before=after=None;attempts=0;result=error=save_error=artifact=None;prefix_pass=False
    primary_exception=None;cleanup_error=None;actions=0;stage='spec'
    try:
        spec=build_prefix_spec()
        if manifest.get('f2_goal_prefix_spec_sha256')!=digest(spec):raise ValueError('exact prefix qualification spec not bound')
        write_new(out/'prefix_spec.json',spec)
        from controlled_multi_future.f2_asset_bound_runtime_v3 import RoboTwinRealSapienF2AssetBoundAdapterV3
        from controlled_multi_future.real_sapien_adapter_high_level_v1 import _PinnedSapienRenderDeviceContextV1
        stage='adapter';adapter=RoboTwinRealSapienF2AssetBoundAdapterV3(output_root=out/'adapter',expected_implementation_source_sha256=manifest['implementation_source_sha256'],binding=spec['binding'],planner_only=True)
        adapter.controller_v3_3=make_controller(spec['binding'])
        stage='scene_setup';attempts=1;context=_PinnedSapienRenderDeviceContextV1(adapter.scene(spec['planned'],phase='canonical_prefix_reference',program=None))
        with context as handle:
            scene=handle.scene;scene._cmf_goal_prefix_output=str(out)
            if not hasattr(scene,'planner_query_count'):scene.planner_query_count=0
            before=scene.planner_query_count
            try:
                stage='capture_current';current=adapter.capture_current(scene)
                stage='capture_anchor';anchor=adapter.capture_anchor(scene)
                stage='programs';programs=adapter.build_programs(scene)
                write_new(out/'reference_current_hashes.json',current);write_new(out/'reference_anchor.json',anchor)
                write_new(out/'provisional_programs.json',{'programs':programs,'candidate_universe_frozen':False,'qualification_only':True})
                stage='capture_RGB';rgb=scene.cameras.get_rgb()
                with (out/'current_arrays.npz').open('xb') as f:
                    np.savez_compressed(f,head_rgb=rgb['head_camera']['rgb'],left_wrist_rgb=rgb['left_camera']['rgb'],right_wrist_rgb=rgb['right_camera']['rgb'],
                      joint_qpos=scene.robot.left_entity.get_qpos(),joint_qvel=scene.robot.left_entity.get_qvel())
                prefix_contract=adapter.canonical_prefix_contract(programs);write_new(out/'prefix_contract.json',prefix_contract)
                stage='prefix_execution';result=adapter.plan_and_execute_canonical_prefix(scene,prefix_contract)
                prefix_pass=result['prefix_physical_acceptance']['pass'] is True
                summary={k:v for k,v in result.items() if k!='arrays'}
                write_new(out/'prefix_result.json',summary)
                if prefix_pass:
                    stage='trace_save';trace=out/'prefix_trace.npz';trace_receipt=dict(scene.save_trace(trace))
                    import hashlib
                    trace_receipt['sha256']=hashlib.sha256(trace.read_bytes()).hexdigest()
                    from controlled_multi_future.canonical_prefix_artifact_v1 import build_canonical_prefix_artifact
                    from .artifact_io import write_prefix_artifact
                    stage='prefix_artifact'
                    data,arrays=build_canonical_prefix_artifact(root_slot_id=spec['planned']['slot_id'],family='F2',reference_current_sha256=current['aggregate_sha256'],reference_anchor=anchor,prefix_contract=prefix_contract,
                      planner_seed=result['planner_seed'],planner_query_receipts=result['planner_query_receipts'],planner_source_hash=result['planner_source_hash'],arrays=result['arrays'],
                      semantic_prefix_end_anchor=result['semantic_prefix_end_anchor'],acceptance_prefix_end_anchor=result['acceptance_prefix_end_anchor'],settling_step_count=result['settling_step_count'],
                      settling_policy=result['settling_policy'],prefix_physical_acceptance=result['prefix_physical_acceptance'],reference_trace_source=trace_receipt,
                      reference_event_boundaries=result.get('reference_event_boundaries',{}))
                    artifact=write_prefix_artifact(out/'canonical_prefix_artifact',data,arrays)
            except BaseException as exc:
                primary_exception=exc;error={'type':type(exc).__name__,'message':str(exc),'stage':stage,'traceback':traceback.format_exc()};raise
            finally:
                after=getattr(scene,'planner_query_count',None)
                actions=int(len(getattr(scene,'trace',[]) or [])>1)
                if getattr(scene,'trace',None) and not (out/'prefix_trace.npz').exists():
                    try:scene.save_trace(out/'partial_prefix_trace.npz')
                    except BaseException as exc:save_error={'type':type(exc).__name__,'message':str(exc)}
    except BaseException as exc:
        details={'type':type(exc).__name__,'message':str(exc),'stage':stage,'traceback':traceback.format_exc()}
        if error is None:error=details
        elif exc is not primary_exception:cleanup_error=details
    try:cleanup=None if context is None else context.cleanup_receipt
    except BaseException as exc:cleanup=None;cleanup_error={'type':type(exc).__name__,'message':str(exc),'stage':'cleanup_receipt'}
    known=(attempts==0 and before is None and after is None) or (type(before) is int and type(after) is int and 0<=after-before<=3)
    delta=0 if attempts==0 else after-before if known else None
    safe=known and error is None and save_error is None and cleanup_error is None and cleanup is not None and cleanup.get('cleanup_safety_pass') is True
    value={'schema_version':'f2_goal_real_prefix_qualification_terminal_v1','manifest_sha256':manifest.get('manifest_sha256'),
      'fresh_scene_attempts':attempts,'trajectory_queries':delta,'accounting_complete':known,'action_scenes_observed':actions,'ik_problem_attempts':0,
      'prefix_physical_pass':prefix_pass,'canonical_prefix_artifact':artifact,'error':error,'trace_save_error':save_error,
      'structured_prefix_failure':None if scene is None else getattr(scene,'_cmf_prefix_failure_receipt',None),
      'cleanup':cleanup,'cleanup_error':cleanup_error,'collection_attempts':0,'new_raw_trajectories':0,'new_accepted_roots':0,
      'all_three_relation_qualification_complete':False,'full_root_execution_enabled':False,
      'scientific_route_pass':bool(safe and prefix_pass and artifact is not None),'pass':safe}
    value['receipt_sha256']=digest(value);write_new(out/'job_terminal.json',value);return value
