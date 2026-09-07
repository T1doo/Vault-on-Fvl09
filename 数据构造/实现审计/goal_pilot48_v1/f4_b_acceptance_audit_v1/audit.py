"""Independent read-only B raw/current audit; reports never alter pilot cells."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from controlled_multi_future.raw_writer import verify_raw_artifact_integrity,validate_raw_artifact_contract,validate_raw_streams
from controlled_multi_future.current_hasher import hash_array
from controlled_multi_future.development_video_capture_v1 import validate_development_trajectory_mp4_receipt_v1
from goal_pilot48_v1.f4_b_runtime_v1.binding import PROGRAMS,seal,checked
from goal_pilot48_v1.f4_b_root_runtime_v1.entry import disk_finalizer
from realization_current_layout_audit_v1 import audit as audit_current_storage
from realization_utf8_io_v1 import write_new

W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计'
DEFAULT=W/'Robotwin2/datasets/p48_f4_b_root_001'
SOURCE_SHA='3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))

def branch(root,pid,reference,current_directory=None):
    directory=root/'branches'/pid;final=directory/'receipt.json'
    candidates=sorted((directory/'receipt_history').glob('*.json')) if directory.exists() else []
    receipt=final if final.exists() else candidates[-1] if candidates else None
    raw=directory/'raw/raw_streams.npz';trace=directory/'trace_source.npz';manifest=directory/'raw/manifest.json';video=directory/'video/trajectory.mp4'
    if receipt is None or not all(p.exists() for p in (raw,trace,manifest,video)):
        return dict(program_id=pid,status='pending_incomplete_branch_files',final_branch_receipt_present=final.exists(),accepted=False)
    before={str(p):sha(p) for p in (receipt,raw,trace,manifest,video)}
    b=read(receipt);m=read(manifest)
    integrity=verify_raw_artifact_integrity(directory/'raw');validate_raw_artifact_contract(directory/'raw')
    with np.load(raw,allow_pickle=False) as z:
        streams={k[8:]:z[k] for k in z.files if k.startswith('stream__')}
        raw_image_fields=[k for k in z.files if any(x in k.lower() for x in ('rgb','image'))]
    streams['field_metadata']=m['stream_field_metadata'];validate_raw_streams(streams)
    q=streams['realized_qpos'];v=streams['realized_qvel'];actions=streams['controller_effective_setpoint'];n=len(actions)
    with np.load(trace,allow_pickle=False) as z:
        q0=z['joint_qpos'][0];v0=z['joint_qvel'][0]
        gripper=np.concatenate((z['realized_left_gripper_joint_qpos'][0],z['realized_right_gripper_joint_qpos'][0]))
        trace_image_fields=[k for k in z.files if any(x in k.lower() for x in ('rgb','image'))]
    sem=b.get('verifier',{}).get('family_semantic_verifier',{});role_rows=sem.get('role_receipts',[])
    videos=validate_development_trajectory_mp4_receipt_v1(b['development_video_receipt'],expected_path=video)
    expected_order=list(pid.split('-')[1]);provenance=m['provenance'];components=reference['model_visible_components']
    checks=dict(raw_integrity=integrity['pass'],N_actions_Nplus1_states=n==m['action_count'] and len(q)==len(v)==m['state_count']==n+1,
        action_26_dimensions=actions.shape==(n,26) and m['action_dim']==26,frequency250=m['frequency_hz']==250,
        raw_trace_state0_equal=bool(np.array_equal(q[0],q0) and np.array_equal(v[0],v0)),unique_dofs38=len(q0)==len(v0)==38,
        unique76_state_hash=hash_array(np.concatenate((q0.astype(np.float64),v0.astype(np.float64))))==components['robot_state_sha256'],
        gripper_hash=hash_array(gripper)==components['gripper_actual_state_sha256'],
        real_r_pc=provenance.get('synthetic') is False and provenance.get('program_id')==pid and provenance.get('realization_spec',{}).get('realization')=='r_pc',
        trace_provenance=provenance.get('trace_source_sha256')==before[str(trace)],
        branch_current_hash=b.get('branch_current',{}).get('aggregate_sha256')==reference['aggregate_sha256'],
        anchor_gate=b.get('anchor_equivalence',{}).get('equivalent') is True,
        original_verifier_recorded_pass=b.get('verifier',{}).get('pass') is True and sem.get('pass') is True,
        original_semantic_checks=bool(sem.get('checks')) and all(sem['checks'].values()),
        realized_role_order=[r.get('role') for r in role_rows]==expected_order and all(r.get('pass') is True and all(r.get('checks',{}).values()) for r in role_rows),
        execution_no_new_planner=b.get('suffix_execution_planner_query_delta')==0,
        video_integrity=videos['pass'],source_profile=reference['reconstruction_spec_audit']['simulation_configuration']['implementation_source_sha256']==SOURCE_SHA)
    current=None
    if current_directory is not None:
        metadata=read(Path(current_directory)/'current.json')
        if Path(metadata['parent_root']).resolve()!=root.resolve() or metadata['current']['aggregate_sha256']!=reference['aggregate_sha256']:
            raise ValueError('current source is not this exact B root')
        current=audit_current_storage(current_directory,trace)
        if current['unique_articulation_dofs']!=38 or current['model_visible_robot_state_dimension']!=76:raise ValueError('current storage decode changed')
    after={str(p):sha(p) for p in (receipt,raw,trace,manifest,video)}
    if before!=after:raise ValueError('branch changed during audit; retry readonly snapshot')
    return dict(program_id=pid,status='branch_locally_verified' if all(checks.values()) else 'branch_check_failed',accepted=False,
        final_branch_receipt_present=final.exists(),receipt_source=str(receipt),checks=checks,file_hashes=before,
        action_count=n,state_count=n+1,primary_action_array_sha256=hash_array(actions),raw_sha256=before[str(raw)],
        current_storage_audit=current,current_RGB_persisted=current is not None,raw_image_fields=raw_image_fields,trace_image_fields=trace_image_fields,
        final_state_equivalence_payload=b.get('final_state_equivalence_payload'),original_branch_status=b.get('status'),
        verifier_scope='original hash-bound verifier/role gate records plus raw/time/current checks; no simulator replay or full physical verifier rerun')

def run(output=DEFAULT,*,current_directory=None):
    output=Path(output).resolve();root=output/'development_root'
    reference=read(root/'reference_current_hashes.json');rows=[]
    if current_directory is None and (root/'current/current_arrays.npz').exists():current_directory=root/'current'
    for pid in PROGRAMS:
        try:rows.append(branch(root,pid,reference,current_directory))
        except BaseException as exc:rows.append(dict(program_id=pid,status='audit_error',accepted=False,error={'type':type(exc).__name__,'message':str(exc)}))
    ready=[r for r in rows if r.get('status')=='branch_locally_verified']
    unique=len(ready)==3 and len({r['raw_sha256'] for r in ready})==3 and len({r['primary_action_array_sha256'] for r in ready})==3
    goal_path=output/'goal_terminal.json';guard_path=output.parent/(output.name+'_guard')/(output.name+'.terminal.json')
    terminal_complete=False;terminal_error=None;finalizer=None;derived_resource=False;original_goal_pass=None
    if goal_path.exists() and guard_path.exists() and (root/'root_receipt.json').exists():
        try:
            goal=checked(read(goal_path));guard=checked(read(guard_path));manifest=checked(read(A/'goal_pilot48_v1/jobs'/(output.name+'.json')),'manifest_sha256')
            original_goal_pass=goal['pass']
            terminal_complete=goal['pass'] and goal['accounting_complete'] and goal['resource_counts']==dict(solver_problems=460,fresh_scenes=11,action_scenes=7,collection_attempts=3) and guard['child_exit_code']==0 and guard['task_owned_cleanup_pass'] and guard['manifest_sha256']==goal['manifest_sha256']==manifest['manifest_sha256']
            rr=goal['runtime_result'];inner_accepted=rr['root_receipt']['status']=='accepted'
            # Reproduce the original inner physical/disk finalizer arguments,
            # independently of the later outer accounting failure.
            f=disk_finalizer(dict(root_receipt=rr['root_receipt'],development_root_pass=inner_accepted,development_accepted_root_count=int(inner_accepted),development_accepted_trajectory_count=3 if inner_accepted else 0),manifest['jobs'][0],output)
            finalizer={k:f.get(k) for k in ('accepted','checks','counts','root_receipt','receipt_sha256')}
            terminal_complete=bool(terminal_complete and finalizer['accepted'])
            acceptance_path=Path(__file__).parent/'RESOURCE_ACCOUNTING_ACCEPTANCE_001.json'
            if not terminal_complete and acceptance_path.exists() and output.name=='p48_f4_b_root_001':
                from goal_pilot48_v1.f4_b_motion_runtime_v2.binding import root_inputs
                job={}
                for field,path in dict(source_root_goal_terminal=goal_path,source_root_guard_terminal=guard_path,
                    source_root_manifest=A/'goal_pilot48_v1/jobs'/(output.name+'.json'),source_root_resource_acceptance=acceptance_path).items():
                    job[field+'_path']=str(path);job[field+'_file_sha256']=sha(path)
                root_inputs(job);derived_resource=True
        except BaseException as exc:terminal_error={'type':type(exc).__name__,'message':str(exc)}
    eligible=(terminal_complete or derived_resource) and unique and all(r.get('current_RGB_persisted') for r in ready)
    return seal(dict(schema_version='cmf_B_independent_acceptance_audit_v1',snapshot_unix_time=time.time(),root=str(root),rows=rows,
        root_Goal_Guard_terminal_verified=terminal_complete,terminal_error=terminal_error,disk_finalizer=finalizer,
        original_goal_pass=original_goal_pass,derived_resource_acceptance_verified=derived_resource,
        three_distinct_raw_and_action_arrays=unique,current_storage_directory=None if current_directory is None else str(current_directory),
        eligibility_recommendation='eligible_after_explicit_current_reference_publication' if eligible else 'pending_not_registered',
        eligible_candidate_cells=3 if eligible else 0,pilot_cells_modified=False,root_acceptance_issued=False,
        current_gap='none' if current_directory is not None else 'only_current_hashes_no_lossless_head_left_right_RGB_artifact',
        new_scenes=0,new_raw=0,GPU_execution=False,source_profile_sha256=SOURCE_SHA,
        source_bindings={str(A/'realization_current_layout_audit_v1.py'):sha(A/'realization_current_layout_audit_v1.py'),str(A/'goal_pilot48_v1/reuse18/audit.json'):sha(A/'goal_pilot48_v1/reuse18/audit.json')}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root-job',type=Path,default=DEFAULT);parser.add_argument('--current-directory',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if not args.output.resolve().is_relative_to(Path(__file__).resolve().parent):raise ValueError('report must stay in independent audit directory')
    report=run(args.root_job,current_directory=args.current_directory);write_new(args.output,report)
    print(json.dumps({'receipt_sha256':report['receipt_sha256'],'eligible_candidate_cells':report['eligible_candidate_cells'],'current_gap':report['current_gap']},ensure_ascii=False))
