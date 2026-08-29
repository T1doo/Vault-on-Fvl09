import unittest

from controlled_multi_future.f3_shared_prefix_diagnosis_v3_3 import (
    GRASP_BOUNDARIES,
    SHARED_V_NOMINAL_AMPLITUDE_M_V3_3,
    build_shared_prefix_diagnosis,
)
from controlled_multi_future.family_runners_v3_1 import (
    F3_H_NOMINAL_AMPLITUDE_M_V3_3,
    F3_V_NOMINAL_AMPLITUDE_M_V3_3,
)


class F3SharedPrefixV3_3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.diagnosis = build_shared_prefix_diagnosis()

    def test_old_shared_v_failure_is_common_not_program_specific(self):
        self.assertTrue(self.diagnosis["pass_diagnosis"])
        self.assertEqual(len(self.diagnosis["records"]), 3)
        self.assertTrue(
            all(
                0.039 <= record["eef_metrics"]["negative_amplitude"] < 0.04
                for record in self.diagnosis["records"]
            )
        )
        self.assertTrue(
            all(
                record["selected_gripper_contact_fraction"] == 1.0
                for record in self.diagnosis["records"]
            )
        )

    def test_uniform_v_repair_keeps_h_and_thresholds(self):
        repair = self.diagnosis["selected_uniform_repair"]
        self.assertEqual(
            F3_V_NOMINAL_AMPLITUDE_M_V3_3,
            SHARED_V_NOMINAL_AMPLITUDE_M_V3_3,
        )
        self.assertEqual(F3_V_NOMINAL_AMPLITUDE_M_V3_3, 0.055)
        self.assertEqual(F3_H_NOMINAL_AMPLITUDE_M_V3_3, 0.05)
        self.assertFalse(repair["verifier_threshold_relaxed"])
        self.assertFalse(repair["program_specific_correction_allowed"])
        self.assertEqual(tuple(repair["grasp_boundary_measurements"]), GRASP_BOUNDARIES)


if __name__ == "__main__":
    unittest.main()
