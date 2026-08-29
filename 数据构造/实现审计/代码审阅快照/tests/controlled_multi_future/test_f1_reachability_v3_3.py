import unittest

from controlled_multi_future.f1_three_object_reachability_v3_3 import (
    build_reachability_review,
)


class F1ReachabilityV3_3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = build_reachability_review()

    def test_comparison_preserves_all_three_roles_and_failure(self):
        records = {item["role"]: item for item in self.review["records"]}
        self.assertEqual(set(records), {"red", "green", "blue"})
        self.assertEqual(records["red"]["planner_status"], "passed")
        self.assertEqual(records["green"]["planner_status"], "passed")
        self.assertEqual(records["blue"]["failure_segment"], "target_lift")
        self.assertLess(
            max(item["eef_workspace_margin_m"]["lift"] for item in records.values())
            - min(item["eef_workspace_margin_m"]["lift"] for item in records.values()),
            0.002,
        )

    def test_uniform_repair_and_missing_joint_margin_are_explicit(self):
        repair = self.review["selected_uniform_repair"]
        self.assertIn("two 4cm", repair["rule"])
        self.assertFalse(repair["layout_changed"])
        self.assertFalse(repair["target_role_specific_parameters"])
        self.assertTrue(repair["planner_only_gate_required_before_execution"])
        self.assertTrue(
            all(item["joint_limit_margin"] is None for item in self.review["records"])
        )
        self.assertTrue(
            all(
                item["joint_limit_margin_status"]
                == "pending_fixed_gpu0_planner_only_gate"
                for item in self.review["records"]
            )
        )


if __name__ == "__main__":
    unittest.main()
