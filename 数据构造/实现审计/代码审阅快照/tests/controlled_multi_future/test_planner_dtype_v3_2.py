import unittest

import numpy as np

from controlled_multi_future.planner_dtype_v3_2 import (
    GEOMETRY_DTYPE,
    PLANNER_DTYPE,
    geometry_array,
    normalize_planner_control,
    planner_array,
    planner_dtype_receipt,
)


class PlannerDtypeV3_2Test(unittest.TestCase):
    def test_nonzero_float64_inputs_become_float32_at_planner_boundary(self):
        qpos = np.asarray([0.25, -0.5, 1.25], dtype=np.float64)
        pose = np.asarray([0.1, -0.2, 0.9, 1.0, 0.0, 0.0, 0.0], dtype=np.float64)
        self.assertEqual(planner_array(qpos).dtype, PLANNER_DTYPE)
        self.assertEqual(planner_array(pose, shape=(7,)).dtype, PLANNER_DTYPE)
        self.assertTrue(np.any(planner_array(qpos) != 0))

    def test_control_position_velocity_and_audit_geometry_are_explicit(self):
        control = normalize_planner_control(
            {
                "status": "Success",
                "position": np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float64),
                "velocity": np.asarray([[0.01, 0.02], [0.03, 0.04]], dtype=np.float64),
            }
        )
        self.assertEqual(control["position"].dtype, PLANNER_DTYPE)
        self.assertEqual(control["velocity"].dtype, PLANNER_DTYPE)
        self.assertEqual(geometry_array(control["position"]).dtype, GEOMETRY_DTYPE)
        receipt = planner_dtype_receipt(qpos=[0.1], goal_pose=[0, 0, 1, 1, 0, 0, 0], control=control)
        self.assertEqual(receipt["qpos"]["dtype"], "float32")
        self.assertEqual(receipt["goal_pose"]["dtype"], "float32")
        self.assertEqual(receipt["control"]["position"]["dtype"], "float32")


if __name__ == "__main__":
    unittest.main()
