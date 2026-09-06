"""Exact two-scene non-action subset of the existing F3 conditional decision."""
import fcntl,hashlib,importlib.util,json,os,subprocess,sys
from pathlib import Path
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';RUNTIME=Path(__file__).resolve().parent;BRIDGE=A/'f2_f3_model_bridge_v1_1'
sys.path.insert(1,str(BRIDGE));sys.path.insert(2,str(A))
GUARD_ENTRY='GUARD_ENTRY';POST_CHILD='POST_CHILD'
def file_sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical_hash(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def checked(p,key='receipt_sha256'):
    d=json.loads(Path(p).read_text(encoding='utf-8'));v=dict(d);h=v.pop(key)
    if canonical_hash(v)!=h:raise ValueError('hash mismatch: '+str(p))
    return d

def load_manifest(path,*,execution=True,runner=False,post=False):
    m=checked(path,'manifest_sha256');auth=checked(A/'EXTERNAL_EXECUTION_F2_F3_FOCUS_DECISION_V1_20260906.json')
    if m['authorization_receipt_sha256']!=auth['receipt_sha256'] or m['authorization_file_sha256']!=file_sha(A/'EXTERNAL_EXECUTION_F2_F3_FOCUS_DECISION_V1_20260906.json'):raise PermissionError('decision binding')
    parent=checked(A/'EXTERNAL_EXECUTION_DECISION_MODEL_REALIZATION_20260905_V1.json')
    if parent['receipt_sha256']!='46c42f0470fcf5be8bb34c619606c7a4d4d5b4f72827eaae13a899eec10ac09d':raise PermissionError('parent decision')
    if auth['decision']['F3']['existing_caps']['additional_non_action_conformance_scenes']!=2:raise PermissionError('conformance scene scope')
    if m['allowed_physical_gpu_indices']!=list(range(8)) or m['gpu_jobs_serial'] is not True:raise PermissionError('GPU scope')
    if not m['approved'] or not m['gpu_execution_authorized']:raise PermissionError('not approved')
    for field in ('physical_execution_authorized','stage1_authorized','formal_360_authorized','training_authorized','automatic_retry'):
        if m[field] is not False:raise PermissionError(field)
    for p,h in m['source_files'].items():
        if not Path(p).resolve().is_relative_to(W) or file_sha(p)!=h:raise ValueError('source changed: '+p)
    for p,h in m['input_files'].items():
        if file_sha(p)!=h:raise ValueError('input changed: '+p)
    for role,name in (('guard','guarded_launcher.py'),('runner','job_runner.py')):
        if m[role+'_script_path']!=str(RUNTIME/name) or file_sha(RUNTIME/name)!=m[role+'_script_sha256']:raise ValueError('dispatch identity')
    if len(m['jobs'])!=1:raise ValueError('one job')
    job=m['jobs'][0]
    for k,v in {'family':'F3','fresh_scene_cap':1,'trajectory_query_cap':0,'physical_attempt_cap':0,'states_per_scene':5,'timeout_seconds':3600}.items():
        if job[k]!=v:raise ValueError('budget '+k)
    if m['candidate_ids']!=auth['decision']['F3']['candidates']:raise ValueError('candidate order')
    cache=Path(m['cache_directory'])/job['job_id']
    if len(str(cache/'tmp').encode())>100:raise ValueError('TMPDIR')
    if not post and Path(job['output_namespace']).exists():raise FileExistsError('used conformance scope')
    if not runner and not post and (Path(m['guard_directory']).exists() or cache.exists()):raise FileExistsError('used Guard/cache')
    prior=checked(m['prior_terminal_path']);prior_guard=checked(m['prior_guard_path'])
    if prior['scene_attempts']!=1 or prior['trajectory_queries']!=0 or prior_guard['task_owned_cleanup_pass'] is not True:raise ValueError('previous scene accounting/cleanup')
    if m['previous_non_action_scenes']!=1 or m['cumulative_non_action_scene_cap']!=2:raise PermissionError('remaining scene budget')
    if m['live_scene_recipe_id']!='f3-final-pose-v3-r1401':raise PermissionError('only remaining live asset scene permitted')
    if runner:
        start_path=Path(m['guard_directory'])/(job['job_id']+'.start.json');start=checked(start_path);idx=start['physical_gpu_index']
        lease=W/'Robotwin2/gpu_leases/production_micro_gate_v1'/f'physical_gpu_{idx}.lock'
        if start['manifest_sha256']!=m['manifest_sha256'] or start['guard_pid']!=os.getppid() or start['family']!='F3':raise PermissionError('Guard parent binding')
        if os.environ.get('CUDA_VISIBLE_DEVICES')!=start['gpu_uuid'] or os.environ.get('CMF_GPU_LEASE_PATH')!=str(lease) or os.environ.get('CMF_MODEL_GUARD_START_RECEIPT')!=str(start_path) or 'LD_LIBRARY_PATH' in os.environ:raise PermissionError('Guard environment')
        with lease.open('r+') as f:
            try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:return m
            fcntl.flock(f.fileno(),fcntl.LOCK_UN)
        raise PermissionError('lease not held')
    return m

def load_and_validate_manifest_job(path,job_id,*,phase,require_execution_authorized,executable_role,executable_path):
    if require_execution_authorized is not True:raise PermissionError('authorization')
    m=load_manifest(path,post=phase==POST_CHILD);job=m['jobs'][0];g=Path(m['guard_directory']);cache=Path(m['cache_directory'])/job_id
    if job_id!=job['job_id'] or executable_role!='guard' or str(Path(executable_path).resolve())!=m['guard_script_path']:raise ValueError('job identity')
    paths={'guard_directory':str(g),'start_receipt':str(g/(job_id+'.start.json')),'guard_terminal':str(g/(job_id+'.terminal.json')),'stdout_log':str(g/(job_id+'.stdout.log')),'stderr_log':str(g/(job_id+'.stderr.log')),'output':job['output_namespace'],'cache_job':str(cache)}
    if phase==GUARD_ENTRY:
        base=W/'Robotwin2/production_micro_gate_v1/guarded_launcher.py'
        if file_sha(base)!='d666db0b9059c0abed5473024873919531dfff60d8f56346067909c357597210':raise ValueError('base Guard source')
        spec=importlib.util.spec_from_file_location('model_guard_source',base);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        project=W/'Robotwin2/project/RoboTwin'
        if module.python_tree_sha(project/'controlled_multi_future')!=m['implementation_source_sha256']:raise ValueError('active source changed')
        if subprocess.check_output(['git','-C',str(project),'rev-parse','HEAD'],text=True,timeout=20).strip()!=m['robotwin_tracked_head']:raise ValueError('official source revision changed')
        if subprocess.check_output(['git','-C',str(project),'status','--porcelain','--untracked-files=no'],text=True,timeout=20).strip():raise ValueError('official source dirty')
    elif phase==POST_CHILD:
        guard=checked(paths['guard_terminal']);terminal=checked(Path(job['output_namespace'])/'job_terminal.json')
        if guard['task_owned_cleanup_pass'] is not True or cache.exists():raise ValueError('Guard cleanup')
        if terminal['manifest_sha256']!=m['manifest_sha256'] or terminal['scene_attempts']>1 or terminal['physical_attempts']!=0:raise ValueError('terminal scope')
        if terminal['accounting_complete'] and terminal['trajectory_queries']!=0:raise ValueError('unapproved trajectory query')
        if (guard['child_exit_code']==0)!=terminal['pass']:raise ValueError('exit propagation')
        paths['phase_validation']={'job_succeeded':terminal['pass']}
    else:raise ValueError('phase')
    return {'manifest':m,'job':job,'paths':paths,'phase':phase}
