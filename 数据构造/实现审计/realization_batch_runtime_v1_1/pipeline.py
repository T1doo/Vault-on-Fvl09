"""Single-fresh-scene realization collection using the original family executors."""
import copy,json,time
from pathlib import Path
import numpy as np
from catalog import W,A,SOURCE_SHA,read,sha,canonical,seal,make_adapter,source_branch
from retiming import retime

class ScientificFailure(RuntimeError):pass
def write_new(path,value):
    from controlled_multi_future.canonical_artifact import canonical_jsonable
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(canonical_jsonable(value),f,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)

def segment_window(query_ids,active,queries,name,arm='left'):
    matches=[q for q in queries if q['source']==name and q['arm']==arm]
    if len(matches)!=1:raise ValueError('ambiguous or absent segment query: '+name)
    column=0 if arm=='left' else 1
    rows=np.flatnonzero((np.asarray(query_ids)[:,column]==matches[0]['query_id']) & np.asarray(active,dtype=bool)[:,column])
    if len(rows)==0 or rows[0]==0 or not np.all(np.diff(rows)==1):raise ValueError('absent or noncontiguous segment intervals: '+name)
    # Dense trace contains an initial state row, then one realized row per
    # executed command. The first active row ends the first interval.
    return int(rows[0]-1),int(rows[-1]),int(len(rows))

def variations_from_trace(cell,result,scene,retiming):
    sem=result['semantic_verifier'];new_rows=sem['suffix_segment_execution_receipts']
    parent=source_branch(cell)['verifier']['family_semantic_verifier'];old_rows=parent['suffix_segment_execution_receipts']
    old_by={r['segment_id']:r for r in old_rows};new_by={r['segment_id']:r for r in new_rows}
    source_path=Path(cell['parent_root'])/'branches'/cell['program']['program_id']/'trace_source.npz'
    with np.load(source_path,allow_pickle=False) as z:
        old_eef=z['eef_pose'];old_time=z['timestamp'];old_ids=z['planner_query_id'];old_active=z['planner_goal_active'];old_queries=json.loads(str(z['planner_queries_json'].item()))
    new_ids=np.asarray([r['planner_query_id'] for r in scene.trace]);new_active=np.asarray([r['planner_goal_active'] for r in scene.trace])
    measures=[]
    for index in cell['changed_indices']:
        name=cell['targets'][index]['segment_id'];o=old_by[name];n=new_by[name]
        os,oe,old_n=segment_window(old_ids,old_active,old_queries,name)
        ns,ne,new_n=segment_window(new_ids,new_active,scene.planner_queries,name)
        if cell['variant']=='r_inv_path':
            observed=float(scene.trace[ne]['eef'][2]-old_eef[oe,2])
            passed=observed>=cell['minimum_realized_path_delta_z_m']
            measures.append({'segment_id':name,'observed_endpoint_z_change_m':observed,'required_minimum_m':cell['minimum_realized_path_delta_z_m'],'pass':bool(passed)})
        else:
            tr=next(r for r in retiming if r['segment_id']==name)
            old_dt=float(old_time[oe]-old_time[os]);new_dt=float(scene.trace[ne]['timestamp']-scene.trace[ns]['timestamp'])
            passed=old_n==tr['old_samples'] and new_n==tr['new_samples'] and new_n>old_n and np.isclose(new_dt/old_dt,tr['actual_execution_interval_scale'],atol=1e-9,rtol=1e-9)
            measures.append({'segment_id':name,'old_steps':old_n,'new_steps':new_n,'old_duration_s':old_dt,'new_duration_s':new_dt,'observed_scale':new_dt/old_dt,'expected_scale':tr['actual_execution_interval_scale'],'pass':bool(passed)})
    return seal({'schema_version':'cmf_realized_variation_verifier_v1','variant':cell['variant'],'source_trace_sha256':sha(source_path),'measurements':measures,'pass':bool(measures) and all(x['pass'] for x in measures)})

def plan_or_load_controls(cell,scene):
    from controlled_multi_future.frozen_suffix_artifact_v1 import load_frozen_suffix_artifact,build_frozen_suffix_artifact,write_frozen_suffix_artifact
    from controlled_multi_future.family_runners_v3_1 import _plan_chain,_planner_reset
    from controlled_multi_future.family_runners_v3_3 import _cache_preplanned_suffix_controls,install_frozen_suffix_controls
    manifest,_,source_controls=load_frozen_suffix_artifact(Path(cell['source_suffix']).parent);src=manifest['execution_spec']
    targets=copy.deepcopy(cell['targets']);transforms=[]
    if cell['variant']=='r_inv_motion':
        controls=copy.deepcopy(source_controls)
        for i in cell['changed_indices']:controls[i],r=retime(controls[i],targets[i]['segment_id']);transforms.append(r)
        spec=copy.deepcopy(src);spec['targets']=targets;spec['realization_control_transforms']=transforms
        from controlled_multi_future.current_hasher import hash_array
        spec['parent_actual_prefix_end_qpos_sha256']=spec['actual_prefix_end_qpos_sha256']
        spec['actual_prefix_end_qpos_sha256']=hash_array(np.asarray(scene.robot.left_entity.get_qpos(),dtype=np.float64))
        spec['new_solver_query_count']=0;spec['source_planner_query_provenance']='replayed_parent_frozen_queries_not_new_solver_calls'
        spec['control_cache_key']=canonical(spec)
        install_frozen_suffix_controls(scene,spec,controls)
        return spec,controls,transforms
    raw=np.asarray(scene.robot.left_entity.get_qpos(),dtype=np.float64);before=int(scene.planner_query_count)
    reset=_planner_reset(scene,planner_seed=int(src['planner_reset_receipt']['planner_seed']),variant_id='development_path:'+cell['cell_id'],arm='left')
    planned=_plan_chain(scene,targets,query_limit=before+len(targets),arm='left')
    if planned['pass'] is not True:raise ScientificFailure('path planner failed: '+planned['segment_receipts'][-1]['segment_id'])
    common={'schema_version','program_id','arm','targets','segment_receipts','planner_reset_receipt','planner_query_receipts','terminal_qpos','terminal_qpos_sha256','control_cache_key',
       'actual_prefix_end_qpos_sha256','actual_prefix_end_qpos_dtype','planner_input_prefix_end_qpos_sha256','planner_input_prefix_end_qpos_dtype','terminal_joint_limit_margin_rad','minimum_terminal_joint_limit_margin_rad','terminal_qpos_within_joint_limits','joint_limit_audit_version'}
    extra={k:copy.deepcopy(v) for k,v in src.items() if k not in common}
    if 'object_target_groups' in extra:
        for group in extra['object_target_groups']:
            start=group['target_start_index'];group['targets']=copy.deepcopy(targets[start:start+group['target_count']])
    extra['parent_target_source_sha256']=cell['source_suffix_file_sha256'];extra['new_target_construction_queries']=0
    cached=_cache_preplanned_suffix_controls(scene,program_id=cell['program']['program_id'],arm='left',targets=targets,raw_actual_qpos=raw,
       planner_input_qpos=raw.astype(np.float32),reset=reset,planned=planned,planner_query_count=int(scene.planner_query_count)-before,extra=extra)
    return cached['execution_spec'],cached['_execution_controls'],transforms

def collect_cell(cell,output,*,shared_current_dir):
    from controlled_multi_future.anchor import compare_anchors
    from controlled_multi_future.current_hasher import require_same_current
    from controlled_multi_future.canonical_prefix_artifact_v1 import load_canonical_prefix_artifact
    from controlled_multi_future.canonical_prefix_replay_v1 import replay_canonical_prefix
    from controlled_multi_future.raw_writer import write_raw_attempt,verify_raw_artifact_integrity
    from controlled_multi_future.frozen_suffix_artifact_v1 import build_frozen_suffix_artifact,write_frozen_suffix_artifact,load_frozen_suffix_artifact
    from controlled_multi_future.development_video_capture_v1 import validate_development_trajectory_mp4_receipt_v1
    from controlled_multi_future.root_orchestrator_v1_2 import _step_hashes
    output=Path(output);output.mkdir(parents=True,exist_ok=False);parent=Path(cell['parent_root']);program=cell['program']
    reference=read(parent/'reference_current_hashes.json');anchor=read(parent/'reference_anchor.json');planned_root=read(parent/'planned_root_slot_spec.json')
    prefix,arrays=load_canonical_prefix_artifact(parent/'canonical_prefix_artifact')
    adapter=make_adapter(cell,output/'scene_work');context=None;scene=None;before=after=None;result=None;error=None;scientific=None;raw=None;verifier=None;variation=None;replay=None;start_anchor=None;current=None;retiming=[]
    started=time.monotonic();branch={'program_id':program['program_id'],'cell_id':cell['cell_id'],'realization':cell['variant'],'root_id':cell['parent_root_id'],
        'candidate_universe_sha256':cell['candidate_universe_sha256'],'prefix_sha256':prefix['prefix_contract_sha256'],'reference_current_sha256':reference['aggregate_sha256'],
        'parent_source_branch_sha256':cell['source_branch_file_sha256'],'status':'running','formal_data':False,'stage0_data':False,'stage1_authorized':False}
    try:
        context=adapter.scene(planned_root,phase='strict_prefix_branch:'+program['program_id'],program=program)
        if cell['family']=='F1':
            from controlled_multi_future.real_sapien_adapter_high_level_v1 import _PinnedSapienRenderDeviceContextV1
            context=_PinnedSapienRenderDeviceContextV1(context)
        with context as handle:
            scene=handle.scene
            if not hasattr(scene,'planner_query_count'):scene.planner_query_count=0
            before=int(scene.planner_query_count)
            try:
                current=adapter.capture_current(scene)
                branch['branch_current']=current
                branch['parent_namespace_binding']=getattr(adapter,'_cmf_parent_namespace_binding',None)
                write_new(output/'candidate_current.json',current)
                require_same_current(reference,current)
                branch['render_device_binding']=getattr(scene,'_cmf_render_device_binding_v1',None)
                start_anchor=adapter.capture_anchor(scene);ae=compare_anchors(anchor,start_anchor)
                if ae['equivalent'] is not True:raise ValueError('parent current/anchor mismatch')
                branch.update(branch_current=current,anchor_equivalence=ae)
                # Save current once for this cohort, while still referring to the original root.
                shared=Path(shared_current_dir)
                if not (shared/'current.json').exists():
                    shared.mkdir(parents=True,exist_ok=True);rgb=scene.cameras.get_rgb()
                    with (shared/'current_arrays.npz').open('xb') as f:np.savez_compressed(f,head_rgb=rgb['head_camera']['rgb'],left_wrist_rgb=rgb['left_camera']['rgb'],right_wrist_rgb=rgb['right_camera']['rgb'],
                        robot_qpos=np.concatenate([scene.robot.left_entity.get_qpos(),scene.robot.right_entity.get_qpos()]),
                        robot_qvel=np.concatenate([scene.robot.left_entity.get_qvel(),scene.robot.right_entity.get_qvel()]),
                        gripper_joint_qpos=np.asarray(start_anchor['gripper_joint_qpos']))
                    write_new(shared/'current.json',seal({'parent_root':str(parent),'current':current,'arrays_file_sha256':sha(shared/'current_arrays.npz')}))
                elif read(shared/'current.json')['current']['aggregate_sha256']!=current['aggregate_sha256']:raise ValueError('cohort current differs')
                adapter.initialize_prefix_replay_trace(scene)
                scene.start_development_video_capture(output/'video/trajectory.mp4')
                replay=replay_canonical_prefix(scene,manifest=prefix,arrays=arrays,reference_current=reference,capture_current=adapter.capture_current,capture_anchor=adapter.capture_anchor)
                replay['replayed_prefix_physical_acceptance']=adapter.validate_replayed_prefix_physical(scene,replay)
                if replay['replayed_prefix_physical_acceptance'].get('pass') is not True:raise ScientificFailure('canonical prefix physical check failed')
                spec,controls,retiming=plan_or_load_controls(cell,scene)
                branch['retiming']=retiming
                artifact,control_arrays=build_frozen_suffix_artifact(root_slot_id=cell['parent_root_id'],family=cell['family'],program_id=program['program_id'],
                    candidate_universe_sha256=cell['candidate_universe_sha256'],prefix_artifact_sha256=prefix['artifact_sha256'],actual_prefix_end_qpos=np.asarray(scene.robot.left_entity.get_qpos(),dtype=np.float64),
                    execution_spec=spec,controls=controls,planner_query_receipts=spec.get('planner_query_receipts',[]))
                write_frozen_suffix_artifact(output/'variant_suffix_artifact',artifact,control_arrays)
                disk,_,disk_controls=load_frozen_suffix_artifact(output/'variant_suffix_artifact')
                for original,loaded in zip(controls,disk_controls):
                    if not np.array_equal(original['position'],loaded['position']) or not np.array_equal(original['velocity'],loaded['velocity']):raise ValueError('control disk roundtrip')
                execution_before=int(scene.planner_query_count)
                realization={'realization':cell['variant'],'formal_data':False,'stage0_data':False,'stage0_authorized':False,'stage1_authorized':False}
                result=adapter.execute_frozen_suffix_spec(scene,program,spec,replay,realization)
                if int(scene.planner_query_count)!=execution_before:raise ValueError('family execution made unexpected planner query')
                verifier=adapter.verify(scene,program,result)
                variation=variations_from_trace(cell,result,scene,retiming)
                trace=output/'trace_source.npz';scene.save_trace(trace)
                result['provenance'].update(trace_source_sha256=sha(trace),trace_source_relative_path='../trace_source.npz',development_data=True,
                    implementation_version='cmf_development_realization_batch_v1_1',parent_root=str(parent),parent_source_branch_sha256=cell['source_branch_file_sha256'],
                    new_planner_queries=int(scene.planner_query_count)-before,planner_query_provenance='new_calls_for_path_or_replayed_parent_queries_for_motion',shared_current_reference=str(shared/'current.json'))
                raw=write_raw_attempt(output/'raw',result['streams'],result['audit_streams'],result['provenance'])
                if verify_raw_artifact_integrity(output/'raw')['pass'] is not True:raise ValueError('raw integrity')
                P=int(prefix['prefix_step_count']);actions=np.asarray(result['streams']['controller_effective_setpoint'],dtype=np.float64)
                branch['executed_prefix']={'executed_prefix_action_sha256':replay['executed_prefix_action_sha256'],'executed_prefix_step_count':P,
                    'executed_prefix_start_state_sha256':replay['start_anchor_equivalence']['candidate_sha256'],'executed_prefix_end_state_sha256':replay['semantic_prefix_end_anchor']['anchor_sha256'],
                    'executed_prefix_start_anchor':start_anchor,'executed_prefix_end_anchor':replay['semantic_prefix_end_anchor'],'canonical_prefix_end_step':P,
                    'first_post_prefix_divergence_step':P,'neutral_confirmation_step_count':0,'neutral_confirmation_minimum_required_steps':0,'post_prefix_action_step_sha256':_step_hashes(actions[P:])}
                branch.update(raw_manifest=raw,verifier=verifier,realized_variation=variation,final_state_equivalence_payload=result.get('final_state_equivalence_payload'))
                if verifier.get('pass') is not True or variation['pass'] is not True:scientific='family_or_realized_variation_failed'
            finally:
                value=getattr(scene,'planner_query_count',None);after=value if type(value) is int else None
    except ScientificFailure as exc:scientific=str(exc)
    except BaseException as exc:
        error={'type':type(exc).__name__,'message':str(exc)}
        mismatch=getattr(exc,'receipt',None)
        if mismatch is not None:branch['same_current_mismatch_receipt']=mismatch
    if (error or scientific) and scene is not None and getattr(scene,'trace',None) and not (output/'trace_source.npz').exists():
        try:
            scene.save_trace(output/'partial_trace_source.npz')
            branch['partial_trace_source']={'path':str(output/'partial_trace_source.npz'),'file_sha256':sha(output/'partial_trace_source.npz')}
        except Exception as exc:error={'type':'PartialTraceWriteFailure','message':str(exc),'prior_error':error,'scientific_failure':scientific}
    cleanup=None if context is None else context.cleanup_receipt
    known=before is not None and after is not None and after>=before
    delta=after-before if known else None
    cleanup_ok=isinstance(cleanup,dict) and cleanup.get('cleanup_safety_pass') is True and cleanup.get('orphan_process_count')==0
    video=None if not cleanup else cleanup.get('development_video_receipt')
    if video is not None:
        try:video_audit=validate_development_trajectory_mp4_receipt_v1(video,expected_path=output/'video/trajectory.mp4')
        except Exception as exc:video_audit={'pass':False,'error_type':type(exc).__name__,'error':str(exc)}
        if video_audit['pass'] is not True:error={'type':'VideoIntegrityFailure','message':'video verifier failed'}
        branch.update(development_video_receipt=video,development_video_integrity=video_audit)
    elif result is not None:error={'type':'VideoIntegrityFailure','message':'completed rollout has no video'}
    success=known and delta<=cell['query_cap'] and cleanup_ok and error is None and scientific is None and raw is not None and verifier is not None and verifier.get('pass') is True and variation is not None and variation['pass'] is True
    branch.update(status='accepted' if success else 'failed_scientific' if scientific and error is None else 'failed_infrastructure',
        error=error,scientific_failure=scientific,planner_before=before,planner_after=after,planner_query_delta=delta,accounting_complete=known,
        cleanup=cleanup,scene_instance_id=None if cleanup is None else cleanup.get('scene_instance_id'),elapsed_seconds=time.monotonic()-started,
        origin_kind='new_real_rollout',raw_written=raw is not None,global_stop=not known or not cleanup_ok or error is not None or (known and delta>cell['query_cap']))
    write_new(output/'receipt.provisional.json',branch)
    return branch
