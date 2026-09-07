import unittest
import numpy as np
from .analyze import OUT,load,sha,digest
from .propose import run

class Tests(unittest.TestCase):
    def test_saved_analysis_binding_and_narrow_collision_evidence(self):
        r=load(OUT/'ANALYSIS_001.json');payload=dict(r);h=payload.pop('receipt_sha256');self.assertEqual(digest(payload),h)
        for p,h in r['source_files'].items():self.assertEqual(sha(p),h)
        self.assertTrue(r['locks_equal_actual_qpos']);self.assertTrue(r['planner_start_equals_last_actual_qpos'])
        pairs=r['target_attached_sphere_collisions']['configured_buffer']['pairs']
        self.assertEqual(len(pairs),4);self.assertEqual({p['obstacle'] for p in pairs},{'scale__0'})
        self.assertEqual(r['target_attached_sphere_collisions']['zero_buffer_diagnostic']['count'],0)
        self.assertFalse(r['mathematical_IK_infeasibility_proven']);self.assertFalse(r['beside_attempted'])
    def test_unique_proposal_recomputes_without_changing_saved_sources(self):
        saved=load(OUT/'SINGLE_REVISION_PROPOSAL_001.json');actual=run();self.assertEqual(actual,saved)
        np.testing.assert_allclose(np.asarray(actual['proposed_release_goal'])-actual['original_release_goal'],[0,0,.004,0,0,0,0],atol=1e-15)
        self.assertTrue(actual['native_and_attached_target_CPU_pass']);self.assertTrue(actual['no_scale_pair_exception'])
        self.assertFalse(actual['actual_robot_target_IK_checked']);self.assertFalse(actual['actual_path_checked'])

if __name__=='__main__':unittest.main()
