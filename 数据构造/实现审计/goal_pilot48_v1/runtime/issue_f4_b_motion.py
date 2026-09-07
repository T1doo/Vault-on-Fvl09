"""Pure B-motion V2/runtime V3 issuer. No reserve, ledger writes or GPU."""
import re
from .issue_f4_b_stage_a import ROOT,A,W,sha,read,digest,_add
from goal_pilot48_v1.runtime_v3.migration import bindings as migrate
from goal_pilot48_v1.f4_b_motion_runtime_v2.binding import root_inputs
from goal_pilot48_v1.f4_b_motion_runtime_v1.binding import catalog

CAPS=dict(solver_problems=0,fresh_scenes=3,action_scenes=3,collection_attempts=3,gpu_lease_seconds=3780)
ROOT_JOB='p48_f4_b_root_001'

def source_fields():
    out=W/'Robotwin2/datasets'/ROOT_JOB
    paths=dict(source_root_goal_terminal=out/'goal_terminal.json',source_root_guard_terminal=out.parent/(ROOT_JOB+'_guard')/(ROOT_JOB+'.terminal.json'),
        source_root_manifest=ROOT/'jobs'/(ROOT_JOB+'.json'),source_root_resource_acceptance=ROOT/'f4_b_acceptance_audit_v1/RESOURCE_ACCOUNTING_ACCEPTANCE_001.json')
    fields={}
    for name,path in paths.items():fields[name+'_path']=str(path);fields[name+'_file_sha256']=sha(path)
    root,bound,receipt=root_inputs(fields)
    cells=catalog(root,bound,receipt)
    fields.update(catalog_sha256=cells['receipt_sha256'],root_artifact_files=cells['dependencies'])
    return fields,paths,cells

def timing():
    folder=W/'Robotwin2/datasets/cmf_realization_unattempted8_v1_3/F4_A_path/branches'
    paths=[folder/pid/'receipt.json' for pid in ('F4-ABC','F4-ACB','F4-BAC')]
    values=[read(p)['elapsed_seconds'] for p in paths];total=sum(values)
    if not 0<total<3600:raise ValueError('historical three-variant wall time reference changed')
    return dict(reference_files={str(p):sha(p) for p in paths},elapsed_seconds=values,total_elapsed_seconds=total,
        child_timeout_seconds=3600,lease_seconds=3780,walltime_multiplier=3600/total,
        A_reference_timing_only=True,A_current_or_raw_reused=False)

def assert_fresh(job_id):
    if not re.fullmatch(r'p48_f4_b_motion_[a-z0-9_]+',job_id):raise ValueError('B-motion namespace required')
    paths=[ROOT/'jobs'/(job_id+'.json'),W/'Robotwin2/datasets'/job_id,W/'Robotwin2/datasets'/(job_id+'_guard'),
        W/'Robotwin2/datasets'/(job_id+'_meter'),W/'Robotwin2/cache/p48'/job_id]
    if any(p.exists() for p in paths):raise FileExistsError('B-motion namespace consumed')

def build_manifest(job_id,reservation):
    assert_fresh(job_id)
    if reservation.get('kind')!='RESERVE' or reservation.get('job_id')!=job_id or reservation.get('reserved')!=CAPS or not reservation.get('event_sha256'):
        raise ValueError('exact caller reservation required')
    c=read(ROOT/'CONTRACT.json');body=dict(c);claim=body.pop('receipt_sha256')
    if digest(body)!=claim or not c['adopted_by_user_goal'] or sha(ROOT/'USER_GOAL_SOURCE.md')!=c['source_file_sha256']:
        raise ValueError('Goal source/authority mismatch')
    fields,paths,cells=source_fields();parent=read(paths['source_root_manifest']);migration=migrate(parent)
    sources=migration['source_files'];inputs=migration['input_files'];time=timing()
    for folder in (ROOT/'runtime',ROOT/'f4_b_motion_runtime_v1',ROOT/'f4_b_motion_runtime_v2',ROOT/'f4_b_acceptance_audit_v1',ROOT/'f4_b_acceptance_audit_v2'):_add(sources,folder.glob('*.py'))
    _add(sources,[ROOT/'runtime/reconcile_root_resolution.py'])
    _add(sources,[A/'realization_batch_runtime_v1_3/pipeline.py',A/'realization_batch_runtime_v1_3/retiming.py',A/'realization_current_layout_audit_v1.py'])
    _add(inputs,[*paths.values(),*map(str,cells['dependencies']),*time['reference_files']])
    acceptance=read(paths['source_root_resource_acceptance']);_add(inputs,[acceptance['resolution_path']])
    # Bind the exact past event hash, not the mutable entire Goal ledger file.
    m=dict(schema_version='cmf_goal_subjob_manifest_v1',goal_id=c['goal_id'],goal_contract_receipt_sha256=claim,
        issuance='ISSUED_UNDER_USER_GOAL',approved=True,gpu_execution_authorized=True,physical_execution_authorized=True,
        allowed_physical_gpu_indices=list(range(8)),gpu_jobs_serial=True,formal_360_authorized=False,training_authorized=False,
        stage0_reopened=False,stage1_authorized=False,pilot_input_authorized=True,run_id=job_id,reserved=dict(CAPS),
        reservation_event_sha256=reservation['event_sha256'],guard_directory=str(W/'Robotwin2/datasets'/(job_id+'_guard')),cache_directory=str(W/'Robotwin2/cache/p48'),
        implementation_source_sha256=parent['implementation_source_sha256'],robotwin_tracked_head=parent['robotwin_tracked_head'],initialization_policy=parent['initialization_policy'],
        source_root_original_goal_pass=False,source_root_resource_acceptance_receipt_sha256=acceptance['receipt_sha256'],
        source_root_budget_event_sha256=acceptance['budget_reconciliation_event_sha256'],current_recovery_pending_until_new_artifact_audit=True,
        timing_derivation=time,**migration,jobs=[dict(job_id=job_id,family='F4',kind='F4_B_MOTION_THREE',requires_live_meter=True,
            runtime_module='goal_pilot48_v1.f4_b_motion_runtime_v2.runtime',runtime_file=str(ROOT/'f4_b_motion_runtime_v2/runtime.py'),
            test_module='goal_pilot48_v1.f4_b_motion_runtime_v2.test_issuer',output_namespace=str(W/'Robotwin2/datasets'/job_id),timeout_seconds=3600,
            resource_caps={k:v for k,v in CAPS.items() if k!='gpu_lease_seconds'},**fields)])
    m['manifest_sha256']=digest(m);return m

def issue_from_reservation(job_id,reservation):return build_manifest(job_id,reservation)
