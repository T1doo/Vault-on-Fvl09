"""Compare actual current arrays/anchors across qualification attempts, not accept roots."""
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
DATA = Path('/nfs_share/lijunhui/Robotwin2/datasets')
PATHS = [DATA/'p48_f2_on_release_revision1_001/on',
         DATA/'p48_f2_beside_qualification_001/beside',
         DATA/'p48_f2_inside_carry_revision1_002']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def run():
    reference = PATHS[0]
    current = read(reference/'actual_current.json')
    anchor = read(reference/'actual_initial_anchor.json')
    replay = read(reference/'actual_replay.json')
    keys = ('artifact_sha256', 'executed_prefix_action_sha256', 'executed_prefix_step_count')
    rows = []
    files = {str(Path(__file__)): sha(Path(__file__))}
    with np.load(reference/'current_arrays.npz', allow_pickle=False) as expected:
        for path in PATHS:
            with np.load(path/'current_arrays.npz', allow_pickle=False) as actual:
                arrays_equal = set(actual.files) == set(expected.files) and all(
                    actual[k].dtype == expected[k].dtype and actual[k].shape == expected[k].shape
                    and actual[k].tobytes() == expected[k].tobytes() for k in expected.files)
            branch_replay = read(path/'actual_replay.json')
            rows.append({'path':str(path), 'current_arrays_byte_equal': arrays_equal,
                         'current_record_equal': read(path/'actual_current.json') == current,
                         'initial_anchor_record_equal': read(path/'actual_initial_anchor.json') == anchor,
                         'replay_identity_equal': all(branch_replay[k] == replay[k] for k in keys),
                         'recorded_prefix_end_equivalent': branch_replay['prefix_end_equivalent']})
            for name in ('current_arrays.npz', 'actual_current.json', 'actual_initial_anchor.json', 'actual_replay.json'):
                files[str(path/name)] = sha(path/name)
    result = {'schema_version':'f2_three_attempt_same_current_lineage_review_v1', 'rows': rows,
              'comparison_pass':all(all(v is True for k,v in row.items() if k != 'path') for row in rows),
              'current_aggregate_sha256':current['aggregate_sha256'],
              'replay_identity':{k:replay[k] for k in keys}, 'files':files,
              'inside_success':False, 'root_or_pilot_acceptance':False,
              'scope':'byte-level current arrays and recorded anchor/prefix lineage only; no suffix success inference',
              'new_gpu_or_physical_execution':False}
    payload = json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    result['receipt_sha256'] = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    return result

if __name__ == '__main__':
    from realization_utf8_io_v1 import write_new
    result = run()
    write_new(ROOT/'F2_QUALIFICATION_LINEAGE_REVIEW_001.json', result)
    print(result['comparison_pass'],result['receipt_sha256'])
