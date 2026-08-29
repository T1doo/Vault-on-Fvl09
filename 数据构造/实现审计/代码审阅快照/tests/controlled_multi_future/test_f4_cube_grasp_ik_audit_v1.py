import inspect
import unittest

from controlled_multi_future.f4_cube_grasp_ik_audit_v1 import (
    F4CubeGraspIKAuditV1,
    joint_limit_margin,
)


class F4CubeGraspIKAuditV1Test(unittest.TestCase):
    def test_joint_margin(self):
        result = joint_limit_margin(
            [0.0, 0.5, -0.5],
            [[-1.0, 1.0], [-1.0, 1.0], [-1.0, 1.0]],
        )
        self.assertTrue(result["within_limits"])
        self.assertAlmostEqual(result["minimum_joint_limit_margin_rad"], 0.5)
        outside = joint_limit_margin(
            [2.0],
            [[-1.0, 1.0]],
        )
        self.assertFalse(outside["within_limits"])

    def test_audit_is_no_action_and_fixed_abc_order(self):
        source = inspect.getsource(F4CubeGraspIKAuditV1.run)
        self.assertIn('for role in ("A", "B", "C")', source)
        self.assertIn("targets[:2]", source)
        self.assertIn('execution_attempt_count": 0', source)
        self.assertNotIn("_execute_control", source)
        self.assertNotIn("take_dense_action", source)
        self.assertNotIn("grasp_actor", source)


if __name__ == "__main__":
    unittest.main()
