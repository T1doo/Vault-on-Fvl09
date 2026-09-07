import copy,json,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from . import runtime,runner_bridge
from .local_counts import LocalCounts
from .spec import build_spec,digest,CAPS
from goal_pilot48_v1.runtime_v3.meter import Meter
from goal_pilot48_v1.f2_controlled_inside_runtime_v2.spec import W

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from goal_pilot48_v1.f2_inward_runtime_v1.runtime import dependencies
        dependencies();cls.spec=build_spec();cls.artifact,cls.arrays=runtime.load_reference()
    def case(self,failure=None):
        spec=self.spec;artifact=self.artifact
        with tempfile.TemporaryDirectory(dir=W/'Robotwin2/tmp',prefix='inside_wrapper_cpu_') as tmp:
            out=Path(tmp)/'job';meter=Meter(Path(tmp)/'meter',CAPS)
            class Base:
                def setup_scene(s):
                    meter.charge('fresh_scenes');meter.scene_ids[id(s)]=1
                    if failure=='setup':raise RuntimeError('fixture setup failure')
                def move(s):pass
            class Trace:
                def replay_effective_setpoint_step(s,*a,**kw):
                    if failure=='first_action':raise RuntimeError('fixture first action failure')
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
            scene=Scene()
            class Context:
                cleanup_receipt=None
                def __enter__(s):
                    try:scene.setup_scene()
                    except Exception:s.cleanup_receipt={'cleanup_safety_pass':True};raise
                    return types.SimpleNamespace(scene=scene)
                def __exit__(s,*a):
                    s.cleanup_receipt={'cleanup_safety_pass':failure!='cleanup'}
                    if failure=='cleanup':raise RuntimeError('fixture cleanup failure')
            context=Context()
            class Adapter:
                def __init__(s,**kw):pass
                def scene(s,*a,**kw):return context
                def capture_current(s,scene):
                    r=copy.deepcopy(spec['prefix_lineage']['reference_current'])
                    if failure=='current':r['aggregate_sha256']='wrong';r['model_visible_aggregate_sha256']='wrong'
                    return r
                def capture_anchor(s,scene):return copy.deepcopy(artifact['reference_anchor'])
                def initialize_prefix_replay_trace(s,scene):scene.trace=[{'CPU_initial':True}];scene.planner_query_count=0
                def validate_replayed_prefix_physical(s,*a):return {'pass':True,'CPU_fixture_only':True}
            def replay(s,*args):
                s.replay_effective_setpoint_step();return {'prefix_end_equivalent':True,'planner_query_delta':0,'CPU_fixture_only':True}
            def suffix(s,*args,**kw):
                fn=meter.solver(lambda goal_pose:None,kind='MotionGen.plan_single')
                for _ in range(5):s.planner_query_count+=1;fn(None)
                return {'pass':True,'CPU_fixture_only':True}
            manifest={'jobs':[{'output_namespace':str(out)}],'inside_qualification_spec_sha256':digest(spec),'implementation_source_sha256':'CPU','manifest_sha256':'CPU'}
            meter.install_replay_hook(Trace)
            with patch.object(runtime,'LocalCounts',side_effect=lambda:LocalCounts(Base,Trace)),patch.object(runtime,'components',return_value=(Adapter,lambda c:c)),patch.object(runtime,'build_spec',return_value=spec),patch.object(runtime,'load_reference',return_value=(artifact,{})),patch.object(runtime,'actual_replay',side_effect=replay),patch.object(runtime,'inside_run',side_effect=suffix):
                result=runner_bridge.run(manifest,meter=meter)
            meter.close();return result
    def test_real_wrapper_lifecycle_and_live_local_counts(self):
        r=self.case();self.assertTrue(r['scientific_route_pass']);self.assertTrue(r['meter_audit']['pass']);self.assertEqual(r['trajectory_queries'],5);self.assertEqual(r['action_scenes_observed'],1);self.assertEqual(r['fresh_scene_attempts'],1)
    def test_real_wrapper_failure_before_first_row_is_still_action(self):
        r=self.case('first_action');self.assertFalse(r['scientific_route_pass']);self.assertTrue(r['meter_audit']['pass']);self.assertEqual(r['action_scenes_observed'],1);self.assertEqual(r['trajectory_queries'],0)
    def test_real_wrapper_scene_setup_current_and_cleanup_failure(self):
        for reason in ('setup','current','cleanup'):
            r=self.case(reason);self.assertFalse(r['scientific_route_pass']);self.assertEqual(r['fresh_scene_attempts'],1);self.assertTrue(r['meter_audit']['pass'])
            if reason in ('setup','current'):self.assertEqual(r['action_scenes_observed'],0)
    def test_independent_meter_mismatch_and_IK_rejected(self):
        local={'trajectory_queries':1,'fresh_scene_attempts':1,'action_scenes_observed':1,'collection_attempts':0,'ik_problem_attempts':0}
        counts={'solver_problems':1,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0}
        events=[{'kind':'CHARGE','resource':k,'amount':1,'total':1,'method':'MotionGen.plan_single'} for k in ('solver_problems','fresh_scenes','action_scenes')]
        self.assertTrue(runner_bridge.reconcile(local,counts,events)['pass'])
        self.assertFalse(runner_bridge.reconcile({**local,'action_scenes_observed':0},counts,events)['pass'])
        events[0]['method']='IKSolver.solve_single';self.assertFalse(runner_bridge.reconcile(local,counts,events)['pass'])
