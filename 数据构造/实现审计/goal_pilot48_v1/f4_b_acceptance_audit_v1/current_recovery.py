"""Append-only later-current eligibility check. Never reconstruct RGB from MP4."""
from pathlib import Path
from controlled_multi_future.anchor import compare_anchors
from realization_current_layout_audit_v1 import audit as storage_audit
from .audit import run,read,sha,A,seal,checked,PROGRAMS

def audit_later_current(*,root_job,current_directory,producer_branch,producer_goal,producer_guard):
    root_job=Path(root_job).resolve();root=root_job/'development_root';directory=Path(current_directory).resolve()
    if not root_job.name.startswith('p48_f4_b_root_') or 'F4_A' in str(directory) or 'cmf_f4_v22' in str(directory):
        raise ValueError('only this B root/new B current; historical A is forbidden')
    metadata=read(directory/'current.json');reference=read(root/'reference_current_hashes.json')
    if Path(metadata['parent_root']).resolve()!=root or metadata['current']['aggregate_sha256']!=reference['aggregate_sha256']:
        raise ValueError('later current does not exactly match B root sealed current')
    producer_output=Path(producer_goal).resolve().parent
    if not producer_output.name.startswith('p48_f4_b_motion_') or not directory.is_relative_to(producer_output) or not Path(producer_branch).resolve().is_relative_to(producer_output):
        raise ValueError('later-current producer must be its own new B motion job')
    branch=read(producer_branch);goal=checked(read(producer_goal));guard=checked(read(producer_guard))
    source_manifest=checked(read(A/'goal_pilot48_v1/jobs'/(producer_output.name+'.json')),'manifest_sha256')
    if (not goal.get('pass') or not goal.get('accounting_complete') or not guard.get('task_owned_cleanup_pass') or guard.get('child_exit_code')!=0 or
        guard.get('manifest_sha256')!=goal.get('manifest_sha256')):
        raise ValueError('current producer has not completed owned cleanup/accounting')
    if source_manifest['manifest_sha256']!=goal['manifest_sha256'] or source_manifest['jobs'][0]['runtime_module'] not in ('goal_pilot48_v1.f4_b_motion_runtime_v1.runtime','goal_pilot48_v1.f4_b_motion_runtime_v2.runtime'):
        raise ValueError('current producer source is not the reviewed B motion runtime')
    linked=[b for b in goal.get('runtime_result',{}).get('cohort',{}).get('branch_receipts',[]) if b.get('program_id')==branch.get('program_id')]
    if len(linked)!=1 or linked[0]!=branch:raise ValueError('producer finalized branch not linked by Goal terminal')
    if branch.get('branch_current',{}).get('aggregate_sha256')!=reference['aggregate_sha256']:
        raise ValueError('producer branch did not capture same B current')
    actual_anchor=branch.get('executed_prefix',{}).get('executed_prefix_start_anchor')
    if actual_anchor is None:raise ValueError('producer full initial anchor missing; keep pending')
    anchor=compare_anchors(read(root/'reference_anchor.json'),actual_anchor)
    if not anchor['equivalent']:raise ValueError('later scene anchor differs; keep pending')
    checks=[storage_audit(directory,root/'branches'/pid/'trace_source.npz') for pid in PROGRAMS]
    if not all(c['pass'] and c['unique_articulation_dofs']==38 and c['model_visible_robot_state_dimension']==76 for c in checks):
        raise ValueError('existing lossless current/row0 contract failed')
    independent=run(root_job,current_directory=directory)
    if independent['eligible_candidate_cells']!=3:raise ValueError('B root terminal/data/current acceptance audit still pending')
    return seal(dict(schema_version='cmf_B_later_current_reference_audit_v1',root=str(root),shared_current_directory=str(directory),
        captured_later_not_saved_by_original_root=True,MP4_reconstruction_used=False,A_current_used=False,
        current_json_sha256=sha(directory/'current.json'),current_arrays_sha256=sha(directory/'current_arrays.npz'),
        producer_branch_path=str(producer_branch),producer_branch_sha256=sha(producer_branch),producer_goal_sha256=sha(producer_goal),producer_guard_sha256=sha(producer_guard),
        original_pc_raw_modified=False,anchor_comparison=anchor,pc_current_state_checks=checks,
        shared_reference_for=['B_r_pc','B_r_inv_motion'],independent_root_audit=independent,
        eligibility_only=True,pilot_cells_modified=False,root_acceptance_issued=False,**{'pass':True}))

def historical_rule_evidence():
    path=A/'goal_pilot48_v1/reuse18/audit.json';old=read(path)
    rows=[r for r in old['rows'] if str(r.get('program_id','')).startswith('F4')]
    if len(rows)!=6 or not all(r['current_initial_state_audit']['pass'] for r in rows):raise ValueError('historical rule evidence changed')
    return dict(source_path=str(path),file_sha256=sha(path),rows=[dict(program_id=r['program_id'],realization=r['realization'],
        rollout_id=r['rollout_id'],shared_current_directory=r['current_initial_state_audit']['current_directory'],
        current_hash_and_raw_row0_pass=r['current_initial_state_audit']['pass']) for r in rows],
        rule='earlier r_pc and later real r_inv_path explicitly share later persisted current after exact component hashes and raw row0 checks',
        old_current_not_reused_for_B=True)
