"""CPU-tested controlled physical ordering; no default simulator backend.

Model/geometry prerequisites must pass before a concrete future backend can
execute. The current inside anatomy is incompatible and is refused here.
"""
from dataclasses import dataclass
import functools

def solver_free_execution(function):
    @functools.wraps(function)
    def wrapped(backend,*args,**kwargs):
        before=backend.solver_query_count
        if type(before) is not int or before<0:raise ValueError('unknown solver counter before replay')
        result=function(backend,*args,**kwargs)
        after=backend.solver_query_count
        if type(after) is not int or after!=before:raise RuntimeError('physical frozen-suffix execution made a new solver call')
        result['planner_queries_during_execution']=after-before
        return result
    return wrapped

def require_support_certificate(certificate,relation):
    if certificate.get('relation')!=relation or certificate.get('native_support_certified') is not True:
        raise ValueError('no matching native support certificate')
    if certificate.get('all_robot_and_sidewall_checks_retained') is not True or certificate.get('blanket_container_disable') is not False:
        raise ValueError('unsafe support collision partition')
    if relation=='inside' and certificate.get('unchanged_strict_inside_at_support') is not True:
        raise ValueError('native support conflicts with unchanged strict-inside predicate')

@solver_free_execution
def execute_inside(backend,certificate):
    """Requires already planned three carry + two empty-hand controls (5 calls)."""
    require_support_certificate(certificate,'inside')
    for index in range(3):backend.execute_carried_segment(index)
    backend.wait_and_record(50)
    support=backend.original_controlled_support_gate()
    if not support['pass']:return {'pass':False,'stage':'support_before_open','support_gate':support,'full_open_executed':False}
    safety=None
    for target in (.2,.4,.6,.8,1.):
        if target==1.:
            safety=backend.original_release_safety_gate_v10()
            if not safety['pass']:return {'pass':False,'stage':'release_safety_v10','support_gate':support,'safety_gate':safety,'full_open_executed':False}
        backend.open_gripper(target);backend.wait_and_record(10)
    backend.begin_final_settle_window();backend.wait_and_record(250)
    model=backend.install_actual_released_can_open_gripper_fullworld()
    if not model['pass']:return {'pass':False,'stage':'released_model','full_open_executed':True}
    for index in (3,4):backend.execute_empty_hand_segment(index)
    backend.wait_and_record(75)
    final=backend.original_final_inside_gate_v10()
    return {'pass':final['pass'],'stage':'final_inside_v10','support_gate':support,'safety_gate':safety,'final_gate':final,'full_open_executed':True,
            'primary_gravity_drop':False,'planner_queries_during_execution':0}

@solver_free_execution
def execute_on(backend,certificate):
    """Four preplanned segments; scale support/release uses on semantics only."""
    require_support_certificate(certificate,'on')
    for index in (0,1):backend.execute_carried_segment(index)
    backend.wait_and_record(50)
    support=backend.scale_support_release_gate()
    if not support['pass']:return {'pass':False,'stage':'scale_support_before_open','full_open_executed':False}
    backend.open_gripper(1.);backend.wait_and_record(250)
    model=backend.install_actual_released_can_open_gripper_fullworld()
    if not model['pass']:return {'pass':False,'stage':'released_model','full_open_executed':True}
    for index in (2,3):backend.execute_empty_hand_segment(index)
    backend.wait_and_record(75)
    final=backend.original_on_family_verifier()
    return {'pass':final['pass'],'stage':'on_family_verifier','support_gate':support,'final_gate':final,'full_open_executed':True,'planner_queries_during_execution':0}

def validate_partition_shapes(shapes,allowed_ids,support_plane_world_z,vertices_world):
    """Reject a floor/sidewall compound instead of dropping its wall geometry."""
    if not allowed_ids:raise ValueError('no identified supporting shape')
    by_name={s['name']:s for s in shapes}
    if len(by_name)!=len(shapes) or any(n not in by_name for n in allowed_ids):raise ValueError('unknown/duplicate support shape')
    roles={by_name[n]['role'] for n in allowed_ids}
    if len(roles)!=1 or not roles.issubset({'box','scale'}):raise ValueError('mixed support fixture')
    for name in allowed_ids:
        v=vertices_world(by_name[name])
        if v[:,2].max()>support_plane_world_z+1e-4:raise ValueError('support shape contains geometry above support plane; possible sidewall')
    return {'support_shape_ids':list(allowed_ids),'robot_uses_full_world':True,'only_attached_can_view_filtered':True,'blanket_container_disable':False,
            'native_contact_and_footprint_gate_still_required':True}
