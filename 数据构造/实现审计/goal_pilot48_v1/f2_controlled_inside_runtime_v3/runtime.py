"""Private-globals reuse; frozen v2 and its running model consumers unchanged."""
import types
from goal_pilot48_v1.f2_controlled_inside_runtime_v2 import runtime as old
from .approval import verify_approval
from .transport import audit_transport

class LiveBackend(old.LiveBackend):
    def __init__(self,*args,**kwargs):
        verify_approval();super().__init__(*args,**kwargs);self.slow_open_started=False
    def transport_gate(self):
        from controlled_multi_future.family_runners_v3_3 import _gripper_below_eef_envelope,_f2_left_gripper_assembly_topology,_entity
        if self.slow_open_started:raise ValueError('supported-held projection cannot be reused after slow-open starts')
        topology=_f2_left_gripper_assembly_topology(self.scene)
        return audit_transport(self.scene.trace[self.held_start:],descent_start_relative_row=self.descent_start,verifier=self.verifier,
          held_window_start_trace_row=self.held_start,
          supported_stage_end_relative_row=len(self.scene.trace)-1-self.held_start if self.descent_start is not None else None,
          can_actor_name=_entity(self.scene.can).get_name(),selected_gripper_body_names=_gripper_below_eef_envelope(self.scene,arm='left')['selected_gripper_links'],
          allowed_gripper_assembly_body_names=topology['allowed_gripper_assembly_body_names'],
          named_facility_body_names=[_entity(a).get_name() for a in (self.scene.box,self.scene.scale,self.scene.stand)])
    def open_gripper(self,target):
        self.slow_open_started=True
        return super().open_gripper(target)

def private(fn,**overrides):
    ns=dict(fn.__globals__);ns.update(overrides)
    f=types.FunctionType(fn.__code__,ns,fn.__name__,fn.__defaults__,fn.__closure__);f.__kwdefaults__=fn.__kwdefaults__;return f

def run(*args,**kwargs):
    approval=verify_approval()
    inner=private(old._run,LiveBackend=LiveBackend)
    result=private(old.run,_run=inner)(*args,**kwargs)
    result.update(implementation_version='f2_controlled_inside_runtime_v3',contact_design_approval=approval,
      original_transport_source_unchanged=True,original_failed_contact_audits_retained=True)
    return result
