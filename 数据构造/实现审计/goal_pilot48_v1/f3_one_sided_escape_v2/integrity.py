"""Pure integrity checks that run before CUDA construction or control execution."""
import hashlib,json
import numpy as np
def canonical_hash(value):
    from controlled_multi_future.canonical_artifact import canonical_jsonable
    return hashlib.sha256(json.dumps(canonical_jsonable(value),sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def verify_factory_inputs(robot_config,world_export,certificate):
    from .certificate import validate
    if not validate(certificate):raise ValueError('invalid certificate before CUDA construction')
    if canonical_hash(world_export['shapes'])!=certificate['world_sha256']:raise ValueError('certificate world geometry changed')
    if canonical_hash(robot_config)!=certificate['robot_config_sha256']:raise ValueError('certificate robot config changed')
def verify_actual_binding(certificate,*,native_shapes,joint_names,qpos,actor_pose,eef_pose,world_shapes):
    from .certificate import validate
    if not validate(certificate):raise ValueError('invalid certificate before native screening')
    if canonical_hash(native_shapes)!=certificate['native_geometry_sha256']:raise ValueError('native bottle geometry changed')
    if canonical_hash(world_shapes)!=certificate['world_sha256']:raise ValueError('world geometry changed after planning')
    if list(joint_names)!=certificate['actual_joint_names']:raise ValueError('actual named joint order changed')
    for name,current in [('actual_qpos',qpos),('actual_actor_pose',actor_pose),('actual_eef_pose',eef_pose)]:
        if not np.array_equal(np.asarray(current),np.asarray(certificate[name])):raise ValueError('certificate actual-state binding changed: '+name)
    return True
