from copy import deepcopy
import unittest
from .plan import build,validate_structure,assert_executable

class Tests(unittest.TestCase):
    def test_exact_40_plus_16_and_360_structure_only(self):
        d=build();r=validate_structure(d)
        self.assertEqual(r['roots_by_split'],{'train':20,'validation':8,'test':12})
        self.assertEqual(sum(r['target_trajectories_by_split'].values()),360)
    def test_reserve_no_candidates_hashes_or_preset_split(self):
        for key,value in [('candidate_universe_hash','0'*64),('current',{}),('split','train')]:
            d=build();s=next(s for s in d['slots'] if s['root_slot_type']=='reserve');s[key]=value
            with self.assertRaises(ValueError):validate_structure(d)
    def test_quota_rank_or_atomic_R_mutation_rejected(self):
        for mutator in (lambda d:d['slots'][0].update(layout_difficulty='medium'),lambda d:d['slots'][11].update(reserve_rank=1),lambda d:d['realizations'].pop()):
            d=build();mutator(d)
            with self.assertRaises(ValueError):validate_structure(d)
    def test_no_false_generator_success_authority_or_science_gate(self):
        for mutator in (lambda d:d['generators']['F2'].update(formal_success_rate=.9),lambda d:d['authorizations'].update(formal_collection_authorized=True),lambda d:d['scientific_gates'].update(temporal_identifiability_F3=True)):
            d=build();mutator(d)
            with self.assertRaises(ValueError):validate_structure(d)
    def test_structural_pass_never_authorizes_execution(self):
        d=build();validate_structure(d)
        with self.assertRaises(ValueError):assert_executable(d)

if __name__=='__main__':unittest.main(verbosity=2)
