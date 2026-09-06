"""Recheck all disk artifacts supporting the two append-only resolutions."""
from audit import A, final, write_new
from pathlib import Path

def run():
    f4 = final.check(A / 'F4_ROOT1_ACCEPTED_VIA_RESOLUTION_PUBLICATION_V1.json')
    f1 = final.check(A / 'REALIZATION_UTF8_FAILURE_RESOLUTION_PUBLICATION_V1_20260906.json')
    bindings = dict(f1['artifact_files'])
    bindings.update({v['path']: v['file_sha256'] for v in f4['artifacts']})
    bindings[f1['derived_branch_path']] = f1['derived_branch_file_sha256']
    bindings[f1['reconciliation_path']] = f1['reconciliation_file_sha256']
    for p, h in bindings.items():
        assert final.sha(p) == h, p
    a = final.check(Path(__file__).parent / 'audit.json')
    r = final.seal({'schema_version': 'goal_pilot48_reuse_resolution_integrity_v1',
        'pass': True, 'audit_receipt_sha256': a['receipt_sha256'],
        'F4_resolution_publication': f4['receipt_sha256'],
        'F1_resolution_publication': f1['receipt_sha256'],
        'checked_file_bindings': bindings, 'checked_files': len(bindings),
        'original_files_modified': False, 'new_acceptance_issued': False})
    write_new(Path(__file__).parent / 'resolution_audit.json', r)
    print(r['receipt_sha256'])

if __name__ == '__main__': run()
