"""Independent F1 terminal semantics from actual saved arrays; no runner pass input."""
import json
from pathlib import Path
import numpy as np


def verify_f1_disk(*, raw_dir, spec, program):
    from controlled_multi_future.verifiers import verify_true_cavity_obb
    from controlled_multi_future.geometry import quaternion_orientation_error
    from controlled_multi_future.runtime_v2_contracts import PLASTICBOX_BASE3_CAVITY, PROVISIONAL_RUNTIME_THRESHOLDS as T
    raw_dir=Path(raw_dir)
    checks={}
    try:
        role=program['target_role']; role_spec=next(r for r in spec['roles'] if r['role']==role)
        root=raw_dir.parent.parent.parent
        suffix=json.loads((root/'suffix_artifacts'/program['program_id']/'frozen_suffix_artifact.json').read_text())
        rest=np.asarray(suffix['execution_spec']['targets'][-1]['pose'])
        if suffix['execution_spec']['targets'][-1]['segment_id']!='rest': raise ValueError('frozen rest target missing')
        window=int(T['stable_window_frames'])
        with np.load(raw_dir/'raw_streams.npz',allow_pickle=False) as z:
            selected=z['audit__role_object_pose__'+role]; box=z['audit__role_object_pose__common_box']
            checks['subject_identity']=np.array_equal(selected[-1],z['audit__object_pose'][-1])
            checks['true_inside']=verify_true_cavity_obb(selected[-1],np.asarray(role_spec['size'])/2,box[-1],PLASTICBOX_BASE3_CAVITY)['pass_true_cavity_obb']
            checks['stable_window_present']=len(selected)>=window
            speeds=z['audit__role_object_linear_velocity__'+role][-window:]
            angular=z['audit__role_object_angular_velocity__'+role][-window:]
            checks['stable_linear']=bool(len(speeds)) and float(np.max(np.linalg.norm(speeds,axis=-1)))<=T['stable_linear_speed_mps']
            checks['stable_angular']=bool(len(angular)) and float(np.max(np.linalg.norm(angular,axis=-1)))<=T['eef_stationary_angular_speed_rps']
            subject_name='formal_f1_'+role;support_name='formal_f1_common_box'
            contacts=[json.loads(str(row)) for row in z['audit__contact_pairs_json'][-window:]]
            checks['continuous_box_support_contact']=bool(contacts) and all(any({pair['body_a'],pair['body_b']}=={subject_name,support_name} for pair in row) for row in contacts)
            eef=np.asarray(z['stream__realized_eef'][-1])[:7]
            checks['rest_position']=float(np.linalg.norm(eef[:3]-rest[:3]))<=T['rest_position_error_m']
            checks['rest_orientation']=quaternion_orientation_error(eef[3:],rest[3:])<=T['orientation_error']
            checks['eef_linear_stationary']=float(np.linalg.norm(z['audit__eef_linear_velocity'][-1]))<=T['eef_stationary_linear_speed_mps']
            checks['eef_angular_stationary']=float(np.linalg.norm(z['audit__eef_angular_velocity'][-1]))<=T['eef_stationary_angular_speed_rps']
            checks['gripper_open']=float(z['stream__gripper_command'][-1][0])>.8
            for r in spec['roles']:
                if r['role']==role:continue
                poses=z['audit__role_object_pose__'+r['role']]
                checks['unchanged:'+r['role']]=float(np.max(np.linalg.norm(poses[:,:3]-poses[0,:3],axis=-1)))<=T['non_target_displacement_m']
    except (KeyError,OSError,ValueError,TypeError,StopIteration,IndexError) as exc:
        return {'pass':False,'checks':checks,'error':str(exc),'runner_pass_used':False}
    return {'pass':bool(checks) and all(checks.values()),'checks':checks,'runner_pass_used':False,'threshold_source':'runtime_v2_contracts.PROVISIONAL_RUNTIME_THRESHOLDS','geometry_source':'actual role half-size + PLASTICBOX_BASE3_CAVITY'}
