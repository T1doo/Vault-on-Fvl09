"""Private prefix runner/controller globals, unchanged physical prefix Gates."""
import types,copy
from goal_pilot48_v1.f2_goal_root_runtime_v1 import prefix_runner,prefix_controller,prefix_models
from goal_pilot48_v1.f2_goal_root_runtime_v1.spec import build_prefix_spec as parent_spec
from . import models

def build_prefix_spec():
    s=copy.deepcopy(parent_spec());s.update(schema_version='f2_prefix_clearance_fullworld_first_spec_v2',model_applicability_revision=1,
      parent_failed_job='p48_f2_prefix_001',model_selection='full single/batch first; F2-only actual can/table padding conditional exception',
      native_negative_bound_m=-.0001,positive_gap_upper_bound=None,physical_Gates_changed=False)
    return s

def make_controller(binding):
    from controlled_multi_future import f2_top_contact_root_runtime_v1 as original
    controller=prefix_controller.make_controller(binding)
    method,_=prefix_controller.compile_prefix_method(original,prefix_models.preplan,models.postclose_plan,models.restore_fullworld)
    controller.plan_and_execute_canonical_prefix=types.MethodType(method,controller)
    previous=controller.canonical_prefix_contract
    def contract(programs):
        p=previous(programs);p['prefix_id']='f2_goal_top_contact8_lift12cm_clearance_v2';p['planner_model_schedule']='fullworld_first_then_conditional_F2_native_clearance';return p
    controller.canonical_prefix_contract=contract;return controller

def private_entry():
    ns=dict(prefix_runner.run.__globals__);ns.update(build_prefix_spec=build_prefix_spec,make_controller=make_controller)
    return types.FunctionType(prefix_runner.run.__code__,ns,'run',prefix_runner.run.__defaults__,prefix_runner.run.__closure__)

def run(manifest):return private_entry()(manifest)
