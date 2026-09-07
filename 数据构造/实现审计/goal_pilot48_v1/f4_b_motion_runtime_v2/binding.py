"""Exact root001 derived resource acceptance; original failed Goal remains failed."""
from pathlib import Path
from goal_pilot48_v1.f4_b_program_runtime_v1.runtime import bound_json
from goal_pilot48_v1.f4_b_runtime_v1.binding import checked
from goal_pilot48_v1.f4_b_root_runtime_v1.runtime import prerequisites
from goal_pilot48_v1.f4_b_root_runtime_v1.entry import disk_finalizer
from goal_pilot48_v1.runtime_v3.budget import rows as budget_rows
from goal_pilot48_v1.runtime.issue_f4_b_stage_a import read,sha,W

ACCEPTANCE='48b92d6753431b6ef59b96004a391c70c3b8dc9635e4d393484cde64da0d7daa'
RESOLUTION='c61965087f97bc8743092f326ed7214778ac9db3a332a7fcd2ffe34eb07e2871'

def root_inputs(job):
    goal=bound_json(job,'source_root_goal_terminal');guard=bound_json(job,'source_root_guard_terminal')
    manifest=bound_json(job,'source_root_manifest','manifest_sha256')
    acceptance=bound_json(job,'source_root_resource_acceptance')
    if (acceptance['receipt_sha256']!=ACCEPTANCE or acceptance.get('resource_accounting_complete') is not True or
        acceptance.get('physical_and_disk_finalizer_pass') is not True or acceptance.get('may_prepare_B_motion_under_user_goal') is not True or
        acceptance.get('pilot_input_eligibility_complete') is not False or acceptance.get('new_pilot_inputs_accepted')!=0 or acceptance.get('original_goal_pass') is not False):
        raise ValueError('exact resource-only acceptance required, not fabricated full pilot acceptance')
    resolution=checked(read(acceptance['resolution_path']))
    if resolution['receipt_sha256']!=RESOLUTION or acceptance['resolution_receipt_sha256']!=RESOLUTION:
        raise ValueError('resource resolution differs')
    for path,h in resolution['original_artifact_hashes'].items():
        if sha(path)!=h:raise ValueError('original failed Goal/Guard/meter/root was modified')
    events=[r for r in budget_rows() if r['event_sha256']==acceptance['budget_reconciliation_event_sha256']]
    if len(events)!=1:raise ValueError('resource acceptance has no unique actual budget event')
    event=events[0]
    if event['kind']!='RECONCILE' or event['job_id']!=acceptance['job_id'] or event['actual']!=acceptance['actual_resources'] or event['actual']!=resolution['actual_resources_for_budget_reconcile'] or event['evidence']['resolution_receipt_sha256']!=RESOLUTION:
        raise ValueError('budget-event/resource-resolution chain mismatch')
    if (goal['pass'] is not False or goal['accounting_complete'] is not False or guard['child_exit_code']!=1 or
        not all(guard.get(k) is True for k in ('task_owned_cleanup_pass','gpu_returned_to_idle_baseline','lease_released')) or
        goal['manifest_sha256']!=guard['manifest_sha256'] or goal['manifest_sha256']!=manifest['manifest_sha256'] or
        goal['runtime_result']['finalizer']['accepted'] is not True):
        raise ValueError('original root failure and physical/disk success facts changed')
    parent=Path(manifest['jobs'][0]['output_namespace']).resolve()
    if parent!=W/'Robotwin2/datasets/p48_f4_b_root_001' or manifest['jobs'][0]['runtime_module']!='goal_pilot48_v1.f4_b_root_runtime_v1.runtime':
        raise ValueError('resource recovery is only this exact B root')
    root=parent/'development_root';receipt=read(root/'root_receipt.json')
    if receipt!=goal['runtime_result']['root_receipt'] or receipt['status']!='accepted':raise ValueError('root physics receipt changed')
    bound=prerequisites(manifest['jobs'][0])
    # Reproduce the original INNER disk-finalizer input, prior to the outer
    # failed action-count gate; never turn original Goal.pass into true.
    proof=disk_finalizer(dict(root_receipt=receipt,development_root_pass=True,development_accepted_root_count=1,development_accepted_trajectory_count=3),manifest['jobs'][0],parent)
    if not proof['accepted']:raise ValueError('current disk/physical proof no longer passes')
    return root,bound,receipt
