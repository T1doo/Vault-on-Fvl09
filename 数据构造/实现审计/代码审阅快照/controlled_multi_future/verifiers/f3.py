from ..signals import closed_loop_event_metrics


def verify_motion_event(samples_xyz, center_xyz, main_axis, min_amplitude, max_off_axis, return_tolerance):
    metrics = closed_loop_event_metrics(samples_xyz, center_xyz, main_axis)
    passed = (
        metrics["positive_amplitude"] >= min_amplitude
        and metrics["negative_amplitude"] >= min_amplitude
        and metrics["max_off_axis"] <= max_off_axis
        and metrics["return_error"] <= return_tolerance
    )
    return {"pass": bool(passed), "metrics": metrics}
