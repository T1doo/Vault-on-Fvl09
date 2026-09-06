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
    m=checked(path,'manifest_sha256')
    import yaml
    auth_path=A/'EXTERNAL_NEW_F2_F3_F4B_DECISION_20260906.yaml'
    auth=yaml.safe_load(auth_path.read_text(encoding='utf-8'))
    if m['authorization_file_sha256']!=file_sha(auth_path):raise PermissionError('new decision binding')
    if auth['review_base']['vault_head']!='9ed6a353b59c39d050a6a5b0cbfdaf4c9cdff2ad' or auth['F3']['qualification']['ik_problem_cap']!=6:raise PermissionError('scope')
    cpu=__import__('json').loads((A/'F3_TOPDOWN_CLOSURE_AND_GOAL_MAPPING_V1_20260906.json').read_text(encoding='utf-8'))
    if not all(r['CPU_necessary_gate_pass'] for r in cpu['results']):raise PermissionError('closure prerequisites')
    inner=__import__('json').loads((A/'F3_TOPDOWN_INNER_SURFACE_SAME_SECTION_V1_20260906.json').read_text(encoding='utf-8'))
    if not all(r['necessary_inner_surface_gate_pass'] for r in inner['results']):raise PermissionError('inner surfaces cannot grasp same cross-section')
    if m['allowed_physical_gpu_indices']!=list(range(8)) or m['gpu_jobs_serial'] is not True:raise PermissionError('GPU scope')
    if not m['approved'] or not m['gpu_execution_authorized']:raise PermissionError('not approved')
    for field in ('stage1_authorized','formal_360_authorized','training_authorized','automatic_retry'):
        if m[field] is not False:raise PermissionError(field)
    if m['physical_execution_authorized'] is not True:raise PermissionError('new micro physical authorization')
    replacement=checked(m['replacement_authorization_path'])
    if replacement['approved'] is not True or replacement['receipt_sha256']!=m['replacement_authorization_receipt_sha256']:raise PermissionError('explicit replacement approval')
    prior=checked(m['previous_micro_terminal_path']);prior_guard=checked(m['previous_micro_guard_path'])
    if prior['receipt_sha256']!=replacement['previous_micro_terminal_receipt_sha256'] or prior['trajectory_queries']!=1 or prior['physical_attempts']!=1 or prior_guard['task_owned_cleanup_pass'] is not True:raise ValueError('retained prior attempt/accounting/cleanup')
    if replacement['new_caps']!={'scenes':1,'trajectory_queries':3,'physical_attempts':1,'IK_queries':0,'raw':0,'roots':0} or replacement['cumulative_caps']!={'scenes':4,'IK_queries':6,'trajectory_queries':4,'physical_attempt_slots':2}:raise PermissionError('replacement caps')
    qual=checked(m['qualification_terminal_path']);qguard=checked(m['qualification_guard_path'])
    if qual['qualified_recipes']!=['f3-final-pose-v3-r3063-topdown-geometry-v1'] or qual['IK_problems']!=6 or qguard['task_owned_cleanup_pass'] is not True:raise PermissionError('actual qualification/cleanup')
    for p,h in m['source_files'].items():
        if not Path(p).resolve().is_relative_to(W) or file_sha(p)!=h:raise ValueError('source changed: '+p)
    for p,h in m['input_files'].items():
        if file_sha(p)!=h:raise ValueError('input changed: '+p)
    for role,name in (('guard','guarded_launcher.py'),('runner','job_runner.py')):
        if m[role+'_script_path']!=str(RUNTIME/name) or file_sha(RUNTIME/name)!=m[role+'_script_sha256']:raise ValueError('dispatch identity')
    if len(m['jobs'])!=1:raise ValueError('one job')
    job=m['jobs'][0]
    for k,v in {'family':'F3','fresh_scene_cap':1,'trajectory_query_cap':3,'physical_attempt_cap':1,'ik_problem_cap':0,'timeout_seconds':3600}.items():
        if job[k]!=v:raise ValueError('budget '+k)
    cache=Path(m['cache_directory'])/job['job_id']
    if len(str(cache/'tmp').encode())>100:raise ValueError('TMPDIR')
    if not post and Path(job['output_namespace']).exists():raise FileExistsError('used conformance scope')
    if not runner and not post and (Path(m['guard_directory']).exists() or cache.exists()):raise FileExistsError('used Guard/cache')
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
        guard=checked(paths['guard_terminal'])
        if guard.get('child_pid') is None:
            if guard['task_owned_cleanup_pass'] is not True or cache.exists() or Path(job['output_namespace']).exists():raise ValueError('blocked dispatch cleanup')
            paths['phase_validation']={'job_succeeded':False,'resource_launch_blocked':True,'execution_budget_consumed':False}
            return {'manifest':m,'job':job,'paths':paths,'phase':phase}
        terminal=checked(Path(job['output_namespace'])/'job_terminal.json')
        if guard['task_owned_cleanup_pass'] is not True or cache.exists():raise ValueError('Guard cleanup')
        if terminal['manifest_sha256']!=m['manifest_sha256'] or terminal['scene_attempts']!=1 or terminal['physical_attempts']!=1:raise ValueError('terminal scope')
        if terminal['accounting_complete'] and (terminal['trajectory_queries']>3 or terminal['IK_problems']!=0):raise ValueError('unapproved trajectory query')
        if (guard['child_exit_code']==0)!=terminal['pass']:raise ValueError('exit propagation')
        paths['phase_validation']={'job_succeeded':terminal['pass']}
    else:raise ValueError('phase')
    return {'manifest':m,'job':job,'paths':paths,'phase':phase}
