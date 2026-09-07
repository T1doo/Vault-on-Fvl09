"""Pure new-job issuer for the single evidence-driven first-waypoint change."""
import copy,re,json
import numpy as np
from pathlib import Path
from goal_pilot48_v1.runtime.issue_inside_qualification import ROOT,W,CAPS,merge_checked,sha,checked,digest
from goal_pilot48_v1.inside_qualification_runtime_v3.spec import build_spec,REVIEW,checked_review
PARENT=ROOT/'jobs/p48_f2_inside_qualification_001.json'

def build_manifest(job_id,reservation):
    if not re.fullmatch(r'p48_f2_inside_carry_revision1_[a-z0-9_]+',job_id):raise ValueError('fresh carry revision1 namespace required')
    paths=[ROOT/'jobs'/(job_id+'.json'),W/'Robotwin2/datasets'/job_id,W/'Robotwin2/datasets'/(job_id+'_guard'),W/'Robotwin2/datasets'/(job_id+'_meter'),W/'Robotwin2/cache/p48'/job_id]
    if any(p.exists() for p in paths):raise FileExistsError('carry revision namespace consumed')
    if reservation.get('kind')!='RESERVE' or reservation.get('job_id')!=job_id or reservation.get('reserved')!=CAPS or not reservation.get('event_sha256'):raise ValueError('exact main-thread reservation required')
    p=checked(PARENT,'manifest_sha256')
    for table in ('source_files','input_files'):
        for filename,h in p[table].items():
            if sha(filename)!=h:raise ValueError('frozen parent dependency changed '+filename)
    data=W/'Robotwin2/datasets/p48_f2_inside_qualification_001';guard_path=data.with_name(data.name+'_guard')/'p48_f2_inside_qualification_001.terminal.json'
    goal=checked(data/'goal_terminal.json');local=checked(data/'job_terminal.json');guard=checked(guard_path);r=checked_review()
    for receipt in (goal,guard):
        if receipt['manifest_sha256']!=p['manifest_sha256'] or receipt['job_id']!='p48_f2_inside_qualification_001':raise ValueError('failed parent identity mismatch')
    if not goal['accounting_complete'] or not goal['pass'] or not guard['task_owned_cleanup_pass'] or not guard['gpu_returned_to_idle_baseline']:raise ValueError('failed parent resource cleanup incomplete')
    if goal['resource_counts']!={'solver_problems':1,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0}:raise ValueError('parent counters differ')
    nested=goal['runtime_result'];n=dict(nested);h=n.pop('receipt_sha256')
    if digest(n)!=h or nested['local_terminal_receipt_sha256']!=local['receipt_sha256'] or local['manifest_sha256']!=p['manifest_sha256']:raise ValueError('parent nested/local receipt linkage failed')
    suffix=local['inside_suffix_result']
    if suffix['pass'] or suffix['solver_problems']!=1 or suffix['error']!={'type':'RuntimeError','message':'plan_0 rejected'} or suffix['full_open_executed']:raise ValueError('not the reviewed first carry failure')
    with np.load(data/'qualification_trace.npz',allow_pickle=False) as trace:queries=json.loads(str(trace['planner_queries_json'].item()))
    if len(queries)!=1 or queries[0]['source']!='lift' or queries[0]['motiongen_result_side_channel'][0]['fields']['status']!='MotionGenStatus.IK_FAIL':raise ValueError('actual first carry solver outcome differs')
    m=copy.deepcopy(p);m.pop('manifest_sha256');files=[Path(__file__).resolve()]
    for directory in ('f2_inside_carry_waypoint_revision_v1','inside_qualification_runtime_v3'):files.extend((ROOT/directory).glob('*.py'))
    merge_checked(m['source_files'],{str(q):sha(q) for q in files})
    merge_checked(m['input_files'],{str(q):sha(q) for q in [PARENT,REVIEW,data/'goal_terminal.json',data/'job_terminal.json',guard_path]})
    merge_checked(m['input_files'],r['files'])
    root=ROOT/'inside_qualification_runtime_v3'
    m.update(run_id=job_id,parent_job_id='p48_f2_inside_qualification_001',failure_class='F2_inside_carry_waypoint',evidence_based_revision=1,carry_waypoint_revision=1,
      reserved=dict(CAPS),reservation_event_sha256=reservation['event_sha256'],guard_directory=str(W/'Robotwin2/datasets'/(job_id+'_guard')),
      inside_qualification_spec_sha256=digest(build_spec()),final_inside_target_changed=False,other_four_targets_changed=False,physical_numeric_thresholds_changed=False)
    m['jobs'][0].update(job_id=job_id,kind='F2_INSIDE_CARRY_WAYPOINT_REVISION1',output_namespace=str(W/'Robotwin2/datasets'/job_id),
      runtime_module='goal_pilot48_v1.inside_qualification_runtime_v3.runner_bridge',runtime_file=str(root/'runner_bridge.py'),test_module='goal_pilot48_v1.inside_qualification_runtime_v3.test_all')
    m['manifest_sha256']=digest(m);return m

def issue_from_reservation(job_id,reservation):return build_manifest(job_id,reservation)
