"""One parent Goal authority and one active reservation, not per-stage GPT approval."""
import hashlib,json,sys,fcntl,os,subprocess,importlib.util
from pathlib import Path
RUNTIME=Path(__file__).resolve().parent;ROOT=RUNTIME.parent;A=ROOT.parent;W=Path('/nfs_share/lijunhui');P=W/'Robotwin2/project/RoboTwin'
sys.path.insert(1,str(A));sys.path.insert(2,str(P))
GUARD_ENTRY='GUARD_ENTRY';POST_CHILD='POST_CHILD'
def canonical_hash(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def file_sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def checked(p,key='receipt_sha256'):
    d=json.loads(Path(p).read_text(encoding='utf-8'));v=dict(d);h=v.pop(key)
    if canonical_hash(v)!=h:raise ValueError('hash mismatch '+str(p))
    return d
def load_manifest(path,*,execution=True,runner=False,post=False):
    from budget import snapshot,rows
    m=checked(path,'manifest_sha256');c=checked(ROOT/'CONTRACT.json')
    if m['goal_contract_receipt_sha256']!=c['receipt_sha256'] or not c['adopted_by_user_goal'] or file_sha(ROOT/'USER_GOAL_SOURCE.md')!=c['source_file_sha256']:raise PermissionError('Goal authority/source')
    if m['issuance']!='ISSUED_UNDER_USER_GOAL' or not m['approved'] or not m['gpu_execution_authorized']:raise PermissionError('not issued under user Goal')
    if m['allowed_physical_gpu_indices']!=list(range(8)) or not m['gpu_jobs_serial']:raise PermissionError('GPU scope')
    if any(m[k] for k in ('formal_360_authorized','training_authorized','stage0_reopened')):raise PermissionError('out-of-scope scientific execution')
    if len(m['jobs'])!=1:raise ValueError('one job')
    job=m['jobs'][0];snap=snapshot()
    reservation=next((r for r in rows() if r['kind']=='RESERVE' and r['job_id']==job['job_id']),None)
    if reservation is None or reservation['event_sha256']!=m['reservation_event_sha256'] or reservation['reserved']!=m['reserved']:raise PermissionError('reservation binding')
    if not post and job['job_id'] not in snap['active_reservations']:raise PermissionError('job reservation no longer active')
    if job['resource_caps']!={k:v for k,v in m['reserved'].items() if k!='gpu_lease_seconds'}:raise ValueError('job caps differ from reservation')
    for field in ('source_files','input_files'):
        for p,h in m[field].items():
            if not Path(p).resolve().is_relative_to(W) or file_sha(p)!=h:raise ValueError('changed bound file '+p)
    for role,name in (('guard','guarded_launcher.py'),('runner','job_runner.py')):
        if m[role+'_script_path']!=str(RUNTIME/name) or file_sha(RUNTIME/name)!=m[role+'_script_sha256']:raise ValueError('entry identity')
    out=Path(job['output_namespace']);g=Path(m['guard_directory']);cache=Path(m['cache_directory'])/job['job_id']
    if not out.is_relative_to(W/'Robotwin2/datasets') or len(str(cache/'tmp').encode())>100:raise ValueError('output/cache boundary')
    if not post and out.exists():raise FileExistsError('output namespace used')
    if not runner and not post and (g.exists() or cache.exists()):raise FileExistsError('Guard/cache namespace used')
    if runner:
        start_path=g/(job['job_id']+'.start.json');start=checked(start_path);idx=start['physical_gpu_index'];lease=W/'Robotwin2/gpu_leases/production_micro_gate_v1'/f'physical_gpu_{idx}.lock'
        if start['manifest_sha256']!=m['manifest_sha256'] or start['guard_pid']!=os.getppid():raise PermissionError('Guard parent')
        if os.environ.get('CUDA_VISIBLE_DEVICES')!=start['gpu_uuid'] or os.environ.get('CMF_GPU_LEASE_PATH')!=str(lease) or 'LD_LIBRARY_PATH' in os.environ:raise PermissionError('Guard environment')
        with lease.open('r+') as f:
            try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:return m
            fcntl.flock(f.fileno(),fcntl.LOCK_UN)
        raise PermissionError('lease not held')
    return m
def load_and_validate_manifest_job(path,job_id,*,phase,require_execution_authorized,executable_role,executable_path):
    if not require_execution_authorized:raise PermissionError('authorization required')
    m=load_manifest(path,post=phase==POST_CHILD);job=m['jobs'][0];g=Path(m['guard_directory']);cache=Path(m['cache_directory'])/job_id
    if job_id!=job['job_id'] or executable_role!='guard' or str(Path(executable_path).resolve())!=m['guard_script_path']:raise ValueError('dispatch mismatch')
    paths={'guard_directory':str(g),'start_receipt':str(g/(job_id+'.start.json')),'guard_terminal':str(g/(job_id+'.terminal.json')),'stdout_log':str(g/(job_id+'.stdout.log')),'stderr_log':str(g/(job_id+'.stderr.log')),'output':job['output_namespace'],'cache_job':str(cache)}
    if phase==GUARD_ENTRY:
        base=W/'Robotwin2/production_micro_gate_v1/guarded_launcher.py'
        if file_sha(base)!='d666db0b9059c0abed5473024873919531dfff60d8f56346067909c357597210':raise ValueError('base Guard source')
        s=importlib.util.spec_from_file_location('goal_base_guard',base);b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
        if b.python_tree_sha(P/'controlled_multi_future')!=m['implementation_source_sha256']:raise ValueError('active implementation changed')
        if subprocess.check_output(['git','-C',str(P),'rev-parse','HEAD'],text=True,timeout=20).strip()!=m['robotwin_tracked_head']:raise ValueError('official HEAD')
        if subprocess.check_output(['git','-C',str(P),'status','--porcelain','--untracked-files=no'],text=True,timeout=20).strip():raise ValueError('official source dirty')
    elif phase==POST_CHILD:
        guard=checked(paths['guard_terminal'])
        if not guard['task_owned_cleanup_pass'] or cache.exists():raise ValueError('task cleanup not verified')
        if guard['child_pid'] is None:
            paths['phase_validation']={'job_succeeded':False,'resource_launch_blocked':True};return {'manifest':m,'job':job,'paths':paths,'phase':phase}
        terminal=checked(Path(job['output_namespace'])/'goal_terminal.json')
        if terminal['manifest_sha256']!=m['manifest_sha256'] or not terminal['accounting_complete']:raise ValueError('Goal accounting incomplete')
        if any(terminal['resource_counts'][k]>job['resource_caps'][k] for k in job['resource_caps']):raise ValueError('Goal cap exceeded')
        if (guard['child_exit_code']==0)!=terminal['pass']:raise ValueError('exit mismatch')
        paths['phase_validation']={'job_succeeded':terminal['pass']}
    else:raise ValueError('phase')
    return {'manifest':m,'job':job,'paths':paths,'phase':phase}
