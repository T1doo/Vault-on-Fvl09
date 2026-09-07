"""Real wrapper with CPU fake scene/control backend, no GPU initialization."""
import copy,gc,json,tempfile,types,unittest,weakref
from pathlib import Path
from unittest.mock import patch
import numpy as np
from . import runtime,runner_bridge
from .local_counts import LocalCounts
from .spec import build_spec,digest,CAPS
from goal_pilot48_v1.runtime_v3.meter import Meter
from goal_pilot48_v1.f2_on_beside_runtime_v1.spec import W

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from goal_pilot48_v1.f2_inward_runtime_v1.runtime import dependencies
        dependencies();cls.spec=build_spec();cls.artifact,cls.arrays=runtime.load_reference()
    def case(self,failure=None):
        spec=self.spec;artifact=self.artifact
        with tempfile.TemporaryDirectory(dir=W/'Robotwin2/tmp',prefix='onbeside_wrapper_cpu_') as tmp:
            out=Path(tmp)/'job';meter=Meter(Path(tmp)/'meter',CAPS);scenes=[]
            class Base:
                def setup_scene(s):
                    meter.charge('fresh_scenes');meter.scene_ids[id(s)]=len(scenes)
                    if failure=='setup':raise RuntimeError('CPU fixture setup failure')
                def move(s):pass
            class Trace:
                def replay_effective_setpoint_step(s,*a,**kw):
                    if failure=='first_action':raise RuntimeError('CPU fixture first action failure')
                    s.trace.append({'CPU_fixture_only':True})
                def take_dense_action(s,*a,**kw):pass
            class Scene(Base,Trace):
                planner_query_count=0
                def __init__(s):
                    entity=types.SimpleNamespace(get_qpos=lambda:np.zeros(38),get_qvel=lambda:np.zeros(38));s.robot=types.SimpleNamespace(left_entity=entity)
                    s.cameras=types.SimpleNamespace(get_rgb=lambda:{k:{'rgb':np.zeros((1,1,3),dtype=np.uint8)} for k in ('head_camera','left_camera','right_camera')})
                def save_trace(s,path):
                    with Path(path).open('xb') as f:np.savez_compressed(f,CPU_fixture_only=np.zeros(1))
                    return {'path':str(path),'CPU_fixture_only':True}
            class Context:
                cleanup_receipt=None
                def __init__(s,scene):s.scene=scene
                def __enter__(s):
                    try:s.scene.setup_scene()
                    except Exception:s.cleanup_receipt={'cleanup_safety_pass':True};raise
                    return types.SimpleNamespace(scene=s.scene)
                def __exit__(s,*a):
                    s.cleanup_receipt={'cleanup_safety_pass':failure!='cleanup'}
                    if failure=='cleanup':raise RuntimeError('CPU fixture cleanup failure')
            class Adapter:
                def __init__(s,**kw):pass
                def scene(s,*a,**kw):
                    scene=Scene();scenes.append(scene);return Context(scene)
                def capture_current(s,scene):
                    r=copy.deepcopy(spec['prefix_lineage']['current'])
                    if failure=='current':r['aggregate_sha256']='wrong';r['model_visible_aggregate_sha256']='wrong'
                    return r
                def capture_anchor(s,scene):return copy.deepcopy(artifact['reference_anchor'])
                def initialize_prefix_replay_trace(s,scene):scene.trace=[{'CPU_initial':True}];scene.planner_query_count=0
                def validate_replayed_prefix_physical(s,*a):return {'pass':failure!='prefix_physical','CPU_fixture_only':True}
            def replay(s,*args):
                s.replay_effective_setpoint_step();return {'prefix_end_equivalent':True,'planner_query_delta':0,'CPU_fixture_only':True}
            def suffix(s,*args,**kw):
                fn=meter.solver(lambda goal_pose:None,kind='MotionGen.plan_single')
                for _ in range(4):s.planner_query_count+=1;fn(None)
                if failure!='missing_checks':
                    for i in range(spec['high_level_state_checks'][kw['relation']]):
                        with (Path(kw['output'])/('model_%03d_CPU_start.json'%i)).open('x',encoding='utf-8') as f:
                            json.dump({'high_level_constraint_call':1,'CPU_fixture_only':True},f)
                return {'pass':failure!='suffix','CPU_fixture_only':True}
            manifest={'jobs':[{'output_namespace':str(out)}],'on_beside_qualification_spec_sha256':digest(spec),'implementation_source_sha256':'CPU','manifest_sha256':'CPU'}
            meter.install_replay_hook(Trace)
            with patch.object(runtime,'LocalCounts',side_effect=lambda:LocalCounts(Base,Trace)),patch.object(runtime,'components',return_value=(Adapter,lambda c:c)),patch.object(runtime,'build_spec',return_value=spec),patch.object(runtime,'load_reference',return_value=(artifact,{})),patch.object(runtime,'actual_replay',side_effect=replay),patch.object(runtime,'suffix_run',side_effect=suffix):
                result=runner_bridge.run(manifest,meter=meter)
            meter.close();return result
    def test_real_two_scene_wrapper_and_independent_meter(self):
        r=self.case();self.assertTrue(r['scientific_route_pass']);self.assertTrue(r['meter_audit']['pass']);self.assertEqual(r['trajectory_queries'],8)
        self.assertEqual(r['action_scenes_observed'],2);self.assertEqual(r['fresh_scene_attempts'],2);self.assertFalse(r['whole_root_qualification_complete'])
    def test_first_action_failure_counted_and_second_unattempted(self):
        r=self.case('first_action');self.assertFalse(r['scientific_route_pass']);self.assertTrue(r['meter_audit']['pass'])
        self.assertEqual(r['action_scenes_observed'],1);self.assertEqual(r['trajectory_queries'],0);self.assertEqual(r['unattempted_relations'],['beside'])
    def test_setup_current_cleanup_prefix_and_suffix_stop(self):
        for reason in ('setup','current','cleanup','prefix_physical','suffix','missing_checks'):
            r=self.case(reason);self.assertFalse(r['scientific_route_pass']);self.assertEqual(r['fresh_scene_attempts'],1)
            self.assertTrue(r['meter_audit']['pass']);self.assertEqual(r['unattempted_relations'],['beside'])
            if reason in ('setup','current'):self.assertEqual(r['action_scenes_observed'],0)
    def test_independent_counts_reject_IK_and_missing_action(self):
        local={'trajectory_queries':1,'fresh_scene_attempts':1,'action_scenes_observed':1,'collection_attempts':0,'ik_problem_attempts':0}
        counts={'solver_problems':1,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0}
        events=[{'kind':'CHARGE','resource':k,'amount':1,'total':1,'method':'MotionGen.plan_single'} for k in ('solver_problems','fresh_scenes','action_scenes')]
        self.assertTrue(runner_bridge.reconcile(local,counts,events)['pass'])
        self.assertFalse(runner_bridge.reconcile({**local,'action_scenes_observed':0},counts,events)['pass'])
        events[0]['method']='IKSolver.solve_single';self.assertFalse(runner_bridge.reconcile(local,counts,events)['pass'])
    def test_retired_scene_collectable_and_counts_survive_identifier_reuse(self):
        class Base:
            def setup_scene(s):s.planner_query_count=0;s.trace=[]
            def move(s):pass
        class Trace:
            def replay_effective_setpoint_step(s):pass
            def take_dense_action(s):pass
        class Scene(Base,Trace):pass
        local=LocalCounts(Base,Trace)
        with local:
            first=Scene();first.setup_scene();first.replay_effective_setpoint_step();first.planner_query_count=4
            reference=weakref.ref(first);local.retire_completed()
            with self.assertRaisesRegex(RuntimeError,'repetition'):first.setup_scene()
            del first;gc.collect();self.assertIsNone(reference())
            self.assertEqual(local.scenes,{})
            second=Scene()
            # A dead weak reference at this ID represents Python ID reuse.
            local.seen[id(second)]=reference
            second.setup_scene();second.take_dense_action();second.planner_query_count=4
            local.retire_completed();local.retire_completed()
            self.assertEqual(local.snapshot(),dict(fresh_scene_attempts=2,action_scenes_observed=2,
                trajectory_queries=8,ik_problem_attempts=0,collection_attempts=0))
            with self.assertRaisesRegex(RuntimeError,'two-scene'):Scene().setup_scene()
    def test_bad_retired_counter_rejects_but_releases_reference(self):
        class Base:
            def setup_scene(s):s.trace=[];s.planner_query_count='invalid'
            def move(s):pass
        class Trace:
            def replay_effective_setpoint_step(s):pass
            def take_dense_action(s):pass
        class Scene(Base,Trace):pass
        local=LocalCounts(Base,Trace)
        with local:
            scene=Scene();scene.setup_scene();reference=weakref.ref(scene)
            with self.assertRaises(ValueError):local.retire_completed()
            del scene;gc.collect();self.assertIsNone(reference())
            with self.assertRaises(ValueError):local.snapshot()
