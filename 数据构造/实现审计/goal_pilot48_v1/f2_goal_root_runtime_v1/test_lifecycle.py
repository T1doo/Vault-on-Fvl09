"""Actual run() lifecycle and actual canonical publication; no GPU objects."""
import copy,json,locale,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from .spec import W,A,build_prefix_spec,digest
from . import prefix_runner,artifact_io
from .runner_bridge import reconcile

class LifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from controlled_multi_future.canonical_prefix_artifact_v1 import load_canonical_prefix_artifact
        cls.parent=W/'Robotwin2/datasets/controlled_multi_future_f2_top_contact_root_v1/f2-top-contact-development-rpc-root-v1-run1/root/canonical_prefix_artifact'
        cls.fixture,cls.arrays=load_canonical_prefix_artifact(cls.parent)

    def case(self,failure=None,prefix_pass=True,cleanup_failure=False,artifact_failure=False):
        events=[];fixture=self.fixture;arrays=self.arrays
        class Scene:
            planner_query_count=0
            trace=[]
            def __init__(self):
                self.robot=types.SimpleNamespace(left_entity=types.SimpleNamespace(get_qpos=lambda:np.zeros(38),get_qvel=lambda:np.zeros(38)))
                self.cameras=types.SimpleNamespace(get_rgb=self.rgb)
            def rgb(self):
                events.append('RGB')
                if failure=='RGB':raise ValueError('RGB earliest')
                return {k:{'rgb':np.zeros((2,2,3),dtype=np.uint8)} for k in ('head_camera','left_camera','right_camera')}
            def save_trace(self,path):
                events.append('save')
                if failure=='save':raise OSError('save earliest')
                with Path(path).open('xb') as f:np.savez_compressed(f,CPU_fixture_not_physical=np.zeros(1))
                return {'path':str(path)}
        scene=Scene()
        class Context:
            cleanup_receipt=None
            def __enter__(self):
                events.append('enter')
                if failure=='enter':self.cleanup_receipt={'cleanup_safety_pass':True};raise RuntimeError('setup earliest')
                return types.SimpleNamespace(scene=scene)
            def __exit__(self,*args):
                events.append('cleanup');self.cleanup_receipt={'cleanup_safety_pass':not cleanup_failure}
                if cleanup_failure:raise RuntimeError('cleanup later')
                return False
        context=Context()
        class Adapter:
            def __init__(self,**kwargs):events.append('adapter')
            def scene(self,*args,**kwargs):events.append('scene_factory');return context
            def capture_current(self,scene):
                events.append('current')
                if failure=='current':raise ValueError('current earliest')
                return {'aggregate_sha256':fixture['reference_current_sha256']}
            def capture_anchor(self,scene):
                events.append('anchor')
                if failure=='anchor':raise ValueError('anchor earliest')
                return fixture['reference_anchor']
            def build_programs(self,scene):events.append('programs');return [{'program_id':k} for k in ('F2-inside','F2-on','F2-beside')]
            def canonical_prefix_contract(self,p):return fixture['prefix_contract']
            def plan_and_execute_canonical_prefix(self,scene,p):
                events.append('execute');scene.planner_query_count=3;scene.trace=[{'initial_state':True},{}]
                if failure=='execute':raise RuntimeError('execute earliest')
                result={k:copy.deepcopy(fixture[k]) for k in ('semantic_prefix_end_anchor','acceptance_prefix_end_anchor','planner_seed','planner_query_receipts','planner_source_hash','settling_policy','prefix_physical_acceptance','reference_event_boundaries')}
                result.update(arrays=arrays,settling_step_count=fixture['settling_step_count_excluded_from_semantic_prefix']);result['prefix_physical_acceptance']['pass']=prefix_pass
                return result
        modules={'controlled_multi_future.f2_asset_bound_runtime_v3':types.SimpleNamespace(RoboTwinRealSapienF2AssetBoundAdapterV3=Adapter),
                 'controlled_multi_future.real_sapien_adapter_high_level_v1':types.SimpleNamespace(_PinnedSapienRenderDeviceContextV1=lambda c:c)}
        spec=build_prefix_spec()
        with tempfile.TemporaryDirectory(dir=W/'Robotwin2/tmp',prefix='f2_prefix_lifecycle_') as tmp:
            out=Path(tmp)/'job';m={'manifest_sha256':'CPU_fake_lifecycle','implementation_source_sha256':'CPU','f2_goal_prefix_spec_sha256':digest(spec),'jobs':[{'output_namespace':str(out)}]}
            with patch.dict(sys.modules,modules),patch.object(prefix_runner,'make_controller',return_value=object()):
                if artifact_failure:
                    with patch.object(artifact_io,'write_prefix_artifact',side_effect=OSError('artifact earliest')):r=prefix_runner.run(m)
                else:r=prefix_runner.run(m)
            r['test_artifact_file_exists']=(out/'canonical_prefix_artifact/canonical_prefix_artifact.json').exists()
            return r,events

    def test_real_run_success_publishes_valid_artifact(self):
        r,e=self.case();self.assertTrue(r['pass']);self.assertTrue(r['scientific_route_pass']);self.assertTrue(r['test_artifact_file_exists'])
        self.assertLess(e.index('current'),e.index('execute'));self.assertLess(e.index('anchor'),e.index('execute'));self.assertLess(e.index('RGB'),e.index('execute'))
        self.assertEqual(r['trajectory_queries'],3);self.assertEqual(r['action_scenes_observed'],1)

    def test_current_anchor_RGB_fail_before_any_action_with_cleanup(self):
        for phase in ('current','anchor','RGB'):
            with self.subTest(phase=phase):
                r,e=self.case(failure=phase);self.assertFalse(r['pass']);self.assertFalse(r['scientific_route_pass'])
                self.assertNotIn('execute',e);self.assertIn('cleanup',e);self.assertEqual(r['action_scenes_observed'],0)
                self.assertIn(phase,r['error']['message'])

    def test_setup_failure_and_save_failure_retained(self):
        r,_=self.case(failure='enter');self.assertFalse(r['accounting_complete']);self.assertEqual(r['error']['message'],'setup earliest')
        r,e=self.case(failure='save');self.assertEqual(r['error']['stage'],'trace_save');self.assertIsNotNone(r['trace_save_error']);self.assertIn('cleanup',e)

    def test_earliest_error_survives_cleanup_failure(self):
        r,_=self.case(failure='current',cleanup_failure=True)
        self.assertEqual(r['error']['message'],'current earliest');self.assertEqual(r['cleanup_error']['message'],'cleanup later')

    def test_physical_failure_or_publication_failure_never_scientific_pass(self):
        r,_=self.case(prefix_pass=False);self.assertTrue(r['pass']);self.assertFalse(r['scientific_route_pass']);self.assertFalse(r['test_artifact_file_exists'])
        r,_=self.case(artifact_failure=True);self.assertTrue(r['prefix_physical_pass']);self.assertFalse(r['scientific_route_pass']);self.assertEqual(r['error']['stage'],'prefix_artifact')

    def test_real_prefix_writer_forced_C_locale_UTF8_exclusive(self):
        from controlled_multi_future.canonical_prefix_artifact_v1 import canonical_json_sha256,load_canonical_prefix_artifact
        m=copy.deepcopy(self.fixture);m.pop('prefix_arrays_npz_sha256',None);m.pop('artifact_sha256');m['CPU_diagnostic_note']='数据构造测试';m['artifact_sha256']=canonical_json_sha256(m)
        saved=locale.setlocale(locale.LC_CTYPE)
        try:
            locale.setlocale(locale.LC_CTYPE,'C')
            with tempfile.TemporaryDirectory(dir=W/'Robotwin2/tmp',prefix='prefix_utf8_') as tmp:
                out=Path(tmp)/'artifact';artifact_io.write_prefix_artifact(out,m,self.arrays)
                restored,_=load_canonical_prefix_artifact(out);self.assertEqual(restored['CPU_diagnostic_note'],'数据构造测试')
                with self.assertRaises(FileExistsError):artifact_io.write_prefix_artifact(out,m,self.arrays)
        finally:locale.setlocale(locale.LC_CTYPE,saved)

    def test_prefix_meter_requires_3_MotionGen_0_IK_exact_partitions(self):
        counts=dict(solver_problems=3,fresh_scenes=1,action_scenes=1,collection_attempts=0)
        r=dict(trajectory_queries=3,fresh_scene_attempts=1,action_scenes_observed=1,ik_problem_attempts=0,collection_attempts=0)
        events=[dict(kind='CHARGE',resource=k,amount=1,total=1) for k in ('fresh_scenes','action_scenes')]
        events += [dict(kind='CHARGE',resource='solver_problems',amount=1,total=i,method='MotionGen.plan_single') for i in range(1,4)]
        self.assertTrue(reconcile(r,counts,events)['pass']);events[-1]['method']='IKSolver.solve_single'
        self.assertFalse(reconcile(r,counts,events)['pass']);self.assertFalse(reconcile(r,{**counts,'collection_attempts':1},events)['pass'])

if __name__=='__main__':unittest.main()
