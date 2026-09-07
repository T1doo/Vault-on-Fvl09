"""Pure root builder; no reservation/publication and no historical A qualification reuse."""
import re
from .issue_f4_b_stage_a import ROOT,A,W,sha,read,digest,_add
from goal_pilot48_v1.runtime_v2.migration import bindings as migrate_bindings

CAPS=dict(solver_problems=460,fresh_scenes=11,action_scenes=7,collection_attempts=3,gpu_lease_seconds=5580)
SOURCE_JOB='p48_f4_b_template_001'
TIMING_REFERENCE=W/'Robotwin2/datasets/cmf_f4_v22_authorized_root1/development_root/root_receipt.json'

def timeout_derivation():
    old=read(TIMING_REFERENCE)
    if old.get('status')!='accepted' or old.get('planner_query_count_total')!=136 or old.get('branch_execution_attempt_count')!=3:
        raise ValueError('historical full-root timing reference changed shape')
    elapsed=old['elapsed_seconds']
    if not isinstance(elapsed,(int,float)) or not 0<elapsed<5400:raise ValueError('timing reference invalid')
    return dict(reference_path=str(TIMING_REFERENCE),reference_file_sha256=sha(TIMING_REFERENCE),historical_elapsed_seconds=elapsed,
        historical_manifest_timeout_seconds=28800,new_child_timeout_seconds=5400,new_lease_seconds=5580,
        observed_walltime_multiplier=5400/elapsed,extra_guard_cleanup_seconds=180,
        rationale='one identical-stage-count root, about2.49x observed2167s; finite90min child instead of historical8h cap',
        old_A_evidence_is_timing_only=True,A_physical_qualification_reused=False)

def evidence_bindings():
    out=W/'Robotwin2/datasets'/SOURCE_JOB
    paths=dict(source_template_evidence=out/'template_evidence.json',source_template_goal_terminal=out/'goal_terminal.json',
        source_template_guard_terminal=W/'Robotwin2/datasets'/(SOURCE_JOB+'_guard')/(SOURCE_JOB+'.terminal.json'),
        source_template_manifest=ROOT/'jobs'/(SOURCE_JOB+'.json'))
    fields={}
    for name,path in paths.items():fields[name+'_path']=str(path);fields[name+'_file_sha256']=sha(path)
    evidence=read(paths['source_template_evidence'])
    fields['b_payload_sha256']=evidence['b_payload_sha256'];fields['b_scene_spec_sha256']=evidence['b_scene_spec_sha256']
    from goal_pilot48_v1.f4_b_root_runtime_v1.runtime import prerequisites
    prerequisites(fields)  # Strict real template + all earlier B qualifications.
    return fields,paths

def assert_fresh(job_id):
    if not re.fullmatch(r'p48_f4_b_root_[a-z0-9_]+',job_id):raise ValueError('B root namespace required')
    paths=[ROOT/'jobs'/(job_id+'.json'),W/'Robotwin2/datasets'/job_id,W/'Robotwin2/datasets'/(job_id+'_guard'),
        W/'Robotwin2/datasets'/(job_id+'_meter'),W/'Robotwin2/cache/p48'/job_id]
    if any(p.exists() for p in paths):raise FileExistsError('B root namespace consumed')

def build_manifest(job_id,reservation):
    assert_fresh(job_id)
    if reservation.get('kind')!='RESERVE' or reservation.get('job_id')!=job_id or reservation.get('reserved')!=CAPS or not reservation.get('event_sha256'):
        raise ValueError('exact caller reservation required')
    c=read(ROOT/'CONTRACT.json');body=dict(c);claimed=body.pop('receipt_sha256')
    if digest(body)!=claimed or not c['adopted_by_user_goal'] or sha(ROOT/'USER_GOAL_SOURCE.md')!=c['source_file_sha256']:
        raise ValueError('Goal authority/source mismatch')
    fields,paths=evidence_bindings();parent=read(paths['source_template_manifest']);timing=timeout_derivation()
    migration=migrate_bindings(parent);sources=migration['source_files'];inputs=migration['input_files']
    for folder in (ROOT/'runtime',ROOT/'f4_b_root_runtime_v1'):_add(sources,folder.glob('*.py'))
    _add(sources,[A/'f4_development_root_runtime_v2_2/job_runner.py'])
    _add(inputs,[*paths.values(),TIMING_REFERENCE])
    m=dict(schema_version='cmf_goal_subjob_manifest_v1',goal_id=c['goal_id'],goal_contract_receipt_sha256=claimed,
        issuance='ISSUED_UNDER_USER_GOAL',approved=True,gpu_execution_authorized=True,physical_execution_authorized=True,
        allowed_physical_gpu_indices=list(range(8)),gpu_jobs_serial=True,formal_360_authorized=False,training_authorized=False,
        stage0_reopened=False,stage1_authorized=False,pilot_input_authorized=True,run_id=job_id,
        reserved=dict(CAPS),reservation_event_sha256=reservation['event_sha256'],
        guard_directory=str(W/'Robotwin2/datasets'/(job_id+'_guard')),cache_directory=str(W/'Robotwin2/cache/p48'),
        implementation_source_sha256=parent['implementation_source_sha256'],robotwin_tracked_head=parent['robotwin_tracked_head'],
        initialization_policy=parent['initialization_policy'],timeout_derivation=timing,**migration,
        jobs=[dict(job_id=job_id,family='F4',kind='F4_B_STRICT_PREFIX_ROOT',
            runtime_module='goal_pilot48_v1.f4_b_root_runtime_v1.runtime',runtime_file=str(ROOT/'f4_b_root_runtime_v1/runtime.py'),
            test_module='goal_pilot48_v1.f4_b_root_runtime_v1.test_issuer',requires_live_meter=True,
            timeout_seconds=5400,output_namespace=str(W/'Robotwin2/datasets'/job_id),
            resource_caps={k:v for k,v in CAPS.items() if k!='gpu_lease_seconds'},**fields)])
    m['manifest_sha256']=digest(m);return m

def issue_from_reservation(job_id,reservation):return build_manifest(job_id,reservation)
