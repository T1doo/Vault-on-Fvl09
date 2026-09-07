"""Pure issuer using an external main reservation; never reserves or launches."""
import copy,re
from pathlib import Path
from goal_pilot48_v1.runtime.issue_f2_prefix_clearance import ROOT,W,sha,checked,digest
from goal_pilot48_v1.runtime_v3.migration import bindings as migrate
CAPS={'solver_problems':8,'fresh_scenes':2,'action_scenes':2,'collection_attempts':0,'gpu_lease_seconds':3780}
PARENT=ROOT/'jobs/p48_f2_prefix_clearance_001.json'

def fresh(job):
    if not re.fullmatch(r'p48_f2_on_beside_qualification_[a-z0-9_]+',job):raise ValueError('fresh two-relation qualification namespace required')
    paths=[ROOT/'jobs'/(job+'.json'),W/'Robotwin2/datasets'/job,W/'Robotwin2/datasets'/(job+'_guard'),W/'Robotwin2/datasets'/(job+'_meter'),W/'Robotwin2/cache/p48'/job]
    if any(p.exists() for p in paths):raise FileExistsError('namespace already used')
def merge_checked(dst,src):
    for p,h in src.items():
        if sha(p)!=h or p in dst and dst[p]!=h:raise ValueError('source/input hash conflict '+p)
        dst[p]=h
def parent_evidence():
    p=checked(PARENT,'manifest_sha256');data=W/'Robotwin2/datasets/p48_f2_prefix_clearance_001'
    for table in ('source_files','input_files'):
        for filename,h in p[table].items():
            if sha(filename)!=h:raise ValueError('frozen parent dependency changed '+filename)
    gp=data.with_name(data.name+'_guard')/'p48_f2_prefix_clearance_001.terminal.json'
    goal=checked(data/'goal_terminal.json');local=checked(data/'job_terminal.json');guard=checked(gp)
    for r in (goal,guard):
        if r['manifest_sha256']!=p['manifest_sha256'] or r['job_id']!='p48_f2_prefix_clearance_001':raise ValueError('parent identity mismatch')
    nested=goal['runtime_result'];payload=dict(nested);h=payload.pop('receipt_sha256')
    if digest(payload)!=h or nested['parent_runtime_receipt_sha256']!=local['receipt_sha256'] or local['manifest_sha256']!=p['manifest_sha256']:raise ValueError('parent nested receipt mismatch')
    if not all((goal['pass'],goal['accounting_complete'],nested['scientific_route_pass'],local['prefix_physical_pass'],local['scientific_route_pass'],guard['task_owned_cleanup_pass'],guard['gpu_returned_to_idle_baseline'],guard['lease_released'])):raise ValueError('parent physical/accounting/cleanup incomplete')
    if goal['resource_counts']!={'solver_problems':3,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0}:raise ValueError('parent counts changed')
    return p,[PARENT,data/'goal_terminal.json',data/'job_terminal.json',gp]

def build_manifest(job_id,reservation):
    fresh(job_id)
    if reservation.get('kind')!='RESERVE' or reservation.get('job_id')!=job_id or reservation.get('reserved')!=CAPS or not reservation.get('event_sha256'):raise ValueError('exact external reservation required')
    from goal_pilot48_v1.f2_on_beside_qualification_v1.spec import build_spec
    spec=build_spec();p,inputs=parent_evidence();m=copy.deepcopy(p);m.pop('manifest_sha256');m.update(migrate(p))
    root=ROOT/'f2_on_beside_qualification_v1'
    sources=[*root.glob('*.py'),*(ROOT/'f2_on_beside_runtime_v1').glob('*.py'),ROOT/'f2_controlled_inside_runtime_v2/live_models.py',Path(__file__).resolve()]
    # Shared model helper is reused without calling any inside rule/spec.
    merge_checked(m['source_files'],{str(q):sha(q) for q in sources})
    merge_checked(m['input_files'],spec['prefix_lineage']['files'])
    merge_checked(m['input_files'],{str(q):sha(q) for q in inputs+[ROOT/'f2_on_beside_impact_review_v1/REPORT.md']})
    m.update(run_id=job_id,parent_job_id='p48_f2_prefix_clearance_001',failure_class='F2_on_beside_fresh_physical_qualification',
      reserved=dict(CAPS),reservation_event_sha256=reservation['event_sha256'],guard_directory=str(W/'Robotwin2/datasets'/(job_id+'_guard')),
      on_beside_qualification_spec_sha256=digest(spec),high_level_state_check_cap=16,high_level_state_check_breakdown={'on':6,'beside':10},
      qualification_relation_order=['on','beside'],stop_on_first_required_failure=True,inside_contact_permission_used=False,
      whole_root_qualification_complete=False,prefix_replayed_not_requalified=True,physical_Gates_changed=False,
      allowed_physical_gpu_indices=list(range(8)),issuance='ISSUED_UNDER_USER_GOAL',gpu_execution_authorized=True,approved=True)
    m['jobs']=[{'job_id':job_id,'family':'F2','kind':'F2_ON_BESIDE_TWO_FRESH_QUALIFICATION','output_namespace':str(W/'Robotwin2/datasets'/job_id),
      'timeout_seconds':3600,'requires_live_meter':True,'runtime_module':'goal_pilot48_v1.f2_on_beside_qualification_v1.runner_bridge',
      'runtime_file':str(root/'runner_bridge.py'),'test_module':'goal_pilot48_v1.f2_on_beside_qualification_v1.test_all',
      'resource_caps':{k:v for k,v in CAPS.items() if k!='gpu_lease_seconds'}}]
    m['manifest_sha256']=digest(m);return m
def issue_from_reservation(job_id,reservation):return build_manifest(job_id,reservation)
