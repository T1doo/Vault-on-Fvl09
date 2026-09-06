"""Independent CPU-only read-only audit; writes only this report directory."""
import json, sys, time
from pathlib import Path
import numpy as np

W = Path('/nfs_share/lijunhui')
A = W / 'Vault-on-Fvl09/数据构造/实现审计'
sys.path[:0] = [str(A), str(A / '代码审阅快照')]
import realization_final_audit_v1 as final
import realization_current_layout_audit_v1 as current
from controlled_multi_future.raw_writer import validate_raw_streams
from realization_utf8_io_v1 import write_new

def run():
    started = time.time()
    evidence = final.run()
    old = final.read(A / 'REALIZATION_NINE_FINAL_AUDIT_V1_20260906.json')
    assert evidence == old, 'existing finalized evidence changed'
    layout = current.run()
    assert layout == final.read(A / 'REALIZATION_CURRENT_STORAGE_LAYOUT_AUDIT_V1_20260906.json')
    bindings = {str(A / n): final.sha(A / n) for n in (
        'REALIZATION_NINE_FINAL_AUDIT_V1_20260906.json',
        'REALIZATION_CURRENT_STORAGE_LAYOUT_AUDIT_V1_20260906.json',
        'PILOT_18_CELL_ELIGIBILITY_READONLY_RECHECK_V1_20260906.json',
        'realization_final_audit_v1.py', 'realization_current_layout_audit_v1.py')}
    currents = {c['parent_root_id']: layout['cohorts'][i]['current_directory']
                for i, c in enumerate(evidence['cohorts'])}
    rows = []
    for row in evidence['rows']:
        b = Path(row['rollout_id'])
        manifest = final.read(b / 'raw/manifest.json')
        with np.load(b / 'raw/raw_streams.npz', allow_pickle=False) as raw:
            streams = {k[8:]: raw[k] for k in raw.files if k.startswith('stream__')}
        streams['field_metadata'] = manifest['stream_field_metadata']
        validate_raw_streams(streams)
        n = len(streams['controller_effective_setpoint'])
        assert n == manifest['action_count']
        assert len(streams['realized_qpos']) == manifest['state_count'] == n + 1
        with np.load(b / 'trace_source.npz', allow_pickle=False) as tr:
            assert np.array_equal(streams['realized_qpos'][0], tr['joint_qpos'][0])
            assert np.array_equal(streams['realized_qvel'][0], tr['joint_qvel'][0])
        ca = current.audit(currents[row['root_id']], b / 'trace_source.npz')
        assert manifest['provenance']['program_id'] == row['program_id']
        assert not manifest['provenance']['synthetic']
        assert final.sha(b / 'raw/raw_streams.npz') == row['raw_id']
        rows.append({**row, 'actions': n, 'states': n + 1,
            'raw_N_Nplus1_stream_contract_pass': True,
            'raw_state0_equals_trace_state0': True,
            'current_initial_state_audit': ca,
            'trace_sha256': final.sha(b / 'trace_source.npz'),
            'raw_provenance_realization_spec': manifest['provenance']['realization_spec'],
            'video_sha256': final.sha(b / 'video/trajectory.mp4')})
        print('checked', row['root_id'], row['program_id'], row['realization'], flush=True)
    assert len(rows) == len({r['raw_id'] for r in rows}) == 18
    report = final.seal({'schema_version': 'goal_pilot48_independent_reuse18_v1',
        'pass': True, 'eligible_existing_cells': 18, 'existing_roots': 3,
        'goal_target_roots': 8, 'goal_target_cells': 48,
        'scope': 'Explicit reuse eligibility only; scheduling authority signs adoption separately',
        'scientific_stage1_gate_pass_claimed': False,
        'stage_acceptance_issued': False, 'original_artifacts_modified': False,
        'new_scenes': 0, 'new_raw': 0, 'gpu_execution': False,
        'bindings': bindings, 'rows': rows, 'elapsed_seconds': time.time() - started,
        'coverage': ['all18 disk raw/trace/video hashes', 'root finalizer recomputation',
          'N actions/N+1 states with frozen 250Hz interval alignment',
          'all18 current state equals trace/raw row0 using lossless 38+38 decode',
          'current RGB and gripper component hashes', 'root/program/realization binding',
          'F4 six-trajectory final-state equivalence', 'legal resolved-receipt lineage inherited from hash-bound catalog'],
        'limitations': ['No simulator replay or new visual inspection; existing immutable video content hashes and recorded verifier evidence are reused.',
          'F4 original failed terminal and F1 UTF8 failure remain preserved; adoption relies on their previously authorized append-only resolution, not rewritten original receipts.',
          'Historical cleanup receipts are verified; this audit does not infer a new live GPU cleanup event.',
          'Semantic family verifier results are hash-bound and root-finalized; this audit does not rerun every physical verifier implementation.']})
    write_new(Path(__file__).parent / 'audit.json', report)
    return report

if __name__ == '__main__':
    result = run()
    print(json.dumps({'pass': result['pass'], 'cells': 18, 'receipt_sha256': result['receipt_sha256']}))
