"""Conditional five-stage B physical isolation; no issuer or GPU launch here."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import traceback
from ..f4_b_runtime_v1.binding import checked,seal,payload
from ..f4_b_runtime_v1.stages import physical_spec
from ..f4_b_runtime_v1.adapter import make_adapter
from ..f4_b_program_runtime_v1.runtime import bound_json,prerequisites as program_prerequisites,SOURCE_SHA
from realization_utf8_io_v1 import write_new

STAGES=('A_ONLY','B_ONLY','C_ONLY','AB_NONINTERFERENCE','AC_NONINTERFERENCE')
PROGRAM={'A_ONLY':'F4-ABC','B_ONLY':'F4-BAC','C_ONLY':'F4-ACB','AB_NONINTERFERENCE':'F4-ABC','AC_NONINTERFERENCE':'F4-ACB'}
CAPS=dict(solver_problems=720,fresh_scenes=5,action_scenes=5,collection_attempts=0)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def prerequisites(job):
    terminal=bound_json(job,'source_program_goal_terminal')
    guard=bound_json(job,'source_program_guard_terminal')
    manifest=bound_json(job,'source_program_manifest','manifest_sha256')
    panel=terminal.get('runtime_result') or {}
    if (terminal.get('pass') is not True or terminal.get('accounting_complete') is not True or
        terminal.get('resource_counts')!=dict(solver_problems=450,fresh_scenes=3,action_scenes=0,collection_attempts=0) or
        panel.get('program_panel_pass') is not True or panel.get('independent_meter',{}).get('pass') is not True or
        guard.get('child_exit_code')!=0 or guard.get('task_owned_cleanup_pass') is not True or
        guard.get('manifest_sha256')!=manifest['manifest_sha256'] or terminal.get('manifest_sha256')!=manifest['manifest_sha256'] or
        manifest['jobs'][0].get('runtime_module')!='goal_pilot48_v1.f4_b_program_runtime_v1.runtime'):
        raise ValueError('three published B program results with clean Guard required')
    stage_a,scene_spec,current=program_prerequisites(manifest['jobs'][0])
    if job.get('b_scene_spec_sha256')!=scene_spec['planned_scope_spec_sha256'] or job.get('b_payload_sha256')!=payload()['receipt_sha256']:
        raise ValueError('isolation scene differs from B source')
    sources={}
    for index,pid in enumerate(('F4-ABC','F4-ACB','F4-BAC')):
        field='source_'+pid.lower().replace('-','_')
        envelope=bound_json(job,field)
        if envelope!=panel['rows'][index] or envelope.get('program_pass') is not True or envelope.get('accounting',{}).get('solver_problems')!=150:
            raise ValueError('program envelope not the actual accepted B source')
        sources[pid]=envelope
    return stage_a,scene_spec,current,sources

class EpochRecorder:
    """Preserve native query ledgers and diagnostic trace before each reset."""
    def __init__(self,scene,directory):
        self.scene=scene;self.directory=Path(directory);self.epochs=[];self.last_count=0
        self.had='initialize_trace' in vars(scene);self.original_override=vars(scene).get('initialize_trace')
        self.original=scene.initialize_trace
        def initialize(*a,**kw):
            self.flush();result=self.original(*a,**kw);self.last_count=0;return result
        scene.initialize_trace=initialize
    def flush(self):
        count=getattr(self.scene,'planner_query_count',0);rows=deepcopy(getattr(self.scene,'planner_queries',[]))
        if count==0 and not rows:return
        if count==self.last_count:return
        if type(count) is not int or len(rows)!=count or [r.get('query_id') for r in rows]!=list(range(1,count+1)):
            raise ValueError('trace epoch planner ledger incomplete')
        record=dict(epoch=len(self.epochs),planner_api_calls=count,query_rows=rows)
        if getattr(self.scene,'trace',None):
            path=self.directory/f'trace_epoch_{len(self.epochs):02d}.npz'
            if path.exists():raise FileExistsError('diagnostic trace already exists')
            self.scene.save_trace(path);record.update(trace_path=str(path),trace_sha256=sha(path))
        self.epochs.append(record);self.last_count=count
    def close(self):
        try:self.flush()
        finally:
            if self.had:self.scene.initialize_trace=self.original_override
            else:delattr(self.scene,'initialize_trace')
    def accounting(self,stage):
        rows=[r for e in self.epochs for r in e['query_rows']]
        batches=[r for r in rows if r.get('query_type')=='batched_grasp_target_selection']
        singles=[r for r in rows if r.get('query_type')!='batched_grasp_target_selection']
        max_single=20 if stage in STAGES[:3] else 30
        if len(batches)>12 or len(singles)>max_single or any(r.get('batch_size')!=10 or len(r.get('ordered_goal_poses',[]))!=10 for r in batches):
            raise ValueError('isolation query topology changed')
        return dict(planner_api_calls=len(rows),target_batch_calls=len(batches),target_goal_problems=10*len(batches),
            single_goal_problems=len(singles),solver_problems=10*len(batches)+len(singles),
            expected_complete_solver_problems=140 if stage in STAGES[:3] else 150)

def run_one(stage,source,stage_a,scene_spec,reference_current,directory):
    from controlled_multi_future.f4_bounded_physical_micro_v1 import run_f4_bounded_physical_micro_v1
    prior=source['spec'];pid=PROGRAM[stage]
    spec=physical_spec(source['terminal'],stage_a=stage_a,program_id=pid,
        slot_id=source['physical_micro_slot_id'],planner_reset_nonce=prior['planner_reset_nonce'],isolation_stage=stage)
    directory.mkdir(parents=True,exist_ok=False);write_new(directory/'physical_spec.json',spec)
    adapter=make_adapter(output_root=directory/'scene',source_sha256=SOURCE_SHA,planned_spec=scene_spec)
    context=adapter.scene(scene_spec,phase='F4_B_ISOLATION_'+stage,program=None)
    result=error=save_error=recorder=accounting=current=anchor=None;entered=False;actions=False
    try:
        with context as handle:
            scene=handle.scene;entered=True
            if scene.robot.communication_flag:raise ValueError('unmetered planner worker')
            current=adapter.capture_current(scene);anchor=adapter.capture_anchor(scene)
            write_new(directory/'current.json',current);write_new(directory/'anchor.json',anchor)
            if current.get('aggregate_sha256')!=reference_current['aggregate_sha256']:
                raise ValueError('isolation did not reconstruct same B current')
            recorder=EpochRecorder(scene,directory)
            try:
                scene.initialize_trace(scene.common_x,scene_spec['arm'],role_actors=scene.role_actors)
                # Original executor initializes right common-X then left suffix;
                # EpochRecorder preserves all ten prefix queries and raw trace.
                actions=True
                result=run_f4_bounded_physical_micro_v1(scene,spec,capture_anchor_callback=adapter.capture_anchor)
            finally:
                try:recorder.close();accounting=recorder.accounting(stage)
                except BaseException as exc:save_error=dict(type=type(exc).__name__,message=str(exc))
    except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
    cleanup=context.cleanup_receipt
    physical_pass=result is not None and result.get('stage_physically_qualified') is True
    if physical_pass and (accounting is None or accounting['solver_problems']!=accounting['expected_complete_solver_problems']):
        error=dict(type='AccountingError',message='passing isolation query topology mismatch');physical_pass=False
    envelope=seal(dict(stage=stage,program_id=pid,spec=spec,result=result,error=error,trace_save_error=save_error,
        cleanup=cleanup,current=current,anchor=anchor,scene_attempts=int(entered),physical_attempted=actions,
        accounting=accounting,accounting_complete=accounting is not None and save_error is None,
        physical_pass=physical_pass,epochs=[] if recorder is None else recorder.epochs))
    write_new(directory/'scene_receipt.json',envelope)
    return envelope

def reconcile(output,rows):
    path=Path(output).parent/(Path(output).name+'_meter')/'events.jsonl';raw=path.read_bytes()
    if not raw or not raw.endswith(b'\n'):raise ValueError('missing/truncated independent Goal meter')
    counts={k:0 for k in CAPS}
    for line in raw.decode('utf-8').splitlines():
        event=json.loads(line)
        if event.get('kind')!='CHARGE':continue
        key=event.get('resource');n=event.get('amount')
        if key not in counts or type(n) is not int or n<=0:raise ValueError('invalid independent charge')
        counts[key]+=n
        if counts[key]!=event.get('total') or counts[key]>CAPS[key]:raise ValueError('meter progression/cap mismatch')
    if not rows or any(not row['accounting_complete'] for row in rows):raise ValueError('unknown scene accounting')
    expected=sum(row['accounting']['solver_problems'] for row in rows)
    if counts['solver_problems']!=expected or counts['fresh_scenes']!=sum(r['scene_attempts'] for r in rows) or counts['collection_attempts']!=0:
        raise ValueError('independent meter/native epochs disagree')
    # Failed prefix planning may have executed no robot action. Preserve the
    # independent actual action count, do not equate slot entry with movement.
    if counts['action_scenes']>sum(r['physical_attempted'] for r in rows):raise ValueError('unexpected action scene')
    if all(r['physical_pass'] for r in rows) and counts['action_scenes']!=len(rows):raise ValueError('passing scenes lack actual action charges')
    return dict(path=str(path),file_sha256=hashlib.sha256(raw).hexdigest(),counts=counts,**{'pass':True})

def run(manifest):
    job=manifest['jobs'][0]
    if job.get('resource_caps')!=CAPS:raise ValueError('five isolation caps must be720/5/5/0')
    stage_a,scene_spec,current,sources=prerequisites(job)
    out=Path(job['output_namespace']);out.mkdir(parents=True,exist_ok=False)
    rows=[];error=None
    try:
        for index,stage in enumerate(STAGES,1):
            row=run_one(stage,sources[PROGRAM[stage]],stage_a,scene_spec,current,out/f'{index:02d}_{stage}')
            rows.append(row);cleanup=row.get('cleanup') or {}
            if not row['physical_pass'] or not cleanup.get('cleanup_safety_pass') or cleanup.get('orphan_process_count')!=0:break
    except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
    meter=meter_error=None
    try:meter=reconcile(out,rows)
    except BaseException as exc:meter_error=dict(type=type(exc).__name__,message=str(exc))
    clean=bool(rows) and all((r.get('cleanup') or {}).get('cleanup_safety_pass') is True and (r.get('cleanup') or {}).get('orphan_process_count')==0 for r in rows)
    infrastructure=error is None and all(r.get('error') is None and r.get('trace_save_error') is None for r in rows)
    science=len(rows)==5 and all(r['physical_pass'] for r in rows) and clean and meter is not None and infrastructure
    evidence=seal(dict(status='B_ALL_FIVE_ISOLATION_PASS' if science else 'B_ISOLATION_FAILED_WITH_EVIDENCE',
        b_scene_spec_sha256=scene_spec['planned_scope_spec_sha256'],b_payload_sha256=payload()['receipt_sha256'],
        rows=[dict(stage=r['stage'],program_id=r['program_id'],physical_pass=r['physical_pass'],scene_receipt_sha256=r['receipt_sha256']) for r in rows],
        **{'pass':science}))
    write_new(out/'isolation_evidence.json',evidence)
    terminal=seal(dict(rows=rows,evidence=evidence,error=error,independent_meter=meter,meter_error=meter_error,
        scene_attempts=sum(r['scene_attempts'] for r in rows),accounting_complete=meter is not None,
        scientific_route_pass=science,isolation_pass=science,skipped_stages=list(STAGES[len(rows):]),
        next_gate='THREE_B_FULL_PROGRAM_TEMPLATES' if science else 'REVIEW_FAILED_ISOLATION',
        **{'pass':infrastructure and clean and meter is not None}))
    write_new(out/'runtime_terminal.json',terminal);return terminal
