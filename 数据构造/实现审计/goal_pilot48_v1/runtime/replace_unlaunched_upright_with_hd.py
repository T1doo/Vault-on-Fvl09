"""Main-only issuance replacement; preserve an unused manifest and its ledger history."""
from . import budget
from .issue_upright_hd_video import build_manifest, PRIOR, CAPS, checked, sha

OLD = 'p48_f3_upright_qualification_001'
NEW = 'p48_f3_upright_qualification_hd_001'

def main():
    prior = checked(PRIOR, 'manifest_sha256')
    if prior['jobs'][0]['job_id'] != OLD:
        raise ValueError('unexpected old qualification')
    snap = budget.snapshot()
    if snap['active_reservations'] != {OLD:CAPS}:
        raise ValueError('only the exact unlaunched reservation can be replaced')
    # Fully validate the new sources and old absence before any ledger mutation.
    build_manifest(NEW, dict(kind='RESERVE', job_id=NEW, reserved=CAPS, event_sha256='PREVALIDATION_ONLY'))
    zero = {key:0 for key in budget.KEYS}
    evidence = {'reason':'USER_REQUESTED_NATIVE_HD_ALL_VIEWS_BEFORE_FIRST_EXECUTION',
                'old_manifest_path':str(PRIOR), 'old_manifest_file_sha256':sha(PRIOR),
                'old_output_guard_meter_cache_all_absent':True,
                'no_child_or_GPU_job_launched':True, 'physical_attempt_consumed':False,
                'replacement_job_id':NEW}
    event = budget.reconcile(OLD, zero, evidence)
    budget.append(budget.ROOT/'attempts.jsonl', {
        'job_id':OLD, 'status':'CANCELLED_UNLAUNCHED_FOR_USER_HD_VIDEO_REQUEST',
        'counts':zero, 'reconciliation_event_sha256':event['event_sha256'],
        'original_manifest_preserved':True})
    reservation = budget.reserve(NEW, CAPS, 'same first upright-B qualification with display-only HD multiview video')
    manifest = build_manifest(NEW, reservation)
    manifest.pop('manifest_sha256')
    manifest['prior_zero_consumption_reconciliation_sha256'] = event['event_sha256']
    manifest['source_files'][__file__] = sha(__file__)
    manifest['manifest_sha256'] = budget.digest(manifest)
    budget.atomic(budget.ROOT/'jobs'/f'{NEW}.json', manifest)
    print(manifest['manifest_sha256'])

if __name__ == '__main__':
    main()
