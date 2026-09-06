"""CPU-only F4-B issuer construction. Never reserve, publish, or launch here.

The main scheduler supplies a real reservation, then exclusively publishes the
returned manifest. Tests use an in-memory CPU-only reservation.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
A=ROOT.parent
W=Path('/nfs_share/lijunhui')
P=W/'Robotwin2/project/RoboTwin'
CAPS=dict(solver_problems=156,fresh_scenes=1,action_scenes=0,collection_attempts=0,gpu_lease_seconds=1980)
PARENT=A/'F4_V2_2_APPROVED_ROOT1_MANIFEST_20260905.json'
PARENT_FILE_SHA='c178bc3397226a1cb64a968acfae55ee8f86f55da24cd91813ae4496cfb982df'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def _add(table,paths):
    for path in paths:
        p=Path(path).resolve()
        if not p.is_relative_to(W) or not p.is_file():raise ValueError('missing/outside input '+str(path))
        current=sha(p)
        if str(p) in table and table[str(p)]!=current:raise ValueError('earlier frozen hash changed '+str(p))
        table[str(p)]=current

def _inherit(table,path,expected):
    p=Path(path).resolve()
    if not p.is_relative_to(W) or sha(p)!=expected:raise ValueError('parent F4 dependency changed '+str(path))
    if str(p) in table and table[str(p)]!=expected:raise ValueError('conflicting parent F4 hash '+str(p))
    table[str(p)]=expected

def _parent_file_bindings(value,sources,inputs):
    if isinstance(value,list):
        for item in value:_parent_file_bindings(item,sources,inputs)
    elif isinstance(value,dict):
        if 'path' in value and 'file_sha256' in value:
            path=value['path'];_inherit(sources if Path(path).suffix=='.py' else inputs,path,value['file_sha256'])
        for key,path in value.items():
            if key.endswith('_path') and isinstance(path,str):
                base=key[:-5]
                expected=value.get(base+'_file_sha256',value.get(base+'_sha256'))
                if expected is not None:_inherit(sources if Path(path).suffix=='.py' else inputs,path,expected)
            if isinstance(path,(dict,list)):_parent_file_bindings(path,sources,inputs)

def bindings():
    if sha(PARENT)!=PARENT_FILE_SHA:raise ValueError('exact retained F4 parent manifest changed')
    parent=read(PARENT);body=dict(parent);claimed=body.pop('manifest_sha256')
    if digest(body)!=claimed:raise ValueError('parent F4 manifest self-hash mismatch')
    sources={};inputs={}
    _parent_file_bindings(parent,sources,inputs)
    for path,expected in parent['asset_hashes_by_family']['F4'].items():_inherit(inputs,P/path,expected)
    # A evidence is retained only as immutable lineage, never B qualification.
    _add(inputs,[PARENT,ROOT/'CONTRACT.json',ROOT/'USER_GOAL_SOURCE.md',
        A/'F4_PILOT_B_NEW_LAYOUT_CPU_PROPOSAL_V1_20260906.json'])
    for folder in (ROOT/'runtime',ROOT/'f4_b_runtime_v1',ROOT/'f4_b_runtime_v2'):_add(sources,folder.glob('*.py'))
    _add(sources,[A/'realization_utf8_io_v1.py',W/'Robotwin2/production_micro_gate_v1/guarded_launcher.py'])
    _add(sources,(P/'envs').rglob('*.py'))
    _add(sources,(P/'controlled_multi_future').rglob('*.py'))
    _add(inputs,[p for p in (P/'task_config').rglob('*') if p.is_file() and p.suffix in ('.yml','.yaml','.json')])
    _add(inputs,[p for p in (P/'envs/curobo/src/curobo').rglob('*') if p.is_file() and p.suffix in ('.yml','.yaml','.cu','.cuh','.cpp','.h')])
    _add(inputs,[p for p in (P/'assets/embodiments/aloha-agilex').rglob('*') if p.is_file() and p.suffix.lower() in ('.yml','.yaml','.urdf','.stl','.obj','.dae','.mtl','.glb')])
    tray=P/'assets/objects/008_tray'
    _add(inputs,[tray/'model_data0.json',tray/'points_info.json',tray/'collision/base0.glb',tray/'visual/base0.glb'])
    # Other F4 bodies are procedural boxes from the fully hashed scene source.
    from goal_pilot48_v1.f4_b_runtime_v2.runtime import source_inputs
    local=source_inputs()
    if parent['implementation_source_sha256']!=local['implementation_source_sha256']:
        raise ValueError('F4 parent active source differs')
    for path,expected in local['files'].items():_inherit(sources if Path(path).suffix=='.py' else inputs,path,expected)
    return sources,inputs,parent

def assert_fresh(job_id):
    if not re.fullmatch(r'p48_f4_b_stage_a_[a-z0-9_]+',job_id):raise ValueError('F4-B Stage-A namespace required')
    paths=[ROOT/'jobs'/(job_id+'.json'),W/'Robotwin2/datasets'/job_id,
        W/'Robotwin2/datasets'/(job_id+'_guard'),W/'Robotwin2/datasets'/(job_id+'_meter'),W/'Robotwin2/cache/p48'/job_id]
    if any(p.exists() for p in paths):raise FileExistsError('F4-B Stage-A namespace already used')

def build_manifest(job_id,reservation):
    assert_fresh(job_id)
    if reservation.get('kind')!='RESERVE' or reservation.get('job_id')!=job_id or reservation.get('reserved')!=CAPS or not reservation.get('event_sha256'):
        raise ValueError('exact caller-supplied F4-B reservation required')
    c=read(ROOT/'CONTRACT.json');body=dict(c);h=body.pop('receipt_sha256')
    if digest(body)!=h or not c['adopted_by_user_goal'] or sha(ROOT/'USER_GOAL_SOURCE.md')!=c['source_file_sha256']:
        raise ValueError('Goal authority/source mismatch')
    sources,inputs,parent=bindings()
    from goal_pilot48_v1.f4_b_runtime_v1.binding import payload,runtime_spec
    b=payload();spec=runtime_spec()
    m=dict(schema_version='cmf_goal_subjob_manifest_v1',goal_id=c['goal_id'],goal_contract_receipt_sha256=h,
        issuance='ISSUED_UNDER_USER_GOAL',approved=True,gpu_execution_authorized=True,physical_execution_authorized=False,
        allowed_physical_gpu_indices=list(range(8)),gpu_jobs_serial=True,formal_360_authorized=False,training_authorized=False,
        stage0_reopened=False,stage1_authorized=False,pilot_input_authorized=False,
        run_id=job_id,reservation_event_sha256=reservation['event_sha256'],reserved=dict(CAPS),
        guard_directory=str(W/'Robotwin2/datasets'/(job_id+'_guard')),cache_directory=str(W/'Robotwin2/cache/p48'),
        implementation_source_sha256=parent['implementation_source_sha256'],robotwin_tracked_head=parent['robotwin_tracked_head'],
        source_files=sources,input_files=inputs,
        initialization_policy='skip dummy MotionGen.warmup and log separately; actual cold solves independently metered',
        B_lineage=dict(payload_sha256=b['receipt_sha256'],scene_seed=spec['seed'],
            planned_scene_spec_sha256=spec['planned_scope_spec_sha256'],
            A_success_reused_as_B_qualification=False,source_stage_a_status='pending_actual_GPU_evidence'),
        jobs=[dict(job_id=job_id,family='F4',kind='F4_B_SOURCE_STAGE_A',
            runtime_module='goal_pilot48_v1.f4_b_runtime_v2.runtime',runtime_file=str(ROOT/'f4_b_runtime_v2/runtime.py'),
            test_module='goal_pilot48_v1.f4_b_runtime_v2.test_issuer',output_namespace=str(W/'Robotwin2/datasets'/job_id),
            timeout_seconds=1800,resource_caps={k:v for k,v in CAPS.items() if k!='gpu_lease_seconds'},
            b_payload_sha256=b['receipt_sha256'],planned_scene_spec_sha256=spec['planned_scope_spec_sha256'])])
    for role,name in (('guard','guarded_launcher.py'),('runner','job_runner.py')):
        m[role+'_script_path']=str(ROOT/'runtime'/name);m[role+'_script_sha256']=sha(ROOT/'runtime'/name)
    m['manifest_sha256']=digest(m)
    return m

def issue_from_reservation(job_id,reservation):
    """Return only; main scheduler owns reserve and exclusive publication."""
    return build_manifest(job_id,reservation)
