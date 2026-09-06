import unittest
import numpy as np
from .analyze import OUT, load
from .propose import derive

class Tests(unittest.TestCase):
    def test_saved_GPU_FK_reproduced_and_no_false_C_collision(self):
        r = load(OUT / 'analysis_v1_1.json')
        self.assertLess(r['maximum_CPU_vs_recorded_FK_metric_error_m'], 2e-6)
        self.assertEqual(r['records']['C']['full_valid_count'], 8)
        self.assertEqual(r['records']['C']['selected_CPU_collision']['self_buffered_overlaps'], [])
        for key in ('U_new', 'D_new'):
            self.assertEqual(r['records'][key]['within_position_tolerance_count'], 0)
            self.assertGreater(r['records'][key]['K2_pass_count'], 0)

    def test_proposal_exactly_reproducible_without_query_or_search(self):
        actual = derive(load(OUT / 'analysis_v1_1.json'))
        frozen = load(OUT / 'proposal_revision1.json')
        self.assertEqual(actual, frozen['derivation'])
        self.assertEqual(actual['selected_existing_solution_indices'], {'C': 6, 'U_new': 12, 'D_new': 4})
        self.assertEqual(actual['layout_candidates_searched'], 0)
        self.assertLess(actual['distance_to_known_C_after_m'], actual['distance_to_known_C_before_m'])

    def test_orientation_support_and_relation_preserved(self):
        p = load(OUT / 'proposal_revision1.json')
        np.testing.assert_allclose(np.asarray(p['new_U_reported_goal'])[:3] - np.asarray(p['new_D_reported_goal'])[:3], [0, 0, .08], atol=1e-12)
        self.assertTrue(p['geometry_audit']['pass'])
        self.assertEqual(p['geometry_audit']['forbidden_moving_stand_intersections'], [])
        self.assertTrue(p['geometry_audit']['inside_false'] and p['geometry_audit']['on_false'])
        self.assertFalse(p['GPU_IK_verified'])
        self.assertTrue(p['new_root_current_anchor_required'])

if __name__ == '__main__': unittest.main()
