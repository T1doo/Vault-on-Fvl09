"""Upright scene/spec hooks only; never instantiate a Scene at import time."""
import copy,types
import numpy as np
from .geometry import matrix,pose
def make_scene_class(spec,base_class=None,pose_factory=None):
    if spec['selected_design']!='B_upper_straight_body' or spec['asset_id']!=13:raise ValueError('only uniquely selected upright B/13')
    if base_class is None:
        from controlled_multi_future.probes.scene_inspection import F3Scene
        base_class=F3Scene
    original=base_class.load_actors;env=dict(original.__globals__);create=env['create_actor']
    if pose_factory is None:pose_factory=lambda p:env['sapien'].Pose(p[:3],p[3:])
    def upright_create(scene,old_pose,modelname,*args,**kwargs):
        if modelname!='001_bottle' or kwargs.get('model_id')!=13:raise ValueError('unexpected actor replacement')
        return create(scene,pose_factory(spec['bottle_actor_pose']),modelname,*args,**kwargs)
    env['create_actor']=upright_create
    fn=types.FunctionType(original.__code__,env)
    class UprightF3Scene(base_class):
        def load_actors(self):
            self._cmf_upright_design_spec=copy.deepcopy(spec)
            fn(self)
    return UprightF3Scene
def derive_targets(spec,actual_bottle_pose):
    actual=matrix(actual_bottle_pose)
    return {name:pose(actual@matrix(spec[name+'_in_bottle_frame'])) for name in ('grasp','pregrasp')}
def initial_gate(snapshot,spec):
    from controlled_multi_future.anchor import quaternion_angular_error
    from controlled_multi_future.f3_scene_binding_equivalence_v1 import BOTTLE_POSITION_ATOL_M,BOTTLE_ORIENTATION_ATOL_RAD,FIXTURE_POSITION_ATOL_M,FIXTURE_ORIENTATION_ATOL_RAD
    from controlled_multi_future.runtime_v2_contracts import PROVISIONAL_RUNTIME_THRESHOLDS as T
    def pose_check(a,b,p,r):return np.linalg.norm(np.asarray(a[:3])-b[:3])<=p and quaternion_angular_error(a[3:],b[3:])<=r
    expected=spec['expected_mass_properties'];actual=snapshot['mass_properties']
    checks={'seed_exact':snapshot['seed']==spec['seed'],'actual_scene_identity':bool(snapshot['scene_instance_id']),
        'canonical_settle60':snapshot['canonical_settle_steps']==60,'asset13_scale_unchanged':snapshot['asset_id']==13 and snapshot['scale']==[.132]*3,
        'bottle_pose_original_tolerances':bool(pose_check(snapshot['bottle_pose'],spec['bottle_actor_pose'],BOTTLE_POSITION_ATOL_M,BOTTLE_ORIENTATION_ATOL_RAD)),
        'pad_pose_original_tolerances':bool(pose_check(snapshot['pad_pose'],spec['pad_actor_pose'],FIXTURE_POSITION_ATOL_M,FIXTURE_ORIENTATION_ATOL_RAD)),
        'marker_pose_original_tolerances':bool(pose_check(snapshot['marker_pose'],[0,-.05,.95,1,0,0,0],FIXTURE_POSITION_ATOL_M,FIXTURE_ORIENTATION_ATOL_RAD)),
        'real_pad_support':snapshot['pad_physical_contact'] is True,'contact_signal_complete':snapshot['contact_signal_complete'] is True,
        'linear_stable_original':np.linalg.norm(snapshot['linear_velocity'])<=T['stable_linear_speed_mps'],
        'angular_stable_original':np.linalg.norm(snapshot['angular_velocity'])<=T['eef_stationary_angular_speed_rps'],
        'mass_exact':actual['mass_kg']==expected['mass_kg'],
        'inertia_exact':np.array_equal(actual['principal_inertia_kg_m2'],expected['principal_inertia_kg_m2']),
        'local_COM_exact':np.array_equal(actual['cmass_local_pose'],expected['cmass_local_pose'])}
    checks={k:bool(v) for k,v in checks.items()}
    return {'pass':all(checks.values()),'checks':checks,'new_nominal_pose_not_new_numeric_tolerances':True,
        'historical_mass_record_world_COM_not_used':True,'actual_target_or_stability_not_inferred_from_CPU':True}
