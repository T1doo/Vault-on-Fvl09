"""Pure F3 one-sided-mode builder. Caller supplies reservation; never writes/launches."""
import copy,re
from pathlib import Path
from .issue_f4_b_stage_a import ROOT,A,W,sha,read,digest,_add
from goal_pilot48_v1.runtime_v2.migration import bindings as migrate_bindings
CAPS=dict(solver_problems=3,fresh_scenes=1,action_scenes=1,collection_attempts=0,gpu_lease_seconds=1080)
PARENT_JOB='p48_f3_tangent_micro_001'
EXPECTED_CPU_RECEIPT='1dde8a3aba566d83c5e4e48e227689e3ca84870f0ca113f5925c383c980201ff'

def checked(path,key='receipt_sha256'):
    value=read(path);body=dict(value);claimed=body.pop(key)
    if digest(body)!=claimed:raise ValueError('self-hash changed '+str(path))
    return value

def prerequisites():
    parent_path=ROOT/'jobs'/(PARENT_JOB+'.json');parent=checked(parent_path,'manifest_sha256')
    # Verify every old source/input BEFORE additions or runtime migration.
    migrated=migrate_bindings(parent)
    out=W/'Robotwin2/datasets'/PARENT_JOB
    terminal=checked(out/'goal_terminal.json')
    guard_path=W/'Robotwin2/datasets'/(PARENT_JOB+'_guard')/(PARENT_JOB+'.terminal.json');guard=checked(guard_path)
    if terminal['job_id']!=PARENT_JOB or terminal['manifest_sha256']!=parent['manifest_sha256'] or not terminal['accounting_complete']:
        raise ValueError('tangent001 terminal identity/accounting incomplete')
    if terminal['resource_counts']!=dict(solver_problems=2,fresh_scenes=1,action_scenes=1,collection_attempts=0) or terminal['pass'] is not False:
        raise ValueError('tangent001 original failure not preserved')
    if terminal['runtime_result']['error']['message']!='new tangent certificate rejected; old supported condition remains failed':raise ValueError('tangent001 failure class changed')
    trace_receipt=read(out/'diagnostic_trace_receipt.json')
    if trace_receipt!=terminal['runtime_result']['trace'] or sha(trace_receipt['path'])!=trace_receipt['sha256']:raise ValueError('tangent001 real trace binding changed')
    if guard['run_id']!=PARENT_JOB or guard['child_exit_code']!=1 or guard['task_owned_cleanup_pass'] is not True or guard.get('timed_out'):
        raise ValueError('tangent001 not terminal with clean owned resources')
    cpu_path=ROOT/'f3_one_sided_escape_v2/CPU_AUDIT_V2_1.json';cpu=checked(cpu_path)
    if cpu['receipt_sha256']!=EXPECTED_CPU_RECEIPT or cpu['tests_run']!=43 or cpu['pass'] is not True or len(cpu['source_bindings'])!=25:
        raise ValueError('latest exact 43-test/25-source CPU seal required')
    sources=migrated['source_files'];inputs=migrated['input_files']
    for p,h in cpu['source_bindings'].items():
        if not Path(p).resolve().is_relative_to(W):raise ValueError('CPU source outside workspace')
        if sha(p)!=h:raise ValueError('current CPU-bound source changed '+p)
        if p in sources and sources[p]!=h:raise ValueError('parent/CPU source conflict '+p)
        sources[p]=h
    if sha(ROOT/'f3_tangent_escape_v1/CPU_AUDIT_V1_1.json')!=cpu['supersedes_CPU_AUDIT_file_sha256']:raise ValueError('old CPU history changed')
    if sha(ROOT/'f3_one_sided_escape_v2/CPU_AUDIT_V2.json')!=cpu['supersedes_initial_V2_CPU_audit_sha256']:raise ValueError('initial V2 CPU history changed')
    evidence=checked(ROOT/'f3_one_sided_escape_v2/CPU_INPUT_BINDINGS.json')
    if evidence['CPU_audit_receipt']!=cpu['receipt_sha256']:raise ValueError('CPU input/source audit mismatch')
    for path,expected in evidence['input_bindings'].items():
        if not Path(path).resolve().is_relative_to(W):raise ValueError('CPU input outside workspace')
        if sha(path)!=expected:raise ValueError('changed real CPU input '+path)
        if path in inputs and inputs[path]!=expected:raise ValueError('parent/CPU input conflict '+path)
        inputs[path]=expected
    for folder in (ROOT/'f3_one_sided_escape_v2',ROOT/'f3_runtime_v6',ROOT/'f3_one_sided_eligibility_review_v1',ROOT/'f3_one_sided_issuer_review_v1'):
        _add(sources,folder.glob('*.py'));_add(inputs,folder.glob('*.json'));_add(inputs,folder.glob('*.md'))
    _add(sources,[Path(__file__),ROOT/'runtime/issue_f4_b_stage_a.py'])
    _add(inputs,[parent_path,guard_path,*[p for p in out.rglob('*') if p.is_file()]])
    recipe=checked(parent['recipe_spec_path']);route=checked(parent['route_spec_path'])
    if recipe['stability_recipe_revision']!=3 or recipe['lift_m']!=.025 or route['pregrasp_route_revision']!=2 or route['max_single_queries']!=3:
        raise ValueError('unchanged recipe3/route2/lift25 required')
    if route['height_recipe_id']!=recipe['proposal_id']:raise ValueError('recipe/route identity mismatch')
    return parent,migrated,dict(parent_manifest_path=str(parent_path),parent_manifest_sha256=parent['manifest_sha256'],
        parent_terminal_receipt_sha256=terminal['receipt_sha256'],parent_guard_receipt_sha256=guard['receipt_sha256'],
        current_cpu_audit_path=str(cpu_path),current_cpu_audit_receipt_sha256=cpu['receipt_sha256'])

def assert_fresh(job_id):
    if not re.fullmatch(r'p48_f3_one_sided_micro_[a-z0-9_]+',job_id):raise ValueError('fresh tangent micro namespace required')
    paths=[ROOT/'jobs'/(job_id+'.json'),W/'Robotwin2/datasets'/job_id,W/'Robotwin2/datasets'/(job_id+'_guard'),W/'Robotwin2/datasets'/(job_id+'_meter'),W/'Robotwin2/cache/p48'/job_id]
    if any(p.exists() for p in paths):raise FileExistsError('used tangent namespace')

def build_manifest(job_id,reservation):
    assert_fresh(job_id)
    if reservation.get('kind')!='RESERVE' or reservation.get('job_id')!=job_id or reservation.get('reserved')!=CAPS or not reservation.get('event_sha256'):
        raise ValueError('exact caller-supplied reservation required')
    contract=checked(ROOT/'CONTRACT.json')
    if not contract['adopted_by_user_goal'] or sha(ROOT/'USER_GOAL_SOURCE.md')!=contract['source_file_sha256']:raise ValueError('Goal authority changed')
    parent,migrated,fields=prerequisites();manifest=copy.deepcopy(parent);manifest.pop('manifest_sha256')
    if parent['goal_contract_receipt_sha256']!=contract['receipt_sha256']:raise ValueError('parent current Goal mismatch')
    manifest.update(migrated,run_id=job_id,reserved=dict(CAPS),reservation_event_sha256=reservation['event_sha256'],
        guard_directory=str(W/'Robotwin2/datasets'/(job_id+'_guard')),allowed_physical_gpu_indices=list(range(8)),gpu_jobs_serial=True,
        model_eligibility_revision=2,model_eligibility_schema='stable_grasp_one_sided_native_unloading_escape_v2',
        native_lower_bound_epsilon_m=.0001,positive_gap_upper_bound_m=None,parent_model_eligibility_revision_consumed=1,
        failure_class='planner_support_pair_eligibility',evidence_based_revision=3,pregrasp_route_revision=2,
        high_level_start_state_check_cap=6,high_level_start_state_checks_are_solver_problems=False,
        high_level_start_state_check_breakdown=dict(original_full=2,pair=2,restored_full=2),
        old_supported_gate_unchanged=True,physical_verifier_thresholds_unchanged=True,shared_v_authorized=False,**fields)
    manifest['jobs'][0].update(job_id=job_id,kind='F3_MICRO',model_variant='ONE_SIDED_MODEL_ELIGIBILITY_V2',
        output_namespace=str(W/'Robotwin2/datasets'/job_id),runtime_module='goal_pilot48_v1.f3_runtime_v6.micro',
        runtime_file=str(ROOT/'f3_runtime_v6/micro.py'),test_module='goal_pilot48_v1.f3_runtime_v6.test_all',timeout_seconds=900,
        resource_caps={k:v for k,v in CAPS.items() if k!='gpu_lease_seconds'})
    manifest['manifest_sha256']=digest(manifest)
    return manifest

def issue_from_reservation(job_id,reservation):return build_manifest(job_id,reservation)
