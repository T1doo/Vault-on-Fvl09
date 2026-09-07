"""Main-only adoption of the exact root001 action-meter correction.

Original Goal/Guard/raw/meter files remain immutable. This is resource
reconciliation, not pilot input acceptance or recovery of missing current RGB.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from goal_pilot48_v1.runtime.budget import ROOT, read, digest, rows, reconcile, atomic, append
from goal_pilot48_v1.f4_b_acceptance_audit_v1.action_resolution import run as recompute
from realization_utf8_io_v1 import write_new

JOB = 'p48_f4_b_root_001'
PROOF = ROOT / 'f4_b_acceptance_audit_v1/ACTION_RESOURCE_RESOLUTION_001.json'
OUTPUT = ROOT / 'f4_b_acceptance_audit_v1/RESOURCE_ACCOUNTING_ACCEPTANCE_001.json'
EXPECTED_PROOF = 'c61965087f97bc8743092f326ed7214778ac9db3a332a7fcd2ffe34eb07e2871'

def main():
    proof = read(PROOF)
    body = dict(proof)
    claimed = body.pop('receipt_sha256')
    if digest(body) != claimed or claimed != EXPECTED_PROOF or recompute() != proof:
        raise ValueError('exact original-evidence correction did not reproduce')
    actual = proof['actual_resources_for_budget_reconcile']
    expected = dict(solver_problems=460, fresh_scenes=11, action_scenes=7,
                    collection_attempts=3, gpu_lease_seconds=2145)
    if actual != expected or not proof['resource_accounting_resolved']:
        raise ValueError('unexpected resource correction')
    evidence = dict(resolution_path=str(PROOF), resolution_receipt_sha256=claimed,
                    original_artifact_hashes=proof['original_artifact_hashes'],
                    correction_scope=proof['correction_scope'],
                    original_goal_pass=False, original_goal_files_modified=False,
                    current_RGB_recovery_status='pending_separate')
    prior = [e for e in rows() if e['kind'] == 'RECONCILE' and e['job_id'] == JOB]
    if prior:
        if len(prior) != 1 or prior[0]['actual'] != actual or prior[0]['evidence'] != evidence:
            raise ValueError('different or duplicated existing reconciliation')
        event = prior[0]
    else:
        event = reconcile(JOB, actual, evidence)
    value = dict(schema_version='cmf_f4_b_root_resource_acceptance_v1', job_id=JOB,
                 resolution_receipt_sha256=claimed, resolution_path=str(PROOF),
                 budget_reconciliation_event_sha256=event['event_sha256'],
                 actual_resources=actual, original_goal_pass=False,
                 original_goal_guard_meter_raw_modified=False,
                 physical_and_disk_finalizer_pass=True, resource_accounting_complete=True,
                 current_RGB_recovery_status='pending_separate',
                 pilot_input_eligibility_complete=False, new_pilot_inputs_accepted=0,
                 may_prepare_B_motion_under_user_goal=True,
                 formal_collection_authorized=False)
    value['receipt_sha256'] = digest(value)
    if OUTPUT.exists():
        if read(OUTPUT) != value:
            raise ValueError('existing acceptance differs; no overwrite permitted')
    else:
        write_new(OUTPUT, value)
    attempts_path = ROOT / 'attempts.jsonl'
    import json
    prior_attempts = [json.loads(line) for line in attempts_path.read_text(encoding='utf-8').splitlines() if line]
    matching = [e for e in prior_attempts if e['job_id'] == JOB]
    status = 'PHYSICAL_RAW_ROOT_PASS_ACCOUNTING_RESOLVED_CURRENT_PENDING'
    attempt = dict(job_id=JOB, status=status, counts=actual,
                   reconciliation_event_sha256=event['event_sha256'],
                   resource_acceptance_receipt_sha256=value['receipt_sha256'])
    if matching:
        if matching != [attempt]:
            raise ValueError('existing attempt record differs')
    else:
        append(attempts_path, attempt)
    state = read(ROOT / 'STATE.json')
    state['running'] = None
    old_pause = state.get('gpu_queue_pause')
    if old_pause:
        state.setdefault('resolved_gpu_queue_pauses', []).append(
            dict(original_pause=old_pause, resolution_receipt_sha256=claimed))
    state['gpu_queue_pause'] = None
    state['last_job'] = dict(job_id=JOB, status=status, counts=actual)
    state['last_turn_classification'] = 'progress'
    state['families']['F4'] = 'B_THREE_RAW_PHYSICS_DISK_PASS_RESOURCES_RESOLVED_CURRENT_AND_MOTION_PENDING'
    state['next_task'] = 'F3 one-sided micro or F2 prefix; B motion with resolved-root binding and matching current recovery'
    atomic(ROOT / 'STATE.json', state)
    print(json.dumps(dict(receipt_sha256=value['receipt_sha256'], charged=actual,
                          budget=state['budget'], pilot_input_accepted=state['pilot_input_accepted']), ensure_ascii=False))

if __name__ == '__main__':
    main()
