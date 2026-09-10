"""F1 family orchestration over the existing launcher, ledger and reserve policy.

CPU imports only. Preparation never grants execution; the production entry checks
one whole-family approval before touching a GPU backend. No other family dispatch.
"""
import argparse
import copy
import csv
import fcntl
import hashlib
import io
import json
import os
import time
from pathlib import Path
import scene_plan as scenes
import file_source_pin as pins

HERE = Path(__file__).resolve().parent
WORKSPACE = Path('/nfs_share/lijunhui')
COUNTERS = ('fresh_scenes', 'action_scenes', 'collection_attempts', 'solver_problems', 'gpu_lease_seconds')
BASE = dict(zip(COUNTERS, (33, 21, 9, 192, 7200)))
ROOT_CAP = dict(zip(COUNTERS, (66, 42, 18, 384, 14400)))
ATTEMPT = {**ROOT_CAP, 'gpu_lease_seconds': 7200}
COPY_ROOT = WORKSPACE / 'CVPR_FutureIntent_Data/releases/formal_v1/F1'
RAW_ROOT = WORKSPACE / 'Robotwin2/datasets/formal_f1_full_v1'
TASK = 'formal_f1_full_20260910_v1'


def workspace_path(path):
    from portable_v2 import origin
    return origin(Path(path).absolute())


def sha(path):
    return hashlib.sha256(workspace_path(path).read_bytes()).hexdigest()


def write(path, value):
    path = workspace_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.partial')
    with temp.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def budget():
    from family_entry import get_call_budget
    calls=get_call_budget({'family':'F1'})
    counter_map={'fresh_scenes':'fresh','action_scenes':'action','collection_attempts':'collection','solver_problems':'solver_cap'}
    for counter,short in counter_map.items():
        if BASE[counter]!=3*sum(stage[short] for stage in calls['per_cohort_stages'].values()):
            raise ValueError('native call graph changed: regenerate the full budget')
        if ROOT_CAP[counter]!=calls['max_root_with_one_recovery_each_cohort'][short]:
            raise ValueError('native bounded recovery budget changed')
    # Real native call graph: 3 cohorts each (1 pristine + 3 geometry +
    # 1 prefix + 3 preflight + 3 collection). Recovery: 8 + missing per cohort.
    sections = {
        'ten_primary_normal': {k: 10*v for k, v in BASE.items()},
        'ten_primary_recovery_allowance': {k: 10*(ROOT_CAP[k]-BASE[k]) for k in COUNTERS},
        'four_reserve_normal': {k: 4*v for k, v in BASE.items()},
        'four_reserve_recovery_allowance': {k: 4*(ROOT_CAP[k]-BASE[k]) for k in COUNTERS},
    }
    return {'execution_authorized': False, 'allowed_physical_gpu_indices': list(range(8)),
            'native_call_graph':calls,
            'two_child_tight_bound_per_root':dict(zip(COUNTERS[:4],(42,26,10,256))),
            'two_child_tight_bound_all_fourteen':dict(zip(COUNTERS[:4],(588,364,140,3584))),
            'tight_bound_assumptions':['at most two actually launched children per root','first unaccepted cell stops that child','completed cohorts and accepted cells reused without execution','only one failed cohort repeats 8 fresh/4 action/64 solver preparation','no external qualification or third attempt'],
            'management_caps_are_conservative_not_predicted_consumption':True, 'sections': sections, 'total_caps': {k: sum(s[k] for s in sections.values()) for k in COUNTERS},
            'per_root_total_cap': ROOT_CAP, 'per_attempt_reservation_max': ATTEMPT,
            'max_gpu_attempts_per_root': 2, 'timeout_seconds': 6500,
            'cleanup_grace_seconds': 600, 'lease_overhead_seconds': 100,
            'lease_seconds_are_caps_not_measured_cost': True,
            'first_eighteen_included_in_ninety': True,
            'recovery_scenes_per_affected_cohort': {'fresh': '8 + missing_cells', 'action': '4 + missing_cells', 'collection': 'missing_cells', 'solver_cap': 64},
            'failed_primary_cost_preserved': True, 'gpu_copy_policy': 'release and settle before CPU-only copy',
            'fault_cleanup_included_in_each_attempt_700_seconds': True,
            'phase_reallocation_within_total_allowed': True,
            'cpu_io': {'max_cpu_finalizers': 2, 'max_copy_workers': 1, 'max_gpu_jobs': 8}}


def freeze_spec(spec):
    spec = copy.deepcopy(spec)
    # Agent-owned helper is required: no provisional fallback.
    from f1_disk_verifier import contract_for_f1
    spec['f1_verifier_contract'] = contract_for_f1(spec)
    spec['generator_version'] = scenes.VERSION
    spec['planned_slot_id'] = spec['root_id']
    spec['activation_receipt_hash'] = 'not_applicable'
    spec['original_primary_slot_id'] = spec['root_id']
    spec['candidate_presentation'] = {'model_order':'random_per_sample', 'audit_only_ids':True, 'programs':spec['programs']}
    spec['observation_hashes'] = {'current':None,'anchor':None,'canonical_prefix':None}
    spec['split_access_policy'] = 'No recipe tuning on validation/test; stop and record contamination if shared repair uses their outcomes'
    spec.pop('spec_sha256', None)
    spec['spec_sha256'] = scenes.hash_json(spec)
    scenes.validate_resolved(spec)
    return spec


def make_job(spec, directory, source, *, authorized=False, activation=None, raw_root=RAW_ROOT, copy_root=COPY_ROOT):
    directory = Path(directory)
    rid = spec['root_id']
    sp = directory / (rid + '.spec.json')
    ap = directory / (rid + '.authorization.json')
    write(sp, spec)
    auth = {'gpu_execution_authorized': authorized, 'spec_sha256': spec['spec_sha256'],
            'implementation_source_sha256': pins.native_implementation_hash(), 'source_files': source,
            'source_bundle_sha256': pins.bundle_hash(source),
            'job_limits': {'timeout_seconds': 6500, 'cleanup_grace_seconds': 600, 'gpu_reservation_seconds': 7200},
            'copy_destination': str(Path(copy_root)/rid), 'resume': False,
            'approval_status': 'APPROVED_FULL_F1' if authorized else 'PENDING_FULL_F1_USER_APPROVAL',
            'stage1_scientific_claim': False}
    write(ap, auth)
    job = {'job_id': 'full_' + rid, 'root_id': rid, 'spec_path': str(sp), 'spec_file_sha256': sha(sp),
           'authorization_path': str(ap), 'authorization_file_sha256': sha(ap), 'output': str(Path(raw_root)/rid),
           'reservation': ATTEMPT, 'root_budget_caps': ROOT_CAP,
           'timeout_seconds': 6500, 'cleanup_grace_seconds': 600, 'lease_overhead_seconds': 100}
    if activation:
        job['activation_receipt'] = activation
    return job


def prepare(directory):
    directory = workspace_path(directory)
    if (directory/'manifest.json').exists() and json.loads((directory/'manifest.json').read_text(encoding='utf-8')).get('execution_authorized') is True:
        raise PermissionError('never overwrite an approved package; use an explicit compatibility amendment')
    plan = scenes.generate()
    scenes.validate_plan(plan)
    write(directory/'PLANNED_SLOTS.json', plan)
    source = pins.inventory()
    primary = [s for s in plan['slots'] if s['family']=='F1' and s['reserve_rank'] is None]
    reserve = [s for s in plan['slots'] if s['family']=='F1' and s['reserve_rank'] is not None]
    jobs = [make_job(freeze_spec(scenes.resolve(s)), directory/'specs', source) for s in primary]
    matrix = []
    for s, j in zip(primary, jobs):
        spec = json.loads(Path(j['spec_path']).read_text(encoding='utf-8'))
        for p in spec['programs']:
            for r in spec['realizations']:
                matrix.append({'planned_slot_id': s['root_id'], 'root_id': s['root_id'], 'split':s['split'],
                               'difficulty':s['difficulty'], 'program_id':p['program_id'], 'realization_id':r,
                               'raw_root':j['output'], 'copy_root':str(COPY_ROOT/s['root_id']),
                               'status':'PLANNED_NOT_EXECUTED', 'actual_current_sha256':None,
                               'actual_anchor_sha256':None, 'actual_prefix_sha256':None})
    manifest = {'schema':'f1_full_production_v1', 'scope':'F1_FULL_PRODUCTION', 'family':'F1', 'task_id':TASK,
                'execution_authorized':False, 'cpu_copy_recovery_authorized':True,
                'allowed_physical_gpu_indices':list(range(8)), 'root_ids':[s['root_id'] for s in primary],
                'jobs':jobs, 'reserve_slots':reserve, 'planned_plan_path':str(directory/'PLANNED_SLOTS.json'),
                'planned_plan_sha256':scenes.hash_json(plan), 'planned_plan_file_sha256':sha(directory/'PLANNED_SLOTS.json'),
                'target_valid_roots':10, 'target_cells':90, 'budget_caps':budget()['total_caps'],
                'source_files':source, 'source_bundle_sha256':pins.bundle_hash(source),
                'max_concurrent_gpu_jobs':8, 'max_gpu_jobs':8, 'max_cpu_finalizers':2, 'max_copy_workers':1,
                'recovery_policy':{'max_gpu_attempts':2, 'allowed_failure_classes':['physical_infeasible','transient_execution'],
                                   'shared_error_policy':'STOP_NEW_DISPATCH', 'copy_only_does_not_consume_gpu_attempt':True},
                'reserve_job_template':{'reservation':ATTEMPT,'root_budget_caps':ROOT_CAP,'timeout_seconds':6500,'cleanup_grace_seconds':600,'lease_overhead_seconds':100},
                'first_wave_root_ids':[s['root_id'] for s in primary[:2]],
                'automatic_remaining_after_first_wave':True, 'next_family_automatic':False,
                'copy_family_root':str(COPY_ROOT), 'qualification_status':'PHYSICS_PENDING',
                'quota_status':'PERSONAL_QUOTA_UNKNOWN',
                'storage_policy':{'task_bytes_cap':256*2**30,'task_file_cap':50000,'dispatch_headroom_bytes':32*2**30,'minimum_shared_free_bytes':300*2**30}, 'approval':None}
    write(directory/'manifest.json', manifest)
    write(directory/'F1_BUDGET_REQUEST.json', budget())
    write(directory/'NINETY_CELL_PLAN.json', matrix)
    write(directory/'RESERVE_RULES.json', {'slots':reserve, 'activation':'scene_plan.activate_reserves',
        'order':'complete barrier then failed original-primary rank', 'specs':'generated only at activation',
        'inherit':['split','difficulty'], 'max_activations':4, 'extra_target_cells':0})
    return validate_package(manifest, require_authorized=False)


def validate_package(manifest, *, require_authorized=True, compatibility=None):
    if require_authorized and manifest.get('execution_authorized') is not True:
        raise PermissionError('F1 full-family execution requires one explicit approval; GPU remains disabled')
    if manifest.get('execution_authorized') is True and not manifest.get('test_only'):
        approval=manifest.get('approval',{}).get('record',{})
        if approval.get('decision')!='APPROVE_FULL_F1_90' or approval.get('budget_caps')!=manifest['budget_caps'] or not approval.get('user_instruction_reference'):
            raise PermissionError('missing whole-family approval record')
    if manifest.get('family')!='F1' or manifest.get('scope')!='F1_FULL_PRODUCTION':
        raise ValueError('this entry dispatches F1 only')
    expected = [f'F1_{i:06d}' for i in range(1,11)]
    if manifest['root_ids']!=expected or len(manifest['jobs'])!=10 or [j['job_id'] for j in manifest['jobs']]!=['full_'+r for r in expected]:
        raise ValueError('all ten primary roots are required')
    if manifest['budget_caps']!=budget()['total_caps'] or manifest['allowed_physical_gpu_indices']!=list(range(8)):
        raise ValueError('family budget or GPU contract changed')
    if (manifest['target_valid_roots'],manifest['target_cells'])!=(10,90) or manifest['next_family_automatic'] is not False:
        raise ValueError('completion or family boundary changed')
    if manifest.get('first_wave_root_ids')!=expected[:2] or manifest.get('automatic_remaining_after_first_wave') is not True:
        raise ValueError('first wave must be the two frozen train roots with automatic continuation')
    if any(manifest.get(k)!=v for k,v in {'max_concurrent_gpu_jobs':8,'max_gpu_jobs':8,'max_cpu_finalizers':2,'max_copy_workers':1}.items()):
        raise ValueError('concurrency contract changed')
    if len({j['output'] for j in manifest['jobs']})!=10:
        raise ValueError('duplicate raw output destination')
    pins.validate(compatibility or manifest)
    replacements={j['root_id']:j for j in (compatibility or {}).get('jobs',[])}
    plan_path = Path(manifest['planned_plan_path'])
    if sha(plan_path)!=manifest['planned_plan_file_sha256']:
        raise ValueError('planned slots file changed')
    plan=json.loads(plan_path.read_text(encoding='utf-8'))
    scenes.validate_plan(plan)
    if scenes.hash_json(plan)!=manifest['planned_plan_sha256']:
        raise ValueError('plan binding changed')
    if manifest.get('reserve_slots')!=[s for s in plan['slots'] if s['family']=='F1' and s['reserve_rank'] is not None]:
        raise ValueError('reserve slots changed')
    for slot, job in zip([s for s in plan['slots'] if s['family']=='F1' and s['reserve_rank'] is None],manifest['jobs']):
        if compatibility:
            if job['root_id'] not in replacements:raise ValueError('whole-family resume requires explicit compatibility review for every primary job')
            job=replacements[job['root_id']]
        if job['root_id']!=slot['root_id'] or sha(job['spec_path'])!=job['spec_file_sha256'] or sha(job['authorization_path'])!=job['authorization_file_sha256']:
            raise ValueError('job identity or file changed')
        spec=json.loads(Path(job['spec_path']).read_text(encoding='utf-8'))
        if spec!=freeze_spec(scenes.resolve(slot)):
            raise ValueError('resolved scene differs from frozen generator')
        workspace_path(job['output']);workspace_path(job['spec_path']);workspace_path(job['authorization_path'])
        auth=json.loads(Path(job['authorization_path']).read_text(encoding='utf-8'))
        expected_copy=workspace_path(manifest['copy_family_root'])/job['root_id']
        if workspace_path(auth['copy_destination'])!=expected_copy:
            raise ValueError('copy destination/root binding mismatch')
        if not manifest.get('test_only') and (Path(job['output'])!=RAW_ROOT/job['root_id'] or expected_copy!=COPY_ROOT/job['root_id']):
            raise ValueError('production paths changed')
        if job['root_budget_caps']!=ROOT_CAP or job['reservation']!=ATTEMPT:raise ValueError('root caps changed')
        pins.validate(auth)
        if auth['spec_sha256']!=spec['spec_sha256'] or auth['gpu_execution_authorized'] is not manifest['execution_authorized']:
            raise ValueError('child approval mismatch')
    return {'pass':True,'primary_roots':10,'reserve_slots':4,'planned_cells':90,'gpu_initialized':False,'execution_authorized':manifest['execution_authorized']}


def _state(path, manifest):
    if path.exists():
        value=json.loads(path.read_text(encoding='utf-8'))
        if value['manifest_sha256']!=scenes.hash_json(manifest):
            raise ValueError('family namespace belongs to another frozen manifest')
        return value
    return {'manifest_sha256':scenes.hash_json(manifest), 'task_id':manifest['task_id'],
            'status':'FIRST_WAVE', 'phase':'first', 'active_roots':manifest['first_wave_root_ids'],
            'accepted_by_primary':{}, 'terminal_history':[], 'activated_jobs':[], 'events':[],
            'next_family_dispatched':False}


def _origin(rid, activation):
    return next((r['primary_root_id'] for r in activation.get('records',[]) if r['reserve_root_id']==rid),rid)


def _activation_jobs(manifest, state_dir, activation, previous_jobs=(), source_override=None):
    jobs=[];previous={j['root_id']:j for j in previous_jobs}
    source=source_override or manifest['source_files']
    for record in activation['records']:
        if record['reserve_root_id'] in previous:
            jobs.append(previous[record['reserve_root_id']]);continue
        # Save an immutable proof, not a hash of the mutable activation ledger.
        directory=state_dir/'activations'/record['reserve_root_id']
        proof=directory/'reserve_activation_receipt.json'
        body={'plan_hash':activation['plan_hash'],'records':[record]}
        if proof.exists() and json.loads(proof.read_text(encoding='utf-8'))!=body:
            raise ValueError('reserve activation identity changed')
        write(proof,body)
        spec=freeze_spec(record['resolved_spec'])
        spec['activation_receipt_hash']=sha(proof)
        spec['original_primary_slot_id']=record['primary_root_id']
        spec.pop('spec_sha256');spec['spec_sha256']=scenes.hash_json(spec)
        jobs.append(make_job(spec,directory/('config_'+pins.bundle_hash(source)[:16]),source,authorized=manifest['execution_authorized'],
                             activation={'path':str(proof),'sha256':sha(proof)},raw_root=Path(manifest['jobs'][0]['output']).parent,copy_root=Path(manifest['copy_family_root'])))
    return jobs


def run(manifest, state_dir, *, backend=None, max_waves=None, compatibility_ref=None):
    """Continuous automatic 18→90. Only idle-card waiting yields to caller.

    Uses one immutable manifest and one launcher ledger for all waves/attempts.
    Backends may substitute GPU mechanics in CPU tests; acceptance still goes
    through launcher's independent completion and actual portable reader.
    """
    if manifest.get('execution_authorized') is not True:raise PermissionError('F1 full-family execution requires one explicit approval; GPU remains disabled')
    from first_wave_launcher import launch_wave,validate_compatibility,verify_completed_job
    state_dir=workspace_path(state_dir)
    initial_state=_state(state_dir/'FAMILY_STATE.json',manifest)
    compatibility=validate_compatibility(manifest,state_dir/'launcher',compatibility_ref,activated_jobs=initial_state['activated_jobs']) if compatibility_ref else None
    validate_package(manifest,compatibility=compatibility)
    state_dir=workspace_path(state_dir)
    if not state_dir.is_relative_to(WORKSPACE):raise ValueError('workspace-only state')
    state_dir.mkdir(parents=True,exist_ok=True)
    with (state_dir/'family_coordinator.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=state_dir/'FAMILY_STATE.json'
        state=_state(path,manifest)
        plan=json.loads(Path(manifest['planned_plan_path']).read_text(encoding='utf-8'))
        activation_path=state_dir/'reserve_activations.json'
        activation=json.loads(activation_path.read_text(encoding='utf-8')) if activation_path.exists() else {'records':[]}
        jobs={j['root_id']:j for j in manifest['jobs']+state['activated_jobs']}
        if compatibility:jobs.update({j['root_id']:j for j in compatibility['jobs']})
        if state['status'] in ('COMPLETE','READY_FAMILY_AUDIT'):
            state['family_audit']=publish_family(manifest,state,jobs,state_dir)
            state['status']='COMPLETE'
            write(path,state);return state
        waves=0
        while True:
            if max_waves is not None and waves>=max_waves:break
            active=state['active_roots']
            lpath=state_dir/'launcher/STATE.json'
            previous=json.loads(lpath.read_text(encoding='utf-8')) if lpath.exists() else {'jobs':{}}
            records=previous['jobs']
            ready=[];recover={};copy_only=[];terminals={};shared=[]
            for rid in active:
                job=jobs[rid];record=records.get(job['job_id'],{})
                status=record.get('status')
                if status=='PASS':terminals[rid]='PASSED'
                elif status in ('UNRESOLVED','SOURCE_CHANGED','BUDGET_OVERRUN','RUNNING'):
                    shared.append({'root_id':rid,'reason':status})
                elif status=='COPY_FAILED':
                    copy_only.append(job['job_id'])
                elif status=='FAILED':
                    classification=record.get('failure_class')
                    attempts=record.get('attempt_count',record.get('attempt',1))
                    proof=(compatibility or {}).get('job_proofs',{}).get(job['job_id'],{})
                    resolution=proof.get('receipt',{}).get('failure_resolution',{})
                    repaired=resolution.get('status')=='FIXED_CPU_VERIFIED' and resolution.get('failure_class')==classification
                    if classification not in manifest['recovery_policy']['allowed_failure_classes'] and not repaired:
                        shared.append({'root_id':rid,'reason':classification or 'unclassified_failure'})
                    elif attempts<2:
                        recover[job['job_id']]={'request_id':f'{job["job_id"]}:resume:{attempts+1}',
                            'failure_class':classification,'mode':'resume'}
                        ready.append(job['job_id'])
                    else:terminals[rid]='FAILED'
                else:ready.append(job['job_id'])
            if shared:
                state.update(status='STOPPED_SHARED_OR_UNRESOLVED',blocking=shared);write(path,state);return state
            if len(terminals)==len(active):
                for rid,status in terminals.items():
                    if status=='PASSED':
                        verify_completed_job(jobs[rid],allow_synthetic=manifest.get('test_only') is True)
                        record=records[jobs[rid]['job_id']]
                        if not record.get('owned_cleanup_pass') or not record.get('release_confirmed'):
                            raise ValueError('root terminal missing owned cleanup/release')
                for rid, result in terminals.items():
                    if result=='PASSED':state['accepted_by_primary'][_origin(rid,activation)]=rid
                try:
                    activation=scenes.activate_reserves(plan,activation_path,terminals,wave=state['phase'])
                except ValueError as exc:
                    if 'reserve exhausted' not in str(exc):raise
                    state.update(status='FORMAL_DATASET_INCOMPLETE',blocking=[{'reason':'four ordered reserves exhausted'}])
                    write(path,state);return state
                state['terminal_history'].append({'phase':state['phase'],'terminals':terminals})
                prior_jobs=[jobs[j['root_id']] for j in state['activated_jobs']]
                state['activated_jobs']=_activation_jobs(manifest,state_dir,activation,prior_jobs,compatibility['source_files'] if compatibility else None)
                jobs.update({j['root_id']:j for j in state['activated_jobs']})
                replacements=activation['barriers'][-1]['replacement_ids']
                if replacements:
                    state['active_roots']=replacements
                elif state['phase']=='first':
                    if set(state['accepted_by_primary'])!=set(manifest['first_wave_root_ids']):raise ValueError('first-wave acceptance mismatch')
                    state['events'].append({'event':'FIRST_18_AUTOMATIC_GATE_PASSED','new_approval_required':False})
                    state.update(phase='remaining',status='REMAINING',active_roots=manifest['root_ids'][2:])
                else:
                    state.update(status='READY_FAMILY_AUDIT',active_roots=[])
                    write(path,state)
                    result=publish_family(manifest,state,jobs,state_dir)
                    state.update(status='COMPLETE',family_audit=result)
                    write(path,state);return state
                write(path,state);continue
            # Conservative first-root initial gate: no second root before any
            # independently completed first cell. Sequential completion is valid
            # when only one ready/idle card; later waves use configured parallelism.
            if state['phase']=='first' and len(active)==2:
                first=jobs[active[0]]
                if active[0] not in terminals:
                    ready=[j for j in ready if j==first['job_id']]
                    recover={k:v for k,v in recover.items() if k in ready}
            write(path,state)
            write(state_dir/'storage_pre_dispatch.json',check_storage(manifest,state['activated_jobs']))
            result=launch_wave(manifest,state_dir/'launcher',backend=backend,ready_job_ids=ready,
                               recovery_requests=recover,copy_only_job_ids=copy_only,activated_jobs=state['activated_jobs'],compatibility_ref=compatibility_ref)
            waves+=1
            if not result.get('results'):
                state['status']='WAITING_IDLE_OR_READY';write(path,state);return state
        write(path,state);return state


def check_storage(manifest, activated_jobs=()):
    """Bounded accounting of owned destinations; df is not a quota guarantee."""
    directories=[]
    for job in manifest['jobs']+list(activated_jobs):
        directories.append(Path(job['output']))
        auth=json.loads(Path(job['authorization_path']).read_text(encoding='utf-8'))
        destination=Path(auth['copy_destination'])
        directories.append(destination)
        directories.append(destination.with_name(destination.name+'_cells'))
        directories.extend(destination.parent.glob('.'+destination.name+'.staging-*'))
    count=total=0
    for directory in set(directories):
        directory=workspace_path(directory)
        if directory.is_symlink():raise ValueError('storage symlink')
        if not directory.exists():continue
        for parent, dirs, files in os.walk(directory,followlinks=False):
            for name in dirs+files:
                if (Path(parent)/name).is_symlink():raise ValueError('storage contains symlink')
            for name in files:
                count+=1;total+=(Path(parent)/name).stat().st_size
    policy=manifest['storage_policy'];fs=os.statvfs(WORKSPACE)
    available=fs.f_bavail*fs.f_frsize
    if total+policy['dispatch_headroom_bytes']>policy['task_bytes_cap'] or count>policy['task_file_cap']:
        raise RuntimeError('task storage cap/headroom reached; preserve raw and stop new dispatch')
    if available<policy['minimum_shared_free_bytes']:
        raise RuntimeError('shared volume free space below dispatch floor')
    return {'owned_published_bytes':total,'owned_published_files':count,'shared_available_bytes':available,
            'personal_quota_confirmed':False,'active_staging_headroom_reserved_bytes':policy['dispatch_headroom_bytes'],
            'policy':policy,'pass':True}


def publish_family(manifest,state,jobs,state_dir):
    from first_wave_launcher import verify_completed_job
    from portable_v2 import read, safe
    selected=state['accepted_by_primary']
    if set(selected)!=set(manifest['root_ids']) or len(set(selected.values()))!=10:
        raise ValueError('ten distinct replacements for ten planned slots required')
    ledger_state=json.loads((Path(state_dir)/'launcher/STATE.json').read_text(encoding='utf-8'))
    if ledger_state.get('status') in ('UNRESOLVED','BUDGET_OVERRUN','SOURCE_CHANGED'):
        raise ValueError('unresolved family resources/source prevent publication')
    rows=[];roots=[]
    for primary in manifest['root_ids']:
        rid=selected[primary];job=jobs[rid]
        record=ledger_state['jobs'].get(job['job_id'],{})
        if record.get('status')!='PASS' or not record.get('owned_cleanup_pass') or not record.get('release_confirmed') or not record.get('attempts') or any(a.get('settled') is not True for a in record['attempts']):
            raise ValueError('selected root lacks settled PASS/owned cleanup/release')
        completion=verify_completed_job(job,allow_synthetic=manifest.get('test_only') is True)
        if completion.get('pass') is not True:raise ValueError('independent root completion failed')
        spec=json.loads(Path(job['spec_path']).read_text(encoding='utf-8'))
        primary_job=next(j for j in manifest['jobs'] if j['root_id']==primary)
        primary_spec=json.loads(Path(primary_job['spec_path']).read_text(encoding='utf-8'))
        if (spec['split'],spec['difficulty'])!=(primary_spec['split'],primary_spec['difficulty']):raise ValueError('selected root changed original slot split/difficulty')
        if rid!=primary:
            binding=job.get('activation_receipt',{})
            if not binding or sha(binding['path'])!=binding['sha256']:raise ValueError('replacement missing immutable activation proof')
            proof=json.loads(workspace_path(binding['path']).read_text(encoding='utf-8'))
            match=[r for r in proof.get('records',[]) if r.get('reserve_root_id')==rid and r.get('primary_root_id')==primary]
            if proof.get('plan_hash')!=manifest['planned_plan_sha256'] or len(match)!=1 or spec.get('activation_receipt_hash')!=binding['sha256'] or spec.get('original_primary_slot_id')!=primary:raise ValueError('replacement belongs to another original primary slot')
        destination=Path(json.loads(Path(job['authorization_path']).read_text(encoding='utf-8'))['copy_destination'])
        group=json.loads((destination/'root_manifest.json').read_text(encoding='utf-8'))
        for relative in group['relative_cell_paths']:
            payload=read(safe(destination,relative));audit=payload['audit']
            rows.append({'planned_slot_id':primary,'root_id':rid,'split':spec['split'],'difficulty':spec['difficulty'],
                         'cell_key':audit['cell_key'],'relative_path':str(Path(rid)/relative),
                         'cell_manifest_sha256':sha(safe(destination,relative)/'portable_manifest.json')})
        roots.append({'planned_slot_id':primary,'root_id':rid,'split':spec['split'],'difficulty':spec['difficulty'],
                      'root_manifest_sha256':sha(destination/'root_manifest.json'),'copied_cells':9,
                      'execution_authorization_source_bundle_sha256':json.loads(Path(job['authorization_path']).read_text(encoding='utf-8'))['source_bundle_sha256'],
                      'source_compatibility_receipt':json.loads(Path(job['authorization_path']).read_text(encoding='utf-8')).get('source_compatibility_receipt'),
                      'original_capture_sources':'preserved per cell; may predate explicitly reviewed source-only amendment'})
    if len(rows)!=90 or len({r['cell_key'] for r in rows})!=90:raise ValueError('ninety unique cells required')
    from collections import Counter
    if Counter((r['split'],r['difficulty']) for r in roots)!=Counter(scenes.SPLITS):raise ValueError('split/difficulty inheritance mismatch')
    from controlled_multi_future.redesign_f2_f3_v2.execution_ledger_v2 import ExecutionLedgerV2
    ledger=ExecutionLedgerV2(Path(state_dir)/'launcher/execution_ledger.jsonl',contract_sha256=scenes.hash_json(manifest),task_id=manifest['task_id'],caps=manifest['budget_caps']).totals()
    if any(ledger['consumed'][k]>manifest['budget_caps'][k] for k in COUNTERS):raise ValueError('family budget overrun')
    if any(ledger['reserved'].values()):raise ValueError('unsettled reservations prevent family completion')
    result={'family':'F1','status':'COMPLETE','roots':roots,'cells':90,'contract_source_bundle_sha256':manifest['source_bundle_sha256'],
            'budget':ledger,'terminal_history':state['terminal_history'],'next_family_dispatched':False,
            'attempt_history':[{ 'job_id':jid,'root_id':record.get('root_id'),'status':record.get('status'),'failure_class':record.get('failure_class'),
                'attempts':[{k:a.get(k) for k in ('attempt','ledger_job_id','child_launched','actual','settled','owned_cleanup_pass','release_confirmed','source_bundle_sha256')} for a in record.get('attempts',[])]} for jid,record in sorted(ledger_state['jobs'].items())],
            'synthetic':manifest.get('test_only') is True,'research_eligible':False,'stage1_scientific_claim':False,'copy_type':'independent files on same NFS; not offsite backup'}
    destination=Path(manifest['copy_family_root'])
    destination.mkdir(parents=True,exist_ok=True)
    output=io.StringIO();writer=csv.DictWriter(output,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    temporary=destination/'dataset_index.csv.partial';temporary.write_text(output.getvalue());os.replace(temporary,destination/'dataset_index.csv')
    result['dataset_index_sha256']=sha(destination/'dataset_index.csv')
    write(destination/'FAMILY_MANIFEST.json',result)
    return result


def seal_approved_package(proposal_dir, destination, approval_path):
    """Future explicit authorization operation; never invoked during preparation.

    Preserve the false proposal and bind a new approval record/config snapshot.
    The human approval record must name this exact proposal and the full cap.
    """
    proposal_dir=Path(proposal_dir);destination=Path(destination);approval_path=Path(approval_path)
    proposal=json.loads((proposal_dir/'manifest.json').read_text(encoding='utf-8'))
    validate_package(proposal,require_authorized=False)
    approval=json.loads(approval_path.read_text(encoding='utf-8'))
    if approval.get('decision')!='APPROVE_FULL_F1_90' or approval.get('proposal_manifest_sha256')!=sha(proposal_dir/'manifest.json'):
        raise PermissionError('explicit approval must bind the complete F1 proposal')
    if approval.get('budget_caps')!=proposal['budget_caps'] or not approval.get('user_instruction_reference'):
        raise PermissionError('full budget and user instruction reference required')
    if destination.exists():raise FileExistsError('approval snapshot destination must be new')
    prepare(destination)
    manifest=json.loads((destination/'manifest.json').read_text(encoding='utf-8'))
    manifest['execution_authorized']=True
    manifest['approval']={'record':approval,'record_file_sha256':sha(approval_path)}
    for job in manifest['jobs']:
        ap=Path(job['authorization_path']);auth=json.loads(ap.read_text(encoding='utf-8'))
        auth.update(gpu_execution_authorized=True,approval_status='APPROVED_FULL_F1',approval=manifest['approval'])
        write(ap,auth);job['authorization_file_sha256']=sha(ap)
    write(destination/'manifest.json',manifest)
    return validate_package(manifest)


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['prepare','preflight','run','seal-approval'])
    p.add_argument('--package',type=Path,default=HERE/'F1_FULL_PRODUCTION')
    p.add_argument('--state-dir',type=Path,default=WORKSPACE/'Robotwin2/datasets/formal_f1_full_v1_state')
    p.add_argument('--approval-file',type=Path);p.add_argument('--approved-destination',type=Path)
    p.add_argument('--compatibility-file',type=Path)
    a=p.parse_args(argv)
    if a.command=='seal-approval':
        if not a.approval_file or not a.approved_destination:p.error('approval file and new destination required')
        result=seal_approved_package(a.package,a.approved_destination,a.approval_file)
    elif a.command=='prepare':result=prepare(a.package)
    else:
        manifest=json.loads((a.package/'manifest.json').read_text(encoding='utf-8'))
        result=validate_package(manifest,require_authorized=False) if a.command=='preflight' else run(manifest,a.state_dir,compatibility_ref={'path':str(a.compatibility_file.absolute()),'sha256':sha(a.compatibility_file)} if a.compatibility_file else None)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':main()
