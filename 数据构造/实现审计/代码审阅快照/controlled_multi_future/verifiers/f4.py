from ..signals import first_stable_true_frame


def verify_common_prefix(
    *,
    footprint_result,
    support_contact_samples,
    stable_speed_samples,
    neutral_return_error,
    neutral_orientation_error,
    non_target_result,
    gripper_open,
    thresholds,
    eef_linear_speed,
    eef_angular_speed,
):
    import numpy as np

    required = int(thresholds["stable_window_frames"])
    contacts = np.asarray(support_contact_samples, dtype=bool).reshape(-1)
    speeds = np.asarray(stable_speed_samples, dtype=float).reshape(-1)
    checks = {
        "tray_footprint": footprint_result.get("pass_support_footprint") is True,
        "support_contact_window": len(contacts) >= required and bool(np.all(contacts[-required:])),
        "stable_window": len(speeds) >= required and bool(np.all(speeds[-required:] <= float(thresholds["stable_linear_speed_mps"]))),
        "neutral_return": float(neutral_return_error) <= float(thresholds["neutral_position_error_m"]),
        "neutral_orientation": float(neutral_orientation_error) <= float(thresholds["orientation_error"]),
        "non_target_stability": non_target_result.get("pass") is True,
        "gripper_open": bool(gripper_open),
        "eef_linear_stationary": float(eef_linear_speed) <= float(thresholds["eef_stationary_linear_speed_mps"]),
        "eef_angular_stationary": float(eef_angular_speed) <= float(thresholds["eef_stationary_angular_speed_rps"]),
    }
    return {"pass": all(checks.values()), "checks": checks}


def completion_frame(slot_predicate_values, stability_frames):
    return first_stable_true_frame(slot_predicate_values, stability_frames)


def verify_completed_slots_preserved(before, after):
    completed = [name for name, value in before.items() if bool(value)]
    broken = [name for name in completed if not bool(after.get(name, False))]
    return {"pass": not broken, "broken_slots": broken}
