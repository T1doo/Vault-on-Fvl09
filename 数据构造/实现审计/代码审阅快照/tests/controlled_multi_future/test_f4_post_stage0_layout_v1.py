import unittest

from controlled_multi_future.f4_post_stage0_layout_v1 import (
    LAYOUT,
    SELECTED_EXISTING_CORRIDOR_ID,
    audit_f4_post_stage0_layout_v1,
)
from controlled_multi_future.f4_right_workspace_layout_v4 import (
    LAYOUT as STAGE0_LAYOUT,
)


class F4PostStage0LayoutV1Tests(unittest.TestCase):
    def test_only_slots_and_version_change(self):
        for key in ("object_poses", "common_x_pose", "tray", "branch_neutral_pose"):
            self.assertEqual(LAYOUT[key], STAGE0_LAYOUT[key])
        self.assertNotEqual(LAYOUT["slot_poses"], STAGE0_LAYOUT["slot_poses"])

    def test_cpu_geometry_and_robustness_pass(self):
        result = audit_f4_post_stage0_layout_v1()
        self.assertTrue(result["pass"])
        self.assertTrue(result["checks"]["slot_pair_robustness_margin"])
        self.assertTrue(result["checks"]["slot_object_robustness_margin"])
        self.assertTrue(result["checks"]["slot_common_robustness_margin"])

    def test_existing_corridor_is_reused_without_extension(self):
        self.assertEqual(SELECTED_EXISTING_CORRIDOR_ID, "lower_carry_height")


if __name__ == "__main__":
    unittest.main()
