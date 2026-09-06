"""Main scheduler-only finite subjob issuance under the adopted Goal."""
import json,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from budget import ROOT,read,digest,atomic,reserve
W=Path('/nfs_share/lijunhui');A=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def issue_f3_micro(job_id):
    contract=read(ROOT/'CONTRACT.json');caps={'solver_problems':3,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0,'gpu_lease_seconds':1080}
    event=reserve(job_id,caps,'F3 support-aware micro; unchanged physics gates; first or repeated fresh-scene confirmation')
    parent=read(A/'F3_R3063_BOOTSTRAP_REPLACEMENT_MANIFEST_V1_20260906.json')
    sources=dict(parent['source_files'])
    for folder in [ROOT/'runtime',ROOT/'f3_runtime_v1',A/'support_pair_collision_v1']:
        for p in folder.glob('*.py'):sources[str(p)]=sha(p)
    runtime=ROOT/'runtime';m={'schema_version':'cmf_goal_subjob_manifest_v1','goal_id':contract['goal_id'],'goal_contract_receipt_sha256':contract['receipt_sha256'],'issuance':'ISSUED_UNDER_USER_GOAL','approved':True,'gpu_execution_authorized':True,'physical_execution_authorized':True,
        'allowed_physical_gpu_indices':list(range(8)),'gpu_jobs_serial':True,'formal_360_authorized':False,'training_authorized':False,'stage0_reopened':False,'stage1_authorized':False,'pilot_input_authorized':True,
        'run_id':job_id,'reservation_event_sha256':event['event_sha256'],'reserved':caps,'guard_directory':str(W/'Robotwin2/datasets'/(job_id+'_guard')),'cache_directory':str(W/'Robotwin2/cache/p48'),
        'implementation_source_sha256':parent['implementation_source_sha256'],'robotwin_tracked_head':parent['robotwin_tracked_head'],'source_files':sources,'input_files':dict(parent['input_files']),
        'initialization_policy':'skip dummy MotionGen.warmup, log separately; real planner lazy initialization; no task solves omitted',
        'jobs':[{'job_id':job_id,'family':'F3','kind':'F3_MICRO','runtime_module':'goal_pilot48_v1.f3_runtime_v1.micro','runtime_file':str(ROOT/'f3_runtime_v1/micro.py'),'test_module':'goal_pilot48_v1.f3_runtime_v1.test_lifecycle','output_namespace':str(W/'Robotwin2/datasets'/job_id),'timeout_seconds':900,'resource_caps':{k:v for k,v in caps.items() if k!='gpu_lease_seconds'}}]}
    m['input_files'][str(ROOT/'CONTRACT.json')]=sha(ROOT/'CONTRACT.json');m['input_files'][str(ROOT/'USER_GOAL_SOURCE.md')]=sha(ROOT/'USER_GOAL_SOURCE.md')
    for role,name in [('guard','guarded_launcher.py'),('runner','job_runner.py')]:m[role+'_script_path']=str(runtime/name);m[role+'_script_sha256']=sha(runtime/name)
    m['manifest_sha256']=digest(m);path=ROOT/'jobs'/(job_id+'.json');path.parent.mkdir(exist_ok=True)
    if path.exists():raise FileExistsError('manifest exists')
    atomic(path,m);print(str(path));return m
if __name__=='__main__':issue_f3_micro(sys.argv[1])
