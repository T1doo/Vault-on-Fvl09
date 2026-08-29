import inspect
from pathlib import Path
import unittest

from controlled_multi_future.f2_inside_release_diagnosis_v3_3 import (
    SAMPLE_OFFSETS,
    build_inside_diagnosis,
)
from controlled_multi_future.f2_mutually_exclusive_region_layout_v2 import (
    LAYOUT_VERSION,
    build_region_layout_review,
)
from controlled_multi_future.family_runners_v3_1 import F2RunnerV3_1


class F2V3_3DiagnosisAndRegionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.regions = build_region_layout_review(grid_step_m=0.01)
        cls.diagnosis = build_inside_diagnosis()

    def test_region_layout_grid_is_mutually_exclusive(self):
        self.assertEqual(self.regions["layout"]["layout_version"], LAYOUT_VERSION)
        self.assertTrue(self.regions["pass"])
        self.assertEqual(self.regions["grid_proof"]["overlap_count"], 0)
        self.assertTrue(all(self.regions["checks"].values()))
        self.assertGreater(
            self.regions["facility_center_distances_m"]["scale_stand_center_m"],
            0.3,
        )

    def test_inside_failure_is_before_release_ejection(self):
        self.assertEqual(
            self.diagnosis["classification"],
            "box_wall_collision_and_ejection_before_gripper_release",
        )
        self.assertTrue(self.diagnosis["pass_diagnosis"])
        self.assertTrue(all(self.diagnosis["classification_checks"].values()))
        samples = self.diagnosis["samples"]
        for offset in SAMPLE_OFFSETS:
            self.assertIn(f"after_release_{offset}", samples)
        self.assertFalse(samples["before_release"]["can_obb_inside_true_cavity"])
        self.assertGreater(samples["before_release"]["can_speed_mps"], 1.0)
        self.assertLess(samples["before_release"]["table_edge_clearance_m"], 0.0)
        self.assertFalse(
            self.diagnosis["selected_global_repair"][
                "full_obb_inside_verifier_relaxed"
            ]
        )

    def test_scene_and_predicate_use_v2_layout_exclusions(self):
        scene_source = (
            Path(__file__).resolve().parents[2]
            / "controlled_multi_future/probes/scene_inspection.py"
        ).read_text(encoding="utf-8")
        self.assertIn('layout.get("scale_xyz"', scene_source)
        self.assertIn('layout.get("stand_xyz"', scene_source)
        rollout_source = inspect.getsource(F2RunnerV3_1.rollout)
        self.assertIn("and not inside", rollout_source)
        self.assertIn("and not on", rollout_source)


if __name__ == "__main__":
    unittest.main()
