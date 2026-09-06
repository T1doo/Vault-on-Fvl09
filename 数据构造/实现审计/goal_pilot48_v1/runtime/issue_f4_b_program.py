"""Pure CPU builder using the real completed B source qualification."""
from pathlib import Path
import re
from .issue_f4_b_stage_a import ROOT,A,W,P,sha,read,digest,_add,_inherit

CAPS=dict(solver_problems=450,fresh_scenes=3,action_scenes=0,collection_attempts=0,gpu_lease_seconds=1980)
SOURCE_JOB='p48_f4_b_stage_a_001'
NONCE_BASE=202609070400
EVIDENCE_RECEIPT='8714090570cf6193aecc1df71ccb4ddb3aadced115945a1164025997de7134c7'

def evidence_bindings():
    directory=W/'Robotwin2/datasets'/SOURCE_JOB
    paths=dict(source_stage_a_evidence=directory/'source_stage_a_evidence.json',
        source_stage_a_goal_terminal=directory/'goal_terminal.json',
        source_stage_a_guard_terminal=W/'Robotwin2/datasets'/(SOURCE_JOB+'_guard')/(SOURCE_JOB+'.terminal.json'),
        source_stage_a_manifest=ROOT/'jobs'/(SOURCE_JOB+'.json'))
    fields={}
    for name,path in paths.items():fields[name+'_path']=str(path);fields[name+'_file_sha256']=sha(path)
    evidence=read(paths['source_stage_a_evidence'])
    if evidence.get('receipt_sha256')!=EVIDENCE_RECEIPT:raise ValueError('different B source qualification')
    from goal_pilot48_v1.f4_b_runtime_v1.binding import payload,runtime_spec
    fields['b_payload_sha256']=payload()['receipt_sha256']
    fields['planned_scene_spec_sha256']=runtime_spec('f4_stage_b_planner',stage_a=evidence)['planned_scope_spec_sha256']
    from goal_pilot48_v1.f4_b_program_runtime_v1.runtime import prerequisites
    prerequisites(fields)  # Actual source Goal/Guard/evidence compatibility.
    return fields,paths

def bindings():
    fields,paths=evidence_bindings();parent=read(paths['source_stage_a_manifest'])
    sources={};inputs={}
    for key,destination in (('source_files',sources),('input_files',inputs)):
        for path,expected in parent[key].items():_inherit(destination,path,expected)
    for folder in (ROOT/'runtime',ROOT/'f4_b_program_runtime_v1'):_add(sources,folder.glob('*.py'))
    _add(inputs,paths.values())
    return sources,inputs,parent,fields

def assert_fresh(job_id):
    if not re.fullmatch(r'p48_f4_b_program_[a-z0-9_]+',job_id):raise ValueError('F4-B program namespace required')
    paths=[ROOT/'jobs'/(job_id+'.json'),W/'Robotwin2/datasets'/job_id,
        W/'Robotwin2/datasets'/(job_id+'_guard'),W/'Robotwin2/datasets'/(job_id+'_meter'),W/'Robotwin2/cache/p48'/job_id]
    if any(p.exists() for p in paths):raise FileExistsError('F4-B program namespace used')

def build_manifest(job_id,reservation):
    assert_fresh(job_id)
    if reservation.get('kind')!='RESERVE' or reservation.get('job_id')!=job_id or reservation.get('reserved')!=CAPS or not reservation.get('event_sha256'):
        raise ValueError('exact caller-provided reservation required')
    contract=read(ROOT/'CONTRACT.json');c=dict(contract);claimed=c.pop('receipt_sha256')
    if digest(c)!=claimed or not contract['adopted_by_user_goal'] or sha(ROOT/'USER_GOAL_SOURCE.md')!=contract['source_file_sha256']:
        raise ValueError('Goal authority/source changed')
    sources,inputs,parent,evidence=bindings()
    m=dict(schema_version='cmf_goal_subjob_manifest_v1',goal_id=contract['goal_id'],goal_contract_receipt_sha256=claimed,
        issuance='ISSUED_UNDER_USER_GOAL',approved=True,gpu_execution_authorized=True,physical_execution_authorized=False,
        allowed_physical_gpu_indices=list(range(8)),gpu_jobs_serial=True,formal_360_authorized=False,training_authorized=False,
        stage0_reopened=False,stage1_authorized=False,pilot_input_authorized=False,run_id=job_id,
        reserved=dict(CAPS),reservation_event_sha256=reservation['event_sha256'],
        guard_directory=str(W/'Robotwin2/datasets'/(job_id+'_guard')),cache_directory=str(W/'Robotwin2/cache/p48'),
        implementation_source_sha256=parent['implementation_source_sha256'],robotwin_tracked_head=parent['robotwin_tracked_head'],
        source_files=sources,input_files=inputs,initialization_policy=parent['initialization_policy'],
        source_stage_a_job=SOURCE_JOB,source_stage_a_evidence_receipt_sha256=EVIDENCE_RECEIPT,
        jobs=[dict(job_id=job_id,family='F4',kind='F4_B_THREE_PROGRAM_PLANNERS',
            runtime_module='goal_pilot48_v1.f4_b_program_runtime_v1.runtime',runtime_file=str(ROOT/'f4_b_program_runtime_v1/runtime.py'),
            test_module='goal_pilot48_v1.f4_b_program_runtime_v1.test_issuer',
            output_namespace=str(W/'Robotwin2/datasets'/job_id),timeout_seconds=1800,
            resource_caps={k:v for k,v in CAPS.items() if k!='gpu_lease_seconds'},
            planner_reset_nonce_base=NONCE_BASE,**evidence)])
    for role,name in (('guard','guarded_launcher.py'),('runner','job_runner.py')):
        m[role+'_script_path']=str(ROOT/'runtime'/name);m[role+'_script_sha256']=sha(ROOT/'runtime'/name)
    m['manifest_sha256']=digest(m);return m

def issue_from_reservation(job_id,reservation):
    """No ledger/job writes; main thread reserves and publishes exclusively."""
    return build_manifest(job_id,reservation)
