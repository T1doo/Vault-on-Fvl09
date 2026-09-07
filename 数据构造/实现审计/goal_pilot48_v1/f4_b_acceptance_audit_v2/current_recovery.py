"""V2 shared-current recovery uses explicit-pass hardened independent audit."""
from goal_pilot48_v1.f4_b_acceptance_audit_v1 import current_recovery as old
from goal_pilot48_v1.f4_b_runtime_v1.stages import bound_function
from .audit import run

def audit_later_current(**kwargs):
    return bound_function(old.audit_later_current,run=run)(**kwargs)
