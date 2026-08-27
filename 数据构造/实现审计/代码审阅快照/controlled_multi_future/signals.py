"""Pure verifier-signal helpers; thresholds remain proposals until Stage 2."""

from __future__ import annotations

import numpy as np


def inside_volume(point_xyz, lower_xyz, upper_xyz, margin=0.0) -> bool:
    point = np.asarray(point_xyz, dtype=float)
    lower = np.asarray(lower_xyz, dtype=float) + float(margin)
    upper = np.asarray(upper_xyz, dtype=float) - float(margin)
    return bool(np.all(point >= lower) and np.all(point <= upper))


def top_surface_region(point_xyz, center_xyz, half_extent_xy, z_tolerance) -> bool:
    point = np.asarray(point_xyz, dtype=float)
    center = np.asarray(center_xyz, dtype=float)
    half_xy = np.asarray(half_extent_xy, dtype=float)
    return bool(np.all(np.abs(point[:2] - center[:2]) <= half_xy) and abs(point[2] - center[2]) <= z_tolerance)


def beside_annulus(point_xyz, reference_xyz, inner_radius, outer_radius, z_tolerance) -> bool:
    point = np.asarray(point_xyz, dtype=float)
    reference = np.asarray(reference_xyz, dtype=float)
    radial = float(np.linalg.norm(point[:2] - reference[:2]))
    return bool(inner_radius <= radial <= outer_radius and abs(point[2] - reference[2]) <= z_tolerance)


def closed_loop_event_metrics(samples_xyz, center_xyz, main_axis: int) -> dict:
    samples = np.asarray(samples_xyz, dtype=float)
    center = np.asarray(center_xyz, dtype=float)
    if samples.ndim != 2 or samples.shape[1] != 3 or samples.shape[0] < 2:
        raise ValueError("samples_xyz must be at least 2x3")
    if main_axis not in (0, 1, 2):
        raise ValueError("main_axis must be x=0, y=1, or z=2")
    delta = samples - center
    other = [axis for axis in (0, 1, 2) if axis != main_axis]
    return {
        "positive_amplitude": float(np.max(delta[:, main_axis])),
        "negative_amplitude": float(-np.min(delta[:, main_axis])),
        "max_off_axis": float(np.max(np.linalg.norm(delta[:, other], axis=1))),
        "start_error": float(np.linalg.norm(samples[0] - center)),
        "return_error": float(np.linalg.norm(samples[-1] - center)),
    }


def first_stable_true_frame(values, stability_frames: int):
    if stability_frames <= 0:
        raise ValueError("stability_frames must be positive")
    run = 0
    for index, value in enumerate(values):
        run = run + 1 if bool(value) else 0
        if run == stability_frames:
            return index - stability_frames + 1
    return None
