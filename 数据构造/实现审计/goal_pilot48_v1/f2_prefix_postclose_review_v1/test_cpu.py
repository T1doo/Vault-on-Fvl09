import json,unittest
from pathlib import Path
class Tests(unittest.TestCase):
    def test_positive_clearance_and_real_contact_window(self):
        r=json.loads((Path(__file__).parent/'analysis.json').read_text(encoding='utf-8'))
        self.assertGreater(r['terminal_native_gap_m'],.0001)
        self.assertGreater(r['last50_native_gap_range_m'][0],0)
        self.assertEqual(r['last50_physical_table_frames'],0)
        self.assertEqual(r['last50_both_fingers_physical_frames'],50)
        self.assertTrue(r['last50_all_relevant_contact_evidence_complete'])
    def test_model_gap_not_misrepresented_as_native_penetration(self):
        r=json.loads((Path(__file__).parent/'analysis.json').read_text(encoding='utf-8'))
        pair=r['CPU_transferred_literal_sphere_model']['world_nearest'][0]
        self.assertEqual((pair['link'],pair['obstacle']),('attached_can','table__0'))
        self.assertLess(pair['buffered_clearance_m'],0)
        self.assertEqual(r['CPU_transferred_literal_sphere_model']['self_buffered_overlaps'],[])
        self.assertLess(r['last50_grasp_relative_translation_drift_m'],.005)
        self.assertLess(r['last50_grasp_relative_orientation_drift_rad'],.05)
        self.assertEqual(r['new_GPU_or_solver_calls'],0)
if __name__=='__main__':unittest.main()
