"""Read-only pilot registration consistency, NOT a raw/physics acceptance gate."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = {
    'F1': ('F1-red', 'F1-green', 'F1-blue'),
    'F2': ('F2-inside', 'F2-on', 'F2-beside'),
    'F3': ('F3-VVHH', 'F3-VHVH', 'F3-VHHV'),
    'F4': ('F4-ABC', 'F4-ACB', 'F4-BAC'),
}
REALIZATIONS = {'A': ('r_pc', 'r_inv_path'), 'B': ('r_pc', 'r_inv_motion')}
ACCEPTED = {'accepted_existing', 'accepted_new'}


def inspect_document(document):
    errors = []
    rows = document.get('cells', [])
    expected = {(f, p, program, r) for f, programs in PROGRAMS.items()
                for p, realizations in REALIZATIONS.items()
                for program in programs for r in realizations}
    keys = [tuple(row.get(k) for k in ('family', 'pilot', 'program_id', 'realization')) for row in rows]
    if len(keys) != 48 or set(keys) != expected or len(set(keys)) != len(keys):
        errors.append('exact_48_unique_frozen_cells_required')
    accepted = [row for row in rows if row.get('status') in ACCEPTED]
    if type(document.get('accepted')) is not int or document['accepted'] != len(accepted):
        errors.append('reported_accepted_count_mismatch')
    if document.get('scientific_stage1_completion_claimed') is not False:
        errors.append('pilot_matrix_cannot_claim_scientific_stage1')
    groups = defaultdict(list)
    unique = {key: set() for key in ('raw_id', 'trace_sha256', 'rollout_id')}
    required_true = ('pilot_input_accepted', 'raw_integrity_pass', 'raw_N_Nplus1_stream_contract_pass',
                     'raw_state0_equals_trace_state0', 'video_integrity_pass', 'same_current_pass',
                     'anchor_equivalence_pass', 'family_verifier_pass', 'fresh_scene_pass',
                     'cleanup_pass', 'failure_history_complete')
    for row in rows:
        identity = '/'.join(str(row.get(k)) for k in ('family', 'pilot', 'program_id', 'realization'))
        if tuple(row.get(k) for k in ('family', 'pilot', 'program_id', 'realization')) not in expected:
            errors.append(identity + ':invalid_frozen_cell_identity')
            continue
        status = row.get('status')
        if status == 'pending':
            if row.get('evidence') is not None:
                errors.append(identity + ':pending_evidence_must_not_imply_acceptance')
            continue
        if status not in ACCEPTED:
            errors.append(identity + ':unknown_registration_status')
            continue
        e = row.get('evidence')
        if not isinstance(e, dict):
            errors.append(identity + ':accepted_evidence_missing')
            continue
        groups[(row['family'], row['pilot'])].append(e)
        if any(e.get(k) != row.get(k) for k in ('family', 'pilot', 'program_id', 'realization')):
            errors.append(identity + ':evidence_cell_identity_mismatch')
        if any(e.get(k) is not True for k in required_true):
            errors.append(identity + ':recorded_gate_not_passed')
        if (e.get('origin_kind') != 'real_rollout' or e.get('derived_from_raw_id') is not None
                or type(e.get('orphan_process_count')) is not int or e['orphan_process_count'] != 0):
            errors.append(identity + ':real_rollout_or_cleanup_provenance_invalid')
        if type(e.get('actions')) is not int or e['actions'] <= 0 or e.get('states') != e['actions'] + 1:
            errors.append(identity + ':N_Nplus1_invalid')
        for key, seen in unique.items():
            value = e.get(key)
            if not isinstance(value, str) or not value or value in seen:
                errors.append(identity + ':' + key + '_missing_or_reused')
            else:
                seen.add(value)
        c = e.get('current_initial_state_audit') or {}
        current_keys = ('head_rgb', 'left_wrist_rgb', 'right_wrist_rgb', 'model_visible_robot_state',
                        'gripper_state', 'storage_array_file_hash')
        if (c.get('pass') is not True or c.get('unique_articulation_dofs') != 38
                or c.get('model_visible_robot_state_dimension') != 76
                or c.get('raw_reference_state_index') != 0 or c.get('future_state_values_used') is not False
                or any(c.get('checks', {}).get(k) is not True for k in current_keys)):
            errors.append(identity + ':recorded_current_audit_invalid')
        if row['family'] in ('F3', 'F4') and e.get('final_state_equivalence_pass') is not True:
            errors.append(identity + ':recorded_final_state_equivalence_missing')
    complete = []
    roots_seen = {}
    for group, evidence in groups.items():
        label = '/'.join(group)
        for key in ('root_id', 'current_sha256', 'candidate_universe_sha256'):
            values = {e.get(key) for e in evidence}
            if len(values) != 1 or None in values or '' in values:
                errors.append(label + ':mixed_or_missing_' + key)
        root = evidence[0].get('root_id')
        if root in roots_seen and roots_seen[root] != group:
            errors.append(label + ':root_reused_across_pilot_slots')
        roots_seen[root] = group
        if len(evidence) == 6:
            complete.append(label)
    return {'schema_version': 'pilot48_registration_consistency_audit_v1', 'pass': not errors,
            'errors': errors, 'registered_accepted': len(accepted), 'target': 48,
            'registered_by_family': dict(Counter(r['family'] for r in accepted)),
            'complete_six_cell_pilot_groups': sorted(complete),
            'registration_matrix_full': not errors and len(accepted) == 48,
            'raw_or_physical_evidence_reverified': False, 'pilot_cells_modified': False,
            'scientific_stage1_completion_proven': False, 'goal_completion_proven': False}


def audit_file(path=ROOT / 'pilot_cells.json'):
    data = Path(path).read_bytes()
    result = inspect_document(json.loads(data.decode('utf-8')))
    result['source_path'] = str(path)
    result['source_file_sha256'] = sha256(data).hexdigest()
    return result


if __name__ == '__main__':
    print(json.dumps(audit_file(), ensure_ascii=False, indent=2))
