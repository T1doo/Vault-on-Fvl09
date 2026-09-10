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
        p=json.loads(pointer.read_text())
        if p.get('status')=='STARTED' or not (pointer.parent/p['root_relative']/'root_receipt.json').exists():
            raise RuntimeError('started cohort missing terminal receipt; usage unresolved')
    if not receipts:
        if pointers or list(output.glob('**/root_events.jsonl')):
            raise RuntimeError('native execution may have started; usage unresolved')
        return {**{k:0 for k in COUNTERS},'gpu_lease_seconds':int(lease_seconds)}
    totals={k:0 for k in COUNTERS};totals['gpu_lease_seconds']=int(lease_seconds)
    for path in receipts:
        r=json.loads(path.read_text());cleanup=r['cleanup_records']
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
        from controlled_multi_future.redesign_f2_f3_v2.gpu import child_environment
        env=child_environment(card['gpu_uuid']);env['PATH']=str(PYTHON.parent)+os.pathsep+str(ROOT/'Robotwin2/tools/cuda-12.1/bin')+os.pathsep+env.get('PATH','');cache=receipt_dir/'child_cache';cache.mkdir()
        for name in ('TMPDIR','XDG_CACHE_HOME','TORCH_EXTENSIONS_DIR','TRITON_CACHE_DIR','CUDA_CACHE_PATH','MPLCONFIGDIR'):
            path=cache/name.lower();path.mkdir();env[name]=str(path)
        env.update(PYTHONPATH=str(PROJECT)+os.pathsep+str(HERE),PYTHONDONTWRITEBYTECODE='1',ROBOTWIN_ROOT=str(PROJECT),ROBOTWIN_WORKSPACE=str(ROOT/'Robotwin2'),CMF_GPU_GUARD_PHYSICAL_INDEX=str(card['physical_index']))
        command=[str(PYTHON),str(HERE/'execution_cli.py'),'--spec',job['spec_path'],'--authorization',job['authorization_path'],'--output',job['output']]
        started=time.monotonic();wall=time.time();process=None;owned={};timed_out=False;error=None
        def processes():
            raw=subprocess.run(['ps','-u',str(os.getuid()),'-o','pid=,ppid=,pgid=,lstart=,comm='],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
            found={}
            for line in raw.splitlines():
                parts=line.split(None,8)
                if len(parts)==9:found[int(parts[0])]={'pid':int(parts[0]),'ppid':int(parts[1]),'pgid':int(parts[2]),'start':' '.join(parts[3:8]),'comm':parts[8]}
            return found
        def observe():
            found=processes()
            ids={process.pid} | set(owned)
            changed=True
            while changed:
                more={pid for pid,p in found.items() if p['ppid'] in ids or p['pgid']==process.pid}
                changed=not more<=ids;ids|=more
            for pid in ids & found.keys():
                if pid not in owned:owned[pid]=found[pid]
            return {pid:p for pid,p in found.items() if pid in owned and p['start']==owned[pid]['start']}
        def terminate_owned(signum):
            for pid,p in observe().items():
                try:os.kill(pid,signum)
                except ProcessLookupError:pass
        try:
            with (receipt_dir/'stdout.log').open('w') as stream:
                process=subprocess.Popen(command,cwd=PROJECT,env=env,start_new_session=True,stdout=stream,stderr=subprocess.STDOUT)
                observe();write(receipt_dir/'process_start.json',{'pid':process.pid,'ppid':os.getpid(),'pgid':process.pid,'started_wall':wall,'started_monotonic':started,'command':command,'owned':list(owned.values())})
                while process.poll() is None:
                    observe()
                    if time.monotonic()-started>=job['timeout_seconds']:
                        timed_out=True;break
                    time.sleep(.2)
                # End boundary before cleanup or receipt usage parsing.
                write(receipt_dir/'child_end.json',{'ended_wall':time.time(),'ended_monotonic':time.monotonic(),'returncode':process.poll(),'timeout':timed_out,'owned':list(owned.values())})
                if timed_out:terminate_owned(signal.SIGTERM)
                deadline=time.monotonic()+job['cleanup_grace_seconds']/2
                while process.poll() is None and time.monotonic()<deadline:observe();time.sleep(.1)
                # Reap own root and remove surviving owned workers even on normal exit.
                alive=observe()
                if alive:terminate_owned(signal.SIGTERM)
                deadline=time.monotonic()+job['cleanup_grace_seconds']/2
                while observe() and time.monotonic()<deadline:
                    process.poll();time.sleep(.1)
                if observe():terminate_owned(signal.SIGKILL)
                process.wait(timeout=1)
                remaining=observe()
        except BaseException as exc:
            error={'type':type(exc).__name__,'message':str(exc)}
            write(receipt_dir/'child_end.json',{'ended_wall':time.time(),'ended_monotonic':time.monotonic(),'error':error,'owned':list(owned.values())})
            remaining={}
            if process is not None:
                try:terminate_owned(signal.SIGKILL);process.wait(timeout=1);remaining=observe()
                except BaseException as cleanup_exc:remaining={'unknown':str(cleanup_exc)}
        result={'pid':process.pid if process else None,'returncode':process.returncode if process else None,'timeout':timed_out,'error':error,'started_wall':wall,'ended_wall':time.time(),'lease_seconds':math.ceil(time.monotonic()-started),'owned_process_tree':list(owned.values()),'owned_cleanup_pass':not remaining and (process is None or process.returncode is not None),'remaining_owned':remaining,'host_process_visibility':True,'launched':process is not None}
        write(receipt_dir/'process_cleanup.json',result)
        return result


def read_bound_job_configs(job):
    values=[]
    for path_key,hash_key in (('spec_path','spec_file_sha256'),('authorization_path','authorization_file_sha256')):
        raw=Path(job[path_key]).read_bytes()
        if not isinstance(job.get(hash_key),str) or hashlib.sha256(raw).hexdigest()!=job[hash_key]:
            raise ValueError('frozen job config bytes changed: '+path_key)
        values.append(json.loads(raw))
    return tuple(values)


def verify_completed_job(job):
    """Re-read independent root result and every copied package; exit 0 is insufficient."""
    import portable_v2
    output=Path(job['output']);spec,authorization=read_bound_job_configs(job)
    result=json.loads((output/'execution_result.json').read_text())
    independent=json.loads((output/'independent_structure.json').read_text())
    if result.get('pass') is not True or independent.get('pass') is not True or independent.get('research_eligible') is not True or independent.get('native_physical_evidence') is not True:
        raise ValueError('native independent acceptance absent/failed')
    if independent.get('root_id')!=job['root_id'] or result.get('root_id')!=job['root_id'] or len(independent.get('cells',[]))!=9:
        raise ValueError('independent root identity/matrix mismatch')
    if {k:v for k,v in result.items() if k!='copy'}!=independent:raise ValueError('execution result differs from independent root evidence')
    destination=portable_v2.origin(authorization['copy_destination']);copied=json.loads((destination/'root_manifest.json').read_text())
    registry=json.loads((destination.parent/'registry.json').read_text())
    if copied!=result.get('copy') or registry.get(str(destination))!=copied or copied.get('synthetic') is not False:
        raise ValueError('copy/registry binding mismatch')
    expected={f"{spec['root_id']}:{p['program_id']}:{r}" for p in spec['programs'] for r in spec['realizations']};observed=set()
    for relative in copied.get('relative_cell_paths',[]):
        payload=portable_v2.read(portable_v2.safe(destination,relative));m=payload['audit'];observed.add(m['cell_key'])
        if m['root_id']!=job['root_id'] or m['scene_spec_sha256']!=spec['spec_sha256'] or m.get('synthetic') is True:raise ValueError('copied cell identity/source mismatch')
        if copied['cells'].get(m['cell_key'])!=m['spec_sha256']:raise ValueError('copied nested version mismatch')
    if observed!=expected or len(copied['relative_cell_paths'])!=9:raise ValueError('copied root incomplete')
    return {'pass':True,'root_id':job['root_id'],'copied_cells':9,'original_path_fallback':False}


def validate_manifest(manifest):
    if manifest.get('execution_authorized') is not True:
        raise PermissionError('first-wave GPU execution has not been authorized')
    if manifest.get('allowed_physical_gpu_indices')!=list(range(8)) or manifest.get('root_ids')!=['F1_000001','F1_000002']:
        raise ValueError('only frozen first two F1 roots and GPU0–7 permitted')
    validate_sources(manifest)
    jobs=manifest.get('jobs',[])
    if len(jobs)!=2 or {j['root_id'] for j in jobs}!=set(manifest['root_ids']) or len({j['job_id'] for j in jobs})!=2:
        raise ValueError('first wave must bind exactly two unique root jobs')
    for job in jobs:
        for k in ('spec_path','authorization_path','output'):
            p=Path(job[k])
            if not p.is_absolute() or not p.resolve().is_relative_to(ROOT) or any(x.is_symlink() for x in [p,*p.parents] if x.is_relative_to(ROOT)):raise ValueError('unsafe job path')
        spec,authorization=read_bound_job_configs(job)
        validate_resolved(spec);validate_sources(authorization)
        if spec['root_id']!=job['root_id'] or spec['family']!='F1' or authorization.get('gpu_execution_authorized') is not True or authorization.get('spec_sha256')!=spec['spec_sha256']:
            raise ValueError('child spec/authorization mismatch')
        if any(type(job['reservation'].get(k)) is not int or job['reservation'][k]<0 for k in COUNTERS):raise ValueError('invalid job reservation')
        if type(job.get('timeout_seconds')) is not int or job['timeout_seconds']<=0 or type(job.get('cleanup_grace_seconds')) is not int or job['cleanup_grace_seconds']<4:
            raise ValueError('finite timeout/cleanup required')
        if job['timeout_seconds']+job['cleanup_grace_seconds']+job.get('lease_overhead_seconds',100)>job['reservation']['gpu_lease_seconds']:
            raise ValueError('timeout + cleanup + snapshot/reap overhead exceeds GPU lease reservation')
        if type(job.get('lease_overhead_seconds',100)) is not int or job.get('lease_overhead_seconds',100)<100:raise ValueError('at least 100 seconds bounded pre/post/reap overhead required')
        if authorization.get('job_limits')!={'timeout_seconds':job['timeout_seconds'],'cleanup_grace_seconds':job['cleanup_grace_seconds'],'gpu_reservation_seconds':job['reservation']['gpu_lease_seconds']}:raise ValueError('child limits differ from launcher reservation')
        destination=Path(authorization.get('copy_destination',''))
        if not destination.is_absolute() or not destination.resolve().is_relative_to(ROOT):raise ValueError('fixed independent copy destination required')
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


def launch_wave(manifest,state_dir,backend=None):
    jobs=validate_manifest(manifest) # Must run before snapshot, lease or ledger mutation.
    backend=backend or HostBackend();state_dir=Path(state_dir)
    if not state_dir.is_absolute() or not state_dir.resolve().is_relative_to(ROOT) or state_dir.is_symlink():raise ValueError('new workspace namespace required')
    from controlled_multi_future.redesign_f2_f3_v2.execution_ledger_v2 import ExecutionLedgerV2
    from controlled_multi_future.redesign_f2_f3_v2.gpu import assign_ready_jobs,guard_card
    existing=state_dir/'STATE.json';binding_path=state_dir/'namespace_binding.json';binding={'task_id':manifest['task_id'],'contract_sha256':hash_json(manifest)}
    if state_dir.exists() and any(state_dir.iterdir()):
        if existing.exists():
            if json.loads(existing.read_text()).get('task_id')!=manifest['task_id']:raise ValueError('foreign namespace')
        elif not binding_path.exists() or json.loads(binding_path.read_text())!=binding:raise ValueError('refuse nonempty foreign namespace before mutation')
    state_dir.mkdir(parents=True,exist_ok=True)
    if binding_path.exists() and json.loads(binding_path.read_text())!=binding:raise ValueError('namespace contract changed')
    write(binding_path,binding)
    write(state_dir/'nfs_lock_probe.json',verify_nfs_lock(state_dir))
    with (state_dir/'coordinator.lock').open('a') as coordinator:
        fcntl.flock(coordinator,fcntl.LOCK_EX|fcntl.LOCK_NB)
        contract_hash=hash_json(manifest);state_path=state_dir/'STATE.json'
        ledger=ExecutionLedgerV2(state_dir/'execution_ledger.jsonl',contract_sha256=contract_hash,task_id=manifest['task_id'],caps=manifest['budget_caps'])
        state=json.loads(state_path.read_text()) if state_path.exists() else {'task_id':manifest['task_id'],'contract_sha256':contract_hash,'jobs':{},'status':'READY'}
        if state['task_id']!=manifest['task_id'] or state['contract_sha256']!=contract_hash:raise ValueError('namespace belongs to another task')
        if any(ledger.totals()['reserved'].values()) or state['status'] in ('UNRESOLVED','BUDGET_OVERRUN','FAILED','SOURCE_CHANGED'):raise RuntimeError('unresolved reservation/overrun must be reconciled before dispatch')
        ready=[j for j in jobs if j['job_id'] not in state['jobs']]
        if not ready:return {'state':state,'results':[],'deferred_roots':[],'gpu_initialized_by_coordinator':False,'idempotent':True}
        wave=backend.snapshot();write(state_dir/'wave_snapshot.json',wave)
        assigned=assign_ready_jobs(ready,wave)['assignments'];mutex=threading.Lock();write(state_path,state)
        def run(job,assignment):
            job_id=job['job_id'];lease=None;reserved=False;safe_release=True;lease_started=None;job_directory=state_dir/'jobs'/job_id;job_directory.mkdir(parents=True,exist_ok=True)
            directory=job_directory/('attempt_'+str(1+len(list(job_directory.glob('attempt_*')))));directory.mkdir()
            try:
                if Path(job['output']).exists() and any(Path(job['output']).iterdir()):raise ValueError('fresh first-wave output is nonempty; do not re-count historical output')
                read_bound_job_configs(job)
                lease_started=time.monotonic()
                lease=backend.acquire(assignment['physical_gpu_index'],assignment['gpu_uuid'])
                pre=backend.snapshot();write(directory/'pre_snapshot.json',pre);card=guard_card(pre,assignment['physical_gpu_index'],assignment['gpu_uuid'])
                with mutex:
                    ledger.reserve(job_id,job['reservation'],idempotency_key='reserve:'+job_id)
                    reserved=True;state['jobs'][job_id]={'status':'RUNNING','root_id':job['root_id'],'gpu_uuid':card['gpu_uuid'],'physical_gpu_index':card['physical_index']};write(state_path,state)
                read_bound_job_configs(job)
                safe_release=False
                execution=backend.run(job,card,directory)
                # Required boundary is saved BEFORE CPU parsing of child receipts.
                write(directory/'end_and_cleanup_evidence.json',execution)
                post=backend.snapshot();write(directory/'post_snapshot.json',post)
                device=next(c for c in post['gpus'] if c['gpu_uuid']==card['gpu_uuid'])
                owned_pids={p['pid'] for p in execution.get('owned_process_tree',[])}
                gpu_owned_remaining=[p['pid'] for p in device.get('compute_processes',[]) if p['pid'] in owned_pids]
                cleanup=execution.get('owned_cleanup_pass') is True and execution.get('host_process_visibility') is True and not gpu_owned_remaining
                result={**execution,'device_idle_observed':device.get('independently_fresh_idle') is True,'selected_physical_index':card['physical_index'],'selected_uuid':card['gpu_uuid'],'pre_post_host_snapshots':True,'gpu_owned_remaining_pids':gpu_owned_remaining}
                if not cleanup:raise RuntimeError('owned cleanup unproven; retain reservation')
                safe_release=True
                release=backend.release(lease);lease_ended=time.monotonic();lease=None;write(directory/'lease_release.json',release)
                if release.get('released') is not True:raise RuntimeError('GPU lease release failed; retain reservation')
                result['lease_release']=release
                result['child_elapsed_seconds']=execution['lease_seconds']
                result['lease_seconds']=math.ceil(lease_ended-lease_started)
                result['coordinator_lease_interval']={'start_monotonic':lease_started,'end_monotonic':lease_ended,'includes_pre_post_snapshots':True}
                write(directory/'lease_end_evidence.json',result)
                actual=usage_from_receipts(job['output'],result['lease_seconds'])
                completion=None
                if execution['returncode']==0:
                    try:completion=verify_completed_job(job)
                    except (ValueError,OSError,KeyError,TypeError) as exc:completion={'pass':False,'error':str(exc)}
                result['independent_completion']=completion
                with mutex:
                    event=ledger.settle(job_id,job['reservation'],actual,idempotency_key='settle:'+job_id)
                    reserved=False
                    status='BUDGET_OVERRUN' if event['event_type']=='BUDGET_OVERRUN' else 'PASS' if execution['returncode']==0 and completion and completion.get('pass') is True else 'FAILED'
                    result.update(status=status,actual=actual);state['jobs'][job_id].update(result)
                    if status=='BUDGET_OVERRUN' or (status!='PASS' and state['status'] not in ('BUDGET_OVERRUN','UNRESOLVED')):state['status']=status
                    write(directory/'job_receipt.json',result);write(state_path,state)
                return result
            except BaseException as exc:
                with mutex:
                    value={'status':'UNRESOLVED' if reserved else 'DEFERRED','error':str(exc),'reservation_retained':reserved}
                    if reserved:state['status']='UNRESOLVED';state['jobs'].setdefault(job_id,{}).update(value)
                    write(directory/'job_receipt.json',value);write(state_path,state)
                return value
            finally:
                if lease is not None:
                    if safe_release:write(directory/'lease_release.json',backend.release(lease))
                    else:write(directory/'ownership_unresolved.json',{'lease_release_claimed':False,'reservation_retained':reserved,'held_until_owner_reconciliation_or_guard_process_exit':True,'physical_index':assignment['physical_gpu_index'],'gpu_uuid':assignment['gpu_uuid']})
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(run,next(j for j in ready if j['job_id']==a['job_id']),a) for a in assigned]
            results=[f.result() for f in futures]
        try:validate_sources(manifest)
        except BaseException as exc:
            state['status']='SOURCE_CHANGED';state['source_error']=str(exc);state['budget']=ledger.totals();write(state_path,state);raise
        if all(state['jobs'].get(j['job_id'],{}).get('status')=='PASS' for j in jobs):state['status']='COMPLETE'
        elif state['status']=='READY':state['status']='WAITING_IDLE_OR_READY'
        state['budget']=ledger.totals();write(state_path,state)
        return {'state':state,'results':results,'deferred_roots':[j['root_id'] for j in ready if j['root_id'] not in {a['root_id'] for a in assigned}],'gpu_initialized_by_coordinator':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True,type=Path);p.add_argument('--state-dir',required=True,type=Path);a=p.parse_args()
    result=launch_wave(json.loads(a.manifest.read_text()),a.state_dir)
    print(json.dumps({'status':result['state']['status'],'deferred_roots':result['deferred_roots']}))
    return 0 if result['state']['status']=='COMPLETE' else 1
if __name__=='__main__':raise SystemExit(main())
