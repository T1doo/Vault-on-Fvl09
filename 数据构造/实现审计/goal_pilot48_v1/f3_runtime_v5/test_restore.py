import tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from . import micro
class Tests(unittest.TestCase):
    def case(self,primary=False,restore_error=False,full_valid=True,restore_keys=None):
        scene=SimpleNamespace(_cmf_scene_instance_id='CPU_TEST_SCENE');calls=[]
        def inner(*a):
            scene._cmf_escape_model_branch='tangent';calls.append('physical')
            if primary:raise ValueError('primary')
            return {'pass':True}
        def restore(*a):
            calls.append('restore')
            if restore_error:raise RuntimeError('restoration')
            return {k:{'valid':full_valid} for k in (('motion_gen','motion_gen_batch') if restore_keys is None else restore_keys)}
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as d,patch.object(micro,'_execute_inner',side_effect=inner),patch('goal_pilot48_v1.f3_tangent_escape_v1.live.restore',side_effect=restore):
            try:result=micro.execute(scene,{},Path(d))
            except Exception as exc:result=exc
        return calls,result
    def test_full_restore_after_success(self):
        c,r=self.case();self.assertEqual(c,['physical','restore']);self.assertTrue(r['pass'])
    def test_restoration_invalid_cannot_return_micro_pass(self):
        c,r=self.case(full_valid=False);self.assertFalse(r['pass'])
    def test_restore_even_on_original_failure(self):
        c,r=self.case(primary=True);self.assertEqual(c,['physical','restore']);self.assertEqual(str(r),'primary')
    def test_restoration_failure_does_not_mask_original(self):
        c,r=self.case(primary=True,restore_error=True);self.assertEqual(str(r),'primary')
    def test_restoration_failure_not_silently_accepted(self):
        c,r=self.case(restore_error=True);self.assertEqual(str(r),'restoration')
    def test_empty_or_partial_restoration_not_pass(self):
        for keys in ([],['motion_gen'],['motion_gen','motion_gen_batch','extra']):
            c,r=self.case(restore_keys=keys);self.assertFalse(r['pass'])
if __name__=='__main__':unittest.main()
