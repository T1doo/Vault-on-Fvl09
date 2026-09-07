"""Inside suffix only, on a caller-owned freshly replayed canonical scene.

No issuer/scene/root collector is installed here. The caller owns mandatory
live action/collection meter and cleanup, even on a returned failure.
"""
import numpy as np
from .spec import build_targets,prefix_lineage,digest
from .controller import execute
from .native import screen_actor_path
from . import gates

class LiveBackend:
    def __init__(self,scene,spec,certificate,output):
        from .live_models import LiveModels
        from goal_pilot48_v1.f2_inside_native_floor_v1.geometry_verifier import GeometryVerifier
        self.scene=scene;self.spec=spec;self.models=LiveModels(scene,output);self.verifier=GeometryVerifier(certificate);self.binding=scene._cmf_f2_asset_binding_v3
        self.plans={};self.before=scene.planner_query_count;self.settle_rows=None;self.held_start=len(scene.trace)-1;self.descent_start=None
    @property
    def solver_query_count(self):return self.scene.planner_query_count
    def install_carried_fullworld(self):return self.models.install_carried_fullworld()
    def install_floor_only(self):return self.models.install_floor_only(self.verifier.c,self.spec['target_geometry'],self.spec['target_actor_pose'])
    def plan_one(self,i):
        from controlled_multi_future.family_runners_v3_1 import _plan_chain
        if i in self.plans or self.solver_query_count>=self.before+5:raise ValueError('single attempt per segment')
        plan=_plan_chain(self.scene,[self.spec['targets'][i]],query_limit=self.before+5,arm='left');self.plans[i]=plan
        return {'pass':plan.get('pass') is True,'segment_receipts':plan.get('segment_receipts',[])}
    def screen_carried(self,i):
        from controlled_multi_future.family_runners_v3_3 import _pose
        control=self.plans[i]['controls'][0];poses=self.models.native_can_actor_poses(control)
        return screen_actor_path(poses,_pose(self.scene.box),self.verifier,actual_start_can_pose=_pose(self.scene.can),require_support=i==2)
    def execute_one(self,i):
        from controlled_multi_future.high_level_physical_runner_v1 import _execute_planned_segment
        before=self.solver_query_count
        if i==2:self.descent_start=len(self.scene.trace)-1-self.held_start
        r=_execute_planned_segment(self.scene,self.plans[i]['controls'],[self.spec['targets'][i]],0,'left')
        if self.solver_query_count!=before:raise ValueError('execution unexpectedly invoked solver')
        gate=self.transport_gate() if i<3 else None
        return {'pass':gate['pass'] if gate is not None else True,'original_execution_receipt':r,'full_held_transport_gate':gate,
          'per_segment_numeric_tracking_gate_existed_in_original_F2':False}
    def transport_gate(self):
        from controlled_multi_future.family_runners_v3_3 import _gripper_below_eef_envelope,_f2_left_gripper_assembly_topology,_entity
        from .transport import audit_transport
        topology=_f2_left_gripper_assembly_topology(self.scene)
        return audit_transport(self.scene.trace[self.held_start:],descent_start_relative_row=self.descent_start,verifier=self.verifier,
          can_actor_name=_entity(self.scene.can).get_name(),selected_gripper_body_names=_gripper_below_eef_envelope(self.scene,arm='left')['selected_gripper_links'],
          allowed_gripper_assembly_body_names=topology['allowed_gripper_assembly_body_names'],
          named_facility_body_names=[_entity(actor).get_name() for actor in (self.scene.box,self.scene.scale,self.scene.stand)])
    def wait_and_record(self,n):
        from controlled_multi_future.high_level_physical_runner_v1 import _wait_and_record
        _wait_and_record(self.scene,n)
        if n==250 and hasattr(self,'settle_start'):self.settle_rows=list(self.scene.trace[self.settle_start:])
    def support_gate(self):
        original=gates.support_gate(self.scene,self.binding,self.verifier);transport=self.transport_gate()
        return {'pass':bool(original['pass'] and transport['pass']),'support_gate':original,'whole_held_and_support_window_transport':transport}
    def release_safety_gate(self):return gates.release_safety_gate(self.scene,self.binding,gates.physical_rows(self.scene.trace[-50:]),self.verifier,selected_finger_link_names=self.scene.selected_gripper_links())
    def open_gripper(self,target):
        from controlled_multi_future.high_level_physical_runner_v1 import _must_action,_arm_tag
        _must_action(self.scene,self.scene.open_gripper(_arm_tag('left'),pos=target),'f2_inside_native_floor_slow_release_'+str(target))
    def begin_settle(self):self.settle_start=len(self.scene.trace)
    def install_released_fullworld(self):
        from model_apply import runtime_joint_state
        from controlled_multi_future.family_runners_v3_3 import _pose,_arm_gripper_open
        names,q=runtime_joint_state(self.scene)
        evidence={'pass':True,'full_open_executed':True,'gripper_full_open':bool(_arm_gripper_open(self.scene,'left')),
          'can_world_pose':np.asarray(_pose(self.scene.can)).tolist(),'joint_names':list(names),'qpos':np.asarray(q).tolist()}
        evidence['receipt_sha256']=digest(evidence)
        return self.models.install_actual_released_fullworld(evidence)
    def final_gate(self):
        from controlled_multi_future.high_level_physical_runner_v1 import _f2_relation_predicates,_arm_eef_pose,_arm_gripper_open,quaternion_angular_error
        from controlled_multi_future.runtime_v2_contracts import PROVISIONAL_RUNTIME_THRESHOLDS as t
        current=np.asarray(_arm_eef_pose(self.scene,'left'));neutral=np.asarray(self.spec['targets'][4]['pose'])
        rest=bool(np.linalg.norm(current[:3]-neutral[:3])<=t['rest_position_error_m'] and quaternion_angular_error(current[3:],neutral[3:])<=t['orientation_error'])
        relations=_f2_relation_predicates(self.scene,self.binding)
        original=gates.final_inside_gate(gates.physical_rows(self.settle_rows),self.verifier,on_predicate=relations['on'],beside_predicate=relations['beside'],gripper_full_open=_arm_gripper_open(self.scene,'left'),arm_rest_pass=rest)
        from controlled_multi_future.family_runners_v3_3 import _pose
        from goal_pilot48_v1.f2_inside_native_floor_v1.contact import verify_floor_contact_window
        final_geometry=self.verifier.evaluate(_pose(self.scene.can),_pose(self.scene.box),binding_sha256=self.binding['binding_sha256'])
        final_contact=verify_floor_contact_window(gates.physical_rows(self.scene.trace[-10:]),self.verifier,expected_frames=10)
        from controlled_multi_future.family_runners_v3_3 import _stable_and_support
        from controlled_multi_future.geometry import quaternion_orientation_error
        stable_rows,speeds,support=_stable_and_support(self.scene,self.scene.can,self.scene.box)
        angular=[float(np.linalg.norm(r['actor_angular_velocity'])) for r in stable_rows]
        family_checks={'stable_window':bool(speeds) and max(speeds)<=t['stable_linear_speed_mps'] and bool(angular) and max(angular)<=t['eef_stationary_angular_speed_rps'],
          'support_contact_window':bool(support) and all(support),'rest_position':bool(np.linalg.norm(current[:3]-neutral[:3])<=t['rest_position_error_m']),
          'rest_orientation':bool(quaternion_orientation_error(current[3:],neutral[3:])<=t['orientation_error']),
          'eef_linear_stationary':bool(np.linalg.norm(self.scene.trace[-1]['eef_linear_velocity'])<=t['eef_stationary_linear_speed_mps']),
          'eef_angular_stationary':bool(np.linalg.norm(self.scene.trace[-1]['eef_angular_velocity'])<=t['eef_stationary_angular_speed_rps'])}
        return {'pass':bool(original['pass'] and final_geometry['pass'] and final_contact['pass'] and all(family_checks.values())),
          'original_250_settle_and_rest_gate':original,'actual_after_retreat_rest_geometry':final_geometry,
          'actual_after_retreat_rest_floor_contact':final_contact,'original_family_final_checks':family_checks,'physical_thresholds_changed':False}

def validate_initial_anchor_lineage(actual_sha256,reference_sha256,equivalence):
    if equivalence is None:
        if actual_sha256!=reference_sha256:raise ValueError('different anchor hash requires original equivalence receipt')
        return True
    if equivalence.get('equivalent') is not True or equivalence.get('failures')!=[] or equivalence.get('reference_sha256')!=reference_sha256 or equivalence.get('candidate_sha256')!=actual_sha256:raise ValueError('anchor equivalence/reference/actual lineage mismatch')
    return True

def _run(scene,replay,*,output,current_sha256,initial_anchor_sha256,initial_anchor_equivalence=None):
    """Fresh replay comes from the unchanged canonical replay verifier."""
    from controlled_multi_future.family_runners_v3_3 import F2ControllerV3_3,_arm_eef_pose,_pose
    from goal_pilot48_v1.f2_inside_native_floor_v1.certificate import build_live_certificate
    lineage=prefix_lineage()
    if current_sha256!=lineage['reference_current']['aggregate_sha256']:raise ValueError('not the qualified same current/anchor')
    validate_initial_anchor_lineage(initial_anchor_sha256,lineage['initial_anchor_sha256'],initial_anchor_equivalence)
    prefix_gate=F2ControllerV3_3.validate_replayed_prefix_physical(None,scene,replay)
    if prefix_gate['pass'] is not True:raise ValueError('fresh replay original prefix physical Gate failed')
    certificate=build_live_certificate(scene)
    spec=build_targets(actual_eef_pose=_arm_eef_pose(scene,'left'),actual_can_pose=_pose(scene.can),actual_box_pose=_pose(scene.box),
      neutral_eef_pose=scene.robot.left_original_pose,certificate=certificate,lineage=lineage)
    result=execute(LiveBackend(scene,spec,certificate,output),spec)
    result.update(spec=spec,fresh_prefix_gate=prefix_gate,actual_initial_anchor_sha256=initial_anchor_sha256,initial_anchor_equivalence=initial_anchor_equivalence,cleanup_owned_by_caller=True,root_execution_ready=False)
    return result

def run(scene,replay,*,output,current_sha256,initial_anchor_sha256,initial_anchor_equivalence=None):
    """Retain earliest failure, including scene/model initialization failure."""
    before=int(scene.planner_query_count)
    try:result=_run(scene,replay,output=output,current_sha256=current_sha256,initial_anchor_sha256=initial_anchor_sha256,initial_anchor_equivalence=initial_anchor_equivalence)
    except Exception as e:
        result={'pass':False,'error':{'type':type(e).__name__,'message':str(e)},'solver_problems':int(scene.planner_query_count)-before,
          'independent_ik_problems':0,'scene_creation_attempts':0,'containing_fresh_scene_budget':1,'collection_attempts':0,
          'cleanup_owned_by_caller':True,'root_execution_ready':False,'whole_root_pass':False}
    return result
