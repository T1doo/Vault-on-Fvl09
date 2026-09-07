"""Main-only exact six-cell adoption after independent F4 final audit.

Idempotent recovery preserves the exact previous UTF-8 registration in a
separate snapshot; it never rewrites raw, Guard, budget or old evidence.
"""
import json
from hashlib import sha256
from pathlib import Path
from goal_pilot48_v1.runtime.budget import ROOT, read, atomic, digest
from goal_pilot48_v1.pilot_registration_v1.merge import merge_f4_b
from goal_pilot48_v1.pilot_matrix_audit_v1.audit import inspect_document
from realization_utf8_io_v1 import write_new

REPORT = ROOT / 'f4_b_pilot_acceptance_v2/FINAL_AUDIT_001.json'
EXPECTED = '0b44d845f9472514c665e09f502fc58b182da251e57d2eee202a2069df43a487'
OLD_SHA = '0c406b8659fdb31b6a6a7087506b5d597aa2d8c2e49e4f0bc17a3d94800461fd'
HERE = ROOT / 'pilot_registration_v1'
W = Path('/nfs_share/lijunhui')


def file_sha(path):
    path = Path(path).resolve()
    if not path.is_relative_to(W):
        raise ValueError('evidence outside workspace')
    return sha256(path.read_bytes()).hexdigest()


def main():
    report = read(REPORT)
    if report.get('receipt_sha256') != EXPECTED or report.get('late_release_verified') is not True:
        raise ValueError('exact independent final audit required')
    for cell in report['cells']:
        e = cell['evidence']; directory = Path(e['rollout_id'])
        files = [('raw/raw_streams.npz', 'raw_id'), ('trace_source.npz', 'trace_sha256'),
                 ('video/trajectory.mp4', 'video_sha256'), ('receipt.json', 'receipt_file_sha256')]
        for name, key in files:
            if file_sha(directory / name) != e[key]:
                raise ValueError('audited rollout changed before adoption')
        current = e['current_initial_state_audit']; cp = Path(current['current_directory'])
        if file_sha(cp / 'current.json') != current['current_json_file_sha256']:
            raise ValueError('shared current metadata changed')
        if file_sha(cp / 'current_arrays.npz') != read(cp / 'current.json')['arrays_file_sha256']:
            raise ValueError('shared current arrays changed')
    table_path = ROOT / 'pilot_cells.json'; snapshot_path = HERE / 'BEFORE_F4_B_001.json'
    if snapshot_path.exists():
        snapshot = read(snapshot_path)
        original = snapshot['original_utf8_text'].encode('utf-8')
    else:
        original = table_path.read_bytes()
        snapshot = dict(schema_version='pilot_registration_exact_backup_v1',
                        original_file_sha256=sha256(original).hexdigest(),
                        original_utf8_text=original.decode('utf-8'))
    if sha256(original).hexdigest() != OLD_SHA or snapshot['original_file_sha256'] != OLD_SHA:
        raise ValueError('original18-cell registration differs')
    old = json.loads(original.decode('utf-8'))
    updated, consistency = merge_f4_b(old, report)
    if updated['accepted'] != 24:
        raise ValueError('this adoption must produce exactly24 registered inputs')
    encoded = (json.dumps(updated, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    expected_new_sha = sha256(encoded).hexdigest()
    current_bytes = table_path.read_bytes()
    if current_bytes not in (original, encoded):
        raise ValueError('registration changed concurrently; no overwrite')
    if not snapshot_path.exists():
        write_new(snapshot_path, snapshot)
    if current_bytes == original:
        atomic(table_path, updated)
    if file_sha(table_path) != expected_new_sha or not inspect_document(read(table_path))['pass']:
        raise ValueError('post-write registration verification failed')
    receipt = dict(schema_version='main_F4_B_pilot_adoption_v1',
                   independent_audit_receipt_sha256=EXPECTED, independent_audit_file_sha256=file_sha(REPORT),
                   previous_registration_file_sha256=OLD_SHA, registration_file_sha256=expected_new_sha,
                   previous_registration_exact_backup=str(snapshot_path),
                   registered_input_count_before=18, registered_input_count_after=24,
                   added_cells=[{k: c[k] for k in ('family', 'pilot', 'program_id', 'realization')} for c in report['cells']],
                   original_raw_Guard_files_modified=False, new_GPU_execution=False,
                   scientific_stage1_completed=False, full_goal_completed=False,
                   registration_consistency=consistency)
    receipt['receipt_sha256'] = digest(receipt)
    target = HERE / 'F4_B_ADOPTION_001.json'
    if target.exists():
        if read(target) != receipt:
            raise ValueError('different prior adoption receipt')
    else:
        write_new(target, receipt)
    state = read(ROOT / 'STATE.json'); before = json.dumps(state, sort_keys=True)
    state['pilot_input_accepted'] = 24
    state['families']['F4'] = 'PILOT_A_B_12_INPUTS_ACCEPTED_WITH_PRESERVED_LATE_RELEASE_LINEAGE'
    state['last_pilot_adoption_receipt_sha256'] = receipt['receipt_sha256']
    state['last_turn_classification'] = 'progress'
    if json.dumps(state, sort_keys=True) != before:
        atomic(ROOT / 'STATE.json', state)
    print(json.dumps({'receipt': receipt['receipt_sha256'], 'pilot_accepted': 24,
                      'registration_sha256': expected_new_sha, 'all_existing_cells_preserved': True}))


if __name__ == '__main__':
    main()
