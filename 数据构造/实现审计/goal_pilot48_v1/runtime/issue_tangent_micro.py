"""Pure F3 tangent-mode builder. Caller supplies reservation; never writes/launches."""
import copy,re
from pathlib import Path
from .issue_f4_b_stage_a import ROOT,A,W,sha,read,digest,_add
from goal_pilot48_v1.runtime_v2.migration import bindings as migrate_bindings
CAPS=dict(solver_problems=3,fresh_scenes=1,action_scenes=1,collection_attempts=0,gpu_lease_seconds=1080)
PARENT_JOB='p48_f3_micro_006'
EXPECTED_CPU_RECEIPT='91d2e0566e1da4619c359ce06aae1fb09a1904d1cbf065aaf2ec377fb3512c50'

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
        raise ValueError('006 terminal identity/accounting incomplete')
    if terminal['resource_counts']!=dict(solver_problems=2,fresh_scenes=1,action_scenes=1,collection_attempts=0) or terminal['pass'] is not False:
        raise ValueError('006 original failure not preserved')
    if terminal['runtime_result']['error']['message']!='table contact cannot replace pad support witness':raise ValueError('006 failure class changed')
    if guard['run_id']!=PARENT_JOB or guard['child_exit_code']!=1 or guard['task_owned_cleanup_pass'] is not True or guard.get('timed_out'):
        raise ValueError('006 not terminal with clean owned resources')
    cpu_path=ROOT/'f3_tangent_escape_v1/CPU_AUDIT_V1_1.json';cpu=checked(cpu_path)
    if cpu['receipt_sha256']!=EXPECTED_CPU_RECEIPT or cpu['tests_run']!=36 or cpu['pass'] is not True or len(cpu['source_bindings'])!=21:
        raise ValueError('latest exact 36-test/21-source CPU seal required')
    sources=migrated['source_files'];inputs=migrated['input_files']
    for p,h in cpu['source_bindings'].items():
        if sha(p)!=h:raise ValueError('current CPU-bound source changed '+p)
        if p in sources and sources[p]!=h:raise ValueError('parent/CPU source conflict '+p)
        sources[p]=h
    if sha(ROOT/'f3_tangent_escape_v1/CPU_AUDIT.json')!=cpu['supersedes_CPU_AUDIT_file_sha256']:raise ValueError('old CPU history changed')
    for folder in (ROOT/'f3_tangent_escape_v1',ROOT/'f3_runtime_v5',ROOT/'f3_support_state_006_audit_v1',ROOT/'f3_tangent_issuer_review_v1'):
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
    if not re.fullmatch(r'p48_f3_tangent_micro_[a-z0-9_]+',job_id):raise ValueError('fresh tangent micro namespace required')
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
        model_eligibility_revision=1,model_eligibility_schema='stable_grasp_native_tangent_unloading_escape_v1',
        failure_class='planner_support_pair_eligibility',evidence_based_revision=3,pregrasp_route_revision=2,
        high_level_start_state_check_cap=6,high_level_start_state_checks_are_solver_problems=False,
        high_level_start_state_check_breakdown=dict(original_full=2,pair=2,restored_full=2),
        old_supported_gate_unchanged=True,physical_verifier_thresholds_unchanged=True,shared_v_authorized=False,**fields)
    manifest['jobs'][0].update(job_id=job_id,kind='F3_MICRO',model_variant='TANGENT_MODEL_ELIGIBILITY_V1',
        output_namespace=str(W/'Robotwin2/datasets'/job_id),runtime_module='goal_pilot48_v1.f3_runtime_v5.micro',
        runtime_file=str(ROOT/'f3_runtime_v5/micro.py'),test_module='goal_pilot48_v1.f3_runtime_v5.test_all',timeout_seconds=900,
        resource_caps={k:v for k,v in CAPS.items() if k!='gpu_lease_seconds'})
    manifest['manifest_sha256']=digest(manifest)
    return manifest

def issue_from_reservation(job_id,reservation):return build_manifest(job_id,reservation)
