"""Pure main-scheduler F2 model-applicability revision1 builder; no reserve."""
import copy,hashlib,json,re
from pathlib import Path
from goal_pilot48_v1.runtime_v3.migration import bindings as migrate
ROOT=Path(__file__).resolve().parents[1];W=Path('/nfs_share/lijunhui')
CAPS=dict(solver_problems=3,fresh_scenes=1,action_scenes=1,collection_attempts=0,gpu_lease_seconds=1980)
PARENT=ROOT/'jobs/p48_f2_prefix_001.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def checked(p,key='receipt_sha256'):
    d=read(p);v=dict(d);h=v.pop(key)
    if digest(v)!=h:raise ValueError('self hash mismatch '+str(p))
    return d
def fresh(job):
    if not re.fullmatch(r'p48_f2_prefix_clearance_[a-z0-9_]+',job):raise ValueError('new clearance namespace required')
    paths=[ROOT/'jobs'/(job+'.json'),W/'Robotwin2/datasets'/job,W/'Robotwin2/datasets'/(job+'_guard'),W/'Robotwin2/datasets'/(job+'_meter'),W/'Robotwin2/cache/p48'/job]
    if any(p.exists() for p in paths):raise FileExistsError('clearance namespace consumed')

def build_manifest(job_id,reservation):
    fresh(job_id)
    if reservation.get('kind')!='RESERVE' or reservation.get('job_id')!=job_id or reservation.get('reserved')!=CAPS or not reservation.get('event_sha256'):raise ValueError('exact external reservation required')
    from goal_pilot48_v1.f2_prefix_clearance_runtime_v2.runtime import build_prefix_spec
    p=checked(PARENT,'manifest_sha256');data=W/'Robotwin2/datasets/p48_f2_prefix_001'
    terminal=checked(data/'goal_terminal.json');local=checked(data/'job_terminal.json');guard_path=data.with_name(data.name+'_guard')/'p48_f2_prefix_001.terminal.json';guard=checked(guard_path)
    if terminal['manifest_sha256']!=p['manifest_sha256'] or terminal['job_id']!='p48_f2_prefix_001' or not terminal['accounting_complete']:raise ValueError('parent Goal terminal binding/accounting')
    if guard['manifest_sha256']!=p['manifest_sha256'] or guard['job_id']!='p48_f2_prefix_001' or not guard['task_owned_cleanup_pass']:raise ValueError('parent Guard cleanup/identity')
    if local['trajectory_queries']!=2 or local['prefix_physical_pass'] or local['error']['message']!='new target has no native supported-table witness':raise ValueError('unexpected parent failure; review before revision')
    m=copy.deepcopy(p);m.pop('manifest_sha256');m.update(migrate(p))
    root=ROOT/'f2_prefix_clearance_runtime_v2'
    for q in root.glob('*.py'):m['source_files'][str(q)]=sha(q)
    m['source_files'][str(Path(__file__).resolve())]=sha(__file__)
    inputs=[PARENT,data/'goal_terminal.json',data/'job_terminal.json',guard_path,data/'partial_prefix_trace.npz',data/'prefix_open_model.json',ROOT/'f2_prefix_postclose_review_v1/analysis.json',ROOT/'f2_prefix_postclose_review_v1/RECOMMENDATION.md']
    for q in inputs:m['input_files'][str(q)]=sha(q)
    m.update(run_id=job_id,parent_job_id='p48_f2_prefix_001',failure_class='F2_postclose_model_applicability',evidence_based_revision=1,
      reserved=dict(CAPS),reservation_event_sha256=reservation['event_sha256'],guard_directory=str(W/'Robotwin2/datasets'/(job_id+'_guard')),
      f2_goal_prefix_spec_sha256=digest(build_prefix_spec()),model_applicability_revision=1,physical_Gates_changed=False,
      high_level_state_check_cap=6,high_level_state_checks_are_solver_problems=False,
      high_level_state_check_breakdown=dict(full=2,conditional_pair=2,restored_full=2))
    m['jobs']=[dict(job_id=job_id,family='F2',kind='F2_REAL_PREFIX_CLEARANCE_REVISION1',output_namespace=str(W/'Robotwin2/datasets'/job_id),timeout_seconds=1800,
      requires_live_meter=True,runtime_module='goal_pilot48_v1.f2_prefix_clearance_runtime_v2.runner_bridge',runtime_file=str(root/'runner_bridge.py'),
      test_module='goal_pilot48_v1.f2_prefix_clearance_runtime_v2.test_all',resource_caps={k:v for k,v in CAPS.items() if k!='gpu_lease_seconds'})]
    m['manifest_sha256']=digest(m);return m

def issue_from_reservation(job_id,reservation):return build_manifest(job_id,reservation)
