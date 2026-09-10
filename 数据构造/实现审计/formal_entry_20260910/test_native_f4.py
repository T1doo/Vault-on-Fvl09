import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
import native_f4 as n
import scene_plan as s

class F4Tests(unittest.TestCase):
 def setUp(self):self.spec=s.resolve(next(x for x in s.generate()['slots'] if x['family']=='F4'))
 def test_request_uses_explicit_geometry(self):
  q=n.qualification_request(self.spec);self.assertFalse(q['qualification_executed']);self.assertEqual(q['source_layout']['A'],next(r['pose'] for r in self.spec['roles'] if r['role']=='A'));self.assertEqual(q['program_ids'],['F4-ABC','F4-ACB','F4-BAC'])
 def test_no_default_qualification(self):
  with self.assertRaises(ValueError):n.load_qualification(self.spec,{})
 def test_no_gpu_permission_before_native_import(self):
  with self.assertRaises(ValueError):n.run_native_root(self.spec,Path('/nfs_share/lijunhui/Robotwin2/tmp/no-f4-execution'),{})
 def test_path_only_three_carry_targets(self):
  targets=[{'segment_id':r+k,'pose':[0.,0.,1.,1.,0.,0.,0.]} for r in 'ABC' for k in ['_grasp','_carry_mid','_release','_neutral']];result=n.path_targets(targets,.015)
  self.assertEqual(targets[1]['pose'][1],0.);self.assertEqual(sum(x!=y for x,y in zip(targets,result)),3)
  for old,new in zip(targets,result):
   if not old['segment_id'].endswith('_carry_mid'):self.assertEqual(old,new)
 def test_missing_carry_rejected(self):
  with self.assertRaises(ValueError):n.path_targets([{'segment_id':'A_carry_mid','pose':[0]*7}],.015)
 def test_actor_factory_consumes_all_roles(self):
  records=[]
  class Actor:
   def set_name(self,name):self.name=name
  class Scene:pass
  def primitive(scene,pose,half,**kw):records.append((pose,list(half),kw));return Actor()
  def asset(scene,pose,name,**kw):records.append((pose,name,kw));return Actor()
  scene=Scene();roles=n.create_roles(scene,self.spec,box=primitive,visual_box=primitive,asset=asset,pose=lambda p,q:list(p)+list(q));self.assertEqual(set(roles),{r['role'] for r in self.spec['roles']});self.assertIs(scene.a,roles['A']);self.assertIs(scene.tray,roles['common_tray']);self.assertIs(scene.slot_a,roles['slot_A'])
  self.assertEqual(len(records),len(self.spec['roles']))
 def test_budget_does_not_hide_preflights(self):
  budget=n.call_budget();self.assertEqual(budget['base_without_qualification_or_recovery']['collection_attempts'],9);self.assertGreater(budget['base_without_qualification_or_recovery']['action_scenes'],9)
if __name__=='__main__':unittest.main()
