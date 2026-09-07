"""Synthetic in-memory candidate reports; never writes real pilot evidence."""
from copy import deepcopy
import json
import unittest
from goal_pilot48_v1.pilot_matrix_audit_v1.audit import ROOT
from .merge import digest, merge_f4_b


class Tests(unittest.TestCase):
    def setUp(self):
        self.disk_document = json.loads((ROOT / 'pilot_cells.json').read_text(encoding='utf-8'))
        self.current = deepcopy(self.disk_document)
        # Construct an in-memory pending B fixture even after real B adoption.
        for row in self.current['cells']:
            if row['family'] == 'F4' and row['pilot'] == 'B':
                if row['status'] in ('accepted_existing', 'accepted_new'):
                    self.current['accepted'] -= 1
                row.update(status='pending', evidence=None)
        self.before = deepcopy(self.current)
        template = next(c['evidence'] for c in self.current['cells'] if c['status'] == 'accepted_existing')
        cells = []
        for p in ('F4-ABC', 'F4-ACB', 'F4-BAC'):
            for r in ('r_pc', 'r_inv_motion'):
                e = deepcopy(template)
                e.update(family='F4', pilot='B', program_id=p, realization=r, root_id='CPU_SYNTHETIC_B',
                         current_sha256='CPU_SYNTHETIC_CURRENT', candidate_universe_sha256='CPU_SYNTHETIC_UNIVERSE',
                         raw_id='CPU_RAW_' + p + r, trace_sha256='CPU_TRACE_' + p + r,
                         rollout_id='CPU_ROLLOUT_' + p + r, pilot_input_accepted=False)
                cells.append(dict(family='F4', pilot='B', program_id=p, realization=r,
                                  status='verified_candidate_pending_main_registration', evidence=e))
        self.report = dict(status='six_verified_candidates_pending_main_registration', eligible_candidate_cells=6,
                           acceptance_issued=False, pilot_cells_modified=False, cells=cells,
                           current_recovery={'pass': True}, pc_audit={'eligible_candidate_cells': 3},
                           recomputed_motion_finalizer={'accepted': True}, six_final_state_equivalence={'equivalent': True},
                           CPU_SYNTHETIC_FIXTURE_NOT_PHYSICAL_EVIDENCE=True)
        self.seal()

    def seal(self):
        self.report.pop('receipt_sha256', None)
        self.report['receipt_sha256'] = digest(self.report)

    def test_exact_merge_preserves_existing_and_never_writes(self):
        updated, checks = merge_f4_b(self.current, self.report)
        self.assertEqual(self.current, self.before)
        self.assertEqual(updated['accepted'], self.current['accepted'] + 6)
        self.assertTrue(checks['pass'])
        self.assertFalse(updated['scientific_stage1_completion_claimed'])
        self.assertEqual(json.loads((ROOT / 'pilot_cells.json').read_text(encoding='utf-8')), self.disk_document)

    def test_second_registration_refused(self):
        updated, _ = merge_f4_b(self.current, self.report)
        with self.assertRaisesRegex(ValueError, 'already populated'):
            merge_f4_b(updated, self.report)

    def test_missing_current_proof_refused(self):
        self.report['current_recovery']['pass'] = False
        self.seal()
        with self.assertRaises(ValueError):
            merge_f4_b(self.current, self.report)

    def test_changed_report_hash_refused(self):
        self.report['cells'][0]['evidence']['raw_id'] = 'tampered'
        with self.assertRaisesRegex(ValueError, 'self-hash'):
            merge_f4_b(self.current, self.report)

    def test_duplicate_raw_or_missing_registered_gate_refused(self):
        self.report['cells'][1]['evidence']['raw_id'] = self.report['cells'][0]['evidence']['raw_id']
        self.seal()
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            merge_f4_b(self.current, self.report)


if __name__ == '__main__':
    unittest.main()
