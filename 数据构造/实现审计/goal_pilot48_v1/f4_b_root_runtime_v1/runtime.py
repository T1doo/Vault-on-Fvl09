"""One B r_pc root only, with the actual live Goal collection meter."""
from pathlib import Path
import traceback
from ..f4_b_program_runtime_v1.runtime import bound_json,SOURCE_SHA
from ..f4_b_template_runtime_v1.runtime import prerequisites as template_prerequisites
from ..f4_b_runtime_v1.binding import payload,seal,PROGRAMS
from ..f4_b_runtime_v1.stages import root_prerequisites
from ..f4_b_runtime_v1.adapter import make_adapter
from realization_utf8_io_v1 import write_new
from .entry import orchestrator,disk_finalizer
from .accounting import instrument_scene_ledger

CAPS=dict(solver_problems=460,fresh_scenes=11,action_scenes=7,collection_attempts=3)

def prerequisites(job):
    evidence=bound_json(job,'source_template_evidence')
    goal=bound_json(job,'source_template_goal_terminal');guard=bound_json(job,'source_template_guard_terminal')
    manifest=bound_json(job,'source_template_manifest','manifest_sha256');parent=goal.get('runtime_result') or {}
    if (goal.get('pass') is not True or goal.get('accounting_complete') is not True or
        goal.get('resource_counts')!=dict(solver_problems=480,fresh_scenes=3,action_scenes=3,collection_attempts=0) or
        parent.get('template_pass') is not True or parent.get('evidence')!=evidence or
        parent.get('independent_meter',{}).get('pass') is not True or
        guard.get('child_exit_code')!=0 or guard.get('task_owned_cleanup_pass') is not True or
        goal.get('manifest_sha256')!=manifest['manifest_sha256'] or guard.get('manifest_sha256')!=manifest['manifest_sha256'] or
        manifest['jobs'][0].get('runtime_module')!='goal_pilot48_v1.f4_b_template_runtime_v1.runtime'):
        raise ValueError('real completed B template source required')
    stage_a,scene,current,sources,isolation=template_prerequisites(manifest['jobs'][0])
    bound=root_prerequisites(stage_a=stage_a,planner_envelopes=sources,isolation=isolation,template=evidence)
    if job.get('b_payload_sha256')!=payload()['receipt_sha256'] or job.get('b_scene_spec_sha256')!=scene['planned_scope_spec_sha256']:
        raise ValueError('root B binding mismatch')
    return bound

def run(manifest,*,meter):
    job=manifest['jobs'][0]
    if job.get('resource_caps')!=CAPS or job.get('requires_live_meter') is not True or meter.closed:
        raise ValueError('B root requires exact caps and live runtime_v2 meter')
    if any(meter.counts.values()):raise ValueError('root starts with nonzero job meter')
    bound=prerequisites(job)
    out=Path(job['output_namespace']);out.mkdir(parents=True,exist_ok=False)
    write_new(out/'bound_prerequisites.json',bound)
    root=None;error=None;finalizer=None;native=[]
    try:
        adapter=make_adapter(output_root=out/'scene_work',source_sha256=SOURCE_SHA,
            planned_spec=bound['planned_spec'],full_program_specs=bound['full_program_specs'])
        executor,writer=orchestrator(adapter,out/'development_root',implementation_version='controlled_multi_future_f4_qualified_development_root_v1')
        with instrument_scene_ledger(adapter,out/'native_scene_ledger') as native:
            with meter.instrument_adapter(adapter,source_profile_sha256=manifest['implementation_source_sha256']):
                root=executor.run_nonformal_root(output_dir=out/'development_root',planned_root_slot_spec=bound['planned_spec'],
                    realization_spec_by_program={p:dict(realization='r_pc',formal_data=False,stage0_data=False,stage1_authorized=False) for p in PROGRAMS},
                    stage0_data=False,stage0_authorized=False,development_video_required=True)
        accepted=root.get('status')=='accepted'
        result=dict(root_receipt=root,development_root_pass=accepted,development_accepted_root_count=int(accepted),development_accepted_trajectory_count=3 if accepted else 0)
        finalizer=disk_finalizer(result,job,out)
    except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
    counts=dict(meter.counts);known=root is not None
    known=known and len(native)==counts['fresh_scenes'] and all(r.get('accounting_complete') is True for r in native)
    known=known and sum(r.get('solver_problems',0) for r in native)==counts['solver_problems']
    known=known and sum(len(h.records) for h in meter.collection_hooks)==counts['collection_attempts']
    if root is not None:
        cleanup=root.get('cleanup_records',[])
        known=known and len(cleanup)==counts['fresh_scenes'] and all(r.get('cleanup_safety_pass') is True and r.get('orphan_process_count')==0 for r in cleanup)
        known=known and root.get('branch_execution_attempt_count')<=counts['collection_attempts']
        # Native API136 is intentionally retained; complete original root
        # independently requires10+3*(12*10+30)=460 actual problems.
        if root.get('status')=='accepted':known=known and counts==CAPS and root.get('planner_query_count_total')==136
    science=error is None and known and finalizer is not None and finalizer.get('accepted') is True
    terminal=seal(dict(root_receipt=root,finalizer=finalizer,error=error,native_scene_ledger=native,scene_attempts=counts['fresh_scenes'],
        collection_attempts=counts['collection_attempts'],resource_counts=counts,accounting_complete=bool(known),
        scientific_route_pass=science,development_root_pass=science,
        development_accepted_root_count=int(science),development_accepted_trajectory_count=3 if science else 0,
        next_gate='THREE_B_R_INV_MOTION_REALIZATIONS' if science else 'REVIEW_INCOMPLETE_B_ROOT',
        **{'pass':error is None and bool(known)}))
    write_new(out/'runtime_terminal.json',terminal);return terminal
