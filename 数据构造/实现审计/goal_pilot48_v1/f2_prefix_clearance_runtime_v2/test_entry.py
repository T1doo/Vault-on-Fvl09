import copy,json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from . import runtime
from goal_pilot48_v1.f2_goal_root_runtime_v1.spec import A,W,digest
from goal_pilot48_v1.f2_goal_root_runtime_v1.test_lifecycle import LifecycleTests

class EntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        LifecycleTests.setUpClass();cls.fixture=LifecycleTests.fixture;cls.arrays=LifecycleTests.arrays
    def run_case(self,fail=False):
        m=self.fixture;a=self.arrays;events=[]
        scene=types.SimpleNamespace(planner_query_count=0,trace=[],robot=types.SimpleNamespace(left_entity=types.SimpleNamespace(get_qpos=lambda:np.zeros(38),get_qvel=lambda:np.zeros(38))))
        scene.cameras=types.SimpleNamespace(get_rgb=lambda:{k:{'rgb':np.zeros((1,1,3),dtype=np.uint8)} for k in ('head_camera','left_camera','right_camera')})
        def save_trace(path):
            with Path(path).open('xb') as f:np.savez_compressed(f,CPU_fixture_only=np.zeros(1))
            return {'path':str(path)}
        scene.save_trace=save_trace
        class Context:
            cleanup_receipt=None
            def __enter__(self):return types.SimpleNamespace(scene=scene)
            def __exit__(self,*args):self.cleanup_receipt={'cleanup_safety_pass':True};events.append('cleanup');return False
        context=Context()
        class Adapter:
            def __init__(self,**kw):pass
            def scene(self,*a,**kw):return context
            def capture_current(self,s):events.append('current');return {'aggregate_sha256':m['reference_current_sha256']}
            def capture_anchor(self,s):events.append('anchor');return m['reference_anchor']
            def build_programs(self,s):return [{'program_id':p} for p in ('F2-inside','F2-on','F2-beside')]
            def canonical_prefix_contract(self,p):return m['prefix_contract']
            def plan_and_execute_canonical_prefix(self,s,p):
                events.append('execute');s.planner_query_count=3;s.trace=[{'initial_state':True},{}]
                if fail:raise ValueError('actual model branch failure fixture')
                r={k:copy.deepcopy(m[k]) for k in ('semantic_prefix_end_anchor','acceptance_prefix_end_anchor','planner_seed','planner_query_receipts','planner_source_hash','settling_policy','prefix_physical_acceptance','reference_event_boundaries')}
                r.update(arrays=a,settling_step_count=m['settling_step_count_excluded_from_semantic_prefix']);return r
        modules={'controlled_multi_future.f2_asset_bound_runtime_v3':types.SimpleNamespace(RoboTwinRealSapienF2AssetBoundAdapterV3=Adapter),
          'controlled_multi_future.real_sapien_adapter_high_level_v1':types.SimpleNamespace(_PinnedSapienRenderDeviceContextV1=lambda x:x)}
        with tempfile.TemporaryDirectory(dir=W/'Robotwin2/tmp',prefix='f2_clearance_entry_') as tmp:
            manifest={'jobs':[{'output_namespace':str(Path(tmp)/'job')}],'manifest_sha256':'CPU-only','implementation_source_sha256':'CPU','f2_goal_prefix_spec_sha256':digest(runtime.build_prefix_spec())}
            with patch.dict(sys.modules,modules),patch.object(runtime,'make_controller',return_value=object()):result=runtime.run(manifest)
            return result,events
    def test_actual_new_run_lifecycle_and_artifact(self):
        r,e=self.run_case();self.assertTrue(r['scientific_route_pass']);self.assertEqual(r['trajectory_queries'],3)
        self.assertEqual(r['action_scenes_observed'],1);self.assertEqual(r['collection_attempts'],0);self.assertLess(e.index('anchor'),e.index('execute'))
    def test_new_run_preserves_model_failure_and_cleanup(self):
        r,e=self.run_case(True);self.assertFalse(r['scientific_route_pass']);self.assertIn('model branch failure',r['error']['message']);self.assertIn('cleanup',e)

class IssuerTests(unittest.TestCase):
    def test_pure_builder_no_ledger_write(self):
        from goal_pilot48_v1.runtime.issue_f2_prefix_clearance import ROOT,CAPS,build_manifest
        ledger=ROOT/'budget_ledger.jsonl';old=ledger.read_bytes();name='p48_f2_prefix_clearance_cpu_test'
        m=build_manifest(name,dict(kind='RESERVE',job_id=name,reserved=CAPS,event_sha256='CPU-preview'))
        self.assertEqual(old,ledger.read_bytes());self.assertTrue(m['jobs'][0]['requires_live_meter']);self.assertEqual(m['jobs'][0]['resource_caps']['solver_problems'],3)
        self.assertIn('/runtime_v3/',m['runner_script_path'])
    def test_pure_builder_used_namespace_rejected(self):
        from goal_pilot48_v1.runtime.issue_f2_prefix_clearance import fresh
        with self.assertRaises(ValueError):fresh('p48_f2_prefix_001')

if __name__=='__main__':unittest.main()
