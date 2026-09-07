"""Fresh current/anchor, exact replay, inside suffix and owned-scene cleanup."""
import traceback
from pathlib import Path
import numpy as np
from .spec import build_spec,digest,REFERENCE,sha
from .local_counts import LocalCounts
from goal_pilot48_v1.f2_controlled_inside_runtime_v2.runtime import run as inside_run

def components():
    from controlled_multi_future.f2_asset_bound_runtime_v3 import RoboTwinRealSapienF2AssetBoundAdapterV3
    from controlled_multi_future.real_sapien_adapter_high_level_v1 import _PinnedSapienRenderDeviceContextV1
    return RoboTwinRealSapienF2AssetBoundAdapterV3,_PinnedSapienRenderDeviceContextV1

def load_reference():
    from controlled_multi_future.canonical_prefix_artifact_v1 import load_canonical_prefix_artifact
    return load_canonical_prefix_artifact(REFERENCE/'canonical_prefix_artifact')

def actual_replay(scene,adapter,artifact,arrays,current):
    from controlled_multi_future.canonical_prefix_replay_v1 import replay_canonical_prefix
    return replay_canonical_prefix(scene,manifest=artifact,arrays=arrays,reference_current=current,capture_current=adapter.capture_current,capture_anchor=adapter.capture_anchor)

def run(manifest):
    from realization_utf8_io_v1 import write_new
    from controlled_multi_future.current_hasher import require_same_current
    from controlled_multi_future.anchor import compare_anchors
    out=Path(manifest['jobs'][0]['output_namespace']);out.mkdir(parents=True,exist_ok=False)
    context=scene=None;error=cleanup_error=save_error=None;result=replay=None;local=LocalCounts();stage='spec';primary=None
    try:
        spec=build_spec()
        if digest(spec)!=manifest.get('inside_qualification_spec_sha256'):raise ValueError('exact qualification spec not bound')
        write_new(out/'qualification_spec.json',spec);artifact,arrays=load_reference()
        if artifact['reference_current_sha256']!=spec['prefix_lineage']['reference_current']['aggregate_sha256']:raise ValueError('artifact/current lineage mismatch')
        Adapter,Context=components();stage='adapter'
        adapter=Adapter(output_root=out/'adapter',expected_implementation_source_sha256=manifest['implementation_source_sha256'],binding=spec['binding'],planner_only=True)
        with local:
            stage='scene_setup';context=Context(adapter.scene(spec['planned'],phase=spec['scene_phase'],program=None))
            with context as handle:
                scene=handle.scene;scene._cmf_goal_prefix_output=str(out)
                try:
                    stage='current_anchor';current=adapter.capture_current(scene);anchor=adapter.capture_anchor(scene)
                    write_new(out/'actual_current.json',current);write_new(out/'actual_initial_anchor.json',anchor)
                    require_same_current(spec['prefix_lineage']['reference_current'],current)
                    comparison=compare_anchors(artifact['reference_anchor'],anchor);write_new(out/'initial_anchor_equivalence.json',comparison)
                    if comparison['equivalent'] is not True:raise ValueError('fresh initial anchor not physically equivalent')
                    stage='current_RGB';rgb=scene.cameras.get_rgb()
                    with (out/'current_arrays.npz').open('xb') as f:
                        np.savez_compressed(f,head_rgb=rgb['head_camera']['rgb'],left_wrist_rgb=rgb['left_camera']['rgb'],right_wrist_rgb=rgb['right_camera']['rgb'],joint_qpos=scene.robot.left_entity.get_qpos(),joint_qvel=scene.robot.left_entity.get_qvel())
                    stage='trace_initialize';adapter.initialize_prefix_replay_trace(scene)
                    if int(scene.planner_query_count)!=0:raise ValueError('initialization consumed solver or counter was inherited')
                    stage='canonical_replay';replay=actual_replay(scene,adapter,artifact,arrays,spec['prefix_lineage']['reference_current']);write_new(out/'actual_replay.json',replay)
                    if replay['prefix_end_equivalent'] is not True or replay['planner_query_delta']!=0:raise ValueError('actual canonical replay failed equivalence/zero-solver contract')
                    stage='fresh_prefix_physical';physical=adapter.validate_replayed_prefix_physical(scene,replay);write_new(out/'fresh_prefix_physical.json',physical)
                    if physical['pass'] is not True:raise ValueError('fresh replay original physical Gate rejected')
                    stage='inside_suffix';result=inside_run(scene,replay,output=out,current_sha256=current['aggregate_sha256'],initial_anchor_sha256=anchor['anchor_sha256'],initial_anchor_equivalence=comparison)
                    write_new(out/'inside_result.json',result)
                except BaseException as exc:
                    primary=exc;error={'stage':stage,'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};raise
                finally:
                    if getattr(scene,'trace',None):
                        try:
                            path=out/'qualification_trace.npz';receipt=dict(scene.save_trace(path));receipt['sha256']=sha(path);write_new(out/'trace_receipt.json',receipt)
                        except BaseException as exc:save_error={'type':type(exc).__name__,'message':str(exc)}
    except BaseException as exc:
        details={'stage':stage,'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        if error is None:error=details
        elif exc is not primary:cleanup_error=details
    if scene is None and len(local.scenes)==1:
        partial=next(iter(local.scenes.values()))
        if getattr(partial,'trace',None) and not (out/'qualification_trace.npz').exists():
            try:
                path=out/'qualification_trace.npz';receipt=dict(partial.save_trace(path));receipt['sha256']=sha(path);write_new(out/'trace_receipt.json',receipt)
            except BaseException as exc:save_error={'type':type(exc).__name__,'message':str(exc)}
    try:cleanup=None if context is None else context.cleanup_receipt
    except BaseException as exc:cleanup=None;cleanup_error={'type':type(exc).__name__,'message':str(exc)}
    try:counts=local.snapshot();known=True
    except Exception as exc:counts={};known=False;error=error or {'type':type(exc).__name__,'message':str(exc),'stage':'local_counts'}
    checks=list(out.glob('model_*_start.json'));high_checks=len(checks)
    safe=known and counts.get('trajectory_queries',6)<=5 and high_checks<=10 and error is None and save_error is None and cleanup_error is None and cleanup is not None and cleanup.get('cleanup_safety_pass') is True
    value={'schema_version':'f2_inside_fresh_replay_qualification_terminal_v1','manifest_sha256':manifest.get('manifest_sha256'),**counts,
      'accounting_complete':known,'high_level_state_checks':high_checks,'high_level_state_check_cap':10,'error':error,'trace_save_error':save_error,'cleanup_error':cleanup_error,'cleanup':cleanup,
      'inside_suffix_result':result,'replay':replay,'new_raw_trajectories':0,'new_accepted_roots':0,'whole_root_qualification_complete':False,
      'qualification_only':True,'pass':safe,'scientific_route_pass':bool(safe and result is not None and result['pass'])}
    value['receipt_sha256']=digest(value);write_new(out/'job_terminal.json',value);return value
