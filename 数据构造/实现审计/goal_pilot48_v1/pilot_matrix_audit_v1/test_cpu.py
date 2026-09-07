import copy
import json
import unittest
from .audit import ROOT, inspect_document


class Tests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads((ROOT / 'pilot_cells.json').read_text(encoding='utf-8'))

    def test_real_current_matrix_is_consistent_but_not_full_goal(self):
        r = inspect_document(self.document)
        self.assertTrue(r['pass'], r['errors'])
        self.assertEqual(r['registered_accepted'], self.document['accepted'])
        self.assertEqual(r['registration_matrix_full'], self.document['accepted'] == 48)
        self.assertFalse(r['goal_completion_proven'])
        self.assertFalse(r['raw_or_physical_evidence_reverified'])

    def test_duplicate_cell_or_missing_cell_rejected(self):
        self.document['cells'][-1] = copy.deepcopy(self.document['cells'][0])
        self.assertFalse(inspect_document(self.document)['pass'])

    def test_duplicate_real_rollout_rejected(self):
        a, b = self.document['cells'][:2]
        b['evidence']['raw_id'] = a['evidence']['raw_id']
        self.assertFalse(inspect_document(self.document)['pass'])

    def test_mixed_current_same_pilot_rejected(self):
        self.document['cells'][0]['evidence']['current_sha256'] = 'changed'
        self.assertFalse(inspect_document(self.document)['pass'])

    def test_false_current_or_gate_not_counted_as_valid_registration(self):
        self.document['cells'][0]['evidence']['current_initial_state_audit']['pass'] = False
        self.assertFalse(inspect_document(self.document)['pass'])

    def test_overclaimed_count_or_science_rejected(self):
        self.document['accepted'] = 48
        self.document['scientific_stage1_completion_claimed'] = True
        self.assertFalse(inspect_document(self.document)['pass'])


if __name__ == '__main__':
    unittest.main()
