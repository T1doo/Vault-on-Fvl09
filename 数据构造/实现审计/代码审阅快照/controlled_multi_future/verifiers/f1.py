import numpy as np


def verify_non_target_displacement(initial_xyz, final_xyz, max_displacement):
    return bool(np.linalg.norm(np.asarray(final_xyz) - np.asarray(initial_xyz)) <= max_displacement)
