"""Pure CPU construction for five B isolation scenes; no reserve or launch."""
import re
from .issue_f4_b_stage_a import ROOT,A,W,P,read,sha,digest,_add,_inherit
CAPS=dict(solver_problems=720,fresh_scenes=5,action_scenes=5,collection_attempts=0,gpu_lease_seconds=3780)
SOURCE_JOB='p48_f4_b_program_001'
SOURCE_TERMINAL_RECEIPT='e4b44492c6d1cfc45826e34145ed24cc71eafc1a7edb3585bb9441e60091273e'

def evidence_bindings():
    out=W/'Robotwin2/datasets'/SOURCE_JOB
    paths=dict(source_program_goal_terminal=out/'goal_terminal.json',
        source_program_guard_terminal=W/'Robotwin2/datasets'/(SOURCE_JOB+'_guard')/(SOURCE_JOB+'.terminal.json'),
        source_program_manifest=ROOT/'jobs'/(SOURCE_JOB+'.json'))
    for pid in ('F4-ABC','F4-ACB','F4-BAC'):paths['source_'+pid.lower().replace('-','_')]=out/pid/'terminal.json'
    fields={}
    for name,path in paths.items():fields[name+'_path']=str(path);fields[name+'_file_sha256']=sha(path)
    terminal=read(paths['source_program_goal_terminal'])
    if terminal['receipt_sha256']!=SOURCE_TERMINAL_RECEIPT:raise ValueError('different program terminal source')
    from goal_pilot48_v1.f4_b_runtime_v1.binding import payload
    fields['b_payload_sha256']=payload()['receipt_sha256']
    fields['b_scene_spec_sha256']=terminal['runtime_result']['rows'][0]['b_scene_spec_sha256']
    from goal_pilot48_v1.f4_b_isolation_runtime_v1.runtime import prerequisites
    prerequisites(fields)
    return fields,paths

def build_manifest(job_id,reservation):
    if not re.fullmatch(r'p48_f4_b_isolation_[a-z0-9_]+',job_id):raise ValueError('isolation namespace required')
    used=[ROOT/'jobs'/(job_id+'.json'),W/'Robotwin2/datasets'/job_id,W/'Robotwin2/datasets'/(job_id+'_guard'),W/'Robotwin2/datasets'/(job_id+'_meter'),W/'Robotwin2/cache/p48'/job_id]
    if any(p.exists() for p in used):raise FileExistsError('isolation namespace already used')
    if reservation.get('kind')!='RESERVE' or reservation.get('job_id')!=job_id or reservation.get('reserved')!=CAPS or not reservation.get('event_sha256'):
        raise ValueError('exact caller-provided reservation required')
    c=read(ROOT/'CONTRACT.json');body=dict(c);claimed=body.pop('receipt_sha256')
    if digest(body)!=claimed or not c['adopted_by_user_goal'] or sha(ROOT/'USER_GOAL_SOURCE.md')!=c['source_file_sha256']:
        raise ValueError('Goal source authority changed')
    fields,paths=evidence_bindings();parent=read(paths['source_program_manifest'])
    sources={};inputs={}
    for field,target in (('source_files',sources),('input_files',inputs)):
        for path,expected in parent[field].items():_inherit(target,path,expected)
    for folder in (ROOT/'runtime',ROOT/'f4_b_isolation_runtime_v1'):_add(sources,folder.glob('*.py'))
    _add(inputs,paths.values())
    m=dict(schema_version='cmf_goal_subjob_manifest_v1',goal_id=c['goal_id'],goal_contract_receipt_sha256=claimed,
        issuance='ISSUED_UNDER_USER_GOAL',approved=True,gpu_execution_authorized=True,physical_execution_authorized=True,
        allowed_physical_gpu_indices=list(range(8)),gpu_jobs_serial=True,formal_360_authorized=False,training_authorized=False,
        stage0_reopened=False,stage1_authorized=False,pilot_input_authorized=False,run_id=job_id,
        reserved=dict(CAPS),reservation_event_sha256=reservation['event_sha256'],
        guard_directory=str(W/'Robotwin2/datasets'/(job_id+'_guard')),cache_directory=str(W/'Robotwin2/cache/p48'),
        implementation_source_sha256=parent['implementation_source_sha256'],robotwin_tracked_head=parent['robotwin_tracked_head'],
        source_files=sources,input_files=inputs,initialization_policy=parent['initialization_policy'],
        jobs=[dict(job_id=job_id,family='F4',kind='F4_B_FIVE_ISOLATION',
            runtime_module='goal_pilot48_v1.f4_b_isolation_runtime_v1.runtime',runtime_file=str(ROOT/'f4_b_isolation_runtime_v1/runtime.py'),
            test_module='goal_pilot48_v1.f4_b_isolation_runtime_v1.test_issuer',timeout_seconds=3600,
            output_namespace=str(W/'Robotwin2/datasets'/job_id),
            resource_caps={k:v for k,v in CAPS.items() if k!='gpu_lease_seconds'},**fields)])
    for role,name in (('guard','guarded_launcher.py'),('runner','job_runner.py')):
        m[role+'_script_path']=str(ROOT/'runtime'/name);m[role+'_script_sha256']=sha(ROOT/'runtime'/name)
    m['manifest_sha256']=digest(m);return m

def issue_from_reservation(job_id,reservation):return build_manifest(job_id,reservation)
