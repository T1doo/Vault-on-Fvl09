"""Explicit approval-bound pure issuance; main thread supplies reservation."""
from pathlib import Path
from goal_pilot48_v1.runtime.issue_inside_qualification import build_preview,CAPS,merge_checked,sha,digest,ROOT
from goal_pilot48_v1.f2_controlled_inside_runtime_v3.approval import APPROVAL,APPROVAL_SHA,PHASE,PHASE_SHA,verify_approval

def build_manifest(job_id,reservation):
    approval=verify_approval()
    if reservation.get('kind')!='RESERVE' or reservation.get('job_id')!=job_id or reservation.get('reserved')!=CAPS or not reservation.get('event_sha256'):raise ValueError('exact main-thread reservation required')
    m=build_preview(job_id);m.pop('manifest_sha256');m.pop('proposed_caps');m.pop('contact_permission_pending')
    from goal_pilot48_v1.inside_qualification_runtime_v2.spec import build_spec
    files=[Path(__file__).resolve()]
    for directory in ('f2_controlled_inside_runtime_v3','inside_qualification_runtime_v2'):files.extend((ROOT/directory).glob('*.py'))
    merge_checked(m['source_files'],{str(p):sha(p) for p in files})
    merge_checked(m['input_files'],{str(APPROVAL):APPROVAL_SHA,str(PHASE):PHASE_SHA})
    root=ROOT/'inside_qualification_runtime_v2'
    m.update(issuance='ISSUED_UNDER_USER_GOAL',approved=True,physical_execution_authorized=True,
      gpu_execution_authorized=True,reserved=dict(CAPS),reservation_event_sha256=reservation['event_sha256'],
      contact_design_approval=approval,inside_qualification_spec_sha256=digest(build_spec()),
      physical_Gates_changed=True,physical_numeric_thresholds_changed=False,
      physical_Gate_change_scope='approved supported-descent box9 contact rule only; original files retained',
      verifier_version='native_floor_v1_plus_supported_descent_box9_rule_v1')
    m['jobs'][0].update(kind='F2_APPROVED_SUPPORTED_INSIDE_QUALIFICATION',runtime_module='goal_pilot48_v1.inside_qualification_runtime_v2.runner_bridge',
      runtime_file=str(root/'runner_bridge.py'),test_module='goal_pilot48_v1.inside_qualification_runtime_v2.test_all')
    m['manifest_sha256']=digest(m);return m

def issue_from_reservation(job_id,reservation):return build_manifest(job_id,reservation)
