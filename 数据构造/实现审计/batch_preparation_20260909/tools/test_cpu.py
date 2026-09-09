import copy, tempfile,unittest,json
from pathlib import Path
import plan,portable
class Checks(unittest.TestCase):
 def test_plan(self):self.assertTrue(plan.validate(plan.generate())['pass'])
 def test_duplicate_physical_parameters(self):
  p=plan.generate();p['slots'][1]['scene_parameters_proposed']=p['slots'][0]['scene_parameters_proposed']
  with self.assertRaises(AssertionError):plan.validate(p)
 def test_missing_realization(self):
  p=plan.generate();p['slots'][0]['expected_cells'].pop()
  with self.assertRaises(AssertionError):plan.validate(p)
 def test_fake_observation_hash(self):
  p=plan.generate();p['slots'][0]['current_sha256']='fake'
  with self.assertRaises(AssertionError):plan.validate(p)
 def test_path_escape(self):
  with self.assertRaises(ValueError):portable.safe(Path('/nfs_share/lijunhui'), '../outside')
 def test_corrupt_and_missing_copy(self):
  with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as t:
   p=Path(t);(p/'data').write_bytes(b'fixture');h=portable.digest(p/'data')
   (p/'portable_manifest.json').write_text(json.dumps({'files':[{'relative_copy_path':'data','file_hash':h}]}))
   portable.verify(p);(p/'data').write_bytes(b'corrupt')
   with self.assertRaises(ValueError):portable.verify(p)
   (p/'data').unlink()
   with self.assertRaises(ValueError):portable.verify(p)
if __name__=='__main__':unittest.main()
