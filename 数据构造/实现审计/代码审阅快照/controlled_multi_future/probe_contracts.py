"""Dependency-free variant and semantic result contracts for audit probes."""

from .runtime_v2_contracts import RUNTIME_V2_PROBE_VARIANTS

HISTORICAL_FAMILY_VARIANTS = {
    "F1": ("fp1", "interior"),
    "F2": ("sector1", "sector2", "pot_left"),
    "F3": ("pad_center", "bottle_fp"),
    "F4": ("common", "A", "B", "C", "common_ab", "ABC", "ACB", "BAC"),
}
FAMILY_VARIANTS = RUNTIME_V2_PROBE_VARIANTS


def result_passed(family, result):
    if not result.get("plan_success"):
        return False
    if "semantic_verifier" in result:
        return result.get("semantic_verifier", {}).get("pass") is True
    if family == "F1":
        displacements = result.get("non_target_displacement_m", {})
        return (
            result.get("inside_verifier", {}).get("pass_provisional_outer_obb") is True
            and bool(result.get("left_gripper_open"))
            and bool(displacements)
            and max(displacements.values()) <= 0.01
        )
    if family == "F2":
        return result.get("beside_annulus_provisional") is True and bool(result.get("left_gripper_open"))
    if family == "F3":
        return (
            result.get("bottle_return_position_error_m", float("inf")) <= 0.05
            and result.get("bottle_return_orientation_error", float("inf")) <= 0.02
            and result.get("rest_return_error_m", float("inf")) <= 0.05
            and result.get("bottle_stable_linear_speed_mps", float("inf")) <= 0.05
            and bool(result.get("left_gripper_open"))
        )
    if family == "F4":
        common = result.get("common_X")
        common_pass = common is None or (common.get("tray_xy_error_m", float("inf")) < 0.08 and common.get("gripper_open") is True)
        blocks = result.get("blocks", [])
        block_pass = all(item.get("slot_predicate_after", {}).get(item.get("role")) is True for item in blocks)
        return common_pass and block_pass and result.get("all_completed_slots_preserved") is True and bool(result.get("left_gripper_open"))
    return False
