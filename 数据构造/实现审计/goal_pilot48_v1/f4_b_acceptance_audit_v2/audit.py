"""Defensive current audit contract. V1/history are unchanged.

V1's pinned dependency currently raises on failure and returns pass=True.
False-return cases below are synthetic robustness tests, not historical errors.
"""
from pathlib import Path
from goal_pilot48_v1.f4_b_acceptance_audit_v1 import audit as old
from goal_pilot48_v1.f4_b_runtime_v1.stages import bound_function

def current_result_passed(value):
    return isinstance(value,dict) and value.get('pass') is True and value.get('unique_articulation_dofs')==38 and value.get('model_visible_robot_state_dimension')==76

def branch(root,pid,reference,current_directory=None):
    row=old.branch(root,pid,reference,current_directory)
    if current_directory is not None and row.get('status') in ('branch_locally_verified','branch_check_failed'):
        metadata=old.read(Path(current_directory)/'current.json')
        bound_components=metadata.get('current',{}).get('model_visible_components')==reference.get('model_visible_components')
        passed=current_result_passed(row.get('current_storage_audit')) and bound_components
        row['checks']['current_storage_explicit_pass_and_sealed_components']=passed
        row['current_storage_verified']=passed
        row['status']='branch_locally_verified' if all(row['checks'].values()) else 'branch_check_failed'
    else:row['current_storage_verified']=False
    return row

def run(output=old.DEFAULT,*,current_directory=None):
    report=bound_function(old.run,branch=branch)(output,current_directory=current_directory)
    report.pop('receipt_sha256',None)
    report['schema_version']='cmf_B_independent_acceptance_audit_v2'
    report['hardening_scope']='explicit dependency pass/38/76/sealed-components checks; no evidence of historical false acceptance'
    if not all(row.get('current_storage_verified') is True for row in report['rows']):
        report['eligible_candidate_cells']=0;report['eligibility_recommendation']='pending_not_registered'
    return old.seal(report)
