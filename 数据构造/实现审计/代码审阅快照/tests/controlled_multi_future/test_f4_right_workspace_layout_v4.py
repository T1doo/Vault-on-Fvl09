import unittest

from controlled_multi_future.f4_right_workspace_layout_v4 import (
    LAYOUT,
    LAYOUT_VERSION,
    build_impact_review,
)
from controlled_multi_future.runtime_v3_3_scope_specs_v1 import (
    planned_scope_spec,
)


class F4RightWorkspaceLayoutV4Test(unittest.TestCase):
    def test_final_uniform_layout_passes_all_cpu_checks(self):
        review = build_impact_review()
        self.assertTrue(review["pass"])
        self.assertEqual(review["layout"]["layout_version"], LAYOUT_VERSION)
        self.assertTrue(all(review["checks"].values()))
        self.assertGreaterEqual(review["object_pairwise_minimum_m"], 0.10)
        self.assertGreaterEqual(review["slot_pairwise_minimum_m"], 0.10)
        self.assertEqual(
            [item[1] for item in review["layout"]["object_poses"].values()],
            [0.02, 0.02, 0.02],
        )

    def test_current_scope_spec_uses_final_layout(self):
        spec = planned_scope_spec("F4_cube_grasp_no_action_ik")
        self.assertEqual(spec["scene_layout"], LAYOUT)
        self.assertIn("if A/B/C no-action IK", build_impact_review()["failure_rule"])


if __name__ == "__main__":
    unittest.main()
