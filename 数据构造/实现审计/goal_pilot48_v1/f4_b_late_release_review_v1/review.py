"""CPU-only review and strict future late-idle verifier. No host/GPU commands."""
from datetime import datetime,timezone
import math
from pathlib import Path
from goal_pilot48_v1.runtime.issue_f4_b_stage_a import ROOT,W,read,sha
from goal_pilot48_v1.f4_b_runtime_v1.binding import checked,seal
from realization_utf8_io_v1 import write_new

JOB='p48_f4_b_motion_001'
OUT=W/'Robotwin2/datasets'/JOB
HERE=Path(__file__).resolve().parent

def selected(snapshot,index,uuid):
    rows=[r for r in snapshot['gpus'] if r['index']==index]
    if len(rows)!=1 or rows[0]['uuid']!=uuid:raise ValueError('selected GPU UUID/index mismatch')
    return rows[0]

def same_original_baseline(pre,post):
    # Byte-equivalent predicate semantics to frozen Guard _returned_to_baseline.
    return (post['memory_used_mib']<=max(64,pre['memory_used_mib']+32) and post['utilization_gpu_percent']==0
        and post['pstate'] in ('P8','P12') and not post['compute_processes'])

def review():
    guard_path=OUT.parent/(JOB+'_guard')/(JOB+'.terminal.json');goal_path=OUT/'goal_terminal.json'
    start_path=guard_path.parent/(JOB+'.start.json');post_path=guard_path.parent/(JOB+'.post_child_validation.json')
    manifest_path=ROOT/'jobs'/(JOB+'.json')
    guard=checked(read(guard_path));goal=checked(read(goal_path));start=checked(read(start_path));post=checked(read(post_path));manifest=checked(read(manifest_path),'manifest_sha256')
    if guard['manifest_sha256']!=goal['manifest_sha256'] or guard['manifest_sha256']!=manifest['manifest_sha256'] or start['manifest_sha256']!=manifest['manifest_sha256']:raise ValueError('execution lineage changed')
    if not goal['pass'] or not goal['accounting_complete'] or goal['runtime_result']['scientific_route_pass'] is not True or goal['resource_counts']!=dict(solver_problems=0,fresh_scenes=3,action_scenes=3,collection_attempts=3):raise ValueError('producer data not complete')
    expected_error=[{'type':'CooldownExhausted','message':'GPU baseline not restored'}]
    if guard['child_exit_code']!=0 or guard['execution_errors'] or guard['cleanup_errors']!=expected_error or guard['timed_out'] or guard['interrupted'] is not None:
        raise ValueError('failure is not solely the original cooldown exhaustion')
    if not guard['cache_removed'] or not guard['lease_released'] or guard['gpu_returned_to_idle_baseline'] is not False or guard['task_owned_cleanup_pass'] is not False:
        raise ValueError('original cleanup/baseline facts changed')
    if post['validation_pass'] is not False:raise ValueError('original POST_CHILD failure must be retained')
    idx=guard['physical_gpu_index'];uuid=guard['gpu_uuid'];pre=selected(guard['pre_snapshot'],idx,uuid);launch=selected(guard['launch_snapshot'],idx,uuid)
    if not same_original_baseline(pre,pre) or not same_original_baseline(pre,launch):raise ValueError('job was not fresh idle at launch')
    polls=guard['post_release_poll_snapshots']
    if len(polls)!=13:raise ValueError('original cooldown length changed')
    rows=[selected(s,idx,uuid) for s in polls]
    pid_sets=[sorted(p['pid'] for p in r['compute_processes']) for r in rows]
    if any(pids!=[3963009] for pids in pid_sets):raise ValueError('cooldown occupants differ from reviewed single foreign PID')
    ownership_path=HERE/'MAIN_HOST_OBSERVATION_001.json';ownership=checked(read(ownership_path))
    if (ownership['original_guard_file_sha256']!=sha(guard_path) or ownership['requested_owned_pids']!=[guard['guard_pid'],guard['child_pid']] or
        ownership['requested_child_pgid']!=guard['child_process_group'] or not ownership['own_pid_and_group_absent'] or ownership['remaining_owned_process_rows'] or
        ownership['current_uid']!=10201 or {r['pid'] for r in ownership['gpu_compute_owner_rows']}!={3963009} or
        any(r['uid']==ownership['current_uid'] for r in ownership['gpu_compute_owner_rows']) or ownership['selected_gpu_idle_now'] is not False):
        raise ValueError('durable host ownership observation does not support pending foreign occupancy')
    files={}
    for table in (manifest['source_files'],manifest['input_files']):
        for p,h in table.items():
            if sha(p)!=h:raise ValueError('bound source/input changed: '+p)
            files[p]=h
    for p in [*OUT.rglob('*'),guard_path,goal_path,start_path,post_path,manifest_path,ownership_path]:
        if p.is_file():files[str(p)]=sha(p)
    return seal(dict(schema_version='cmf_F4_late_release_pending_review_v1',job_id=JOB,status='PENDING_REAL_LATE_IDLE_OBSERVATION',
        original_guard_receipt_sha256=guard['receipt_sha256'],original_goal_receipt_sha256=goal['receipt_sha256'],
        original_guard_file_sha256=sha(guard_path),original_POST_CHILD_pass=False,original_task_owned_cleanup_pass=False,
        original_gpu_returned_to_idle_baseline=False,child_exit_code=0,execution_errors=[],only_cleanup_failure='CooldownExhausted',
        cache_removed=True,lease_released=True,physical_gpu_index=idx,gpu_uuid=uuid,original_pre_selected=pre,
        guard_pid=guard['guard_pid'],child_pid=guard['child_pid'],child_pgid=guard['child_process_group'],
        original_cooldown_last_captured_at=polls[-1]['captured_at'],original_cooldown_selected_rows=rows,
        ownership_observation_path=str(ownership_path),ownership_observation_receipt_sha256=ownership['receipt_sha256'],
        task_user_uid=ownership['current_uid'],observed_foreign_pid=3963009,observed_foreign_uid=ownership['gpu_compute_owner_rows'][0]['uid'],
        host_provenance='main recorded host ps/nvidia observation; Guard itself does not carry UID/process-tree proof',
        immutable_file_hashes=files,original_guard_elapsed_seconds=guard['elapsed_seconds'],
        proposed_actual_resources={**goal['resource_counts'],'gpu_lease_seconds':math.ceil(guard['elapsed_seconds'])+1},
        late_wait_after_lease_release_not_GPU_job_time=True,acceptance_issued=False,budget_reconciled=False,current_GPU_idle_claimed=False))

def verify_future_idle(review_receipt,observation,*,now_utc=None):
    """Caller must supply a NEW actual host observation; no fabricated pass is emitted now.

    Rehashing first may be slow. Main should revalidate files, then capture a new
    observation immediately; if it ages out, reacquire observation, not a job.
    """
    value=checked(review_receipt);obs=checked(observation)
    if value['status']!='PENDING_REAL_LATE_IDLE_OBSERVATION':raise ValueError('wrong pending source')
    for p,h in value['immutable_file_hashes'].items():
        if sha(p)!=h:raise ValueError('immutable source/raw/terminal changed')
    if obs.get('original_guard_file_sha256')!=value['original_guard_file_sha256'] or obs.get('job_id')!=JOB:raise ValueError('late observation source binding')
    if obs.get('requested_owned_pids')!=[value['guard_pid'],value['child_pid']] or obs.get('requested_child_pgid')!=value['child_pgid'] or obs.get('current_uid')!=value['task_user_uid'] or obs.get('own_pid_and_group_absent') is not True or obs.get('remaining_owned_process_rows')!=[]:
        raise ValueError('original owned PID/group absence not rechecked')
    snapshot=obs['snapshot']
    if sorted(g['index'] for g in snapshot['gpus'])!=list(range(8)):raise ValueError('complete fresh GPU0-7 snapshot required')
    current=selected(snapshot,value['physical_gpu_index'],value['gpu_uuid'])
    if current!=obs.get('selected_gpu') or not same_original_baseline(value['original_pre_selected'],current) or obs.get('selected_gpu_idle_now') is not True:
        raise ValueError('original strict idle/baseline rule still not satisfied')
    parsed=lambda s:datetime.fromisoformat(s.replace('Z','+00:00'))
    if now_utc is not None and not (value.get('CPU_TEST_FIXTURE') is True and obs.get('CPU_TEST_FIXTURE') is True):
        raise ValueError('production freshness clock cannot be overridden')
    observed=parsed(obs['observed_at']);captured=parsed(snapshot['captured_at']);now=parsed(now_utc) if now_utc is not None else datetime.now(timezone.utc)
    ages=[(now-observed).total_seconds(),(now-captured).total_seconds()]
    if min(observed,captured)<=parsed(value['original_cooldown_last_captured_at']) or not all(0<=age<=30 for age in ages):
        raise ValueError('late evidence not fresh: reacquire actual observation within30s')
    if obs.get('foreign_processes_signalled') is not False:raise ValueError('foreign process interference is forbidden')
    return seal(dict(schema_version='cmf_F4_late_release_resolution_v1',job_id=JOB,pending_review_receipt_sha256=value['receipt_sha256'],
        original_guard_receipt_sha256=value['original_guard_receipt_sha256'],original_guard_cleanup_pass_remains_false=True,
        original_POST_CHILD_pass_remains_false=True,late_observation_receipt_sha256=obs['receipt_sha256'],
        late_selected_gpu=current,late_capture_at=snapshot['captured_at'],owned_processes_absent_reverified=True,
        late_baseline_restoration_verified=True,resource_release_resolved=True,original_files_modified=False,
        actual_resources_for_main_reconcile=value['proposed_actual_resources'],
        pilot_acceptance_issued=False,budget_reconciled=False,new_GPU_execution=False,
        claim_scope='later strict baseline proof, not rewritten original Guard success',**{'pass':True}))

if __name__=='__main__':
    result=review();write_new(HERE/'PENDING_REVIEW_001.json',result)
    print({'receipt_sha256':result['receipt_sha256'],'status':result['status'],'source_files':len(result['immutable_file_hashes'])})
