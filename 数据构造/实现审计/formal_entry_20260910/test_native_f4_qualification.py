import unittest,sys,json
from pathlib import Path
import native_f4_qualification as q
import scene_plan as s

def synthetic_stage_a():raise AssertionError('synthetic helper must not run')
def build_f4_runtime_spec_v1(*a,**k):raise AssertionError('old layout factory must not run')
def example_builder(a):
 scene=build_f4_runtime_spec_v1('old',stage_a_terminal=synthetic_stage_a())
 return {'scene':scene,'a':a}

class QualificationTests(unittest.TestCase):
 def test_bound_builder_never_calls_old_factory_or_synthetic_helper(self):
  bound=q.bind_builder_to_scene(example_builder,{'new_scene':'explicit'})
  self.assertEqual(bound(4),{'scene':{'new_scene':'explicit'},'a':4})
 def test_no_qualification_without_gpu_authorization(self):
  spec=s.resolve(next(x for x in s.generate()['slots'] if x['family']=='F4'))
  with self.assertRaises(ValueError):q.run_native_qualification(spec,'/nfs_share/lijunhui/Robotwin2/tmp/never-created',{})
 def test_real_geometry_recomputed_from_new_layout(self):
  live='/nfs_share/lijunhui/Robotwin2/project/RoboTwin'
  if live not in sys.path:sys.path.insert(0,live)
  profile=json.loads(Path('/nfs_share/lijunhui/CVPR_FutureIntent_Data/formal_entry_20260910_samples/F4-final/files/frozen_spec.json').read_text())['planned_root_slot_spec']
  for slot in [x for x in s.generate()['slots'] if x['family']=='F4' and x['rank']<=2]:
   spec=s.resolve(slot);a,b=q.prepare_candidates(spec,profile)
   self.assertEqual(a['source_layout']['A'],next(r['pose'] for r in spec['roles'] if r['role']=='A'));self.assertNotEqual(a['candidate_sha256'],profile['f4_source_grasp_candidate_v1']['candidate_sha256']);self.assertTrue(b['construction_valid']);self.assertFalse(a['f1_15_of_15_execution_claim_applies_to_candidate'])
  self.assertFalse({'torch','sapien','curobo'}&set(sys.modules))
if __name__=='__main__':unittest.main()
