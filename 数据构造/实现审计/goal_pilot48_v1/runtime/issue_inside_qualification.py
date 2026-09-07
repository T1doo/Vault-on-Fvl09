"""Pure builder: a supplied main-thread reservation, never reserve here."""
import copy,re
from pathlib import Path
from goal_pilot48_v1.runtime.issue_f2_prefix_clearance import sha,read,checked,digest,ROOT,W
from goal_pilot48_v1.runtime_v3.migration import bindings as migrate

CAPS={'solver_problems':5,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0,'gpu_lease_seconds':1980}
PARENT=ROOT/'jobs/p48_f2_prefix_clearance_001.json'

def fresh(job):
    if not re.fullmatch(r'p48_f2_inside_qualification_[a-z0-9_]+',job):raise ValueError('new inside qualification namespace required')
    paths=[ROOT/'jobs'/(job+'.json'),W/'Robotwin2/datasets'/job,W/'Robotwin2/datasets'/(job+'_guard'),W/'Robotwin2/datasets'/(job+'_meter'),W/'Robotwin2/cache/p48'/job]
    if any(p.exists() for p in paths):raise FileExistsError('qualification namespace consumed')

def merge_checked(dst,src):
    for p,h in src.items():
        if sha(p)!=h or p in dst and dst[p]!=h:raise ValueError('source/input hash conflict '+p)
        dst[p]=h

def build_preview(job_id):
    """CPU-only dependency/shape review; invalid for Guard or job issuance."""
    fresh(job_id)
    from goal_pilot48_v1.inside_qualification_runtime_v1.spec import build_spec
    from goal_pilot48_v1.f2_controlled_inside_runtime_v2.dependencies import additional_bindings
    p=checked(PARENT,'manifest_sha256')
    for table in ('source_files','input_files'):
        for filename,h in p[table].items():
            if sha(filename)!=h:raise ValueError('frozen parent dependency changed '+filename)
    data=W/'Robotwin2/datasets/p48_f2_prefix_clearance_001';guard_path=data.with_name(data.name+'_guard')/'p48_f2_prefix_clearance_001.terminal.json'
    goal=checked(data/'goal_terminal.json');local=checked(data/'job_terminal.json');guard=checked(guard_path)
    for receipt in (goal,guard):
        if receipt['manifest_sha256']!=p['manifest_sha256'] or receipt['job_id']!='p48_f2_prefix_clearance_001':raise ValueError('parent execution identity mismatch')
    nested=goal['runtime_result'];payload=dict(nested);nested_sha=payload.pop('receipt_sha256')
    if digest(payload)!=nested_sha or nested['parent_runtime_receipt_sha256']!=local['receipt_sha256'] or local['manifest_sha256']!=p['manifest_sha256']:raise ValueError('parent nested runtime/local identity mismatch')
    if not goal['pass'] or not goal['accounting_complete'] or not nested['scientific_route_pass'] or not local['prefix_physical_pass'] or not local['scientific_route_pass'] or not guard['task_owned_cleanup_pass'] or not guard['gpu_returned_to_idle_baseline']:raise ValueError('parent qualification/cleanup incomplete')
    if goal['resource_counts']!={'solver_problems':3,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0}:raise ValueError('parent finite counts changed')
    m=copy.deepcopy(p);m.pop('manifest_sha256');m.update(migrate(p));extra=additional_bindings()
    merge_checked(m['source_files'],extra['additional_source_files']);merge_checked(m['input_files'],extra['additional_input_files'])
    root=ROOT/'inside_qualification_runtime_v1'
    merge_checked(m['source_files'],{str(q):sha(q) for q in [*root.glob('*.py'),Path(__file__).resolve()]})
    merge_checked(m['input_files'],{str(q):sha(q) for q in [PARENT,data/'goal_terminal.json',data/'job_terminal.json',guard_path]})
    m.pop('reserved',None);m.pop('reservation_event_sha256',None)
    m.update(run_id=job_id,parent_job_id='p48_f2_prefix_clearance_001',failure_class='F2_inside_controlled_native_floor_qualification',proposed_caps=dict(CAPS),
      issuance='CPU_ONLY_NONISSUED_PREVIEW',approved=False,physical_execution_authorized=False,
      gpu_execution_authorized=False,pilot_input_authorized=False,collection_authorized=False,contact_permission_pending=True,
      guard_directory=str(W/'Robotwin2/datasets'/(job_id+'_guard')),
      inside_qualification_spec_sha256=digest(build_spec()),high_level_state_check_cap=10,
      high_level_state_check_breakdown={'carried_initial':2,'carried_after_lift':2,'floor_full':2,'floor_pair':2,'released_full':2},
      prefix_replayed_not_requalified=True,whole_root_qualification_complete=False,
      verifier_version='f2_inside_native_envelope_piecewise_floor_v1',physical_numeric_thresholds_changed=False)
    m['jobs']=[{'job_id':job_id,'family':'F2','kind':'F2_CONTROLLED_INSIDE_QUALIFICATION','output_namespace':str(W/'Robotwin2/datasets'/job_id),
      'timeout_seconds':1800,'requires_live_meter':True,'runtime_module':'goal_pilot48_v1.inside_qualification_runtime_v1.runner_bridge',
      'runtime_file':str(root/'runner_bridge.py'),'test_module':'goal_pilot48_v1.inside_qualification_runtime_v1.test_all',
      'resource_caps':{k:v for k,v in CAPS.items() if k!='gpu_lease_seconds'}}]
    m['manifest_sha256']=digest(m);return m

def build_manifest(job_id,reservation):
    raise PermissionError('inside controlled held box9 contact permission pending; automatic Goal continuation cannot issue')

def issue_from_reservation(job_id,reservation):return build_manifest(job_id,reservation)
