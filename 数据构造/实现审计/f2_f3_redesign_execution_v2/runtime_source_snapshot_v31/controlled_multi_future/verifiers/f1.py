import numpy as np

from ..geometry import obb_inside_local_cavity


def verify_non_target_displacement(initial_xyz, final_xyz, max_displacement):
    return bool(np.linalg.norm(np.asarray(final_xyz) - np.asarray(initial_xyz)) <= max_displacement)


def verify_true_cavity_obb(actor_pose, actor_half_extents, container_pose, cavity, margin=0.0):
    return obb_inside_local_cavity(
        actor_pose,
        actor_half_extents,
        container_pose,
        cavity["lower_m"],
        cavity["upper_m"],
        margin=margin,
    )


def verify_staged_non_target_displacement(baseline_positions, staged_positions, max_displacement):
    """Expose the first phase that disturbs any non-target object."""

    per_stage = {}
    first_violation = None
    for stage, positions in staged_positions.items():
        per_stage[stage] = {
            role: float(np.linalg.norm(np.asarray(position) - np.asarray(baseline_positions[role])))
            for role, position in positions.items()
        }
        violating = [role for role, value in per_stage[stage].items() if value > max_displacement]
        if violating and first_violation is None:
            first_violation = {"stage": stage, "roles": violating}
    return {"pass": first_violation is None, "per_stage_displacement_m": per_stage, "first_violation": first_violation}
