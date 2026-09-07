from goal_pilot48_v1.inside_qualification_runtime_v1.spec import build_spec as old_spec,CAPS,digest
from goal_pilot48_v1.f2_controlled_inside_runtime_v3.approval import verify_approval

def build_spec():
    value=old_spec();value.update(schema_version='f2_inside_one_fresh_replay_qualification_v2',
      contact_design_approval=verify_approval(),contact_verifier='f2_supported_descent_box9_transport_gate_v1',
      physical_verifier='native_floor_v1_plus_supported_descent_box9_rule_v1',
      contact_phase='descent first new trace row through required50 closed hold, before first slow open')
    return value
