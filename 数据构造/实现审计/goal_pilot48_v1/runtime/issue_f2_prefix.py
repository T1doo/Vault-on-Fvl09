"""Pure prefix-only issuer builder; reservation is supplied by main scheduler."""
import copy,hashlib,json,re
from pathlib import Path
from goal_pilot48_v1.runtime_v2.migration import bindings as migrated_bindings
ROOT=Path(__file__).resolve().parents[1];W=Path('/nfs_share/lijunhui')
PARENT=ROOT/'jobs/p48_f2_u_route_001.json'
CAPS=dict(solver_problems=3,fresh_scenes=1,action_scenes=1,collection_attempts=0,gpu_lease_seconds=1980)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def checked(p,key='receipt_sha256'):
    d=read(p);v=dict(d);h=v.pop(key)
    if digest(v)!=h:raise ValueError('hash mismatch '+str(p))
    return d
def merge(a,b):
    value=dict(a)
    for p,h in b.items():
        if p in value and value[p]!=h:raise ValueError('dependency conflict '+p)
        if not Path(p).resolve().is_relative_to(W) or sha(p)!=h:raise ValueError('dependency changed '+p)
        value[p]=h
    return value

def build_manifest(job_id,reservation):
    if not re.fullmatch(r'p48_f2_prefix_[a-z0-9_]+',job_id):raise ValueError('new prefix namespace required')
    targets=[ROOT/'jobs'/(job_id+'.json'),W/'Robotwin2/datasets'/job_id,W/'Robotwin2/datasets'/(job_id+'_guard'),W/'Robotwin2/datasets'/(job_id+'_meter'),W/'Robotwin2/cache/p48'/job_id]
    if any(p.exists() for p in targets):raise FileExistsError('prefix namespace already used')
    if reservation.get('kind')!='RESERVE' or reservation.get('job_id')!=job_id or reservation.get('reserved')!=CAPS or not reservation.get('event_sha256'):raise ValueError('exact external prefix reservation required')
    from goal_pilot48_v1.f2_goal_root_runtime_v1.dependencies import additional_bindings
    parent=checked(PARENT,'manifest_sha256');extra=additional_bindings();m=copy.deepcopy(parent);m.pop('manifest_sha256')
    migrated=migrated_bindings(parent);m.update(migrated)
    for field in ('source_files','input_files'):m[field]=merge(m[field],extra['additional_'+field])
    terminal_path=W/'Robotwin2/datasets/p48_f2_u_route_001/goal_terminal.json';terminal=checked(terminal_path)
    if not terminal['pass'] or not terminal['accounting_complete'] or not terminal['runtime_result']['scientific_route_pass']:raise ValueError('repaired beside route not actually qualified')
    if terminal.get('job_id')!='p48_f2_u_route_001' or terminal.get('manifest_sha256')!=parent['manifest_sha256']:raise ValueError('parent terminal identity mismatch')
    guard_path=Path(parent['guard_directory'])/'p48_f2_u_route_001.terminal.json';guard=checked(guard_path)
    if guard.get('run_id')!='p48_f2_u_route_001' or guard.get('child_exit_code')!=0 or guard.get('task_owned_cleanup_pass') is not True or guard.get('timed_out'):raise ValueError('parent Guard not cleanly terminal')
    m['input_files'][str(guard_path)]=sha(guard_path)
    m['input_files'][str(terminal_path)]=sha(terminal_path);m['input_files'][str(PARENT)]=sha(PARENT)
    m['source_files'][str(Path(__file__).resolve())]=sha(__file__)
    m.update(extra['manifest_fields']);dest=W/'Robotwin2/datasets'/job_id
    m.update(run_id=job_id,parent_job_id='p48_f2_u_route_001',guard_directory=str(dest.with_name(job_id+'_guard')),reserved=dict(CAPS),
      reservation_event_sha256=reservation['event_sha256'],physical_execution_authorized=True,issuance='ISSUED_UNDER_USER_GOAL',
      phase='F2_NEW_CURRENT_REAL_PREFIX_QUALIFICATION',prefix_only=True,whole_root_execution_authorized=False,
      old_inside_success_inherited=False,collection_authorized=False)
    m['jobs']=[dict(job_id=job_id,family='F2',kind='F2_REAL_PREFIX_QUALIFICATION',output_namespace=str(dest),timeout_seconds=1800,
      requires_live_meter=True,**{k:extra[k] for k in ('runtime_module','runtime_file','test_module','resource_caps')})]
    m['manifest_sha256']=digest(m);return m

def issue_from_reservation(job_id,reservation):return build_manifest(job_id,reservation)
