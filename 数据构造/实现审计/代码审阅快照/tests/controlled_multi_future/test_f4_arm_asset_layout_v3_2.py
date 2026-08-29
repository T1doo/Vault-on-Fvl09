import unittest
import json

from controlled_multi_future.f4_arm_asset_layout_v3_2 import (
    LAYOUT_VERSION,
    RIGHT_ARM_COMMON_GRASP_ORIENTATION_WXYZ,
    build_impact_review,
)


class F4ArmAssetLayoutV3_2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = build_impact_review()

    def test_right_arm_smallest_tray_layout_passes_cpu_geometry(self):
        selected = self.review["selected_layout"]
        self.assertEqual(selected["arm"], "right")
        self.assertEqual(selected["tray"]["model_id"], 0)
        self.assertEqual(selected["layout_version"], LAYOUT_VERSION)
        self.assertEqual(
            selected["branch_neutral_pose"][3:],
            RIGHT_ARM_COMMON_GRASP_ORIENTATION_WXYZ,
        )
        self.assertTrue(self.review["cpu_audit"]["pass_cpu_geometry"])
        self.assertTrue(all(self.review["cpu_audit"]["checks"].values()))

    def test_program_semantics_and_stage0_boundary_remain_fixed(self):
        self.assertFalse(self.review["stage0_authorized"])
        self.assertTrue(self.review["cpu_audit"]["common_route_real_planner_preflight_passed_in_v3_2_run2"])
        self.assertTrue(self.review["cpu_audit"]["full_program_real_planner_preflight_pending"])
        self.assertEqual(set(self.review["selected_layout"]["object_poses"]), {"A", "B", "C"})
        self.assertEqual(set(self.review["selected_layout"]["slot_poses"]), {"A", "B", "C"})
        self.assertGreater(len(json.dumps(self.review, sort_keys=True)), 100)


if __name__ == "__main__":
    unittest.main()
