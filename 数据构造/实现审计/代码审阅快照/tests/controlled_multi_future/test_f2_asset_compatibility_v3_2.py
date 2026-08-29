import unittest

from controlled_multi_future.f2_asset_compatibility_v3_2 import build_matrix


class F2AssetCompatibilityV3_2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = build_matrix()

    def test_fixed_audit_order_finds_no_can_for_base3_then_selects_box2(self):
        self.assertFalse(any(item["strict_full_obb_fit"] for item in self.matrix["stage1_can_ids_current_box"]))
        self.assertEqual(self.matrix["selection_stage"], "box_id_with_current_can")
        self.assertEqual(self.matrix["selected"]["can_model_id"], 1)
        self.assertEqual(self.matrix["selected"]["plasticbox_model_id"], 2)
        self.assertTrue(self.matrix["selected"]["strict_full_obb_fit"])
        self.assertGreater(self.matrix["selected"]["best_orientation"]["minimum_clearance_m"], 0.0)

    def test_matrix_is_cpu_only_and_fail_closed(self):
        self.assertFalse(self.matrix["formal_data"])
        self.assertFalse(self.matrix["stage0_authorized"])
        self.assertEqual(len(self.matrix["can_records"]), 6)
        self.assertEqual(len(self.matrix["plasticbox_cavities"]), 11)


if __name__ == "__main__":
    unittest.main()
