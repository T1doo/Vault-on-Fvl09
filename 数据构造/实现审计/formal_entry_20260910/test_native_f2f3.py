import copy,tempfile,unittest
from pathlib import Path
import numpy as np
import scene_plan as plan
import native_f2f3 as native
class NativeBindingTests(unittest.TestCase):
 def test_actual_compatibility(self):
  for family in ['F2','F3']:
   for slot in [s for s in plan.generate()['slots'] if s['family']==family and s['reserve_rank'] is None]:
    resolved=plan.resolve(slot);bound=native.compatible_spec(resolved)
    self.assertEqual(bound['resolved_scene_spec'],resolved);self.assertEqual(bound['spec_sha256'],resolved['spec_sha256'])
    if family=='F2':
     self.assertEqual(bound['f2']['beside_target_xy'],resolved['targets']['beside']['target'][:2]);self.assertEqual(bound['f2']['box_center_xyz'][:2],next(r['pose'][:2] for r in resolved['roles'] if r['role']=='box'))
 def test_motion_actual_arrays(self):
  with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as t:
   p=Path(t);np.savez(p/'b.npz',controller_effective_setpoint=np.ones((100,26)),eef_pose=np.zeros((100,7)))
   np.savez(p/'a.npz',controller_effective_setpoint=np.ones((175,26)),eef_pose=np.zeros((175,7)))
   b={'program_id':'on','prefix_end_trace_row':9,'trace_path':str(p/'b.npz')};a={'program_id':'on','prefix_end_trace_row':9,'trace_path':str(p/'a.npz'),'motion_hold_segments':[{'label':'after_transport','start_row':10,'end_row':45,'frames':35},{'label':'at_support','start_row':50,'end_row':90,'frames':40}]}
   self.assertTrue(native.f2_motion_check(b,a)['pass']);a['motion_hold_segments'][1]['end_row']=89;self.assertFalse(native.f2_motion_check(b,a)['pass'])
 def test_missing_motion_not_pass(self):
  with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as t:
   p=Path(t)/'a.npz';np.savez(p,controller_effective_setpoint=np.ones((10,26)),eef_pose=np.zeros((10,7)));a={'program_id':'on','prefix_end_trace_row':1,'trace_path':str(p)};self.assertFalse(native.f2_motion_check(a,a)['pass'])
if __name__=='__main__':unittest.main()
