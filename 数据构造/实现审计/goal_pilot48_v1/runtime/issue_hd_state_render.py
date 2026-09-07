"""Display-only GPU job: zero task plans/actions/collections, one render scene."""
import re
from pathlib import Path
from .budget import ROOT,digest
from .issue_one_sided_micro import W,checked,sha
from goal_pilot48_v1.runtime_v3.migration import bindings
from goal_pilot48_v1.hd_state_replay_v1.catalog import verify_f1_scene_source
CAPS=dict(solver_problems=0,fresh_scenes=1,action_scenes=0,collection_attempts=0,gpu_lease_seconds=1980)

def build_manifest(job_id,reservation,item):
    if not re.fullmatch(r'p48_hd_render_[a-z0-9_]+',job_id):raise ValueError('display namespace required')
    if any(p.exists() for p in (ROOT/'jobs'/f'{job_id}.json',W/'Robotwin2/datasets'/job_id,W/'Robotwin2/datasets'/f'{job_id}_guard',W/'Robotwin2/datasets'/f'{job_id}_meter',W/'Robotwin2/cache/p48'/job_id)):
        raise FileExistsError('render namespace already used')
    if reservation.get('kind')!='RESERVE' or reservation.get('job_id')!=job_id or reservation.get('reserved')!=CAPS or not reservation.get('event_sha256'):
        raise ValueError('exact display reservation required')
    parent=checked(ROOT/'jobs/p48_f3_upright_qualification_trace_001.json','manifest_sha256')
    migrated=bindings(parent)
    m={k:parent[k] for k in ('schema_version','goal_id','goal_contract_receipt_sha256','issuance','implementation_source_sha256','robotwin_tracked_head','initialization_policy','cache_directory')}
    m.update(migrated,run_id=job_id,approved=True,gpu_execution_authorized=True,physical_execution_authorized=False,
             allowed_physical_gpu_indices=list(range(8)),gpu_jobs_serial=True,formal_360_authorized=False,
             training_authorized=False,stage0_reopened=False,stage1_authorized=False,
             saved_state_visualization_only=True,not_a_new_family_collection=True,render_item=item,
             reserved=dict(CAPS),reservation_event_sha256=reservation['event_sha256'],guard_directory=str(W/'Robotwin2/datasets'/f'{job_id}_guard'))
    root=ROOT/'hd_state_replay_v1'
    for p in [*root.glob('*.py'),Path(__file__).resolve()]:m['source_files'][str(p)]=sha(p)
    if item['family']=='F1':m['input_files'].update(verify_f1_scene_source())
    for key,hkey in (('trace_path','trace_sha256'),('planned_spec_path','planned_spec_sha256')):
        if sha(item[key])!=item[hkey]:raise ValueError('render input changed')
        m['input_files'][item[key]]=item[hkey]
    m['input_files'][str(ROOT/'pilot_cells.json')]=sha(ROOT/'pilot_cells.json')
    m['jobs']=[dict(job_id=job_id,family='DISPLAY',source_family=item['family'],kind='HD_SAVED_STATE_RENDER',
        output_namespace=str(W/'Robotwin2/datasets'/job_id),timeout_seconds=1800,requires_live_meter=True,
        resource_caps={k:v for k,v in CAPS.items() if k!='gpu_lease_seconds'},max_video_frames=(item['states']+9)//10+2,
        runtime_module='goal_pilot48_v1.hd_state_replay_v1.runtime',runtime_file=str(root/'runtime.py'),
        test_module='goal_pilot48_v1.hd_state_replay_v1.test_all')]
    m['manifest_sha256']=digest(m);return m
