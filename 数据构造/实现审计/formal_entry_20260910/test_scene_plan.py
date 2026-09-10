import copy,json,tempfile,unittest
from pathlib import Path
import scene_plan as s
class SceneTests(unittest.TestCase):
 def test_positive(self):self.assertTrue(s.validate_plan(s.generate())['pass'])
 def test_invalid(self):
  for key,val in [('scale_multiplier',-1),('translation_xy_m',[float('nan'),0]),('remark','different')]:
   p=s.generate();p['slots'][0]['parameters'][key]=val
   with self.assertRaises(ValueError):s.validate_plan(p)
 def test_duplicate_list(self):
  p=s.generate();p['slots'][0]['realizations'].append('r_pc')
  with self.assertRaises(ValueError):s.validate_plan(p)
 def test_not_shared(self):
  p=s.generate();p['slots'][0]['realizations'].append('bad');self.assertEqual(len(p['slots'][1]['realizations']),3);self.assertEqual(len(s.generate()['slots'][0]['realizations']),3)
 def test_signature_ignores_names(self):
  a=s.resolve(s.generate()['slots'][0]);b=copy.deepcopy(a);b['root_id']='renamed';b['roles'][0]['material_source']='remark'
  self.assertEqual(s.physical_signature(a),s.physical_signature(b))
 def test_reserve_order_restart(self):
  p=s.generate()
  with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as tmp:
   pa=Path(tmp)/'a.json';pb=Path(tmp)/'b.json'
   a=s.activate_reserves(p,pa,{'F1_000002':'FAILED','F1_000001':'FAILED'})
   b=s.activate_reserves(p,pb,{'F1_000001':'FAILED','F1_000002':'FAILED'})
   self.assertEqual(a,b);self.assertEqual(a,s.activate_reserves(p,pa,{'F1_000001':'FAILED','F1_000002':'FAILED'}))
   self.assertEqual(a['records'][0]['reserve_root_id'],'F1_000011');self.assertEqual(a['records'][0]['resolved_spec']['difficulty'],'clear')
   self.assertEqual(p['slots'][10]['difficulty'],'inherit_failed_slot')
 def test_reserve_barrier(self):
  with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as tmp:
   with self.assertRaises(ValueError):s.activate_reserves(s.generate(),Path(tmp)/'a.json',{'F1_000001':'FAILED'})
   with self.assertRaises(ValueError):s.activate_reserves(s.generate(),Path(tmp)/'a.json',{f'F1_{i:06d}':'FAILED' for i in range(3,11)},wave='remaining')
 def test_projection_ratio(self):
  for slot in s.generate()['slots']:
   if slot['reserve_rank'] is None:
    x=s.resolve(slot);m=x['difficulty_measurement'];self.assertAlmostEqual(m['computed_ratio'],m['target_ratio'],places=6)
if __name__=='__main__':unittest.main()
