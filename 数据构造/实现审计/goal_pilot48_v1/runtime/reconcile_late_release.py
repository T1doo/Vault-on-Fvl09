"""Main-only exact F4 late-release reconciliation; never alters original Guard."""
from pathlib import Path
import json
from goal_pilot48_v1.runtime.budget import ROOT, read, digest, rows, reconcile, append, atomic
from goal_pilot48_v1.f4_b_late_release_review_v1.review import checked, selected, same_original_baseline, sha
from realization_utf8_io_v1 import write_new

JOB = 'p48_f4_b_motion_001'
HERE = ROOT / 'f4_b_late_release_review_v1'
EXPECTED_RESOLUTION = '3e782f876ac10b3174c396ef2b46e5eeadd1f644d7b339ece3af4763fd44a89e'


def main():
    pending = checked(read(HERE / 'PENDING_REVIEW_001.json'))
    resolution = checked(read(HERE / 'LATE_RELEASE_RESOLUTION_001.json'))
    observation = checked(read(HERE / 'MAIN_HOST_OBSERVATION_004.json'))
    if (resolution['receipt_sha256'] != EXPECTED_RESOLUTION or resolution['job_id'] != JOB
            or resolution['pending_review_receipt_sha256'] != pending['receipt_sha256']
            or resolution['late_observation_receipt_sha256'] != observation['receipt_sha256']
            or resolution['pass'] is not True or resolution['resource_release_resolved'] is not True
            or resolution['late_baseline_restoration_verified'] is not True
            or resolution['original_guard_cleanup_pass_remains_false'] is not True
            or observation['own_pid_and_group_absent'] is not True or observation['remaining_owned_process_rows']):
        raise ValueError('exact main-observed late release proof required')
    gpu = selected(observation['snapshot'], pending['physical_gpu_index'], pending['gpu_uuid'])
    if not same_original_baseline(pending['original_pre_selected'], gpu) or gpu != resolution['late_selected_gpu']:
        raise ValueError('recorded strict baseline proof differs')
    for path, expected in pending['immutable_file_hashes'].items():
        if sha(path) != expected:
            raise ValueError('original source/data/terminal changed: ' + path)
    actual = resolution['actual_resources_for_main_reconcile']
    if actual != dict(solver_problems=0, fresh_scenes=3, action_scenes=3, collection_attempts=3, gpu_lease_seconds=1922):
        raise ValueError('unexpected actual resource counts')
    evidence = dict(late_release_resolution_path=str(HERE / 'LATE_RELEASE_RESOLUTION_001.json'),
                    late_release_resolution_receipt_sha256=EXPECTED_RESOLUTION,
                    late_observation_path=str(HERE / 'MAIN_HOST_OBSERVATION_004.json'),
                    late_observation_receipt_sha256=observation['receipt_sha256'],
                    original_guard_receipt_sha256=pending['original_guard_receipt_sha256'],
                    original_guard_cleanup_pass=False, original_guard_modified=False,
                    raw_guard_elapsed_seconds=pending['original_guard_elapsed_seconds'],
                    lease_charge_rule='ceil(original Guard elapsed)+1; later wait after lease release excluded')
    previous = [e for e in rows() if e['kind'] == 'RECONCILE' and e['job_id'] == JOB]
    newly_reconciled = not previous
    if previous:
        if len(previous) != 1 or previous[0]['actual'] != actual or previous[0]['evidence'] != evidence:
            raise ValueError('different prior reconciliation; refuse duplicate charge')
        event = previous[0]
    else:
        event = reconcile(JOB, actual, evidence)
    acceptance = dict(schema_version='main_F4_late_release_resource_acceptance_v1', job_id=JOB,
                      late_release_resolution_receipt_sha256=EXPECTED_RESOLUTION,
                      budget_reconciliation_event_sha256=event['event_sha256'], actual_resources=actual,
                      resource_release_resolved=True, original_guard_modified=False,
                      original_guard_cleanup_pass=False, pilot_acceptance_issued=False)
    acceptance['receipt_sha256'] = digest(acceptance)
    path = HERE / 'RESOURCE_RELEASE_ACCEPTANCE_001.json'
    if path.exists():
        if read(path) != acceptance:
            raise ValueError('resource acceptance already exists with different contents')
    else:
        write_new(path, acceptance)
    prior_attempts = [json.loads(line) for line in (ROOT / 'attempts.jsonl').read_text(encoding='utf-8').splitlines() if line]
    matching = [a for a in prior_attempts if a['job_id'] == JOB]
    attempt = dict(job_id=JOB, status='SCIENTIFIC_PASS_LATE_GPU_RELEASE_RESOLVED_PILOT_AUDIT_PENDING',
                   counts=actual, reconciliation_event_sha256=event['event_sha256'],
                   resource_acceptance_receipt_sha256=acceptance['receipt_sha256'])
    if matching:
        if matching != [attempt]:
            raise ValueError('different attempt record already exists')
    else:
        append(ROOT / 'attempts.jsonl', attempt)
    state = read(ROOT / 'STATE.json')
    pause = state.get('gpu_queue_pause')
    if pause and pause.get('job_id') == JOB:
        state.setdefault('resolved_gpu_queue_pauses', []).append(
            dict(original_pause=pause, resolution_receipt_sha256=EXPECTED_RESOLUTION))
        state['gpu_queue_pause'] = None
    if newly_reconciled and state.get('running') is None:
        state['last_job'] = dict(job_id=JOB, status=attempt['status'], counts=actual)
        state['families']['F4'] = 'B_PC_AND_MOTION_DATA_PASS_LATE_RELEASE_RESOLVED_PILOT_AUDIT_PENDING'
        state['last_turn_classification'] = 'progress'
        state['next_task'] = 'F4 independent final six-cell audit/adoption; F2 clearance CPU/preflight'
    if state != read(ROOT / 'STATE.json'):
        atomic(ROOT / 'STATE.json', state)
    print(json.dumps({'acceptance_receipt': acceptance['receipt_sha256'], 'newly_reconciled': newly_reconciled,
                      'actual_resources': actual, 'pilot_accepted': state['pilot_input_accepted']}))


if __name__ == '__main__':
    main()
