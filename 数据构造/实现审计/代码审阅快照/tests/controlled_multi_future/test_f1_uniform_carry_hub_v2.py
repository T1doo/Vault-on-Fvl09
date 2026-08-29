import unittest

import numpy as np

from controlled_multi_future.f1_uniform_carry_hub_v2 import (
    F1_CARRY_HUB_XY_M,
    F1_SAFE_TRANSPORT_EEF_Z_M,
    LEGACY_SEGMENT_ORDER,
    REVISION2_SEGMENT_ORDER,
    build_uniform_carry_hub_targets,
    nominal_swept_clearance_audit,
)


class F1UniformCarryHubV2Test(unittest.TestCase):
    def legacy_targets(self):
        values = []
        for index, segment_id in enumerate(LEGACY_SEGMENT_ORDER):
            pose = np.asarray([-0.20, 0.02, 0.88 + 0.01 * index, 0.5, -0.5, 0.5, 0.5])
            if segment_id in ("safe_vertical", "safe_horizontal"):
                pose[2] = F1_SAFE_TRANSPORT_EEF_Z_M
            values.append({"segment_id": segment_id, "pose": pose})
        return values

    def test_repair_is_uniform_common_hub_and_keeps_frozen_height(self):
        revised, audit = build_uniform_carry_hub_targets(self.legacy_targets())
        self.assertEqual(tuple(item["segment_id"] for item in revised), REVISION2_SEGMENT_ORDER)
        by_id = {item["segment_id"]: item for item in revised}
        self.assertTrue(np.array_equal(by_id["carry_hub_low"]["pose"][:2], F1_CARRY_HUB_XY_M))
        self.assertTrue(np.array_equal(by_id["carry_hub_high"]["pose"][:2], F1_CARRY_HUB_XY_M))
        self.assertEqual(by_id["carry_hub_high"]["pose"][2], F1_SAFE_TRANSPORT_EEF_Z_M)
        self.assertFalse(audit["branch_specific_condition"])
        self.assertFalse(audit["scene_layout_changed"])
        self.assertFalse(audit["verifier_changed"])

    def test_nominal_low_hub_sweep_has_positive_clearance_for_all_roles(self):
        audit = nominal_swept_clearance_audit()
        self.assertTrue(audit["pass"])
        self.assertAlmostEqual(audit["minimum_vertical_surface_clearance_m"], 0.036, places=9)
        self.assertEqual(set(audit["roles"]), {"red", "green", "blue"})


if __name__ == "__main__":
    unittest.main()
