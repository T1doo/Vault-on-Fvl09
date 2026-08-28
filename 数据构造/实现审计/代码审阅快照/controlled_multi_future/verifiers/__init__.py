"""Family verifier adapters built from pure signal helpers."""

from .f1 import verify_non_target_displacement, verify_staged_non_target_displacement, verify_true_cavity_obb
from .f2 import classify_exclusive_relation, verify_beside_final_state
from .f3 import verify_eef_bottle_axis_consistency, verify_motion_event, verify_realized_motion_metrics, verify_return_equivalence
from .f4 import completion_frame, verify_common_prefix, verify_completed_slots_preserved

__all__ = [
    "verify_non_target_displacement", "verify_staged_non_target_displacement", "verify_true_cavity_obb",
    "classify_exclusive_relation", "verify_beside_final_state",
    "verify_motion_event", "verify_eef_bottle_axis_consistency", "verify_realized_motion_metrics", "verify_return_equivalence",
    "completion_frame", "verify_common_prefix", "verify_completed_slots_preserved",
]
