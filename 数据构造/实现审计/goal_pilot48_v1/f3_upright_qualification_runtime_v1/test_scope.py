import unittest,copy
from types import SimpleNamespace
from .runtime import validate_first_scope
from .context import restore_step_hook
class Tests(unittest.TestCase):
    def manifest(self):
        caps=dict(solver_problems=6,fresh_scenes=1,action_scenes=1,collection_attempts=0)
        return {'reserved':{**caps,'gpu_lease_seconds':1080},'jobs':[{'kind':'F3_UPRIGHT_QUALIFICATION','requires_live_meter':True,'resource_caps':caps,'timeout_seconds':900}]}
    def test_first_only_and_second17_rejected(self):
        m=self.manifest();validate_first_scope(m);m['jobs'][0]['resource_caps']['solver_problems']=17
        with self.assertRaises(ValueError):validate_first_scope(m)
    def test_wrong_counter_kind_and_missing_meter_rejected(self):
        for key,value in [('kind','F3_MICRO'),('requires_live_meter',False)]:
            m=self.manifest();m['jobs'][0][key]=value
            with self.assertRaises(ValueError):validate_first_scope(m)
    def test_step_hook_restore_even_after_scene_reference_removed(self):
        class Native:
            def step(self):return 'real'
        native=Native();raw=native.step;scene=SimpleNamespace(scene=None,_cmf_original_scene_step=raw);native.step=lambda:'wrapped'
        restore_step_hook(scene);self.assertEqual(native.step(),'real');self.assertFalse(hasattr(scene,'_cmf_original_scene_step'))
if __name__=='__main__':unittest.main()
