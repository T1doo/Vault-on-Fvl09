import json,unittest
from pathlib import Path
import numpy as np
from .analyze import highest_lowest_point_roll
from .floor_review import approved_profile_checks

class Tests(unittest.TestCase):
    def test_rectangle_exact_maximin_support_solution_no_angle_scan(self):
        r=highest_lowest_point_roll([[-1,-2],[-1,2],[1,-2],[1,2]])
        self.assertAlmostEqual(r['minimum_hand_height_relative_to_axis_m'],-1.)
        self.assertAlmostEqual(r['roll_rad'],0.);self.assertEqual(r['pose_angles_evaluated_by_search'],0)
    def test_outside_origin_projection(self):
        r=highest_lowest_point_roll([[1,-1],[1,1],[2,-1],[2,1]])
        self.assertAlmostEqual(r['minimum_hand_height_relative_to_axis_m'],1.);self.assertFalse(r['proof']['axis_origin_inside_convex_hull'])
    def test_real_one_roll_preserves_axis_center_but_fails_robot_not_allowed_by_box9(self):
        r=json.loads(Path(__file__).with_name('ANALYSIS_001.json').read_text(encoding='utf-8'))
        self.assertLess(r['axis_preservation_error'],1e-12);self.assertLess(r['center_preservation_error_m'],1e-12)
        self.assertTrue(r['native_final_five_boundaries_and_floor']['pass']);self.assertEqual(r['roll_derivation']['proof']['tied_optimal_edges'],1)
        checks=approved_profile_checks(r);self.assertFalse(checks['no_hand_world_buffered_collision']);self.assertFalse(checks['no_hand_native_surface_intersection'])
        self.assertFalse(checks['no_can_pair_outside_approved_box9'])
    def test_nonfinite_input_rejected(self):
        with self.assertRaises(ValueError):highest_lowest_point_roll([[np.nan,0],[1,1],[2,0]])
