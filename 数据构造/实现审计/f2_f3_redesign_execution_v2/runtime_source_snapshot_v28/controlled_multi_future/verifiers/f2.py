def classify_exclusive_relation(*, inside, on, beside):
    active = [name for name, value in (("inside", inside), ("on", on), ("beside", beside)) if bool(value)]
    return active[0] if len(active) == 1 else None


def verify_beside_final_state(
    *, inside, on, beside, support_contact, stable_speed_window, gripper_open,
    rest_position_error, rest_orientation_error, eef_linear_speed, eef_angular_speed, thresholds,
):
    exclusive = classify_exclusive_relation(inside=inside, on=on, beside=beside)
    checks = {
        "exclusive_beside": exclusive == "beside",
        "support_contact": bool(support_contact),
        "stable_speed_window": bool(stable_speed_window),
        "gripper_open": bool(gripper_open),
        "rest_position": float(rest_position_error) <= float(thresholds["rest_position_error_m"]),
        "rest_orientation": float(rest_orientation_error) <= float(thresholds["orientation_error"]),
        "eef_linear_stationary": float(eef_linear_speed) <= float(thresholds["eef_stationary_linear_speed_mps"]),
        "eef_angular_stationary": float(eef_angular_speed) <= float(thresholds["eef_stationary_angular_speed_rps"]),
    }
    return {"pass": all(checks.values()), "exclusive_relation": exclusive, "checks": checks}
