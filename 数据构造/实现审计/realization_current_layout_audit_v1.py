"""Lossless current-state storage decoding, verified against immutable raw row0."""
import json,hashlib
from pathlib import Path
import numpy as np
from controlled_multi_future.current_hasher import hash_array
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def audit(current_directory,trace_path):
    current_directory=Path(current_directory);trace_path=Path(trace_path)
    metadata=json.loads((current_directory/'current.json').read_text(encoding='utf-8'))
    components=metadata['current']['model_visible_components']
    with np.load(trace_path,allow_pickle=False) as trace:
        q=trace['joint_qpos'][0];v=trace['joint_qvel'][0]
    with np.load(current_directory/'current_arrays.npz',allow_pickle=False) as stored:
        n=len(q);sq=stored['robot_qpos'].astype(np.float64);sv=stored['robot_qvel'].astype(np.float64)
        assert len(sq)%n==0 and len(sv)==len(sq)
        copies=len(sq)//n
        assert copies in (1,2)
        assert all(np.array_equal(part,q) for part in np.split(sq,copies))
        assert all(np.array_equal(part,v) for part in np.split(sv,copies))
        state=np.concatenate((sq[:n],sv[:n]))
        checks={'storage_array_file_hash':sha(current_directory/'current_arrays.npz')==metadata['arrays_file_sha256'],
            'head_rgb':hash_array(stored['head_rgb'])==components['head_rgb_sha256'],
            'left_wrist_rgb':hash_array(stored['left_wrist_rgb'])==components['wrist_rgb_sha256']['left'],
            'right_wrist_rgb':hash_array(stored['right_wrist_rgb'])==components['wrist_rgb_sha256']['right'],
            'model_visible_robot_state':hash_array(state)==components['robot_state_sha256'],
            'gripper_state':hash_array(stored['gripper_joint_qpos'])==components['gripper_actual_state_sha256']}
        assert all(checks.values())
    return {'current_directory':str(current_directory),'trace_path':str(trace_path),'trace_file_sha256':sha(trace_path),
        'current_json_file_sha256':sha(current_directory/'current.json'),'checks':checks,'pass':True,
        'storage_entity_copies':copies,'unique_articulation_dofs':n,'model_visible_robot_state_dimension':2*n,
        'decoding':'float64 concat(stored_qpos[:unique_dofs], stored_qvel[:unique_dofs]); all redundant copies checked equal to raw initial state',
        'raw_reference_state_index':0,'future_state_values_used':False,'old_files_modified':False}

def run():
    b=W/'Robotwin2/datasets/cmf_realization_unattempted8_v1_3'
    pairs=[(W/'Robotwin2/datasets/cmf_realization_recovery_v1_2/F1_A_path/current',W/'Robotwin2/datasets/cmf_realization_recovery_v1_2/F1_A_path/branches/F1-red/trace_source.npz'),
        (b/'F1_B_motion/current',b/'F1_B_motion/branches/F1-green/trace_source.npz'),(b/'F4_A_path/current',b/'F4_A_path/branches/F4-ABC/trace_source.npz')]
    result={'schema_version':'cmf_realization_current_storage_layout_audit_v1','cohorts':[audit(*p) for p in pairs],
        'source':'runtime_trace._dual_entity_values deduplicates shared Aloha articulation; collector storage concatenated left/right aliases',
        'new_gpu_scenes':0,'new_raw_trajectories':0,'acceptance_thresholds_changed':False}
    result['receipt_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
    return result

if __name__=='__main__':print(json.dumps(run(),sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False))
