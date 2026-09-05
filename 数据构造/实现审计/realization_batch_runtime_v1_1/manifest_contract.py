"""Exact conditional development-batch adapter for the existing GPU Guard."""
import os,fcntl,subprocess,importlib.util
from pathlib import Path
from catalog import W,A,AUTH,SOURCE_SHA,canonical,sha,check,read,build_catalog
GUARD_ENTRY='GUARD_ENTRY';POST_CHILD='POST_CHILD'
canonical_hash=canonical;file_sha=sha
RUNTIME=Path(__file__).resolve().parent
BASE=W/'Robotwin2/production_micro_gate_v1/guarded_launcher.py'
BASE_SHA='d666db0b9059c0abed5473024873919531dfff60d8f56346067909c357597210'
SOURCE_NAMES=('catalog.py','retiming.py','pipeline.py','job_runner.py','guarded_launcher.py','manifest_contract.py','test_cpu.py')

def load_manifest(path,*,execution=True,runner=False,post=False):
    # V1 stopped at a consumed first-cell attempt. This CPU-only recovery
    # version has no execution approval and cannot reuse the old decision.
    if execution:raise PermissionError('V1.1 recovery execution awaits exact replacement/resume approval; old V1 decision cannot be reissued')
    m=check(path,'manifest_sha256');auth=check(AUTH)
    if m['authorization_receipt_sha256']!=auth['receipt_sha256'] or m['authorization_file_sha256']!=sha(AUTH):raise PermissionError('authorization changed')
    msg=auth['authoritative_message']
    if sha(msg['path'])!=msg['file_sha256']:raise PermissionError('review bytes changed')
    decision=auth['decision']['downstream']['conditional_development_realization_batch']
    for k,v in {'rollout_cap':9,'fresh_scene_cap':9,'planner_query_cap':156,'max_attempts_per_cell':1,'automatic_retry':False,'automatic_stage1_promotion':False}.items():
        if decision.get(k)!=v:raise PermissionError('decision mismatch: '+k)
    for k in ('approved','gpu_execution_authorized','planner_execution_authorized','scene_execution_authorized','physical_execution_authorized'):
        if m.get(k) is not True:raise PermissionError(k)
    for k in ('stage1_authorized','formal_360_authorized','training_authorized','h_reveal_authorized','compression_authorized','pi05_authorized','automatic_retry'):
        if m.get(k) is not False:raise PermissionError(k)
    if m['allowed_physical_gpu_indices']!=list(range(8)) or m['gpu_jobs_serial'] is not True:raise ValueError('GPU scope')
    if set(m['source_files'])!={str(RUNTIME/n) for n in SOURCE_NAMES}:raise ValueError('runtime source set')
    for source,digest in {**m['source_files'],**m['publication_source_files'],**m['asset_files']}.items():
        if not Path(source).resolve().is_relative_to(W) or sha(source)!=digest:raise ValueError('changed source: '+source)
    for role,name in (('guard','guarded_launcher.py'),('runner','job_runner.py')):
        if m[role+'_script_path']!=str(RUNTIME/name) or m[role+'_script_sha256']!=sha(RUNTIME/name):raise ValueError('dispatch')
    if sha(m['catalog_path'])!=m['catalog_file_sha256']:raise ValueError('catalog bytes')
    c=check(m['catalog_path'])
    if c!=build_catalog() or c['derived_query_cap']!=123:raise ValueError('live parent/spec/budget mismatch')
    if len(m['jobs'])!=1:raise ValueError('one serial job')
    j=m['jobs'][0]
    for k,v in {'family':'F1_F4','planner_query_cap':123,'fresh_scene_cap':9,'rollout_cap':9,'max_attempts_per_cell':1,'timeout_seconds':21600}.items():
        if j.get(k)!=v:raise ValueError('job contract: '+k)
    for target in (j['output_namespace'],m['guard_directory'],m['cache_directory']):
        if not Path(target).resolve().is_relative_to(W/'Robotwin2'):raise ValueError('path boundary')
    cache=Path(m['cache_directory'])/j['job_id']
    if len(str(cache/'tmp').encode())>100:raise ValueError('TMPDIR too long')
    if not post and Path(j['output_namespace']).exists():raise FileExistsError('batch attempt already consumed')
    if not runner and not post and (Path(m['guard_directory']).exists() or cache.exists()):raise FileExistsError('Guard/cache already consumed')
    if m['implementation_source_sha256']!=SOURCE_SHA:raise ValueError('active source binding')
    if runner:verify_runner_lease(m)
    return m

def verify_runner_lease(m):
    job=m['jobs'][0];path=Path(m['guard_directory'])/(job['job_id']+'.start.json');start=check(path)
    idx=start['physical_gpu_index'];expected=W/'Robotwin2/gpu_leases/production_micro_gate_v1'/f'physical_gpu_{idx}.lock'
    if idx not in range(8) or start['manifest_sha256']!=m['manifest_sha256'] or start['job_id']!=job['job_id']:raise PermissionError('Guard identity')
    if start['family']!=job['family'] or start['guard_pid']!=os.getppid():raise PermissionError('Guard parent')
    if os.environ.get('CUDA_VISIBLE_DEVICES')!=start['gpu_uuid'] or 'LD_LIBRARY_PATH' in os.environ:raise PermissionError('GPU environment')
    if os.environ.get('CMF_GPU_LEASE_PATH')!=str(expected) or start['lease_path']!=str(expected):raise PermissionError('lease binding')
    if os.environ.get('CMF_REALIZATION_GUARD_START_RECEIPT')!=str(path):raise PermissionError('start binding')
    with expected.open('r+') as f:
        try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return True
        fcntl.flock(f.fileno(),fcntl.LOCK_UN)
    raise PermissionError('Guard lease not held')

def validate_terminal(t):
    if not 0<=t['fresh_scene_attempts']<=9 or not 0<=t['raw_trajectory_count']<=9:raise ValueError('scene/raw budget')
    if t['accounting_complete']:
        if type(t['planner_queries']) is not int or not 0<=t['planner_queries']<=123:raise ValueError('query budget')
        if len(t['cells'])!=t['fresh_scene_attempts'] or sum(c['planner_query_delta'] for c in t['cells'])!=t['planner_queries']:raise ValueError('live accounting')
    elif t['planner_queries'] is not None or t['global_stop'] is not True or t['pass'] is not False:raise ValueError('unknown accounting must stop')
    for k in ('new_independent_root_count','stage1_accepted_trajectory_count','formal_trajectory_count'):
        if t[k]!=0:raise ValueError('unauthorized denominator')
    passed=t['error'] is None and not t['global_stop'] and t['accounting_complete'] and len(t['cells'])==9 and len(t['cohorts'])==3 and all(c['status']=='accepted' for c in t['cohorts'])
    if t['pass'] is not passed:raise ValueError('success classification')
    return passed

def load_and_validate_manifest_job(path,job_id,*,phase,require_execution_authorized,executable_role,executable_path):
    if require_execution_authorized is not True:raise PermissionError('execution approval required')
    m=load_manifest(path,post=phase==POST_CHILD);job=m['jobs'][0]
    if job_id!=job['job_id'] or executable_role!='guard' or str(Path(executable_path).resolve())!=m['guard_script_path']:raise ValueError('dispatch identity')
    g=Path(m['guard_directory']);cache=Path(m['cache_directory'])/job_id
    paths={'guard_directory':str(g),'start_receipt':str(g/(job_id+'.start.json')),'guard_terminal':str(g/(job_id+'.terminal.json')),
        'stdout_log':str(g/(job_id+'.stdout.log')),'stderr_log':str(g/(job_id+'.stderr.log')),'output':job['output_namespace'],'cache_job':str(cache)}
    if phase==GUARD_ENTRY:
        if sha(BASE)!=BASE_SHA:raise ValueError('Guard primitives source')
        spec=importlib.util.spec_from_file_location('realization_guard_source_check',BASE);base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
        project=W/'Robotwin2/project/RoboTwin'
        if base.python_tree_sha(project/'controlled_multi_future')!=SOURCE_SHA:raise ValueError('active source tree')
        def git(*args):return subprocess.check_output(['git','-C',str(project),*args],text=True,timeout=20).strip()
        if git('rev-parse','HEAD')!=m['robotwin_tracked_head'] or git('status','--porcelain','--untracked-files=no'):raise ValueError('official tracked tree')
    elif phase==POST_CHILD:
        guard=check(paths['guard_terminal']);terminal=check(Path(job['output_namespace'])/'job_terminal.json')
        if guard['manifest_sha256']!=m['manifest_sha256'] or terminal['manifest_sha256']!=m['manifest_sha256']:raise ValueError('terminal binding')
        if guard['task_owned_cleanup_pass'] is not True or cache.exists():raise ValueError('Guard cleanup')
        success=validate_terminal(terminal)
        for cohort in terminal['cohorts']:
            if sha(cohort['root_receipt_path'])!=cohort['root_receipt_file_sha256']:raise ValueError('cohort disk changed')
            if cohort['status']=='accepted':
                import sys
                sys.path.insert(0,str(A/'downstream_cpu_source_v1_20260905'))
                from cmf_downstream_cpu.collector_publication import audit_completed_root
                audit_completed_root(Path(cohort['root_receipt_path']).parent)
        if (guard['child_exit_code']==0)!=success:raise ValueError('exit propagation')
        paths['phase_validation']={'job_succeeded':success}
    else:raise ValueError('phase')
    return {'manifest':m,'job':job,'paths':paths,'phase':phase}
