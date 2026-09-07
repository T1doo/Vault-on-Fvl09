"""Independent read-only six-cell candidate audit. No automatic registration."""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
from controlled_multi_future.raw_writer import verify_raw_artifact_integrity,validate_raw_artifact_contract,validate_raw_streams
from controlled_multi_future.current_hasher import hash_array
from controlled_multi_future.root_orchestrator_v1_1 import finalize_three_branch_root_v1_1,compare_three_branch_final_state_payloads
from controlled_multi_future.development_video_capture_v1 import validate_development_trajectory_mp4_receipt_v1
from goal_pilot48_v1.f4_b_runtime_v1.binding import checked,seal,PROGRAMS
from goal_pilot48_v1.f4_b_motion_runtime_v2.binding import root_inputs
from goal_pilot48_v1.f4_b_motion_runtime_v1.pipeline import build_pipeline
from goal_pilot48_v1.f4_b_acceptance_audit_v2.audit import run as audit_pc
from goal_pilot48_v1.f4_b_acceptance_audit_v2.current_recovery import audit_later_current
from goal_pilot48_v1.runtime.issue_f4_b_stage_a import ROOT,W,read,sha,digest
from realization_current_layout_audit_v1 import audit as current_audit

DEFAULT=W/'Robotwin2/datasets/p48_f4_b_motion_001'

def gpu_identity(guard,start):
    index=guard.get('physical_gpu_index');uuid=guard.get('gpu_uuid')
    if type(index) is not int or index not in range(8) or not isinstance(uuid,str) or not uuid.startswith('GPU-'):raise ValueError('Guard GPU identity absent')
    if start.get('physical_gpu_index')!=index or start.get('gpu_uuid')!=uuid:raise ValueError('start/terminal GPU identity mismatch')
    rows={}
    for name in ('pre_snapshot','launch_snapshot','post_snapshot'):
        candidates=[g for g in (guard.get(name) or {}).get('gpus',[]) if g.get('index')==index]
        if len(candidates)!=1 or candidates[0].get('uuid')!=uuid:raise ValueError('selected physical GPU UUID differs in '+name)
        rows[name]=candidates[0]
    first=[g for g in start.get('pre_snapshot',{}).get('gpus',[]) if g.get('index')==index]
    if len(first)!=1 or first[0].get('uuid')!=uuid:raise ValueError('start pre-snapshot UUID mismatch')
    return dict(physical_gpu_index=index,gpu_uuid=uuid,selected_snapshot_rows=rows)

def preview_registration(document,candidates):
    """In-memory schema test only; returned preview never writes pilot_cells."""
    from goal_pilot48_v1.pilot_matrix_audit_v1.audit import inspect_document
    preview=deepcopy(document);keys=('family','pilot','program_id','realization')
    for candidate in candidates:
        key=tuple(candidate[k] for k in keys);matches=[i for i,c in enumerate(preview['cells']) if tuple(c[k] for k in keys)==key]
        if len(matches)!=1:raise ValueError('exact target pilot key not unique')
        row=deepcopy(candidate);row['status']='accepted_new';row['evidence']['pilot_input_accepted']=True
        preview['cells'][matches[0]]=row
    preview['accepted']=sum(c['status'] in ('accepted_existing','accepted_new') for c in preview['cells'])
    result=inspect_document(preview)
    if not result['pass']:raise ValueError('candidate mapping not accepted by pilot schema: '+str(result['errors']))
    return result

def terminal_inputs(output):
    output=Path(output).resolve();job_id=output.name
    paths={'goal':output/'goal_terminal.json','guard':output.parent/(job_id+'_guard')/(job_id+'.terminal.json'),
        'manifest':ROOT/'jobs'/(job_id+'.json'),'cohort':output/'root_receipt.json','index':output/'publication_index.json',
        'guard_start':output.parent/(job_id+'_guard')/(job_id+'.start.json')}
    missing=[str(p) for p in paths.values() if not p.exists()]
    if missing:return None,dict(status='pending_producer_terminal',missing_files=missing,eligible_candidate_cells=0)
    for pid in PROGRAMS:
        final=output/'branches'/pid/'receipt.json'
        if not final.exists():return None,dict(status='pending_finalized_branches',missing_files=[str(final)],eligible_candidate_cells=0)
    goal=checked(read(paths['goal']));guard=checked(read(paths['guard']));manifest=checked(read(paths['manifest']),'manifest_sha256');cohort=checked(read(paths['cohort']));index=checked(read(paths['index']))
    start=checked(read(paths['guard_start']))
    if any(x.get('job_id')!=job_id for x in (goal,guard,start)) or guard.get('run_id')!=job_id or start.get('run_id')!=job_id or manifest.get('run_id')!=job_id or manifest['jobs'][0].get('job_id')!=job_id or Path(manifest['jobs'][0]['output_namespace']).resolve()!=output:
        raise ValueError('Goal/job/output/Guard run identity mismatch')
    if start['manifest_sha256']!=manifest['manifest_sha256']:raise ValueError('start manifest binding changed')
    selected_gpu=gpu_identity(guard,start)
    r=goal.get('runtime_result') or {};expected=dict(solver_problems=0,fresh_scenes=3,action_scenes=3,collection_attempts=3)
    if (not goal['pass'] or not goal['accounting_complete'] or goal['resource_counts']!=expected or
        r.get('scientific_route_pass') is not True or r.get('accepted_variant_trajectory_count')!=3 or
        r.get('current_component_audit',{}).get('current_component_validation_pass') is not True or
        r.get('current_component_audit',{}).get('complete_program_realization_matrix') is not True or
        not all(guard.get(k) is True for k in ('task_owned_cleanup_pass','gpu_returned_to_idle_baseline','lease_released')) or guard['child_exit_code']!=0 or
        goal['manifest_sha256']!=guard['manifest_sha256'] or goal['manifest_sha256']!=manifest['manifest_sha256'] or
        cohort!=r.get('cohort') or cohort['status']!='accepted' or index['root_receipt_file_sha256']!=sha(paths['cohort']) or not index['publication_complete']):
        raise ValueError('producer Goal/Guard/cohort/current/publication not complete')
    if not output.name.startswith('p48_f4_b_motion_') or manifest['jobs'][0]['runtime_module']!='goal_pilot48_v1.f4_b_motion_runtime_v2.runtime':raise ValueError('wrong B motion source')
    meter_path=output.parent/(job_id+'_meter')/'events.jsonl';events=[json.loads(l) for l in meter_path.read_text(encoding='utf-8').splitlines()]
    if events[-1]['kind']!='METER_CLOSED':raise ValueError('producer meter not closed')
    counts={k:0 for k in expected};collections=[];action_ordinals=[]
    for e in events:
        if e.get('kind')!='CHARGE':continue
        counts[e['resource']]+=e['amount']
        if counts[e['resource']]!=e['total']:raise ValueError('meter total progression mismatch')
        if e['resource']=='collection_attempts':collections.append(e['program_id'])
        if e['resource']=='action_scenes':action_ordinals.append(e['scene_ordinal'])
    if counts!=expected or collections!=list(PROGRAMS) or len(set(action_ordinals))!=3:raise ValueError('independent producer resource identities mismatch')
    if not guard.get('gpu_uuid') or guard.get('physical_gpu_index') not in range(8):raise ValueError('Guard UUID/physical index absent')
    paths['meter']=meter_path
    return dict(goal=goal,guard=guard,manifest=manifest,cohort=cohort,index=index,paths=paths,counts=counts,gpu_binding=selected_gpu),None

def audit_motion_branch(output,pid,cell,pipeline):
    directory=Path(output)/'branches'/pid
    if not (directory/'receipt.json').exists():raise ValueError('provisional receipt is not final acceptance input')
    b=read(directory/'receipt.json');m=read(directory/'raw/manifest.json')
    if b['status']!='accepted' or b['realization']!='r_inv_motion' or b['planner_query_delta']!=0 or not b['accounting_complete']:raise ValueError('motion final branch not accepted')
    raw_check=verify_raw_artifact_integrity(directory/'raw');validate_raw_artifact_contract(directory/'raw')
    with np.load(directory/'raw/raw_streams.npz',allow_pickle=False) as z:streams={k[8:]:z[k] for k in z.files if k.startswith('stream__')}
    streams['field_metadata']=m['stream_field_metadata'];validate_raw_streams(streams);n=len(streams['controller_effective_setpoint'])
    with np.load(directory/'trace_source.npz',allow_pickle=False) as z:
        if not np.array_equal(streams['realized_qpos'][0],z['joint_qpos'][0]) or not np.array_equal(streams['realized_qvel'][0],z['joint_qvel'][0]):raise ValueError('raw/trace row0 differs')
        trace=[{'planner_query_id':p,'planner_goal_active':a,'timestamp':float(t),'eef':e} for p,a,t,e in zip(z['planner_query_id'],z['planner_goal_active'],z['timestamp'],z['eef_pose'])]
        queries=json.loads(str(z['planner_queries_json'].item()))
    from types import SimpleNamespace
    result={'semantic_verifier':b['verifier']['family_semantic_verifier']}
    variation=pipeline.variations_from_trace(cell,result,SimpleNamespace(trace=trace,planner_queries=queries),b['retiming'])
    if variation!=b['realized_variation'] or variation['pass'] is not True or len(variation['measurements'])!=3:raise ValueError('actual1.10 motion timing verification differs')
    storage=current_audit(Path(output)/'current',directory/'trace_source.npz')
    if storage['pass'] is not True or storage['unique_articulation_dofs']!=38 or storage['model_visible_robot_state_dimension']!=76:raise ValueError('current38/76 contract failed')
    video=validate_development_trajectory_mp4_receipt_v1(b['development_video_receipt'],expected_path=directory/'video/trajectory.mp4')
    semantic=b['verifier']['family_semantic_verifier'];order=[r['role'] for r in semantic['role_receipts']]
    checks=dict(raw_integrity=raw_check['pass'],N_Nplus1=n==m['action_count'] and m['state_count']==len(streams['realized_qpos'])==n+1,
        action26=streams['controller_effective_setpoint'].shape==(n,26),frequency250=m['frequency_hz']==250,
        realization=m['provenance']['realization_spec']['realization']=='r_inv_motion' and m['provenance']['program_id']==pid and m['provenance']['synthetic'] is False,
        verifier=b['verifier']['pass'] is True and semantic['pass'] is True and all(semantic['checks'].values()),
        order=order==list(pid.split('-')[1]),video=video['pass'],anchor=b['anchor_equivalence']['equivalent'],
        cleanup=b['cleanup']['cleanup_safety_pass'] and b['cleanup']['orphan_process_count']==0,
        trace_link=m['provenance']['trace_source_sha256']==sha(directory/'trace_source.npz'))
    if not all(checks.values()):raise ValueError('motion raw/family/video checks failed')
    return dict(program_id=pid,realization='r_inv_motion',branch=b,checks=checks,actions=n,states=n+1,
        raw_id=sha(directory/'raw/raw_streams.npz'),action_array_sha256=hash_array(streams['controller_effective_setpoint']),
        rollout_id=str(directory),trace_sha256=sha(directory/'trace_source.npz'),video_sha256=sha(directory/'video/trajectory.mp4'),
        receipt_sha256=sha(directory/'receipt.json'),current_initial_state_audit=storage,realized_variation_recomputed=variation)

def build_candidates(output=DEFAULT):
    """Pure final audit, to be called only after main confirms producer ended."""
    output=Path(output).resolve();terminal,pending=terminal_inputs(output)
    if pending is not None:return seal({**pending,'pilot_cells_modified':False,'acceptance_issued':False})
    job=terminal['manifest']['jobs'][0];root,bound,parent=root_inputs(job)
    current_recovery=audit_later_current(root_job=root.parent,current_directory=output/'current',producer_branch=output/'branches/F4-ABC/receipt.json',
        producer_goal=terminal['paths']['goal'],producer_guard=terminal['paths']['guard'])
    pc=audit_pc(root.parent,current_directory=output/'current')
    if pc['eligible_candidate_cells']!=3:raise ValueError('three pc cells/current recovery remain pending')
    catalog=checked(read(output/'catalog.json'));pipeline=build_pipeline(bound,terminal['manifest']['implementation_source_sha256'])
    if catalog['receipt_sha256']!=job['catalog_sha256'] or catalog['dependencies']!=job['root_artifact_files']:raise ValueError('catalog not bound to executed manifest')
    for path,h in catalog['dependencies'].items():
        if sha(path)!=h or terminal['manifest']['input_files'].get(path)!=h:raise ValueError('parent artifact hash/manifest input mismatch')
    motion=[audit_motion_branch(output,pid,next(c for c in catalog['cells'] if c['program']['program_id']==pid),pipeline) for pid in PROGRAMS]
    final=[deepcopy(r['branch']) for r in motion]
    for b in final:
        if b!=next(x for x in terminal['cohort']['branch_receipts'] if x['program_id']==b['program_id']):raise ValueError('final disk/Goal branch mismatch')
        if terminal['index']['branch_files'][b['program_id']]!=sha(output/'branches'/b['program_id']/'receipt.json'):raise ValueError('publication index branch mismatch')
    finalizer=finalize_three_branch_root_v1_1(final,reference_current_sha256=read(root/'reference_current_hashes.json')['aggregate_sha256'],root_cleanup_pass=True)
    if not finalizer['accepted'] or final!=[r['branch'] for r in motion]:raise ValueError('original root finalizer divergence/order differs')
    six=[*parent['branch_receipts'],*final];cross=compare_three_branch_final_state_payloads(six)
    if not cross['equivalent'] or cross!=terminal['cohort']['cross_pc_motion_final_state_equivalence']:raise ValueError('six pc/motion final-state equivalence differs')
    raw_ids=[r['raw_sha256'] for r in pc['rows']]+[r['raw_id'] for r in motion]
    action_ids=[r['primary_action_array_sha256'] for r in pc['rows']]+[r['action_array_sha256'] for r in motion]
    if len(set(raw_ids))!=6 or len(set(action_ids))!=6:raise ValueError('duplicate raw/action arrays cannot fill six cells')
    pilot=read(ROOT/'pilot_cells.json');mapping=[]
    for pid in PROGRAMS:
        for real in ('r_pc','r_inv_motion'):
            slots=[c for c in pilot['cells'] if (c['family'],c['pilot'],c['program_id'],c['realization'])==('F4','B',pid,real)]
            if len(slots)!=1:raise ValueError('pilot target cell schema missing/duplicate')
            source=next(r for r in (pc['rows'] if real=='r_pc' else motion) if r['program_id']==pid)
            rollout=root/'branches'/pid if real=='r_pc' else Path(source['rollout_id'])
            program=next(c['program'] for c in catalog['cells'] if c['program']['program_id']==pid)
            evidence=dict(family='F4',pilot='B',program_id=pid,realization=real,root_id=bound['planned_spec']['slot_id'],
                raw_id=source.get('raw_id',source.get('raw_sha256')),rollout_id=str(root/'branches'/pid) if real=='r_pc' else source['rollout_id'],
                actions=source.get('actions',source.get('action_count')),states=source.get('states',source.get('state_count')),
                origin_kind='real_rollout',derived_from_raw_id=None,new_collection=True,evidence_scope='real_simulator_verified',
                raw_integrity_pass=True,raw_N_Nplus1_stream_contract_pass=True,family_verifier_pass=True,video_integrity_pass=True,
                same_current_pass=True,anchor_equivalence_pass=True,final_state_equivalence_pass=True,fresh_scene_pass=True,cleanup_pass=True,orphan_process_count=0,
                current_initial_state_audit=source.get('current_initial_state_audit',source.get('current_storage_audit')),
                program_semantic_sha256=digest(program),trace_sha256=sha(rollout/'trace_source.npz'),video_sha256=sha(rollout/'video/trajectory.mp4'),
                receipt_file_sha256=sha(rollout/'receipt.json'),raw_state0_equals_trace_state0=True,receipt_is_trace_reconstructed=False,
                raw_provenance_realization_spec=read(rollout/'raw/manifest.json')['provenance']['realization_spec'],
                parent_acceptance_inherited=False,current_batch_history_reference='root001 failed Goal preserved plus explicit action-resource resolution and later B motion same-current recovery',
                candidate_universe_sha256=read(root/'candidate_frozen_root_spec.json')['candidate_universe_sha256'],
                current_sha256=read(root/'reference_current_hashes.json')['aggregate_sha256'],
                failure_history_complete=True,original_root_Goal_false_preserved=True,current_captured_later=True,
                acceptance_basis='independent six-cell/current/resource-resolution evidence; explicit main registration pending',pilot_input_accepted=False)
            if slots[0]['status']!='pending' and (slots[0].get('evidence') or {}).get('raw_id')!=evidence['raw_id']:
                raise ValueError('target pilot cell already contains different evidence')
            mapping.append(dict(family='F4',pilot='B',program_id=pid,realization=real,status='verified_candidate_pending_main_registration',evidence=evidence))
    matrix_preview=preview_registration(pilot,mapping)
    return seal(dict(schema_version='cmf_B_pilot_six_candidate_audit_v1',status='six_verified_candidates_pending_main_registration',
        eligible_candidate_cells=6,cells=mapping,current_recovery=current_recovery,pc_audit=pc,motion_branch_audits=motion,
        recomputed_motion_finalizer=finalizer,six_final_state_equivalence=cross,
        producer_terminal_hashes={k:sha(p) for k,p in terminal['paths'].items()},
        pilot_cells_before_file_sha256=sha(ROOT/'pilot_cells.json'),registration_requires_exact_key_merge_without_overwrite=True,
        in_memory_registration_schema_preview=matrix_preview,gpu_identity_binding=terminal['gpu_binding'],
        source_program_profile_sha256=terminal['manifest']['implementation_source_sha256'],
        pilot_cells_modified=False,acceptance_issued=False,new_GPU_runs=0,new_raw=0))
