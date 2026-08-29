import inspect
import unittest

from controlled_multi_future.f3_grasp_lift_diagnostic_v3_2 import (
    F3GraspLiftDiagnosticV3_2,
    _plan_and_execute_lift,
)
from controlled_multi_future.family_runners_v3_1 import F3RunnerV3_1


class F3GraspLiftDiagnosticV3_2Test(unittest.TestCase):
    def test_lift_query_reads_actual_qpos_immediately_before_each_segment(self):
        source = inspect.getsource(_plan_and_execute_lift)
        qpos_read = source.index("scene.robot.left_entity.get_qpos()")
        planner_call = source.index("_plan_left(")
        self.assertLess(qpos_read, planner_call)
        self.assertIn("actual post-grasp qpos", source)
        self.assertIn("planner_dtype_receipt", source)

    def test_diagnostic_order_and_limits_are_frozen(self):
        source = inspect.getsource(F3GraspLiftDiagnosticV3_2.run)
        ordered = [
            "diagnostic_pregrasp",
            "diagnostic_grasp_pose",
            "diagnostic_close_gripper",
            "post_grasp_lift_4cm",
            "post_grasp_lift_8cm",
            "post_grasp_lift_to_full_height",
        ]
        indices = [source.index(value) for value in ordered]
        self.assertEqual(indices, sorted(indices))
        self.assertIn('"planner_query_limit": 16', source)
        self.assertIn('"execution_attempt_count": 1', source)
        self.assertNotIn("VHVH", source)

    def test_full_program_rollout_replans_from_actual_qpos_after_close(self):
        source = inspect.getsource(F3RunnerV3_1.rollout)
        close_index = source.index("prefix_close_gripper")
        actual_qpos_index = source.index("actual post-grasp qpos")
        first_event_index = source.index("self._execute_event")
        self.assertLess(close_index, actual_qpos_index)
        self.assertLess(actual_qpos_index, first_event_index)
        self.assertIn("prefix_lift_4cm", source)
        self.assertIn("prefix_lift_8cm", source)
        self.assertIn("prefix_lift_to_full_height", source)
        self.assertEqual(source.count('(0.04, "prefix_lift_'), 3)


if __name__ == "__main__":
    unittest.main()
