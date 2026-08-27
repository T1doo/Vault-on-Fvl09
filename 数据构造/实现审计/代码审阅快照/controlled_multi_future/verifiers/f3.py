from ..signals import closed_loop_event_metrics


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
