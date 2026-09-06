"""Pure F2 U-route manifest builder; issue() is main-scheduler-only."""
import copy,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
W=Path('/nfs_share/lijunhui'); PARENT=ROOT/'jobs/p48_f2_revision1_001.json'
CAPS={'solver_problems':7,'fresh_scenes':1,'action_scenes':0,'collection_attempts':0,'gpu_lease_seconds':1980}
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def checked(p,key='receipt_sha256'):
    v=read(p);c=dict(v);h=c.pop(key)
    if digest(c)!=h:raise ValueError('self-hash changed '+str(p))
    return v

def merge_verified(parent,additions):
    merged=dict(parent)
    for p,h in parent.items():
        if not Path(p).resolve().is_relative_to(W) or sha(p)!=h:raise ValueError('parent dependency changed '+p)
    for p,h in additions.items():
        if p in merged and merged[p]!=h:raise ValueError('dependency hash conflict '+p)
        if not Path(p).resolve().is_relative_to(W) or sha(p)!=h:raise ValueError('addition dependency changed '+p)
        merged[p]=h
    return merged

def build_manifest(job_id,reservation):
    if not re.fullmatch(r'p48_f2_u_route_[a-z0-9_]+',job_id):raise ValueError('new U-route job namespace required')
    if reservation.get('kind')!='RESERVE' or reservation.get('job_id')!=job_id or reservation.get('reserved')!=CAPS:raise ValueError('exact U-route reservation required')
    from goal_pilot48_v1.f2_inward_runtime_v3.dependencies import additional_bindings
    from goal_pilot48_v1.f2_inward_runtime_v3.contract import build_contract,parent_contract
    additions=additional_bindings();parent=checked(PARENT,'manifest_sha256');m=copy.deepcopy(parent);m.pop('manifest_sha256')
    for field in ('source_files','input_files'):
        m[field]=merge_verified(parent[field],additions['additional_'+field])
    current=build_contract();old=parent_contract()
    if current['binding']!=old['binding'] or current['planned']!=old['planned'] or current['inward_goals']['D_new']!=old['inward_goals']['D_new']:raise ValueError('D/layout/seed changed')
    if parent['reserved']!=CAPS or parent['jobs'][0]['timeout_seconds']!=1800:raise ValueError('parent finite budget mismatch')
    # The parent qualification is evidence, never a substitute for this run's
    # three fresh endpoint calls. Bind its actual pass and cleanup receipts.
    data=W/'Robotwin2/datasets/p48_f2_revision1_001'
    terminal=checked(data/'goal_terminal.json')
    guard_path=data.with_name(data.name+'_guard')/'p48_f2_revision1_001.terminal.json'
    guard=checked(guard_path)
    if not terminal['pass'] or not terminal['accounting_complete'] or not guard['task_owned_cleanup_pass']:raise ValueError('parent integrity/cleanup incomplete')
    d=read(data/'IK/D_new.done.json')['result']['solutions']
    d_count=sum(bool(r['full_valid']) for r in d)
    if d_count!=4:raise ValueError('qualified D evidence changed')
    for p in (PARENT,data/'goal_terminal.json',data/'job_terminal.json',data/'f2_meter_crosschecked_terminal.json',guard_path):m['input_files'][str(p)]=sha(p)
    m['source_files'][str(Path(__file__).resolve())]=sha(__file__)
    tests=ROOT/'f2_inward_runtime_v3/test_issuer.py';m['source_files'][str(tests)]=sha(tests)
    m.update(additions['manifest_fields'])
    dest=W/'Robotwin2/datasets'/job_id
    m.update(run_id=job_id,parent_job_id='p48_f2_revision1_001',reservation_event_sha256=reservation['event_sha256'],reserved=dict(CAPS),
      guard_directory=str(dest.with_name(job_id+'_guard')),issuance='ISSUED_UNDER_USER_GOAL',
      failure_class='F2_endpoint_route_U_height',evidence_based_revision=1,layout_revision_preserved=1,endpoint_route_revision=1)
    # Keep the old layout lineage byte-equivalent at the canonical JSON level.
    m['new_layout_lineage']=copy.deepcopy(parent['new_layout_lineage'])
    m['endpoint_route_lineage']={k:v for k,v in additions['manifest_fields'].items() if k.startswith('f2_route_revision1_')}
    m['endpoint_route_lineage'].update(parent_D_full_valid_solutions=d_count,D_goal_sha256=digest(current['inward_goals']['D_new']),
      layout_binding_unchanged=True,planned_seed_unchanged=True,fresh_IK_goals=['C','U_new','D_new'],reuse_D_to_skip_fresh_check=False)
    job=m['jobs'][0];job.update(job_id=job_id,output_namespace=str(dest),kind='F2_FIXED_LAYOUT_U_ROUTE_REVISION1',timeout_seconds=1800,
      **{k:additions[k] for k in ('runtime_module','runtime_file','resource_caps')},test_module='goal_pilot48_v1.f2_inward_runtime_v3.test_issuer')
    if m['new_layout_lineage']!=parent['new_layout_lineage']:raise ValueError('old layout lineage unexpectedly changed')
    m['manifest_sha256']=digest(m);return m

def issue(job_id):
    """Call only from the main scheduler after previous job reconciliation."""
    from goal_pilot48_v1.runtime.budget import reserve
    from realization_utf8_io_v1 import write_new
    dest=W/'Robotwin2/datasets'/job_id;path=ROOT/'jobs'/(job_id+'.json')
    if any(p.exists() for p in (path,dest,dest.with_name(job_id+'_guard'),dest.with_name(job_id+'_meter'),W/'Robotwin2/cache/p48'/job_id)):raise FileExistsError('used U-route job namespace')
    m=build_manifest(job_id,{'kind':'RESERVE','job_id':job_id,'reserved':dict(CAPS),'event_sha256':'pending_main_reservation'})
    event=reserve(job_id,dict(CAPS),'F2 fixed qualified D/layout; unique U-height endpoint-route revision1; fresh3IK then conditional4route; no action/collection')
    m.pop('manifest_sha256');m['reservation_event_sha256']=event['event_sha256'];m['manifest_sha256']=digest(m);write_new(path,m);return m

if __name__=='__main__':
    import sys
    m=issue(sys.argv[1]);print(ROOT/'jobs'/(m['run_id']+'.json'))
