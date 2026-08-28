from ..signals import closed_loop_event_metrics


def verify_realized_motion_metrics(events, thresholds):
    checks = {}
    for name, event in events.items():
        checks[name] = {
            "eef_positive_amplitude": float(event.get("eef_positive_amplitude", float("-inf"))) >= float(thresholds["motion_min_axis_amplitude_m"]),
            "eef_negative_amplitude": float(event.get("eef_negative_amplitude", float("-inf"))) >= float(thresholds["motion_min_axis_amplitude_m"]),
            "bottle_positive_amplitude": float(event.get("bottle_positive_amplitude", float("-inf"))) >= float(thresholds["motion_min_axis_amplitude_m"]),
            "bottle_negative_amplitude": float(event.get("bottle_negative_amplitude", float("-inf"))) >= float(thresholds["motion_min_axis_amplitude_m"]),
            "eef_off_axis": float(event.get("eef_max_off_axis", float("inf"))) <= float(thresholds["motion_max_off_axis_m"]),
            "bottle_off_axis": float(event.get("bottle_max_off_axis", float("inf"))) <= float(thresholds["motion_max_off_axis_m"]),
            "eef_return": float(event.get("eef_return_error", float("inf"))) <= float(thresholds["motion_max_return_error_m"]),
            "bottle_return": float(event.get("bottle_return_error", float("inf"))) <= float(thresholds["motion_max_return_error_m"]),
            "bottle_orientation": float(event.get("bottle_orientation_drift", float("inf"))) <= float(thresholds["motion_max_orientation_drift"]),
            "selected_gripper_contact": float(event.get("selected_gripper_contact_fraction", 0.0)) >= float(thresholds["motion_min_contact_fraction"]),
            "contact_breaks": int(event.get("contact_break_count", 10**9)) <= int(thresholds["motion_max_contact_break_count"]),
        }
    return {"pass": bool(checks) and all(all(event_checks.values()) for event_checks in checks.values()), "event_checks": checks}


def verify_return_equivalence(
    *,
    position_error,
    orientation_error,
    rest_position_error,
    rest_orientation_error,
    stable_speed_samples,
    support_contact_samples,
    gripper_open,
    thresholds, eef_linear_speed, eef_angular_speed,
):
    import numpy as np

    speeds = np.asarray(stable_speed_samples, dtype=float).reshape(-1)
    contacts = np.asarray(support_contact_samples, dtype=bool).reshape(-1)
    required = int(thresholds["stable_window_frames"])
    checks = {
        "position": float(position_error) <= float(thresholds["position_error_m"]),
        "orientation": float(orientation_error) <= float(thresholds["orientation_error"]),
        "rest": float(rest_position_error) <= float(thresholds["rest_position_error_m"]),
        "rest_orientation": float(rest_orientation_error) <= float(thresholds["orientation_error"]),
        "stable_window": len(speeds) >= required and bool(np.all(speeds[-required:] <= float(thresholds["stable_linear_speed_mps"]))),
        "support_contact_window": len(contacts) >= required and bool(np.all(contacts[-required:])),
        "gripper_open": bool(gripper_open),
        "eef_linear_stationary": float(eef_linear_speed) <= float(thresholds["eef_stationary_linear_speed_mps"]),
        "eef_angular_stationary": float(eef_angular_speed) <= float(thresholds["eef_stationary_angular_speed_rps"]),
    }
    return {"pass": all(checks.values()), "checks": checks, "stable_sample_count": len(speeds), "support_sample_count": len(contacts)}


def verify_eef_bottle_axis_consistency(eef_samples, bottle_samples, main_axis, minimum_axis_correlation=0.8):
    import numpy as np

    eef = np.asarray(eef_samples, dtype=float)
    bottle = np.asarray(bottle_samples, dtype=float)
    if eef.shape != bottle.shape or eef.ndim != 2 or eef.shape[1] != 3:
        raise ValueError("EEF and bottle samples must have matching [N,3] shape")
    if eef.shape[0] < 3:
        raise ValueError("at least three realized samples are required")
    eef_delta = np.diff(eef[:, main_axis])
    bottle_delta = np.diff(bottle[:, main_axis])
    if np.std(eef_delta) == 0 or np.std(bottle_delta) == 0:
        correlation = 0.0
    else:
        correlation = float(np.corrcoef(eef_delta, bottle_delta)[0, 1])
    return {"pass": bool(correlation >= minimum_axis_correlation), "axis_correlation": correlation}


def verify_motion_event(samples_xyz, center_xyz, main_axis, min_amplitude, max_off_axis, return_tolerance):
    metrics = closed_loop_event_metrics(samples_xyz, center_xyz, main_axis)
    passed = (
        metrics["positive_amplitude"] >= min_amplitude
        and metrics["negative_amplitude"] >= min_amplitude
        and metrics["max_off_axis"] <= max_off_axis
        and metrics["return_error"] <= return_tolerance
    )
    return {"pass": bool(passed), "metrics": metrics}
