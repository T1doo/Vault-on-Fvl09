"""Pure CPU template manifest builder; requires real five-stage completion."""
import re
from .issue_f4_b_stage_a import ROOT,A,W,sha,read,digest,_add
from goal_pilot48_v1.runtime_v2.migration import bindings as migrate_bindings
CAPS=dict(solver_problems=480,fresh_scenes=3,action_scenes=3,collection_attempts=0,gpu_lease_seconds=3780)
SOURCE_JOB='p48_f4_b_isolation_001'

def evidence_bindings():
    out=W/'Robotwin2/datasets'/SOURCE_JOB
    paths=dict(source_isolation_evidence=out/'isolation_evidence.json',source_isolation_goal_terminal=out/'goal_terminal.json',
        source_isolation_guard_terminal=W/'Robotwin2/datasets'/(SOURCE_JOB+'_guard')/(SOURCE_JOB+'.terminal.json'),
        source_isolation_manifest=ROOT/'jobs'/(SOURCE_JOB+'.json'))
    fields={}
    for name,path in paths.items():fields[name+'_path']=str(path);fields[name+'_file_sha256']=sha(path)
    evidence=read(paths['source_isolation_evidence'])
    fields['b_payload_sha256']=evidence['b_payload_sha256'];fields['b_scene_spec_sha256']=evidence['b_scene_spec_sha256']
    from goal_pilot48_v1.f4_b_template_runtime_v1.runtime import prerequisites
    prerequisites(fields)  # Missing, failed or still-running source never passes.
    return fields,paths

def assert_fresh(job_id):
    if not re.fullmatch(r'p48_f4_b_template_[a-z0-9_]+',job_id):raise ValueError('template namespace required')
    paths=[ROOT/'jobs'/(job_id+'.json'),W/'Robotwin2/datasets'/job_id,W/'Robotwin2/datasets'/(job_id+'_guard'),
        W/'Robotwin2/datasets'/(job_id+'_meter'),W/'Robotwin2/cache/p48'/job_id]
    if any(p.exists() for p in paths):raise FileExistsError('template namespace consumed')

def build_manifest(job_id,reservation):
    assert_fresh(job_id)
    if reservation.get('kind')!='RESERVE' or reservation.get('job_id')!=job_id or reservation.get('reserved')!=CAPS or not reservation.get('event_sha256'):
        raise ValueError('exact caller-supplied template reservation required')
    c=read(ROOT/'CONTRACT.json');body=dict(c);claimed=body.pop('receipt_sha256')
    if digest(body)!=claimed or not c['adopted_by_user_goal'] or sha(ROOT/'USER_GOAL_SOURCE.md')!=c['source_file_sha256']:
        raise ValueError('Goal authority/source changed')
    fields,paths=evidence_bindings();parent=read(paths['source_isolation_manifest'])
    migrated=migrate_bindings(parent);sources=migrated['source_files'];inputs=migrated['input_files']
    for folder in (ROOT/'runtime',ROOT/'f4_b_template_runtime_v1'):_add(sources,folder.glob('*.py'))
    _add(inputs,paths.values())
    m=dict(schema_version='cmf_goal_subjob_manifest_v1',goal_id=c['goal_id'],goal_contract_receipt_sha256=claimed,
        issuance='ISSUED_UNDER_USER_GOAL',approved=True,gpu_execution_authorized=True,physical_execution_authorized=True,
        allowed_physical_gpu_indices=list(range(8)),gpu_jobs_serial=True,formal_360_authorized=False,training_authorized=False,
        stage0_reopened=False,stage1_authorized=False,pilot_input_authorized=False,run_id=job_id,
        reserved=dict(CAPS),reservation_event_sha256=reservation['event_sha256'],
        guard_directory=str(W/'Robotwin2/datasets'/(job_id+'_guard')),cache_directory=str(W/'Robotwin2/cache/p48'),
        implementation_source_sha256=parent['implementation_source_sha256'],robotwin_tracked_head=parent['robotwin_tracked_head'],
        initialization_policy=parent['initialization_policy'],**migrated,
        jobs=[dict(job_id=job_id,family='F4',kind='F4_B_THREE_TEMPLATES',
            runtime_module='goal_pilot48_v1.f4_b_template_runtime_v1.runtime',runtime_file=str(ROOT/'f4_b_template_runtime_v1/runtime.py'),
            test_module='goal_pilot48_v1.f4_b_template_runtime_v1.test_issuer',requires_live_meter=False,
            timeout_seconds=3600,output_namespace=str(W/'Robotwin2/datasets'/job_id),
            resource_caps={k:v for k,v in CAPS.items() if k!='gpu_lease_seconds'},**fields)])
    m['manifest_sha256']=digest(m);return m

def issue_from_reservation(job_id,reservation):return build_manifest(job_id,reservation)
