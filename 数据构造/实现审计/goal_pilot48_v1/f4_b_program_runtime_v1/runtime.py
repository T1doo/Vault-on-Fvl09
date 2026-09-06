"""Three exact B program planner terminals, conditional on published Stage-A.

No issuer/reservation exists here. All writes are exclusive atomic UTF-8.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import traceback
from ..f4_b_runtime_v1.binding import payload,runtime_spec,validate_stage_a,checked,seal,PROGRAMS,SEED
from ..f4_b_runtime_v1.stages import planner_spec,physical_spec
from ..f4_b_runtime_v1.adapter import make_adapter
from ..f4_b_runtime_v2.runtime import TrackedContext,SOURCE_SHA,source_inputs as stage_a_source_inputs
from realization_utf8_io_v1 import write_new

W=Path('/nfs_share/lijunhui')
CAPS=dict(solver_problems=450,fresh_scenes=3,action_scenes=0,collection_attempts=0)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def bound_json(job,field,key='receipt_sha256'):
    path=Path(job[field+'_path']).resolve()
    if not path.is_relative_to(W) or sha(path)!=job[field+'_file_sha256']:
        raise ValueError('changed/outside published B evidence: '+field)
    return checked(json.loads(path.read_text(encoding='utf-8')),key)

def prerequisites(job):
    evidence=validate_stage_a(bound_json(job,'source_stage_a_evidence'))
    terminal=bound_json(job,'source_stage_a_goal_terminal')
    guard=bound_json(job,'source_stage_a_guard_terminal')
    manifest=bound_json(job,'source_stage_a_manifest','manifest_sha256')
    parent=terminal.get('runtime_result') or {}
    expected=dict(solver_problems=135,fresh_scenes=1,action_scenes=0,collection_attempts=0)
    if (terminal.get('pass') is not True or terminal.get('accounting_complete') is not True or
        terminal.get('resource_counts')!=expected or parent.get('qualification_pass') is not True or
        parent.get('evidence')!=evidence or parent.get('independent_meter',{}).get('pass') is not True or
        terminal.get('manifest_sha256')!=manifest['manifest_sha256'] or
        guard.get('manifest_sha256')!=manifest['manifest_sha256'] or guard.get('child_exit_code')!=0 or
        guard.get('task_owned_cleanup_pass') is not True or
        manifest['jobs'][0].get('runtime_module')!='goal_pilot48_v1.f4_b_runtime_v2.runtime'):
        raise ValueError('published B Stage-A Goal/Guard lineage is not verified')
    scene_spec=runtime_spec('f4_stage_b_planner',stage_a=evidence)
    current=parent.get('result',{}).get('current',{})
    if not current.get('aggregate_sha256'):raise ValueError('B Stage-A reference current missing')
    if job.get('b_payload_sha256')!=payload()['receipt_sha256'] or job.get('planned_scene_spec_sha256')!=scene_spec['planned_scope_spec_sha256']:
        raise ValueError('job B payload/scene binding differs')
    return evidence,scene_spec,current

def query_accounting(rows,count):
    if type(count) is not int or len(rows)!=count or [r.get('query_id') for r in rows]!=list(range(1,count+1)):
        raise ValueError('program query ledger incomplete')
    batch=[r for r in rows if r.get('query_type')=='batched_grasp_target_selection']
    single=[r for r in rows if r.get('query_type')!='batched_grasp_target_selection']
    if len(batch)>12 or len(single)>30 or any(r.get('batch_size')!=10 or len(r.get('ordered_goal_poses',[]))!=10 for r in batch):
        raise ValueError('program 12x10+30 topology changed')
    return dict(planner_api_calls=count,target_batch_calls=len(batch),target_goal_pose_problems=10*len(batch),
        chain_goal_pose_problems=len(single),solver_problems=10*len(batch)+len(single))

def reconcile(output,rows):
    path=Path(output).parent/(Path(output).name+'_meter')/'events.jsonl'
    raw=path.read_bytes()
    if not raw or not raw.endswith(b'\n'):raise ValueError('independent meter missing/truncated')
    actual={k:0 for k in CAPS}
    for line in raw.decode('utf-8').splitlines():
        r=json.loads(line)
        if r.get('kind')!='CHARGE':continue
        key=r.get('resource');n=r.get('amount')
        if key not in actual or type(n) is not int or n<=0:raise ValueError('invalid meter charge')
        actual[key]+=n
        if actual[key]!=r.get('total') or actual[key]>CAPS[key]:raise ValueError('meter total/cap mismatch')
    if any(r.get('accounting_complete') is not True for r in rows):raise ValueError('a program has unknown accounting')
    expected=dict(solver_problems=sum(r['accounting']['solver_problems'] for r in rows),
        fresh_scenes=sum(r['scene_attempts'] for r in rows),action_scenes=0,collection_attempts=0)
    if actual!=expected:raise ValueError('independent meter disagrees with per-program batch N')
    return dict(path=str(path),file_sha256=hashlib.sha256(raw).hexdigest(),counts=actual,**{'pass':True})

def run_one(*,job,program_id,ordinal,scene_spec,reference_current,directory):
    from controlled_multi_future.f4_program_planner_integration_v2 import run_f4_program_planner_v2
    nonce=job['planner_reset_nonce_base']+ordinal
    slot=job['job_id']+'-'+program_id.lower()
    spec=planner_spec(program_id,slot_id=slot+'-planner-source',planner_reset_nonce=nonce)
    directory.mkdir(parents=True,exist_ok=False);write_new(directory/'spec.json',spec)
    state=dict(context_enter_attempts=0,scene_entered=False,query_rows=[],api_count=None,actual_seed=None)
    adapter=make_adapter(output_root=directory/'scene',source_sha256=SOURCE_SHA,planned_spec=scene_spec)
    context=TrackedContext(adapter.scene(scene_spec,phase='F4_B_PROGRAM_PLANNER',program=None),state)
    terminal=error=current=None
    try:
        with context as handle:
            scene=handle.scene;scene._cmf_scene_lifecycle='fresh'
            current=adapter.capture_current(scene)
            if current.get('aggregate_sha256')!=reference_current['aggregate_sha256']:
                raise ValueError('fresh B current differs from published source Stage-A')
            scene.initialize_trace(scene.a,scene_spec['arm'],role_actors=scene.role_actors)
            scene.planner_query_limit=42
            terminal=run_f4_program_planner_v2(scene,spec)
    except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
    cleanup=context.cleanup_receipt;counts=None;known=False
    try:counts=query_accounting(state['query_rows'],state['api_count']);known=state['scene_entered'] and state['actual_seed']==SEED
    except (ValueError,TypeError):pass
    passed=isinstance(terminal,dict) and terminal.get('robot_kinematic_table_world_planner_pass') is True
    if passed:
        try:
            checked(terminal)
            if counts is None or counts['solver_problems']!=150:raise ValueError('passing program lacks 150 actual problems')
            # Validate downstream interface, never claim physical qualification.
            stage={'F4-ABC':'A_ONLY','F4-ACB':'C_ONLY','F4-BAC':'B_ONLY'}[program_id]
            physical_spec(terminal,stage_a=scene_spec['f4_b_source_stage_a_evidence'],program_id=program_id,
                slot_id=slot,planner_reset_nonce=nonce,isolation_stage=stage)
        except BaseException as exc:
            error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc());passed=False
    envelope=seal(dict(spec=spec,terminal=terminal,error=error,cleanup=cleanup,current=current,
        b_scene_spec_sha256=scene_spec['planned_scope_spec_sha256'],physical_micro_slot_id=slot,
        scene_attempts=state['context_enter_attempts'],accounting=counts,accounting_complete=known,
        program_pass=passed and known,physical_execution_count=0))
    write_new(directory/'query_rows.json',state);write_new(directory/'terminal.json',envelope)
    return envelope

def run(manifest):
    job=manifest['jobs'][0]
    if job.get('resource_caps')!=CAPS or type(job.get('planner_reset_nonce_base')) is not int or job['planner_reset_nonce_base']<=0:
        raise ValueError('exact three-program caps and frozen nonce base required')
    _,scene_spec,reference=prerequisites(job)
    inputs=stage_a_source_inputs()
    out=Path(job['output_namespace']);out.mkdir(parents=True,exist_ok=False)
    write_new(out/'source_inputs.json',inputs);write_new(out/'planned_scene_spec.json',scene_spec)
    rows=[];error=None
    try:
        for index,pid in enumerate(PROGRAMS,1):
            row=run_one(job=job,program_id=pid,ordinal=index,scene_spec=scene_spec,
                reference_current=reference,directory=out/pid)
            rows.append(row)
            cleanup=row.get('cleanup') or {}
            if not row['program_pass'] or not cleanup.get('cleanup_safety_pass') or cleanup.get('orphan_process_count')!=0:
                break
    except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
    meter=meter_error=None
    try:meter=reconcile(out,rows)
    except BaseException as exc:meter_error=dict(type=type(exc).__name__,message=str(exc))
    clean=bool(rows) and all((r.get('cleanup') or {}).get('cleanup_safety_pass') is True and (r.get('cleanup') or {}).get('orphan_process_count')==0 for r in rows)
    known=meter is not None
    infrastructure=error is None and all(r.get('error') is None for r in rows)
    science=len(rows)==3 and all(r['program_pass'] for r in rows) and clean and known and infrastructure
    result=seal(dict(schema_version='cmf_goal_f4_b_three_programs_v1',rows=rows,error=error,independent_meter=meter,meter_error=meter_error,
        scene_attempts=sum(r['scene_attempts'] for r in rows),accounting_complete=known,
        scientific_route_pass=science,program_panel_pass=science,
        skipped_programs=list(PROGRAMS[len(rows):]),physical_execution_count=0,collection_attempts=0,
        next_gate='FIVE_B_ISOLATION_STAGES' if science else 'REVIEW_FAILED_B_PROGRAM_NO_PHYSICAL',
        **{'pass':infrastructure and clean and known}))
    write_new(out/'runtime_terminal.json',result);return result
