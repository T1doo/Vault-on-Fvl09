"""Main-only replacement dispatch after an audited no-child Guard stop."""
from pathlib import Path
from . import budget
from .issue_inside_carry import build_manifest, CAPS, W, checked, sha

def main():
    old = 'p48_f2_inside_carry_revision1_001'
    new = 'p48_f2_inside_carry_revision1_002'
    path = W/'Robotwin2/datasets'/f'{old}_guard'/f'{old}.terminal.json'
    guard = checked(path)
    if (guard['job_id'] != old or guard['child_pid'] is not None
            or guard['job_launched'] or guard['execution_budget_consumed']
            or not guard['task_owned_cleanup_pass'] or not guard['lease_released']):
        raise ValueError('not a safely released no-child dispatch')
    events = [e for e in budget.rows() if e['kind'] == 'RECONCILE' and e['job_id'] == old]
    if len(events) != 1 or any(events[0]['actual'][k] for k in CAPS if k != 'gpu_lease_seconds'):
        raise ValueError('no-child usage not independently reconciled')
    preview = {'kind':'RESERVE', 'job_id':new, 'reserved':CAPS, 'event_sha256':'CPU-only'}
    build_manifest(new, preview)
    reservation = budget.reserve(new, CAPS, 'same frozen carry revision1; prior dispatch launched no child; no physical retry')
    manifest = build_manifest(new, reservation)
    manifest.pop('manifest_sha256')
    manifest['dispatch_recovery_of'] = old
    manifest['no_child_guard_receipt_sha256'] = guard['receipt_sha256']
    manifest['input_files'][str(path)] = sha(path)
    manifest['source_files'][str(Path(__file__).resolve())] = sha(Path(__file__))
    manifest['manifest_sha256'] = budget.digest(manifest)
    budget.atomic(budget.ROOT/'jobs'/f'{new}.json', manifest)
    print(manifest['manifest_sha256'])

if __name__ == '__main__':
    main()
