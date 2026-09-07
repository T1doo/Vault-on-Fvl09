"""Exact append-only root001 resource correction; never modify source or ledger."""
import ast
import json
import math
from pathlib import Path
import numpy as np
from controlled_multi_future.canonical_prefix_artifact_v1 import load_canonical_prefix_artifact
from controlled_multi_future.current_hasher import hash_array
from goal_pilot48_v1.f4_b_root_runtime_v1.accounting import count_queries
from types import SimpleNamespace
from .audit import DEFAULT,A,W,sha,read,checked,seal
from realization_utf8_io_v1 import write_new

def trace_evidence(path,prefix,start_row):
    with np.load(path,allow_pickle=False) as z:
        actions=z['controller_effective_setpoint'];q=z['joint_qpos'];timestamps=z['timestamp']
        p=len(prefix);segment=actions[start_row:start_row+p]
        if not np.array_equal(segment,prefix):raise ValueError('actual recorded replay differs from frozen prefix bytes')
        if len(q)!=len(actions) or len(timestamps)!=len(q) or not np.all(np.diff(timestamps)>0):raise ValueError('trace state/time structure')
        command_range=float(np.max(np.ptp(segment[:,:12],axis=0)))
        realized_excursion=float(np.max(np.abs(q[start_row:start_row+p]-q[start_row-1])))
        if not command_range>0 or not realized_excursion>0:raise ValueError('no actual nonconstant command/state motion witness')
        return dict(trace_path=str(path),trace_sha256=sha(path),trace_state_count=len(q),
            actual_recorded_action_intervals=len(q)-1,prefix_action_intervals=p,prefix_start_row=start_row,
            recorded_prefix_actions_sha256=hash_array(segment),frozen_prefix_actions_sha256=hash_array(prefix),
            exact_prefix_actions_equal=True,command_joint_range_rad=command_range,realized_joint_excursion_rad=realized_excursion,
            final_timestamp_seconds=float(timestamps[-1]),actual_drive_execution_witness=True)

def run():
    out=DEFAULT;root=out/'development_root';job_id=out.name
    goal_path=out/'goal_terminal.json';guard_path=out.parent/(job_id+'_guard')/(job_id+'.terminal.json')
    meter_path=out.parent/(job_id+'_meter')/'events.jsonl';manifest_path=A/'goal_pilot48_v1/jobs'/(job_id+'.json')
    critical=[goal_path,guard_path,meter_path,manifest_path,root/'root_receipt.json']
    before={str(p):sha(p) for p in critical}
    goal=checked(read(goal_path));guard=checked(read(guard_path));manifest=checked(read(manifest_path),'manifest_sha256');rr=read(root/'root_receipt.json')
    if goal['pass'] is not False or goal['accounting_complete'] is not False or guard['child_exit_code']!=1:
        raise ValueError('original terminal failure facts changed')
    if rr['status']!='accepted' or goal['runtime_result']['finalizer']['accepted'] is not True:
        raise ValueError('original physical/disk root is not fully accepted')
    if not all(guard.get(k) is True for k in ('task_owned_cleanup_pass','gpu_returned_to_idle_baseline','lease_released')):
        raise ValueError('cleanup/release not verified')
    if guard['manifest_sha256']!=goal['manifest_sha256'] or goal['manifest_sha256']!=manifest['manifest_sha256']:
        raise ValueError('manifest/Guard/Goal lineage differs')
    events=[json.loads(l) for l in meter_path.read_text(encoding='utf-8').splitlines()]
    if events[-1]['kind']!='METER_CLOSED':raise ValueError('meter still live')
    old={k:0 for k in ('solver_problems','fresh_scenes','action_scenes','collection_attempts')}
    charged_actions=set()
    for event in events:
        if event['kind']!='CHARGE':continue
        key=event['resource'];old[key]+=event['amount']
        if old[key]!=event['total']:raise ValueError('original meter charge progression')
        if key=='action_scenes':charged_actions.add(event['scene_ordinal'])
    if old!=goal['resource_counts'] or old!=dict(solver_problems=460,fresh_scenes=11,action_scenes=4,collection_attempts=3):raise ValueError('unexpected original counters')
    if charged_actions!={5,9,10,11}:raise ValueError('unexpected original action-charge identities')
    prefix_manifest,arrays=load_canonical_prefix_artifact(root/'canonical_prefix_artifact');prefix=arrays['effective_setpoint_actions']
    cleanups=rr['cleanup_records']
    if len(cleanups)!=11 or len({c['scene_instance_id'] for c in cleanups})!=11:raise ValueError('11 unique scenes required')
    scene_map=[];added=set();solver=0
    for ordinal,cleanup in enumerate(cleanups,1):
        if not cleanup['cleanup_safety_pass'] or cleanup['orphan_process_count']!=0:raise ValueError('scene cleanup failed')
        native_path=out/'native_scene_ledger'/f'{ordinal:02d}.json';native=read(native_path)
        if native['scene_instance_id']!=cleanup['scene_instance_id'] or native['phase']!=cleanup['phase']:raise ValueError('native scene identity mismatch')
        native_check=count_queries(SimpleNamespace(planner_query_count=native['planner_api_calls'],planner_queries=native['actual_query_rows']))
        solver+=native_check['solver_problems'];phase=cleanup['phase'];proof=None
        if phase=='canonical_prefix_reference':proof=trace_evidence(root/'canonical_prefix_reference_trace.npz',prefix,1)
        elif phase.startswith('suffix_preflight:'):
            pid=phase.split(':',1)[1];receipt_path=root/'suffix_preflight'/pid/'receipt.json';receipt=read(receipt_path);replay=receipt['prefix_replay']
            if replay['executed_prefix_step_count']!=len(prefix) or replay['executed_prefix_action_sha256']!=prefix_manifest['prefix_action_sha256'] or replay['planner_query_delta']!=0 or replay['replayed_prefix_physical_acceptance']['pass'] is not True:
                raise ValueError('suffix preflight exact replay receipt failed')
            proof=trace_evidence(root/'suffix_preflight'/pid/'trace_source.npz',prefix,replay['trace_replay_start_row'])
            proof.update(prefix_replay_receipt_path=str(receipt_path),prefix_replay_receipt_sha256=sha(receipt_path),
                executed_prefix_step_count=replay['executed_prefix_step_count'],replayed_prefix_physical_acceptance=True,
                planner_queries_during_replay=0,settling_action_intervals=replay['settling_step_count_excluded_from_semantic_prefix'])
            if ordinal not in charged_actions:added.add(ordinal)
        elif phase.startswith('strict_prefix_branch:'):
            pid=phase.split(':',1)[1];b=read(root/'branches'/pid/'receipt.json')
            proof=trace_evidence(root/'branches'/pid/'trace_source.npz',prefix,b['prefix_replay']['trace_replay_start_row'])
            proof.update(branch_receipt_sha256=sha(root/'branches'/pid/'receipt.json'),original_verifier_pass=b['verifier']['pass'])
        elif phase=='pristine' or phase.startswith('task_physical_feasibility:'):
            if ordinal in charged_actions or native_check['solver_problems']!=0:raise ValueError('unexpected preparatory task activity')
        else:raise ValueError('unrecognized scene phase')
        scene_map.append(dict(scene_ordinal=ordinal,scene_instance_id=cleanup['scene_instance_id'],phase=phase,
            original_action_charge=ordinal in charged_actions,actual_task_action=proof is not None,
            action_evidence=proof,nonaction_basis=None if proof else 'locked pristine/task callbacks only capture/hash/build programs or pose/geometry feasibility; no replay/operator calls; original meter has no task-action charge',
            native_query_ledger_path=str(native_path),native_query_ledger_sha256=sha(native_path),actual_solver_problems=native_check['solver_problems'],scene_cleanup_pass=True))
    if added!={6,7,8} or solver!=460:raise ValueError('correction is not exactly the three missing replay scenes')
    collection_charges=[e for e in events if e.get('kind')=='CHARGE' and e.get('resource')=='collection_attempts']
    if [e['program_id'] for e in collection_charges]!=['F4-ABC','F4-ACB','F4-BAC']:raise ValueError('three actual collection factory requests changed')
    actual={**old,'action_scenes':len(charged_actions|added),'gpu_lease_seconds':math.ceil(guard['elapsed_seconds'])+1}
    if any(actual[k]>manifest['reserved'][k] for k in actual):raise ValueError('derived actual exceeds existing reservation')
    source_paths=[W/'Robotwin2/project/RoboTwin/controlled_multi_future/canonical_prefix_replay_v1.py',W/'Robotwin2/project/RoboTwin/controlled_multi_future/probes/runtime_trace.py',
        W/'Robotwin2/project/RoboTwin/controlled_multi_future/root_orchestrator_v1_2.py',W/'Robotwin2/project/RoboTwin/controlled_multi_future/family_runners_v3_1.py',
        A/'goal_pilot48_v1/runtime_v2/meter.py']
    if any(sha(p)!=manifest['source_files'][str(p)] for p in source_paths):raise ValueError('executed source changed')
    if before!={str(p):sha(p) for p in critical}:raise ValueError('original artifacts changed during resolution audit')
    return seal(dict(schema_version='cmf_root001_action_scene_resolution_v1',job_id=job_id,
        original_goal_pass=False,original_accounting_complete=False,original_guard_child_exit_code=1,
        original_physical_disk_finalizer_accepted=True,original_meter_counts=old,actual_resources_for_budget_reconcile=actual,
        missing_action_scene_ordinals=sorted(added),scene_action_evidence_map=scene_map,
        original_artifact_hashes=before,executed_source_hashes={str(p):sha(p) for p in source_paths},
        resource_accounting_resolved=True,correction_scope='action_scenes4_to7_only_plus_original_guard_lease_formula',
        lease_charge_rule='ceil(original_guard_elapsed_seconds)+1',raw_guard_elapsed_seconds=guard['elapsed_seconds'],
        original_goal_guard_meter_modified=False,ledger_modified=False,new_GPU_runs=0,new_raw=0,
        root_data_acceptance_issued=False,current_RGB_recovery_status='pending_separate',
        next_main_step='validate resolution hashes, append one explicit budget reconcile using actual_resources_for_budget_reconcile; preserve failed original terminal',**{'pass':True}))

if __name__=='__main__':
    report=run();path=Path(__file__).parent/'ACTION_RESOURCE_RESOLUTION_001.json';write_new(path,report)
    print(json.dumps({'path':str(path),'receipt_sha256':report['receipt_sha256'],'actual':report['actual_resources_for_budget_reconcile']},ensure_ascii=False))
