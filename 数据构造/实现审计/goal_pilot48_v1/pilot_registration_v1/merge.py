"""Pure F4-B registration merge; caller must independently verify disk evidence.

No filesystem writes, acceptance issuance, GPU work or automatic invocation.
"""
from copy import deepcopy
from hashlib import sha256
import json
from goal_pilot48_v1.pilot_matrix_audit_v1.audit import inspect_document


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def merge_f4_b(current, report):
    body = deepcopy(report)
    claimed = body.pop('receipt_sha256', None)
    if claimed != digest(body):
        raise ValueError('candidate audit self-hash mismatch')
    if (report.get('status') != 'six_verified_candidates_pending_main_registration'
            or report.get('eligible_candidate_cells') != 6
            or report.get('acceptance_issued') is not False
            or report.get('pilot_cells_modified') is not False):
        raise ValueError('complete six-candidate audit required')
    if (report.get('current_recovery', {}).get('pass') is not True
            or report.get('pc_audit', {}).get('eligible_candidate_cells') != 3
            or report.get('recomputed_motion_finalizer', {}).get('accepted') is not True
            or report.get('six_final_state_equivalence', {}).get('equivalent') is not True):
        raise ValueError('current, pc, motion and final-state proofs required')
    if not inspect_document(current)['pass']:
        raise ValueError('existing registration inconsistent; refuse mutation')
    expected = {('F4', 'B', p, r) for p in ('F4-ABC', 'F4-ACB', 'F4-BAC')
                for r in ('r_pc', 'r_inv_motion')}
    def key(row):
        return tuple(row.get(k) for k in ('family', 'pilot', 'program_id', 'realization'))
    candidates = report.get('cells', [])
    if len(candidates) != 6 or {key(c) for c in candidates} != expected:
        raise ValueError('exact F4-B six-cell mapping required')
    updated = deepcopy(current)
    for candidate in candidates:
        matches = [i for i, row in enumerate(updated['cells']) if key(row) == key(candidate)]
        if len(matches) != 1:
            raise ValueError('target slot missing or duplicated')
        index = matches[0]
        if updated['cells'][index]['status'] != 'pending' or updated['cells'][index].get('evidence') is not None:
            raise ValueError('target already populated; never overwrite or count twice')
        if (candidate.get('status') != 'verified_candidate_pending_main_registration'
                or candidate.get('evidence', {}).get('pilot_input_accepted') is not False):
            raise ValueError('candidate must not pretend already registered')
        row = deepcopy(candidate)
        row['status'] = 'accepted_new'
        row['evidence']['pilot_input_accepted'] = True
        row['evidence']['independent_candidate_audit_receipt_sha256'] = claimed
        updated['cells'][index] = row
    updated['accepted'] = current['accepted'] + 6
    updated['scientific_stage1_completion_claimed'] = False
    updated.setdefault('additional_candidate_audits', []).append(claimed)
    consistency = inspect_document(updated)
    if not consistency['pass']:
        raise ValueError('merged registration inconsistent: ' + repr(consistency['errors']))
    for before, after in zip(current['cells'], updated['cells']):
        if key(before) not in expected and before != after:
            raise ValueError('unrelated cell changed')
    return updated, consistency
