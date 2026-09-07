"""Future implementation hook only; never installed into the running root."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import uuid
import numpy as np
from controlled_multi_future.current_hasher import hash_array
from realization_utf8_io_v1 import write_new

def build_arrays(scene):
    rgb=scene.cameras.get_rgb();left=scene.robot.left_entity;right=scene.robot.right_entity
    ql=np.asarray(left.get_qpos(),dtype=np.float64);qr=np.asarray(right.get_qpos(),dtype=np.float64)
    vl=np.asarray(left.get_qvel(),dtype=np.float64);vr=np.asarray(right.get_qvel(),dtype=np.float64)
    if ql.shape!=(38,) or vl.shape!=(38,) or not np.array_equal(ql,qr) or not np.array_equal(vl,vr):
        raise ValueError('not the audited shared38-DOF Aloha storage layout')
    from controlled_multi_future.real_sapien_adapter_v1_1 import _gripper_joint_qpos
    return dict(head_rgb=np.asarray(rgb['head_camera']['rgb']),left_wrist_rgb=np.asarray(rgb['left_camera']['rgb']),
        right_wrist_rgb=np.asarray(rgb['right_camera']['rgb']),robot_qpos=np.concatenate((ql,qr)),robot_qvel=np.concatenate((vl,vr)),
        gripper_joint_qpos=np.concatenate((_gripper_joint_qpos(scene.robot,'left'),_gripper_joint_qpos(scene.robot,'right'))))

def validate_arrays(arrays,current):
    c=current['model_visible_components'];q=arrays['robot_qpos'];v=arrays['robot_qvel']
    if q.shape!=(76,) or v.shape!=(76,) or not np.array_equal(q[:38],q[38:]) or not np.array_equal(v[:38],v[38:]):raise ValueError('redundant copies differ')
    checks=dict(head=hash_array(arrays['head_rgb'])==c['head_rgb_sha256'],left=hash_array(arrays['left_wrist_rgb'])==c['wrist_rgb_sha256']['left'],
        right=hash_array(arrays['right_wrist_rgb'])==c['wrist_rgb_sha256']['right'],
        unique76=hash_array(np.concatenate((q[:38],v[:38])))==c['robot_state_sha256'],gripper=hash_array(arrays['gripper_joint_qpos'])==c['gripper_actual_state_sha256'])
    if not all(checks.values()):raise ValueError('capture bytes differ from sealed current hashes')
    return checks

def atomic_npz(path,arrays):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp.'+uuid.uuid4().hex)
    try:
        with tmp.open('xb') as f:np.savez_compressed(f,**arrays);f.flush();os.fsync(f.fileno())
        os.link(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()

@contextmanager
def persist_pristine_current(adapter,*,root_directory):
    root=Path(root_directory).resolve();original=adapter.capture_current;had='capture_current' in vars(adapter);old=vars(adapter).get('capture_current')
    state={'persisted':False,'hook_version':'pristine_current_v1_future_only'}
    def capture(scene):
        current=original(scene)
        phase=getattr(getattr(scene,'_cmf_scene_context_v1_2',None),'phase',None)
        if phase=='pristine':
            if state['persisted']:raise ValueError('pristine current already persisted')
            arrays=build_arrays(scene);checks=validate_arrays(arrays,current)
            path=root/'current/current_arrays.npz';atomic_npz(path,arrays)
            import hashlib
            metadata=dict(parent_root=str(root),current=current,arrays_file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                captured_in_original_pristine_phase=True,storage_decode='existing lossless38+38 state; two equal entity aliases')
            write_new(root/'current/current.json',metadata)
            state.update(persisted=True,component_checks=checks,current_directory=str(root/'current'))
        return current
    adapter.capture_current=capture
    try:yield state
    finally:
        if adapter.capture_current is not capture:raise RuntimeError('current capture hook was replaced')
        if had:adapter.capture_current=old
        else:delattr(adapter,'capture_current')
