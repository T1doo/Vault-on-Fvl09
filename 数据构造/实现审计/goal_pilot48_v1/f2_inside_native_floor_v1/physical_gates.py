"""New geometry provider composed with unchanged original numerical Gates."""
from .certificate import VERSION,digest
from .contact import verify_floor_contact_window

def opening_geometry(scene,binding,certificate,*,can_actor_pose=None,box_actor_pose=None):
    """Original formula, private native can geometry provider; no global patch."""
    import types,numpy as np
    from controlled_multi_future import high_level_physical_runner_v1 as original
    from controlled_multi_future.geometry import compose_pose
    if binding['binding_sha256']!=certificate['binding_sha256']:raise ValueError('opening geometry binding mismatch')
    ns=dict(original._inside_opening_geometry.__globals__)
    def bounds(actor):
        if actor is scene.can:return np.asarray(certificate['can_native_center_m']),np.asarray(certificate['can_native_half_extents_m'])
        return original._actor_local_geometry_bounds(actor)
    def center_pose(actor,*,actor_pose=None):
        center,_=bounds(actor)
        return compose_pose(original._pose(actor) if actor_pose is None else actor_pose,[*center,1,0,0,0])
    ns['_actor_local_geometry_bounds']=bounds;ns['_actor_geometry_center_pose']=center_pose
    fn=types.FunctionType(original._inside_opening_geometry.__code__,ns,original._inside_opening_geometry.__name__,original._inside_opening_geometry.__defaults__,original._inside_opening_geometry.__closure__)
    fn.__kwdefaults__=original._inside_opening_geometry.__kwdefaults__
    return fn(scene,binding,can_actor_pose=can_actor_pose,box_actor_pose=box_actor_pose)

def release_safety_gate(scene,binding,safety_rows,geometry_verifier,*,selected_finger_link_names):
    from controlled_multi_future.f2_release_gates_v10 import audit_f2_release_safety_gate_v10
    if len(safety_rows)!=50:raise ValueError('original50-frame release safety window required')
    c=geometry_verifier.c
    geometry=[opening_geometry(scene,binding,c,can_actor_pose=r['role_actor_poses']['main_can'],box_actor_pose=r['role_actor_poses']['box']) for r in safety_rows]
    original=audit_f2_release_safety_gate_v10(safety_rows,geometry,can_actor_name=c['can_actor_name'],box_actor_name=c['box_actor_name'],selected_finger_link_names=selected_finger_link_names)
    floor=verify_floor_contact_window(safety_rows[-10:],geometry_verifier,expected_frames=10)
    return {'verifier_version':VERSION,'original_release_safety_v10':original,'actual_floor_support_window':floor,
      'pass':bool(original['pass'] and floor['pass']),'physical_thresholds_changed':False}

def final_inside_gate(settle_rows,geometry_verifier,*,on_predicate,beside_predicate,gripper_full_open,arm_rest_pass):
    from controlled_multi_future.f2_release_gates_v10 import audit_f2_final_inside_success_gate_v10
    if len(settle_rows)!=250:raise ValueError('exactly250 post-release settle rows required')
    final=settle_rows[-1];poses=final['role_actor_poses'];c=geometry_verifier.c
    geom=geometry_verifier.evaluate(poses['main_can'],poses['box'],binding_sha256=c['binding_sha256'],frame=final.get('actor_pose_frame','world'))
    support=verify_floor_contact_window(settle_rows[-10:],geometry_verifier,expected_frames=10)
    physical=audit_f2_final_inside_success_gate_v10(settle_rows,true_cavity_obb_pass=geom['pass'],
      relation_predicates={'inside':geom['pass'],'on':on_predicate,'beside':beside_predicate},gripper_full_open=gripper_full_open,
      arm_rest_pass=arm_rest_pass,can_actor_name=c['can_actor_name'],box_actor_name=c['box_actor_name'])
    result={'schema_version':'f2_final_inside_native_floor_v1','verifier_version':VERSION,'certificate_sha256':c['receipt_sha256'],
      'native_geometry':geom,'actual_floor_support_window':support,'unchanged_V10_physical_gate':physical,
      'pass':bool(geom['pass'] and support['pass'] and physical['pass']),
      'physical_thresholds_changed':False,'old_failure_reinterpretation':False}
    result['receipt_sha256']=digest(result);return result

def pre_release_floor_support(rows,geometry_verifier,*,original_support_gate):
    if len(rows)!=50:raise ValueError('original50-frame support window required')
    certificate=verify_floor_contact_window(rows,geometry_verifier,expected_frames=50)
    return {'verifier_version':VERSION,'original_support_gate':original_support_gate,'actual_floor_support_window':certificate,
            'pass':bool(original_support_gate.get('pass') is True and certificate['pass']),'original_thresholds_changed':False}
