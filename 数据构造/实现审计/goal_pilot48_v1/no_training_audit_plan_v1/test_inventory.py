"""CPU inventory/coverage tests, not completion of the proposed audit suite."""
import copy,unittest
from . import inventory

class Tests(unittest.TestCase):
    def test_current_24_metadata_and_scope_flags(self):
        r=inventory.run();self.assertEqual(r['accepted_cell_count'],24);self.assertEqual(r['family_counts'],{'F1':12,'F4':12})
        self.assertTrue(r['registration_structure_rechecked']['pass']);self.assertFalse(r['no_training_suite_complete'])
        self.assertFalse(r['H_views_generated']);self.assertFalse(r['formal_test_accessed'])
    def test_pending_cell_and_reused_identity_do_not_count(self):
        doc=inventory.read(inventory.ROOT/'pilot_cells.json')
        pending=next(c for c in doc['cells'] if c['status']=='pending');pending['evidence']={'pass':True}
        with self.assertRaises(ValueError):inventory.accepted_rows(doc)
        doc=inventory.read(inventory.ROOT/'pilot_cells.json');rows=[c for c in doc['cells'] if c['status'].startswith('accepted')]
        rows[1]['evidence']['raw_id']=rows[0]['evidence']['raw_id']
        with self.assertRaises(ValueError):inventory.accepted_rows(doc)
    def test_existing_model_view_nested_boundary_gap_fixture(self):
        # Document a current interface limitation, not evidence of a trained
        # model leaking. No real RGB/action inputs or H views are generated.
        from controlled_multi_future.model_view import build_model_view
        sample={k:None for k in ('current_rgb','current_robot_state','future_effective_setpoints','candidate_program_semantics','visible_referring_expressions')}
        with self.assertRaises(ValueError):build_model_view({**sample,'branch_id':'CPU_FIXTURE'})
        sample['current_rgb']={'path':'CPU_SYNTHETIC_HIDDEN_PATH'}
        view=build_model_view(sample)
        self.assertIn('path',view['current_rgb']) # shallow projection is not typed recursive sanitization

if __name__=='__main__':unittest.main()
