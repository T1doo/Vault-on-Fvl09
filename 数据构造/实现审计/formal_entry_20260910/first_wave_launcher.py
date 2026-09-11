"""Thin first-wave launcher over existing GPU Guard and ExecutionLedgerV2.

CPU coordinator; no CUDA/SAPIEN imports. Current unsigned/false manifests never
reach even the GPU snapshot. Use only from an explicitly authorized host context.
"""
import argparse,concurrent.futures,fcntl,hashlib,json,math,os,signal,subprocess,threading,time
from pathlib import Path
from file_source_pin import validate as validate_sources
from scene_plan import validate_resolved,hash_json
from family_entry import write
ROOT=Path('/nfs_share/lijunhui');HERE=Path(__file__).resolve().parent
PROJECT=ROOT/'Robotwin2/project/RoboTwin';PYTHON=ROOT/'Robotwin2/env/bin/python'
COUNTERS=('fresh_scenes','action_scenes','collection_attempts','solver_problems','gpu_lease_seconds')


def usage_from_receipts(output,lease_seconds):
    output=Path(output);receipts=[]
    for realization in ('r_pc','r_inv_path','r_inv_motion'):
        base=output/realization
        receipts += list(base.glob('root/root_receipt.json'))+list(base.glob('recovery_*/root/root_receipt.json'))
    pointers=list(output.glob('r_*/cohort_pointer.json'))
    for pointer in pointers:
        p=json.loads(pointer.read_text(encoding='utf-8'))
        if p.get('status')=='STARTED' or not (pointer.parent/p['root_relative']/'root_receipt.json').exists():
            raise RuntimeError('started cohort missing terminal receipt; usage unresolved')
    if not receipts:
        if pointers or list(output.glob('**/root_events.jsonl')):
            raise RuntimeError('native execution may have started; usage unresolved')
        return {**{k:0 for k in COUNTERS},'gpu_lease_seconds':int(lease_seconds)}
    totals={k:0 for k in COUNTERS};totals['gpu_lease_seconds']=int(lease_seconds)
    for path in receipts:
        r=json.loads(path.read_text(encoding='utf-8'));cleanup=r['cleanup_records']
        if not r.get('status') or r['status']=='running':raise RuntimeError('nonterminal root usage')
        totals['fresh_scenes']+=sum(c.get('scene_created') is True for c in cleanup)
        totals['action_scenes']+=sum(int(r[k]) for k in ('canonical_prefix_reference_execution_count','suffix_prefix_replay_count','branch_prefix_replay_count'))
        if any(type(c.get('scene_created')) is not bool or not isinstance(c.get('phase'),str) or not c['phase'] for c in cleanup):
            raise RuntimeError('cleanup scene/phase evidence missing; collection usage unresolved')
        totals['collection_attempts']+=sum(c['scene_created'] and c['phase'].startswith('strict_prefix_branch:') for c in cleanup)
        totals['solver_problems']+=int(r['planner_query_count_total'])
    return totals


class HostBackend:
    """Uses existing shared physical-GPU leases; all process actions are owned."""
    def snapshot(self):
        from controlled_multi_future.redesign_f2_f3_v2.gpu import live_snapshot
        import types
        class TimedSubprocess:
            def __getattr__(self,name):return getattr(subprocess,name)
            def run(self,*args,**kwargs):
                kwargs.setdefault('timeout',10);return subprocess.run(*args,**kwargs)
        namespace=dict(live_snapshot.__globals__);namespace['subprocess']=TimedSubprocess()
        return types.FunctionType(live_snapshot.__code__,namespace)()
    def acquire(self,index,gpu_uuid):
        from controlled_multi_future.probes.gpu_guard_v2_4 import acquire_physical_gpu_lease
        lease=acquire_physical_gpu_lease(index)
        try:
            if not gpu_uuid.startswith('GPU-') or any(not(c.isalnum() or c=='-') for c in gpu_uuid):raise ValueError('invalid UUID')
            uuid_path=Path(lease['lease_path']).parent/('uuid_'+gpu_uuid+'.lock')
            fd=os.open(uuid_path,os.O_CREAT|os.O_RDWR,0o600)
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BaseException:os.close(fd);raise
            lease['_uuid_fd']=fd;lease['uuid_lease_path']=str(uuid_path);return lease
        except BaseException:
            from controlled_multi_future.probes.gpu_guard_v2_4 import release_physical_gpu_lease
            release_physical_gpu_lease(lease);raise
    def release(self,lease):
        from controlled_multi_future.probes.gpu_guard_v2_4 import release_physical_gpu_lease
        if '_uuid_fd' in lease:
            fcntl.flock(lease['_uuid_fd'],fcntl.LOCK_UN);os.close(lease['_uuid_fd'])
        return release_physical_gpu_lease(lease)
    def run(self,job,card,receipt_dir):
        """Always reap owned children, even when diagnostic persistence raises."""
        started=time.monotonic();wall=time.time();process=None;owned={};timed_out=False;error=None;remaining={};persistence_errors=[]
        receipt_dir=Path(receipt_dir)
        def persist(name,value):
            try:evidence(receipt_dir/name,value)
            except BaseException as exc:persistence_errors.append({'file':name,'type':type(exc).__name__,'message':str(exc)})
        def processes():
            raw=subprocess.run(['ps','-u',str(os.getuid()),'-o','pid=,ppid=,pgid=,lstart=,comm='],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=10).stdout
            found={}
            for line in raw.splitlines():
                parts=line.split(None,8)
                if len(parts)==9:found[int(parts[0])]={'pid':int(parts[0]),'ppid':int(parts[1]),'pgid':int(parts[2]),'start':' '.join(parts[3:8]),'comm':parts[8]}
            return found
        def observe():
            if process is None:return {}
            found=processes();ids={process.pid}|set(owned);changed=True
            while changed:
                more={pid for pid,p in found.items() if p['ppid'] in ids or p['pgid']==process.pid};changed=not more<=ids;ids|=more
            for pid in ids & found.keys():
                if pid not in owned:owned[pid]=found[pid]
            return {pid:p for pid,p in found.items() if pid in owned and p['start']==owned[pid]['start']}
        def terminate_owned(signum):
            if process is None:return
            for pid in observe():
                try:os.kill(pid,signum)
                except ProcessLookupError:pass
        try:
            from controlled_multi_future.redesign_f2_f3_v2.gpu import child_environment
            env=child_environment(card['gpu_uuid']);env['PATH']=str(PYTHON.parent)+os.pathsep+str(ROOT/'Robotwin2/tools/cuda-12.1/bin')+os.pathsep+env.get('PATH','');cache=receipt_dir/'child_cache';cache.mkdir()
            for name in ('TMPDIR','XDG_CACHE_HOME','TORCH_EXTENSIONS_DIR','TRITON_CACHE_DIR','CUDA_CACHE_PATH','MPLCONFIGDIR'):
                path=cache/name.lower();path.mkdir();env[name]=str(path)
            env.update(PYTHONPATH=str(PROJECT)+os.pathsep+str(HERE),PYTHONDONTWRITEBYTECODE='1',ROBOTWIN_ROOT=str(PROJECT),ROBOTWIN_WORKSPACE=str(ROOT/'Robotwin2'),CMF_GPU_GUARD_PHYSICAL_INDEX=str(card['physical_index']))
            command=[str(PYTHON),str(HERE/'execution_cli.py'),'--spec',job['spec_path'],'--authorization',job['authorization_path'],'--output',job['output'],'--collect-only']
            if job.get('launch_mode')=='resume':command.append('--resume')
            with (receipt_dir/'stdout.log').open('w') as stream:
                process=subprocess.Popen(command,cwd=PROJECT,env=env,start_new_session=True,stdout=stream,stderr=subprocess.STDOUT)
                observe();persist('process_start.json',{'pid':process.pid,'ppid':os.getpid(),'pgid':process.pid,'started_wall':wall,'started_monotonic':started,'command':command,'owned':list(owned.values())})
                if persistence_errors:raise RuntimeError('process ownership evidence could not be persisted')
                while process.poll() is None:
                    observe()
                    if time.monotonic()-started>=job['timeout_seconds']:timed_out=True;break
                    time.sleep(.2)
        except BaseException as exc:error={'type':type(exc).__name__,'message':str(exc)}
        finally:
            persist('child_end.json',{'ended_wall':time.time(),'ended_monotonic':time.monotonic(),'returncode':process.poll() if process else None,'timeout':timed_out,'error':error,'owned':list(owned.values())})
            # Persistence failure above never short-circuits owned process cleanup.
            if process is not None:
                try:
                    if observe():terminate_owned(signal.SIGTERM)
                    deadline=time.monotonic()+job['cleanup_grace_seconds']
                    while observe() and time.monotonic()<deadline:
                        process.poll();time.sleep(.1)
                    if observe():terminate_owned(signal.SIGKILL)
                    process.wait(timeout=1);remaining=observe()
                except BaseException as exc:
                    remaining={'unknown':{'type':type(exc).__name__,'message':str(exc)}}
                    # Popen belongs to us even if host enumeration itself failed.
                    try:
                        if process.poll() is None:process.kill()
                        process.wait(timeout=1)
                    except BaseException as root_exc:remaining['root_reap_error']=str(root_exc)
        result={'pid':process.pid if process else None,'returncode':process.returncode if process else None,'timeout':timed_out,'error':error,'started_wall':wall,'ended_wall':time.time(),'lease_seconds':math.ceil(time.monotonic()-started),'owned_process_tree':list(owned.values()),'owned_cleanup_pass':not remaining and (process is None or process.returncode is not None),'remaining_owned':remaining,'host_process_visibility':not remaining,'launched':process is not None,'persistence_errors':persistence_errors}
        persist('process_cleanup.json',result)
        return result


def read_bound_job_configs(job):
    values=[]
    for path_key,hash_key in (('spec_path','spec_file_sha256'),('authorization_path','authorization_file_sha256')):
        raw=Path(job[path_key]).read_bytes()
        if not isinstance(job.get(hash_key),str) or hashlib.sha256(raw).hexdigest()!=job[hash_key]:
            raise ValueError('frozen job config bytes changed: '+path_key)
        values.append(json.loads(raw))
    return tuple(values)


def verify_completed_job(job, *, allow_synthetic=False):
    """Re-read independent root result and every copied package; exit 0 is insufficient."""
    import portable_v2
    output=Path(job['output']);spec,authorization=read_bound_job_configs(job)
    result=json.loads((output/'execution_result.json').read_text(encoding='utf-8'))
    independent=json.loads((output/'independent_structure.json').read_text(encoding='utf-8'))
    if result.get('pass') is not True or independent.get('pass') is not True:raise ValueError('independent acceptance absent/failed')
    if allow_synthetic:
        if independent.get('research_eligible') is not False or independent.get('native_physical_evidence') is not False:raise ValueError('fixture must remain nonphysical and ineligible')
    elif independent.get('research_eligible') is not True or independent.get('native_physical_evidence') is not True:raise ValueError('native independent acceptance absent/failed')
    if independent.get('root_id')!=job['root_id'] or result.get('root_id')!=job['root_id'] or len(independent.get('cells',[]))!=9:
        raise ValueError('independent root identity/matrix mismatch')
    if {k:v for k,v in result.items() if k!='copy'}!=independent:raise ValueError('execution result differs from independent root evidence')
    destination=portable_v2.origin(authorization['copy_destination']);portable_v2.read_root(destination);copied=json.loads((destination/'root_manifest.json').read_text(encoding='utf-8'))
    registry=json.loads((destination.parent/'registry.json').read_text(encoding='utf-8'))
    if copied!=result.get('copy') or registry.get(str(destination))!=copied or copied.get('synthetic') is not bool(allow_synthetic):
        raise ValueError('copy/registry binding mismatch')
    expected={f"{spec['root_id']}:{p['program_id']}:{r}" for p in spec['programs'] for r in spec['realizations']};observed=set()
    for relative in copied.get('relative_cell_paths',[]):
        payload=portable_v2.read(portable_v2.safe(destination,relative));m=payload['audit'];observed.add(m['cell_key'])
        if m['root_id']!=job['root_id'] or m['scene_spec_sha256']!=spec['spec_sha256'] or bool(m.get('synthetic'))!=bool(allow_synthetic):raise ValueError('copied cell identity/source mismatch')
        if copied['cells'].get(m['cell_key'])!=m['spec_sha256']:raise ValueError('copied nested version mismatch')
    if observed!=expected or len(copied['relative_cell_paths'])!=9:raise ValueError('copied root incomplete')
    return {'pass':True,'root_id':job['root_id'],'copied_cells':9,'original_path_fallback':False,'synthetic':bool(allow_synthetic),'research_eligible':not allow_synthetic}


def validate_compatibility(manifest,state_dir,reference,activated_jobs=None):
    """Explicit source-only amendment; original manifest and budget contract stay fixed.

    The appendix binds reviewed changed files plus separately hashed per-root
    proofs and replacement job files. No science spec or budget mutation occurs.
    """
    from copy import deepcopy
    from file_source_pin import bundle_hash
    raw=_workspace_path(reference['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=reference['sha256']:raise ValueError('compatibility appendix bytes changed')
    appendix=json.loads(raw)
    if appendix.get('schema')!='f1_runtime_compatibility_appendix_v1' or appendix.get('status')!='CPU_REVIEWED_APPLICABLE' or appendix.get('manifest_sha256')!=hash_json(manifest):raise ValueError('compatibility contract mismatch')
    validate_sources(appendix)
    old=manifest['source_files'];new=appendix['source_files'];changed=sorted(k for k in set(old)|set(new) if old.get(k)!=new.get(k))
    if not changed or appendix.get('changed_files')!=changed or appendix.get('old_source_bundle_sha256')!=manifest['source_bundle_sha256']:raise ValueError('compatibility change inventory mismatch')
    assessments=appendix.get('affected_contracts',{})
    if set(assessments)!=set(changed) or any(not isinstance(x,str) or not x.strip() for x in assessments.values()):raise ValueError('each actual source change needs reviewed contract impact')
    state_path=Path(state_dir)/'STATE.json';state=json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {'jobs':{}}
    if state_path.exists() and (state.get('contract_sha256')!=hash_json(manifest) or state.get('task_id')!=manifest['task_id']):raise ValueError('compatibility belongs to a different task/ledger')
    extras=list(activated_jobs or [])
    for record in state.get('jobs',{}).values():
        bound=record.get('bound_job')
        if bound and bound.get('activation_receipt') and not any(j['job_id']==bound['job_id'] for j in extras):extras.append(bound)
    for job in extras:_validate_activation(manifest,job)
    base={j['job_id']:j for j in manifest['jobs']+extras};replacements=appendix.get('jobs',[])
    if len({j['job_id'] for j in replacements})!=len(replacements) or not set(j['job_id'] for j in replacements)<=set(base):raise ValueError('compatibility job scope')
    proofs={}
    for replacement in replacements:
        jid=replacement['job_id'];original=base[jid]
        for key in ['job_id','root_id','output','reservation','root_budget_caps','timeout_seconds','cleanup_grace_seconds','lease_overhead_seconds']:
            if original.get(key)!=replacement.get(key):raise ValueError('compatibility cannot expand job or budget')
        prior_spec,prior_auth=read_bound_job_configs(original);spec,auth=read_bound_job_configs(replacement)
        if spec!=prior_spec:raise ValueError('source-only compatibility cannot modify scientific spec')
        validate_sources(auth)
        if auth['source_bundle_sha256']!=appendix['source_bundle_sha256'] or auth.get('copy_destination')!=prior_auth.get('copy_destination') or auth.get('gpu_execution_authorized')!=prior_auth.get('gpu_execution_authorized'):raise ValueError('compatibility child scope changed')
        binding=auth.get('source_compatibility_receipt',{});proof_raw=_workspace_path(binding['path']).read_bytes()
        if hashlib.sha256(proof_raw).hexdigest()!=binding['sha256']:raise ValueError('root compatibility proof changed')
        proof=json.loads(proof_raw)
        required={'schema':'f1_source_compatibility_v1','status':'CPU_REVIEWED_APPLICABLE','root_id':spec['root_id'],'spec_sha256':spec['spec_sha256'],'old_source_sha256':prior_auth['implementation_source_sha256'],'new_source_sha256':auth['implementation_source_sha256'],'old_source_bundle_sha256':prior_auth['source_bundle_sha256'],'new_source_bundle_sha256':appendix['source_bundle_sha256'],'scientific_contract_unchanged':True,'changed_files':changed,'affected_contracts':assessments}
        if any(proof.get(k)!=v for k,v in required.items()):raise ValueError('root source compatibility fields mismatch')
        prior=state.get('jobs',{}).get(jid,{})
        resolution=proof.get('failure_resolution')
        if resolution is not None:
            if resolution.get('failure_class')!=prior.get('failure_class') or resolution.get('status')!='FIXED_CPU_VERIFIED' or not resolution.get('evidence_files'):raise ValueError('failure resolution not applicable')
            for evidence_ref in resolution['evidence_files']:
                evidence_bytes=_workspace_path(evidence_ref['path']).read_bytes()
                if hashlib.sha256(evidence_bytes).hexdigest()!=evidence_ref['sha256']:raise ValueError('failure resolution evidence changed')
                regression=json.loads(evidence_bytes)
                if regression.get('pass')is not True or regression.get('source_bundle_sha256')!=appendix['source_bundle_sha256']:raise ValueError('failure fix regression not bound to new source')
        preserved=prior.get('accepted_file_hashes',{})
        for path,sha in preserved.items():
            if hashlib.sha256(_workspace_path(path).read_bytes()).hexdigest()!=sha:raise ValueError('accepted source was changed before compatibility review')
        actual_receipts=list(Path(original['output']).glob('**/branches/*/receipt.json'))
        accepted=[]
        for receipt in actual_receipts:
            if json.loads(receipt.read_text(encoding='utf-8')).get('status')!='accepted':continue
            realization=next((p.name for p in receipt.parents if p.name in ('r_pc','r_inv_path','r_inv_motion')),None)
            if realization is None:raise ValueError('saved accepted cell has no realization lineage')
            rawpath=receipt.parent/'raw/raw_streams.npz';mp=rawpath.parent/'manifest.json';meta=json.loads(mp.read_text(encoding='utf-8'));cp=_workspace_path(meta['provenance']['formal_current_capture_path'])
            row={'program_id':receipt.parent.name,'realization_id':realization,'raw_path':str(rawpath),'raw_sha256':hashlib.sha256(rawpath.read_bytes()).hexdigest(),'manifest_path':str(mp),'manifest_sha256':hashlib.sha256(mp.read_bytes()).hexdigest(),'capture_path':str(cp),'capture_sha256':hashlib.sha256(cp.read_bytes()).hexdigest()}
            if row not in proof.get('accepted_cells',[]):raise ValueError('accepted cell missing from explicit compatibility proof')
            from family_entry import finalize_native_cell
            check=finalize_native_cell(spec=spec,output=Path(original['output']),program_id=row['program_id'],realization=realization,write_receipt=False)
            if check.get('pass')is not True:raise ValueError('new implementation rejects preserved cell')
            accepted.append(row)
        if len(accepted)!=len(proof.get('accepted_cells',[])):raise ValueError('compatibility proof has unrelated cells')
        proofs[jid]={'receipt':proof,'binding':binding};base[jid]=replacement
    return {'source_files':new,'source_bundle_sha256':bundle_hash(new),'jobs':list(base.values()),'applicable_job_ids':sorted(proofs),'job_proofs':proofs,'appendix_binding':reference}


def _workspace_path(value):
    path=Path(value)
    if not path.is_absolute() or not path.resolve().is_relative_to(ROOT) or any(x.is_symlink() for x in [path,*path.parents] if x.is_relative_to(ROOT)):
        raise ValueError('unsafe workspace path')
    return path


def _validate_activation(manifest,job):
    proof=job.get('activation_receipt')
    if not isinstance(proof,dict) or set(proof)!={'path','sha256'}:raise ValueError('activated job requires bound reserve receipt')
    raw=_workspace_path(proof['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=proof['sha256']:raise ValueError('activation bytes changed')
    value=json.loads(raw)
    if value.get('plan_hash')!=manifest.get('planned_plan_sha256') or not value.get('plan_hash'):raise ValueError('activation plan mismatch')
    records=value.get('records',[value.get('record',{})]);matches=[r for r in records if r.get('reserve_root_id')==job['root_id']]
    if len(matches)!=1:raise ValueError('reserve activation must identify one unique root')
    record=matches[0];spec,_=read_bound_job_configs(job)
    base=record.get('resolved_spec',{})
    if not base or any(spec.get(k)!=v for k,v in base.items() if k!='spec_sha256') or record.get('failed_terminal')!='FAILED':raise ValueError('activation resolved science mismatch')
    from f1_disk_verifier import contract_for_f1
    if spec.get('f1_verifier_contract')!=contract_for_f1(spec):raise ValueError('reserve formal verifier contract mismatch')
    if record.get('primary_root_id',record.get('failed_root_id')) not in manifest['root_ids']:raise ValueError('reserve missing primary lineage')
    allowed={s['root_id'] for s in manifest.get('reserve_slots',[])}
    if job['root_id'] not in allowed:raise ValueError('reserve is not in frozen slot set')
    if spec['split']!=record['split'] or spec['difficulty']!=record['difficulty']:raise ValueError('reserve inheritance mismatch')


def validate_manifest(manifest,activated_jobs=None,*,copy_only=False,inactive_job_ids=()):
    if copy_only:
        if manifest.get('cpu_copy_recovery_authorized') is not True:raise PermissionError('CPU copy recovery is not authorized')
    elif manifest.get('execution_authorized') is not True:raise PermissionError('GPU execution has not been authorized')
    if manifest.get('allowed_physical_gpu_indices')!=list(range(8)):raise ValueError('GPU0-7 contract required')
    full=manifest.get('scope')=='F1_FULL_PRODUCTION'
    if not full and manifest.get('root_ids')!=['F1_000001','F1_000002']:raise ValueError('only frozen first two F1 roots permitted by legacy scope')
    validate_sources(manifest)
    base=manifest.get('jobs',[])
    if {j['root_id'] for j in base}!=set(manifest['root_ids']) or len(base)!=len(manifest['root_ids']):raise ValueError('root job matrix mismatch')
    if not full and len(base)!=2:raise ValueError('legacy first wave requires two jobs')
    extra=list(activated_jobs or [])
    if extra and not full:raise ValueError('reserve jobs require full F1 scope')
    jobs=base+extra
    if len({j['job_id'] for j in jobs})!=len(jobs) or len({j['root_id'] for j in jobs})!=len(jobs):raise ValueError('duplicate job/root')
    for job in extra:_validate_activation(manifest,job)
    for job in jobs:
        for key in ('spec_path','authorization_path','output'):_workspace_path(job[key])
        spec,auth=read_bound_job_configs(job);validate_resolved(spec)
        if job['job_id'] not in inactive_job_ids:validate_sources(auth)
        if spec['root_id']!=job['root_id'] or spec['family']!='F1' or auth.get('spec_sha256')!=spec['spec_sha256']:raise ValueError('child spec binding mismatch')
        if not copy_only and auth.get('gpu_execution_authorized') is not True:raise ValueError('child GPU not authorized')
        for counters in [job['reservation'],job.get('root_budget_caps',job['reservation'])]:
            if set(counters)!=set(COUNTERS) or any(type(counters[k]) is not int or counters[k]<0 for k in COUNTERS):raise ValueError('invalid reservation/root cap')
        if type(job.get('timeout_seconds')) is not int or job['timeout_seconds']<=0 or type(job.get('cleanup_grace_seconds')) is not int or job['cleanup_grace_seconds']<4:raise ValueError('finite timeout/cleanup required')
        overhead=job.get('lease_overhead_seconds',100)
        if type(overhead)is not int or overhead<100 or job['timeout_seconds']+job['cleanup_grace_seconds']+overhead>job['reservation']['gpu_lease_seconds']:raise ValueError('timeout exceeds reservation with cleanup/overhead')
        if auth.get('job_limits')!={'timeout_seconds':job['timeout_seconds'],'cleanup_grace_seconds':job['cleanup_grace_seconds'],'gpu_reservation_seconds':job['reservation']['gpu_lease_seconds']}:raise ValueError('child limits differ')
        _workspace_path(auth['copy_destination'])
    n=manifest.get('max_concurrent_gpu_jobs',2)
    if type(n)is not int or not 1<=n<=8:raise ValueError('bounded GPU concurrency required')
    return jobs


def verify_nfs_lock(directory):
    path=Path(directory)/'two_process_lock_probe.lock'
    code="import fcntl,sys; f=open(sys.argv[1],'a'); expected=sys.argv[2]=='blocked'; blocked=False\ntry: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)\nexcept BlockingIOError: blocked=True\nraise SystemExit(0 if blocked==expected else 1)"
    with path.open('a') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        first=subprocess.run([str(PYTHON),'-c',code,str(path),'blocked'],cwd=ROOT,timeout=5).returncode
        fcntl.flock(stream,fcntl.LOCK_UN)
        second=subprocess.run([str(PYTHON),'-c',code,str(path),'free'],cwd=ROOT,timeout=5).returncode
    if first or second:raise RuntimeError('two-process NFS locking failed')
    return {'two_process_conflict_blocked':True,'release_allows_second_process':True}


def evidence(path,value):
    """Evidence write independent of mutable STATE writer, with fsync before rename."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.partial')
    with temporary.open('w') as stream:
        json.dump(value,stream,sort_keys=True,indent=2);stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)


def _stamp():
    return {'wall_seconds':time.time(),'monotonic_seconds':time.monotonic(),'host':os.uname().nodename,'coordinator_pid':os.getpid(),'clock':'time.monotonic:'+time.get_clock_info('monotonic').implementation}


def _zero():return {k:0 for k in COUNTERS}


def _classify(output,execution):
    output=Path(output);checkpoint_path=output/'checkpoint.json';checkpoint=json.loads(checkpoint_path.read_text(encoding='utf-8')) if checkpoint_path.exists() else {}
    independent_path=output/'independent_structure.json';spec_path=output/'root_spec.json'
    if checkpoint.get('status')=='STRUCTURE_READY' and independent_path.is_file() and spec_path.is_file():
        from family_entry import digest
        spec=json.loads(spec_path.read_text(encoding='utf-8'));independent=json.loads(independent_path.read_text(encoding='utf-8'))
        if checkpoint.get('input_sha256')==digest(spec) and independent.get('root_id')==spec.get('root_id') and independent.get('pass')is True:return 'copy_failure'
    active=checkpoint.get('active_realization');statuses=[]
    for realization in ('r_pc','r_inv_path','r_inv_motion'):
        if active and realization!=active:continue
        base=output/realization;pointer=base/'cohort_pointer.json'
        if pointer.is_file():
            value=json.loads(pointer.read_text(encoding='utf-8'));root=_workspace_path(base/value['root_relative']);receipt=root/'root_receipt.json'
            if receipt.is_file():
                terminal=json.loads(receipt.read_text(encoding='utf-8'));status=terminal.get('status');failed=[b for b in terminal.get('branch_receipts',[]) if b.get('status')!='accepted']
                if status=='failed_verifier' and failed and failed[-1].get('status')=='failed_execution':status='failed_execution'
                if status=='failed_verifier' and failed and failed[-1].get('status')=='failed_independent_cell':
                    gate=failed[-1].get('independent_cell_gate',{})
                    if gate.get('pass')is False and gate.get('failure_class')=='PHYSICAL_FAILURE':status='failed_task_physical_feasibility'
                statuses.append(status)
            elif value.get('status') in ('STARTED','EXCEPTION'):statuses.append('failed_implementation_error')
        else:
            candidates=[(0,base/'root/root_receipt.json')]+[(int(p.parent.parent.name.split('_')[-1]),p) for p in base.glob('recovery_*/root/root_receipt.json') if p.parent.parent.name.split('_')[-1].isdigit()]
            present=[x for x in candidates if x[1].is_file()]
            if present:
                terminal=json.loads(max(present,key=lambda x:x[0])[1].read_text(encoding='utf-8'));status=terminal.get('status');failed=[b for b in terminal.get('branch_receipts',[]) if b.get('status')!='accepted']
                if status=='failed_verifier' and failed and failed[-1].get('status')=='failed_execution':status='failed_execution'
                if status=='failed_verifier' and failed and failed[-1].get('status')=='failed_independent_cell':
                    gate=failed[-1].get('independent_cell_gate',{})
                    if gate.get('pass')is False and gate.get('failure_class')=='PHYSICAL_FAILURE':status='failed_task_physical_feasibility'
                statuses.append(status)
    if any(s in ('failed_implementation_error','failed_verifier','failed_current_hash','failed_anchor_equivalence','failed_family_suffix_gate','failed_canonical_prefix_reference','failed_prefix_replay_gate','failed_cleanup_uncertain','failed_candidate_mutation','failed_required_video') for s in statuses):return 'shared_interface_error'
    if any(s in ('failed_planner','failed_task_physical_feasibility') for s in statuses):return 'physical_infeasible'
    if any(s=='failed_execution' for s in statuses):return 'transient_execution'
    if execution.get('timeout'):return 'transient_execution'
    if execution.get('returncode') not in (None,0) and not statuses:return 'transient_execution'
    return 'unknown'


def _failure_evidence(output, execution=None):
    """Classify a terminal attempt without conflating code and physics.

    The historical coarse ``failure_class`` is kept for ledger compatibility,
    while this richer category controls whether a reserve may be consumed.
    A reserve is eligible only after a root has produced two independently
    classified physical failures; engineering, recovery, copy, and unknown
    failures stop the affected line for review instead of changing its scene.
    """
    output = Path(output)
    execution = execution or {}
    receipts = []
    seen_receipt_paths = set()
    for realization in ('r_pc', 'r_inv_path', 'r_inv_motion'):
        base = output / realization
        pointer = base / 'cohort_pointer.json'
        candidates = [base / 'root/root_receipt.json'] + sorted(
            base.glob('recovery_*/root/root_receipt.json')
        )
        if pointer.is_file():
            try:
                value = json.loads(pointer.read_text(encoding='utf-8'))
                root = _workspace_path(base / value['root_relative'])
                candidates.append(root / 'root_receipt.json')
            except BaseException:
                pass
        for path in candidates:
            if path.is_file() and path not in seen_receipt_paths:
                try:
                    receipts.append((path, json.loads(path.read_text(encoding='utf-8'))))
                    seen_receipt_paths.add(path)
                except (OSError, ValueError, TypeError):
                    pass

    details = []
    for path, receipt in receipts:
        status = receipt.get('status')
        error = str(receipt.get('error') or '')
        branch_receipts = receipt.get('branch_receipts') or []
        failed = [item for item in branch_receipts if item.get('status') != 'accepted']
        physical_gate = any(
            item.get('independent_cell_gate', {}).get('failure_class') == 'PHYSICAL_FAILURE'
            for item in failed
        )
        if status in ('failed_task_physical_feasibility', 'failed_planner') or physical_gate:
            category = 'physical_failure'
            reason = 'explicit task/planner or independent physical verifier failure'
        elif status in ('failed_current_hash', 'failed_anchor_equivalence',
                        'failed_canonical_prefix_reference', 'failed_prefix_replay_gate',
                        'failed_family_suffix_gate') or 'recovery actual regenerated' in error:
            category = 'recovery_consistency_error'
            reason = error or status
        elif status in ('failed_implementation_error', 'failed_candidate_mutation',
                        'failed_cleanup_uncertain', 'failed_required_video'):
            category = 'engineering_error'
            reason = error or status
        elif status == 'failed_execution' and ('source' in error.lower() or
                                               'compatibility' in error.lower() or
                                               'unicode' in error.lower() or
                                               'encoding' in error.lower()):
            category = 'engineering_error'
            reason = error
        elif status == 'failed_execution' and receipt.get('budget_counts', {}).get('execution_attempt_count', 0) == 0:
            category = 'engineering_error'
            reason = error or 'execution ended before a physical branch'
        elif status == 'failed_verifier':
            category = 'engineering_error'
            reason = error or 'verifier failure without explicit physical-failure evidence'
        elif status == 'failed_execution':
            category = 'transient_execution'
            reason = error or 'native execution terminated without a classified physical result'
        elif status in ('copy_failure', 'COPY_FAILED'):
            category = 'copy_index_error'
            reason = error or status
        else:
            category = None
            reason = error or status
        details.append({
            'path': str(path),
            'status': status,
            'category': category,
            'reason': reason,
            'physical_started': bool(
                receipt.get('budget_counts', {}).get('execution_attempt_count', 0)
                or receipt.get('branch_execution_attempt_count', 0)
            ),
        })

    categories = [item['category'] for item in details if item['category']]
    if 'physical_failure' in categories and all(
        category in ('physical_failure', None) for category in categories
    ):
        category = 'physical_failure'
    elif 'recovery_consistency_error' in categories:
        category = 'recovery_consistency_error'
    elif 'engineering_error' in categories:
        category = 'engineering_error'
    elif 'copy_index_error' in categories:
        category = 'copy_index_error'
    elif 'transient_execution' in categories:
        category = 'transient_execution'
    elif execution.get('timeout'):
        category = 'resource_unknown'
    elif execution.get('returncode') not in (None, 0):
        category = 'resource_unknown'
    else:
        category = 'unknown'
    physical_started = any(item['physical_started'] for item in details)
    return {
        'category': category,
        'reserve_eligible': category == 'physical_failure',
        'physical_started': physical_started,
        'details': details,
        'evidence_complete': bool(details),
    }


def _root_consumed(jobstate):
    total=_zero()
    for attempt in jobstate.get('attempts',[]):
        if attempt.get('settled'):
            for k in COUNTERS:total[k]+=attempt['actual'][k]
    return total


def _refresh_state(state,jobs):
    statuses=[state['jobs'].get(j['job_id'],{}).get('status') for j in jobs]
    if any(x=='UNRESOLVED' for x in statuses):state['status']='UNRESOLVED'
    elif any(x=='BUDGET_OVERRUN' for x in statuses):state['status']='BUDGET_OVERRUN'
    elif all(x=='PASS' for x in statuses):state['status']='COMPLETE'
    elif any(x in ('FAILED','COPY_FAILED') for x in statuses):state['status']='FAILED'
    else:state['status']='WAITING_IDLE_OR_READY'


def _recoverable(job,previous,request,manifest,compatibility=None):
    policy=manifest.get('recovery_policy',{})
    allowed=list(policy.get('allowed_failure_classes',['physical_infeasible','transient_execution']))
    if compatibility:
        resolution=compatibility.get('receipt',{}).get('failure_resolution',{})
        if resolution.get('failure_class')==previous.get('failure_class') and resolution.get('status')=='FIXED_CPU_VERIFIED':allowed+=[previous['failure_class']]
    if request.get('mode','resume')!='resume' or not isinstance(request.get('request_id'),str) or not request['request_id']:raise ValueError('explicit bounded resume request required')
    if previous.get('status') not in ('FAILED','DEFERRED_READY') or previous.get('failure_class') not in allowed or request.get('failure_class')!=previous.get('failure_class'):raise ValueError('failure classification does not permit resume')
    attempts=previous.get('attempts',[])
    prelease_only=not attempts and previous.get('GPU_started')is False and previous.get('reservation_retained')is False and compatibility is not None
    if not prelease_only and (not attempts or not attempts[-1].get('settled') or not attempts[-1].get('owned_cleanup_pass') or not attempts[-1].get('release_confirmed')):raise ValueError('resume requires settled usage and owned cleanup/release')
    if sum(a.get('child_launched',True) is True for a in attempts)>=policy.get('max_gpu_attempts',policy.get('max_gpu_attempts_per_job',2)):raise ValueError('finite GPU attempt limit exhausted')
    spec,auth=read_bound_job_configs(job)
    if previous.get('spec_sha256')!=spec['spec_sha256']:raise ValueError('scientific spec changed')
    if previous.get('source_bundle_sha256')!=auth['source_bundle_sha256']:
        proof=compatibility.get('receipt',{}) if compatibility else {}
        if proof.get('old_source_bundle_sha256')!=previous.get('source_bundle_sha256') or proof.get('new_source_bundle_sha256')!=auth['source_bundle_sha256']:raise ValueError('source changed without applicable reviewed compatibility')
    # Actual saved immutable records, not their old pass flag alone, bind a resume.
    for file,sha in previous.get('accepted_file_hashes',{}).items():
        if hashlib.sha256(_workspace_path(file).read_bytes()).hexdigest()!=sha:raise ValueError('previously accepted raw changed')


def _accepted_files(output):
    result={}
    for receipt in Path(output).glob('**/branches/*/receipt.json'):
        d=json.loads(receipt.read_text(encoding='utf-8'))
        if d.get('status')!='accepted':continue
        from native_raw_contract import validate_native_raw_contract
        raw=receipt.parent/'raw'
        if not validate_native_raw_contract(raw).get('pass'):raise ValueError('accepted raw integrity no longer passes')
        paths=[receipt,*raw.glob('*')]
        manifest=json.loads((raw/'manifest.json').read_text(encoding='utf-8'))
        capture=manifest.get('provenance',{}).get('formal_current_capture_path')
        if capture:
            cp=_workspace_path(capture);paths.extend([cp,cp.parent/'current.npz',cp.parent/'anchor.json'])
        trace=receipt.parent/'trace_source.npz'
        if trace.is_file():paths.append(trace)
        for path in paths:
            if path.is_file():result[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _delta_usage(output,lease_seconds,baseline):
    cumulative=usage_from_receipts(output,0);actual={k:cumulative[k]-baseline[k] for k in COUNTERS if k!='gpu_lease_seconds'}
    if any(v<0 for v in actual.values()):raise RuntimeError('previous physical consumption disappeared')
    actual['gpu_lease_seconds']=int(lease_seconds)
    return actual,cumulative


def _cpu_copy_job(job,state,state_path,request_id,*,allow_synthetic=False,compatibility=None):
    """No backend construction, snapshot, lease or native scene call on this path."""
    from execution_cli import copy_only
    previous=state['jobs'].get(job['job_id'],{})
    if previous.get('status')=='PASS':
        verified=verify_completed_job(job,allow_synthetic=allow_synthetic)
        return {'status':'PASS','idempotent':True,'GPU_started':False,'copy_completion':verified}
    if previous.get('status')!='COPY_FAILED' or not previous.get('attempts') or not previous['attempts'][-1].get('settled') or not previous['attempts'][-1].get('owned_cleanup_pass') or not previous['attempts'][-1].get('release_confirmed'):raise ValueError('copy-only requires collected/settled/cleaned/released root')
    spec,auth=read_bound_job_configs(job)
    if spec['spec_sha256']!=previous['spec_sha256']:raise ValueError('copy recovery spec mismatch')
    if auth['source_bundle_sha256']!=previous['source_bundle_sha256']:
        proof=compatibility.get('receipt',{}) if compatibility else {}
        if proof.get('old_source_bundle_sha256')!=previous['source_bundle_sha256'] or proof.get('new_source_bundle_sha256')!=auth['source_bundle_sha256']:raise ValueError('copy source changed without reviewed compatibility')
    for path,sha in previous.get('accepted_file_hashes',{}).items():
        if hashlib.sha256(_workspace_path(path).read_bytes()).hexdigest()!=sha:raise ValueError('accepted source changed')
    try:
        copy_only(spec,job['output'],auth);completed=verify_completed_job(job,allow_synthetic=allow_synthetic)
        previous.update(status='PASS',copy_completion=completed,source_bundle_sha256=auth['source_bundle_sha256']);state.setdefault('recovery_requests',{})[request_id]={'job_id':job['job_id'],'mode':'copy_only','status':'PASS'}
        write(state_path,state);return {'status':'PASS','GPU_started':False,'copy_completion':completed}
    except BaseException as exc:
        previous['copy_error']={'type':type(exc).__name__,'message':str(exc)};write(state_path,state);raise


def reconcile_saved_attempts(manifest,state_dir,job_ids=None):
    """CPU-only idempotent settlement from pre-existing measured terminal evidence.

    Missing acquisition/end/cleanup/release or unknown usage is never reconstructed
    using the current wall clock. A live/unknown child remains UNRESOLVED.
    """
    from controlled_multi_future.redesign_f2_f3_v2.execution_ledger_v2 import ExecutionLedgerV2
    state_dir=_workspace_path(state_dir);state_path=state_dir/'STATE.json';state=json.loads(state_path.read_text(encoding='utf-8'))
    if state['contract_sha256']!=hash_json(manifest):raise ValueError('reconcile contract changed')
    ledger=ExecutionLedgerV2(state_dir/'execution_ledger.jsonl',contract_sha256=hash_json(manifest),task_id=manifest['task_id'],caps=manifest['budget_caps'])
    with (state_dir/'coordinator.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for job_id in (job_ids or state['jobs']):
            job=state['jobs'][job_id]
            if job.get('status') not in ('UNRESOLVED','RUNNING'):continue
            attempt=job['attempts'][-1];folder=Path(attempt['evidence_directory'])
            terminal_path=folder/'lease_terminal.json'
            end=json.loads(terminal_path.read_text(encoding='utf-8')) if terminal_path.is_file() else json.loads((folder/'lease_persistence_errors.json').read_text(encoding='utf-8'))['measured_terminal']
            if end.get('release_confirmed') is not True or end.get('owned_cleanup_pass') is not True or not isinstance(end.get('lease_seconds'),int):raise RuntimeError('saved terminal lease evidence unresolved')
            usage_path=folder/'actual_usage.json'
            if usage_path.exists():usage=json.loads(usage_path.read_text(encoding='utf-8'))
            else:
                actual,cumulative=_delta_usage(job['output'],end['lease_seconds'],attempt['usage_baseline']);usage={'actual':actual,'cumulative':cumulative};evidence(usage_path,usage)
            event=ledger.settle(attempt['ledger_job_id'],attempt['reservation'],usage['actual'],idempotency_key='settle:'+attempt['ledger_job_id'])
            attempt.update(actual=usage['actual'],cumulative_usage=usage['cumulative'],settled=True,owned_cleanup_pass=True,release_confirmed=True)
            execution=json.loads((folder/'child_terminal.json').read_text(encoding='utf-8')) if (folder/'child_terminal.json').is_file() else {}
            classification=_classify(job['output'],execution)
            job.update(status='BUDGET_OVERRUN' if event['event_type']=='BUDGET_OVERRUN' else 'COPY_FAILED' if classification=='copy_failure' else 'FAILED',failure_class=classification,actual=usage['actual'],root_collection_verified=classification=='copy_failure',owned_cleanup_pass=True,release_confirmed=True,accepted_file_hashes=_accepted_files(job['output']))
            write(state_path,state)
        _refresh_state(state,[{'job_id':k} for k in state['jobs']]);state['budget']=ledger.totals();write(state_path,state)
        return state


def launch_wave(manifest,state_dir,backend=None,*,ready_job_ids=None,recovery_requests=None,copy_only_job_ids=None,activated_jobs=None,compatibility_ref=None):
    copies=list(copy_only_job_ids or []);requests=recovery_requests or {};allow_synthetic=manifest.get('test_only') is True and getattr(backend,'synthetic_cpu_backend',False) is True
    if manifest.get('test_only') is True and not allow_synthetic:raise PermissionError('test-only manifest requires explicit CPU backend')
    runtime_manifest=manifest;compatibility=None
    if compatibility_ref:
        compatibility=validate_compatibility(manifest,state_dir,compatibility_ref,activated_jobs=activated_jobs)
        runtime_manifest={**manifest,**{k:compatibility[k] for k in ['source_files','source_bundle_sha256']},'jobs':[j for j in compatibility['jobs'] if j['root_id'] in manifest['root_ids']]}
        activated_jobs=[j for j in compatibility['jobs'] if j['root_id'] not in manifest['root_ids']]
    inactive={j['job_id'] for j in manifest['jobs']}-set(compatibility['applicable_job_ids']) if compatibility else set()
    jobs=validate_manifest(runtime_manifest,activated_jobs,copy_only=bool(copies),inactive_job_ids=inactive)
    by={j['job_id']:j for j in jobs};selected=list(by) if ready_job_ids is None else list(ready_job_ids)
    if len(set(selected))!=len(selected) or not set(selected)<=set(by):raise ValueError('ready subset outside frozen jobs')
    if set(selected if not copies else copies)&inactive:raise ValueError('unrebound jobs remain blocked after source revision')
    if copies and (not set(copies)<=set(by) or requests):raise ValueError('invalid copy-only subset')
    state_dir=_workspace_path(state_dir)
    from controlled_multi_future.redesign_f2_f3_v2.execution_ledger_v2 import ExecutionLedgerV2
    from controlled_multi_future.redesign_f2_f3_v2.gpu import assign_ready_jobs,guard_card
    existing=state_dir/'STATE.json';binding_path=state_dir/'namespace_binding.json';contract_hash=hash_json(manifest);binding={'task_id':manifest['task_id'],'contract_sha256':contract_hash}
    if existing.exists():
        previous_namespace=json.loads(existing.read_text(encoding='utf-8'))
        if previous_namespace.get('task_id')!=manifest['task_id'] or previous_namespace.get('contract_sha256')!=contract_hash:raise ValueError('foreign namespace before mutation')
    if state_dir.exists() and any(state_dir.iterdir()) and not existing.exists() and (not binding_path.exists() or json.loads(binding_path.read_text(encoding='utf-8'))!=binding):raise ValueError('foreign namespace')
    state_dir.mkdir(parents=True,exist_ok=True)
    if binding_path.exists() and json.loads(binding_path.read_text(encoding='utf-8'))!=binding:raise ValueError('namespace contract changed')
    write(binding_path,binding);write(state_dir/'nfs_lock_probe.json',verify_nfs_lock(state_dir))
    with (state_dir/'coordinator.lock').open('a') as coordinator:
        fcntl.flock(coordinator,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger=ExecutionLedgerV2(state_dir/'execution_ledger.jsonl',contract_sha256=contract_hash,task_id=manifest['task_id'],caps=manifest['budget_caps'])
        state=json.loads(existing.read_text(encoding='utf-8')) if existing.exists() else {'task_id':manifest['task_id'],'contract_sha256':contract_hash,'jobs':{},'recovery_requests':{},'status':'READY'}
        if state['task_id']!=manifest['task_id'] or state['contract_sha256']!=contract_hash:raise ValueError('foreign task/contract')
        if any(ledger.totals()['reserved'].values()) or state['status'] in ('UNRESOLVED','BUDGET_OVERRUN'):raise RuntimeError('unknown resources must be reconciled first')
        if state['status']=='SOURCE_CHANGED':
            if not compatibility:raise RuntimeError('source revision requires reviewed compatibility')
            state.setdefault('source_amendments',[]).append({'appendix':compatibility['appendix_binding'],'source_error_preserved':state.get('source_error'),'new_source_bundle_sha256':compatibility['source_bundle_sha256']})
            _refresh_state(state,jobs);write(existing,state)
        if copies:
            results=[_cpu_copy_job(by[j],state,existing,'copy:'+j,allow_synthetic=allow_synthetic,compatibility=compatibility['job_proofs'].get(j) if compatibility else None) for j in copies];_refresh_state(state,jobs);state['budget']=ledger.totals();write(existing,state)
            return {'state':state,'results':results,'deferred_roots':[],'gpu_initialized_by_coordinator':False,'copy_only':True}
        if state['status']=='FAILED' and not requests and ready_job_ids is None:raise RuntimeError('failed job requires classified explicit recovery')
        allowed_failures=manifest.get('recovery_policy',{}).get('allowed_failure_classes',['physical_infeasible','transient_execution'])
        if any(j.get('status')=='FAILED' and j.get('failure_class') not in allowed_failures and not (compatibility and compatibility['job_proofs'].get(k,{}).get('receipt',{}).get('failure_resolution',{}).get('status')=='FIXED_CPU_VERIFIED') for k,j in state['jobs'].items()):raise RuntimeError('unclassified/shared failure stops all new dispatch')
        if any(j.get('status')=='COPY_FAILED' for j in state['jobs'].values()):raise RuntimeError('finish CPU-only copy recovery before more GPU work')
        ready=[]
        for jid in selected:
            job=by[jid];prior=state['jobs'].get(jid)
            if prior is None:ready.append((job,None));continue
            if prior.get('status')=='DEFERRED_READY' and jid not in requests:
                pending=prior.get('pending_recovery_request')
                if pending:_recoverable(job,prior,pending,manifest,compatibility['job_proofs'].get(jid) if compatibility else None)
                ready.append((job,pending));continue
            request=requests.get(jid)
            if request and request.get('request_id') in state.get('recovery_requests',{}):
                old_request=state['recovery_requests'][request['request_id']]
                if old_request['job_id']!=jid:raise ValueError('recovery id reused for another job')
                if old_request.get('status')!='DEFERRED_READY':continue
            if request:_recoverable(job,prior,request,manifest,compatibility['job_proofs'].get(jid) if compatibility else None);ready.append((job,request))
        if set(requests)-set(selected):raise ValueError('recovery outside ready subset')
        if not ready:return {'state':state,'results':[],'deferred_roots':[],'gpu_initialized_by_coordinator':False,'idempotent':True}
        backend=backend or HostBackend();wave=backend.snapshot();evidence(state_dir/'wave_snapshot.json',wave)
        ready_jobs=[j for j,_ in ready];assigned=[];used=set()
        for job in ready_jobs:
            bound=state['jobs'].get(job['job_id'],{}).get('fixed_gpu_uuid')
            filtered={**wave,'gpus':[{**c,'independently_fresh_idle':c.get('independently_fresh_idle') and c['gpu_uuid'] not in used and (bound is None or c['gpu_uuid']==bound)} for c in wave['gpus']]}
            allocation=assign_ready_jobs([job],filtered)['assignments']
            if allocation:assigned.extend(allocation);used.add(allocation[0]['gpu_uuid'])
            if len(assigned)>=manifest.get('max_concurrent_gpu_jobs',2):break
        mutex=threading.Lock();copy_limit=threading.Semaphore(manifest.get('max_copy_workers',1));write(existing,state)
        def run(job,assignment,request):
            jid=job['job_id'];prior=state['jobs'].get(jid,{});number=1+len(list((state_dir/'jobs'/jid).glob('attempt_*')));aid=jid+':attempt:'+str(number)
            directory=state_dir/'jobs'/jid/('attempt_'+str(number));directory.mkdir(parents=True,exist_ok=False)
            spec,auth=read_bound_job_configs(job);baseline=usage_from_receipts(job['output'],0) if request else _zero()
            expected_previous=prior['attempts'][-1]['cumulative_usage'] if prior.get('attempts') else _zero()
            if request and any(baseline[k]!=expected_previous[k] for k in COUNTERS if k!='gpu_lease_seconds'):raise ValueError('prior cumulative consumption changed')
            consumed=_root_consumed(prior);caps=job.get('root_budget_caps',job['reservation']);reservation={k:min(job['reservation'][k],caps[k]-consumed[k]) for k in COUNTERS}
            if any(v<0 for v in reservation.values()) or reservation['gpu_lease_seconds']<job['timeout_seconds']+job['cleanup_grace_seconds']+job.get('lease_overhead_seconds',100):raise ValueError('root remaining cap insufficient')
            attempt={'attempt':number,'ledger_job_id':aid,'reservation':reservation,'usage_baseline':baseline,'evidence_directory':str(directory),'request_id':request.get('request_id') if request else None,'settled':False,'child_launched':False,'source_bundle_sha256':auth['source_bundle_sha256'],'spec_sha256':spec['spec_sha256'],'source_compatibility':compatibility['job_proofs'].get(jid) if compatibility else None}
            lease=None;acquired=None;terminal=None;execution=None;release=None;reserved=False;safe_cleanup=False;child_invoked=False;busy=False;post_error=None;error=None
            try:
                if not request and Path(job['output']).exists() and any(Path(job['output']).iterdir()):raise ValueError('fresh output is nonempty; explicit resume required')
                with mutex:
                    ledger.reserve(aid,reservation,idempotency_key='reserve:'+aid);reserved=True
                    state['jobs'][jid]={**prior,'status':'RUNNING','root_id':job['root_id'],'output':job['output'],'spec_sha256':spec['spec_sha256'],'source_bundle_sha256':auth['source_bundle_sha256'],'bound_job':job,'attempts':prior.get('attempts',[])+[attempt],'attempt_count':sum(a.get('child_launched',True)is True for a in prior.get('attempts',[]))}
                    if request:state.setdefault('recovery_requests',{})[request['request_id']]={'job_id':jid,'mode':'resume','attempt':number,'status':'STARTED'}
                    evidence(directory/'attempt_intent.json',attempt);write(existing,state)
                read_bound_job_configs(job);acquire_start=_stamp();lease=backend.acquire(assignment['physical_gpu_index'],assignment['gpu_uuid']);acquired={**_stamp(),'request_start':acquire_start,'job_id':jid,'attempt':number,'physical_index':assignment['physical_gpu_index'],'gpu_uuid':assignment['gpu_uuid']}
                # No snapshot, state write or child operation intervenes before this.
                evidence(directory/'lease_acquired.json',acquired)
                pre=backend.snapshot();evidence(directory/'pre_snapshot.json',pre);card=guard_card(pre,assignment['physical_gpu_index'],assignment['gpu_uuid'])
                read_bound_job_configs(job)
                child_job={**job,'launch_mode':'resume' if request else 'collect','collect_only':True}
                evidence(directory/'child_launch_intent.json',{'job_id':jid,'attempt':number,'clock':_stamp()})
                with mutex:
                    state['jobs'][jid]['fixed_gpu_uuid']=card['gpu_uuid'];state['jobs'][jid]['fixed_physical_index']=card['physical_index'];write(existing,state)
                child_invoked=True;attempt['child_launched']=True
                execution=backend.run(child_job,card,directory)
                if execution.get('launched')is False:attempt['child_launched']=False
                evidence(directory/'child_terminal.json',execution);evidence(directory/'end_and_cleanup_evidence.json',execution)
                safe_cleanup=execution.get('owned_cleanup_pass') is True and execution.get('host_process_visibility') is True
                try:
                    post=backend.snapshot();evidence(directory/'post_snapshot.json',post);device=next(c for c in post['gpus'] if c['gpu_uuid']==card['gpu_uuid']);pids={p['pid'] for p in execution.get('owned_process_tree',[])}
                    remaining=[p['pid'] for p in device.get('compute_processes',[]) if p['pid'] in pids];safe_cleanup=safe_cleanup and not remaining
                    execution.update(device_idle_observed=device.get('independently_fresh_idle') is True,gpu_owned_remaining_pids=remaining)
                except BaseException as exc:
                    post_error={'type':type(exc).__name__,'message':str(exc)};evidence(directory/'post_snapshot_error.json',post_error)
                evidence(directory/'owned_cleanup.json',{'owned_cleanup_pass':safe_cleanup,'post_snapshot_error':post_error,'execution':execution})
            except BaseException as exc:
                error={'type':type(exc).__name__,'message':str(exc)}
                busy=not child_invoked and ((type(exc).__name__ in ('GuardGpuLeaseUnavailable','BlockingIOError') and ('policy' not in str(exc))) or 'not independently fresh and idle' in str(exc))
                evidence(directory/'attempt_exception.json',{**error,'busy_before_child':busy})
                if execution is None and lease is not None:
                    # A backend may have left a measured cleanup receipt before raising.
                    measured=directory/'process_cleanup.json'
                    if measured.is_file():execution=json.loads(measured.read_text(encoding='utf-8'));safe_cleanup=execution.get('owned_cleanup_pass')is True and execution.get('host_process_visibility')is True
                    elif not child_invoked:safe_cleanup=True
            finally:
                if lease is not None:
                    if execution is None and error is None:safe_cleanup=True
                    if safe_cleanup:
                        try:release=backend.release(lease)
                        except BaseException as exc:release={'released':False,'error':{'type':type(exc).__name__,'message':str(exc)}}
                    else:release={'released':False,'reason':'owned cleanup unproven; lease retained until owner reconciliation or process exit'}
                    ended=_stamp() if release.get('released')is True else None
                    terminal={'job_id':jid,'attempt':number,'acquired':acquired,'release_confirmed':release.get('released')is True,'release':release,'owned_cleanup_pass':safe_cleanup,'ended':ended,'post_snapshot_error':post_error,'error':error,'lease_seconds':math.ceil(ended['monotonic_seconds']-acquired['request_start']['monotonic_seconds']) if ended and acquired else None}
                    boundary_errors=[]
                    for name,value in [('lease_terminal.json',terminal),('lease_release.json',release)]:
                        try:evidence(directory/name,value)
                        except BaseException as exc:boundary_errors.append({'file':name,'type':type(exc).__name__,'message':str(exc)})
                    if boundary_errors:evidence(directory/'lease_persistence_errors.json',{'errors':boundary_errors,'measured_terminal':terminal})
                elif reserved:
                    terminal={'job_id':jid,'attempt':number,'acquisition_failed':True,'release_confirmed':True,'owned_cleanup_pass':True,'lease_seconds':0,'error':error};evidence(directory/'lease_terminal.json',terminal)
            # Every measured lease boundary/cleanup/release precedes usage, settle and copy.
            result={'selected_physical_index':assignment['physical_gpu_index'],'selected_uuid':assignment['gpu_uuid'],'attempt':number,**(execution or {}),'lease_seconds':terminal.get('lease_seconds') if terminal else None}
            try:
                if not reserved:raise RuntimeError('reservation not created')
                if not terminal or not terminal['release_confirmed'] or not terminal['owned_cleanup_pass'] or terminal['lease_seconds'] is None:raise RuntimeError('lease ownership or interval unresolved')
                actual,cumulative=_delta_usage(job['output'],terminal['lease_seconds'],baseline);evidence(directory/'actual_usage.json',{'actual':actual,'cumulative':cumulative})
                with mutex:
                    event=ledger.settle(aid,reservation,actual,idempotency_key='settle:'+aid);reserved=False
                    attempt.update(actual=actual,cumulative_usage=cumulative,settled=True,owned_cleanup_pass=True,release_confirmed=True)
                    failure=_classify(job['output'],execution or {})
                    classification=_failure_evidence(job['output'],execution or {})
                    attempt.update(
                        failure_category=classification['category'],
                        reserve_eligible=classification['reserve_eligible'],
                        physical_started=classification['physical_started'],
                    )
                    status='BUDGET_OVERRUN' if event['event_type']=='BUDGET_OVERRUN' else 'DEFERRED_READY' if busy else 'COPY_FAILED' if failure=='copy_failure' else 'FAILED'
                    result.update(status=status,actual=actual,owned_cleanup_pass=True,release_confirmed=True,failure_class=prior.get('failure_class',failure) if busy else failure, failure_category=classification['category'], reserve_eligible=classification['reserve_eligible'], physical_started=classification['physical_started'], failure_evidence=classification,attempt_count=sum(a.get('child_launched',True)is True for a in state['jobs'][jid]['attempts']),pending_recovery_request=request if busy else None,root_collection_verified=failure=='copy_failure',synthetic=allow_synthetic,research_eligible=False)
                    state['jobs'][jid].update(result)
                    accepted_now=_accepted_files(job['output'])
                    if any(accepted_now.get(p)!=sha for p,sha in prior.get('accepted_file_hashes',{}).items()):raise ValueError('preserved accepted bytes changed across attempt')
                    state['jobs'][jid]['accepted_file_hashes']=accepted_now;write(existing,state)
                if status!='BUDGET_OVERRUN' and execution and execution.get('returncode')==0 and not error:
                    try:
                        # Copy after GPU release and physical budget settlement, CPU-only.
                        from execution_cli import copy_only
                        with copy_limit:copy_only(spec,job['output'],auth);completion=verify_completed_job(job,allow_synthetic=allow_synthetic)
                        result.update(status='PASS',independent_completion=completion,root_collection_verified=True)
                    except BaseException as exc:
                        result.update(status='COPY_FAILED' if failure=='copy_failure' else 'FAILED',copy_error={'type':type(exc).__name__,'message':str(exc)},independent_completion={'pass':False,'error':str(exc)})
                with mutex:
                    state['jobs'][jid].update(result)
                    if request:state['recovery_requests'][request['request_id']]['status']=result['status']
                    evidence(directory/'job_receipt.json',result);_refresh_state(state,jobs);state['budget']=ledger.totals();write(existing,state)
                return result
            except BaseException as exc:
                with mutex:
                    result.update(status='UNRESOLVED' if reserved else 'FAILED',error=str(exc),reservation_retained=reserved)
                    state['jobs'].setdefault(jid,{**prior,'attempts':prior.get('attempts',[])+[attempt],'attempt_count':sum(a.get('child_launched',True)is True for a in prior.get('attempts',[]))}).update(result);state['status']='UNRESOLVED' if reserved else 'FAILED'
                    evidence(directory/'job_receipt.json',result);write(existing,state)
                return result
        def guarded_run(job,assignment,request):
            try:return run(job,assignment,request)
            except BaseException as exc:
                with mutex:
                    prior=state['jobs'].get(job['job_id'],{})
                    unknown=prior.get('status')=='RUNNING'
                    result={'status':'UNRESOLVED' if unknown else 'FAILED','failure_class':'shared_interface_error','error':{'type':type(exc).__name__,'message':str(exc)},'GPU_started':None if unknown else False,'reservation_retained':unknown,'clock':_stamp()}
                    directory=state_dir/'jobs'/job['job_id'];directory.mkdir(parents=True,exist_ok=True)
                    evidence(directory/('outer_exception_'+str(time.time_ns())+'.json'),result)
                    spec,auth=read_bound_job_configs(job)
                    state['jobs'][job['job_id']]={**prior,**result,'root_id':job['root_id'],'bound_job':job,'spec_sha256':spec['spec_sha256'],'source_bundle_sha256':auth['source_bundle_sha256']};state['status']=result['status'];write(existing,state)
                    return result
        with concurrent.futures.ThreadPoolExecutor(max_workers=manifest.get('max_concurrent_gpu_jobs',2)) as pool:
            ready_requests={j['job_id']:r for j,r in ready}
            futures=[pool.submit(guarded_run,by[a['job_id']],a,ready_requests.get(a['job_id'])) for a in assigned];results=[f.result() for f in futures]
        try:validate_sources(runtime_manifest)
        except BaseException as exc:state['status']='SOURCE_CHANGED';state['source_error']=str(exc);state['budget']=ledger.totals();write(existing,state);raise
        _refresh_state(state,jobs);state['budget']=ledger.totals();write(existing,state)
        return {'state':state,'results':results,'deferred_roots':[j['root_id'] for j in ready_jobs if j['job_id'] not in {a['job_id'] for a in assigned}],'gpu_initialized_by_coordinator':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True,type=Path);p.add_argument('--state-dir',required=True,type=Path);p.add_argument('--ready-job',action='append');p.add_argument('--recoveries',type=Path);p.add_argument('--copy-only-job',action='append');p.add_argument('--reconcile-only',action='store_true');p.add_argument('--compatibility-file',type=Path);a=p.parse_args();manifest=json.loads(a.manifest.read_text(encoding='utf-8'))
    if a.reconcile_only:result={'state':reconcile_saved_attempts(manifest,a.state_dir),'deferred_roots':[]}
    else:result=launch_wave(manifest,a.state_dir,ready_job_ids=a.ready_job,recovery_requests=json.loads(a.recoveries.read_text(encoding='utf-8')) if a.recoveries else None,copy_only_job_ids=a.copy_only_job,compatibility_ref={'path':str(a.compatibility_file),'sha256':hashlib.sha256(a.compatibility_file.read_bytes()).hexdigest()} if a.compatibility_file else None)
    print(json.dumps({'status':result['state']['status'],'deferred_roots':result['deferred_roots']}));return 0 if result['state']['status']=='COMPLETE' else 1
if __name__=='__main__':raise SystemExit(main())
