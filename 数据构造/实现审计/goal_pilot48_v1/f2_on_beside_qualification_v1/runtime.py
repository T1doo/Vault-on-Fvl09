"""Two fresh scenes, ordered on then beside; first required failure stops."""
from pathlib import Path
import traceback
import numpy as np
from .spec import build_spec,RELATIONS,REFERENCE,digest,sha
from .local_counts import LocalCounts
from goal_pilot48_v1.f2_on_beside_runtime_v1.runtime import run as suffix_run

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
def failure(exc,stage):return {'stage':stage,'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}

def run_one(manifest,spec,relation,out,artifact,arrays,local):
    from realization_utf8_io_v1 import write_new
    from controlled_multi_future.current_hasher import require_same_current
    from controlled_multi_future.anchor import compare_anchors
    out.mkdir(parents=True,exist_ok=False)
    scene=context=None;error=cleanup_error=save_error=None;result=replay=None;stage='adapter';primary=None;before_ids=set(local.scenes)
    try:
        Adapter,Context=components()
        adapter=Adapter(output_root=out/'adapter',expected_implementation_source_sha256=manifest['implementation_source_sha256'],binding=spec['binding'],planner_only=True)
        stage='scene_setup';context=Context(adapter.scene(spec['planned'],phase='f2_'+relation+'_noncollection_qualification',program=None))
        with context as handle:
            scene=handle.scene;scene._cmf_goal_prefix_output=str(out)
            try:
                stage='current_anchor';current=adapter.capture_current(scene);anchor=adapter.capture_anchor(scene)
                write_new(out/'actual_current.json',current);write_new(out/'actual_initial_anchor.json',anchor)
                require_same_current(spec['prefix_lineage']['current'],current)
                comparison=compare_anchors(artifact['reference_anchor'],anchor);write_new(out/'initial_anchor_equivalence.json',comparison)
                if comparison['equivalent'] is not True:raise ValueError('actual initial anchor failed original physical equivalence')
                stage='current_RGB';rgb=scene.cameras.get_rgb()
                with (out/'current_arrays.npz').open('xb') as f:
                    np.savez_compressed(f,head_rgb=rgb['head_camera']['rgb'],left_wrist_rgb=rgb['left_camera']['rgb'],right_wrist_rgb=rgb['right_camera']['rgb'],joint_qpos=scene.robot.left_entity.get_qpos(),joint_qvel=scene.robot.left_entity.get_qvel())
                stage='trace_initialize';adapter.initialize_prefix_replay_trace(scene)
                if scene.planner_query_count!=0:raise ValueError('unexpected initialization solver use')
                stage='canonical_replay';replay=actual_replay(scene,adapter,artifact,arrays,spec['prefix_lineage']['current']);write_new(out/'actual_replay.json',replay)
                if replay['prefix_end_equivalent'] is not True or replay['planner_query_delta']!=0:raise ValueError('real prefix replay failed zero-solver/equivalence')
                stage='fresh_prefix_physical';physical=adapter.validate_replayed_prefix_physical(scene,replay);write_new(out/'fresh_prefix_physical.json',physical)
                if physical['pass'] is not True:raise ValueError('original fresh prefix physical Gate rejected')
                stage='suffix';result=suffix_run(scene,replay,relation=relation,output=out,current_sha256=current['aggregate_sha256'],initial_anchor_sha256=anchor['anchor_sha256'],initial_anchor_equivalence=comparison)
                write_new(out/'qualification_suffix_result.json',result)
            except BaseException as exc:primary=exc;error=failure(exc,stage);raise
            finally:
                if getattr(scene,'trace',None):
                    try:
                        path=out/'qualification_trace.npz';receipt=dict(scene.save_trace(path));receipt['sha256']=sha(path);write_new(out/'trace_receipt.json',receipt)
                    except BaseException as exc:save_error=failure(exc,'save_trace')
    except BaseException as exc:
        if error is None:error=failure(exc,stage)
        elif exc is not primary:cleanup_error=failure(exc,'cleanup')
    new=[s for key,s in local.scenes.items() if key not in before_ids]
    if scene is None and len(new)==1 and getattr(new[0],'trace',None) and not (out/'qualification_trace.npz').exists():
        try:
            path=out/'qualification_trace.npz';receipt=dict(new[0].save_trace(path));receipt['sha256']=sha(path);write_new(out/'trace_receipt.json',receipt)
        except BaseException as exc:save_error=failure(exc,'partial_save')
    try:cleanup=None if context is None else context.cleanup_receipt
    except BaseException as exc:cleanup=None;cleanup_error=failure(exc,'cleanup_receipt')
    # Model namespace also contains planner starts. Count only explicit
    # high_level_constraint_call records, not a filename heuristic.
    import json
    high=sum(json.loads(p.read_text(encoding='utf-8')).get('high_level_constraint_call',0) for p in out.glob('model_*_start.json'))
    cap=spec['high_level_state_checks'][relation]
    safe=error is None and cleanup_error is None and save_error is None and cleanup is not None and cleanup.get('cleanup_safety_pass') is True and high<=cap
    value={'relation':relation,'error':error,'cleanup_error':cleanup_error,'trace_save_error':save_error,'cleanup':cleanup,
      'high_level_state_checks':high,'high_level_state_check_cap':cap,'suffix_result':result,'replay':replay,
      'pass':safe,'scientific_route_pass':bool(safe and high==cap and result is not None and result.get('pass') is True)}
    value['receipt_sha256']=digest(value);write_new(out/'branch_terminal.json',value);return value

def run(manifest):
    from realization_utf8_io_v1 import write_new
    out=Path(manifest['jobs'][0]['output_namespace']);out.mkdir(parents=True,exist_ok=False)
    local=LocalCounts();branches=[];error=None;known=False
    try:
        spec=build_spec()
        if digest(spec)!=manifest.get('on_beside_qualification_spec_sha256'):raise ValueError('exact two-branch qualification spec not bound')
        write_new(out/'qualification_spec.json',spec);artifact,arrays=load_reference()
        if artifact['reference_current_sha256']!=spec['prefix_lineage']['current']['aggregate_sha256']:raise ValueError('canonical/current binding changed')
        with local:
            for relation in RELATIONS:
                try:
                    branch=run_one(manifest,spec,relation,out/relation,artifact,arrays,local);branches.append(branch)
                finally:
                    # Preserve scalar counts, not the closed scene/robot/CUDA models.
                    local.retire_completed()
                    import gc
                    gc.collect()
                if branch['scientific_route_pass'] is not True:break
    except BaseException as exc:error=failure(exc,'qualification')
    try:counts=local.snapshot();known=True
    except BaseException as exc:counts={};error=error or failure(exc,'accounting')
    safe=known and error is None and bool(branches) and all(b['pass'] for b in branches) and counts.get('trajectory_queries',9)<=8
    value={'schema_version':'f2_on_beside_qualification_terminal_v1','manifest_sha256':manifest.get('manifest_sha256'),**counts,
      'error':error,'branches':branches,'unattempted_relations':list(RELATIONS[len(branches):]),'accounting_complete':known,
      'pass':safe,'scientific_route_pass':bool(safe and len(branches)==2 and all(b['scientific_route_pass'] for b in branches)
        and counts['trajectory_queries']==8 and counts['fresh_scene_attempts']==2 and counts['action_scenes_observed']==2),
      'high_level_state_checks':sum(b['high_level_state_checks'] for b in branches),'high_level_state_check_cap':16,
      'stop_on_first_required_failure':True,'new_raw_trajectories':0,'new_accepted_roots':0,'whole_root_qualification_complete':False,
      'qualification_only':True,'inside_contact_permission_used':False}
    value['receipt_sha256']=digest(value);write_new(out/'job_terminal.json',value);return value
