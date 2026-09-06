"""Real new run() wiring with CPU fake scene; no CUDA/Scene construction."""
import tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from . import micro

class Tests(unittest.TestCase):
    def run_case(self,*,init_error=False,execute_error=False,save_error=False,lose_counter=False):
        calls=[]
        class Scene:
            bottle=object();role_actors={};planner_query_count=0
            def initialize_trace(self,*a,**kw):
                calls.append('init')
                if init_error:raise ValueError('init error')
                self.trace=[{'initial':True}];self.markers=[]
        scene=Scene()
        class Context:
            cleanup_receipt={'cleanup_safety_pass':True}
            def __enter__(self):return SimpleNamespace(scene=scene)
            def __exit__(self,*a):calls.append('cleanup')
        class Adapter:
            def scene(self,*a,**kw):return Context()
            def capture_current(self,scene):calls.append('current');return {'scope':'fake_current'}
            def capture_anchor(self,scene):calls.append('anchor');return {'scope':'fake_anchor'}
        def prepare(*a):calls.append('prepare');return {'bound':True}
        def execute(*a):
            calls.append('execute');assert scene.trace and hasattr(scene,'markers');scene.planner_query_count+=1
            if lose_counter:scene.planner_query_count=None
            if execute_error:raise RuntimeError('original execution error')
            return {'pass':False,'earliest_failed_stage':'scientific_negative_fixture'}
        def save(*a):
            calls.append('save')
            if save_error:raise IOError('secondary save error')
            return {'trace':'fake'}
        helper=SimpleNamespace(adapter_for=lambda *a:Adapter(),prepare_f3_scene=prepare,save_trace=save)
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            with patch('goal_pilot48_v1.f3_com_revision_v1.live_mass_properties.capture_mass_properties',return_value={'cmass_local_pose':[0,.11045115,0,1,0,0,0]}),patch.object(micro,'helper',return_value=helper),patch.object(micro,'candidates',return_value=[{}]),patch.object(micro,'candidate_spec',return_value={}),patch.object(micro,'execute',side_effect=execute),patch('controlled_multi_future.planner_qualification_manifests_v2_3._f3_scene_binding',return_value={}),patch('controlled_multi_future.real_sapien_adapter_high_level_v1._PinnedSapienRenderDeviceContextV1',side_effect=lambda x:x):
                r=micro.run({'manifest_sha256':'cpu-fixture','recipe_spec_path':'/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/goal_pilot48_v1/f3_com_revision_v1/recipe.json','jobs':[{'output_namespace':str(Path(directory)/'run')}]})
        return r,calls
    def test_bootstrap_before_executor_and_scientific_negative_clean(self):
        r,c=self.run_case();self.assertEqual(c,['prepare','current','anchor','init','execute','save','cleanup']);self.assertTrue(r['pass']);self.assertFalse(r['micro_pass'])
    def test_bootstrap_failure_cannot_plan_execute_or_save_missing_trace(self):
        r,c=self.run_case(init_error=True);self.assertNotIn('execute',c);self.assertNotIn('save',c);self.assertEqual(r['trajectory_queries'],0);self.assertFalse(r['pass'])
    def test_save_failure_does_not_mask_primary_error(self):
        r,c=self.run_case(execute_error=True,save_error=True);self.assertEqual(r['error']['message'],'original execution error');self.assertEqual(r['trace_save_error']['message'],'secondary save error');self.assertFalse(r['pass'])
    def test_unknown_counter_not_zero(self):
        r,c=self.run_case(lose_counter=True);self.assertFalse(r['accounting_complete']);self.assertIsNone(r['trajectory_queries'])
if __name__=='__main__':unittest.main(verbosity=2)
