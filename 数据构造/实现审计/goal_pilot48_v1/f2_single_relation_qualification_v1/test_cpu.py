import copy,unittest,types
from unittest.mock import patch
import numpy as np
from . import runtime,runner_bridge
from .spec import build_spec,digest,CAPS

class Tests(unittest.TestCase):
    def test_only_release_goal_changed_and_tampering_refused(self):
        from goal_pilot48_v1.f2_on_release_revision_v1.runtime import revise,validate
        from goal_pilot48_v1.f2_on_beside_runtime_v1.spec import load,W
        old=load(W/'Robotwin2/datasets/p48_f2_on_beside_qualification_001/on/suffix_spec.json')
        new=revise(old);self.assertTrue(validate(new));self.assertEqual(new['target_actor_pose'],old['target_actor_pose'])
        for i in (0,2,3):self.assertEqual(new['targets'][i],old['targets'][i])
        np.testing.assert_allclose(np.asarray(new['targets'][1]['pose'])-old['targets'][1]['pose'],[0,0,.004,0,0,0,0],atol=1e-15)
        bad=copy.deepcopy(new);bad['targets'][0]['pose'][2]+=.004;bad.pop('receipt_sha256');bad['receipt_sha256']=digest(bad)
        with self.assertRaises(ValueError):validate(bad)
    def wrapper_case(self,relation,reason=None):
        # Reuse the prior actual run_one CPU fixture, but execute THIS new
        # single-scene wrapper/bridge. It creates only fake CPU Scene objects.
        from goal_pilot48_v1.f2_on_beside_qualification_v1 import test_cpu as fixtures,runner_bridge as oldbridge
        from goal_pilot48_v1.f2_on_beside_qualification_v1.spec import build_spec as oldspec
        from goal_pilot48_v1.f2_inward_runtime_v1.runtime import dependencies
        dependencies();harness=fixtures.Tests();harness.spec=oldspec();harness.artifact,harness.arrays=runtime.base.load_reference()
        spec=build_spec(relation)
        def delegate(m,*,meter):
            m=dict(m);m.update(qualification_relation=relation,single_relation_qualification_spec_sha256=digest(spec))
            return runner_bridge.run(m,meter=meter)
        with patch.object(fixtures,'runner_bridge',types.SimpleNamespace(run=delegate)),patch.object(runtime,'build_spec',return_value=spec),patch.object(runtime,'suffix_callable',side_effect=lambda relation:runtime.base.suffix_run):
            return harness.case(reason)
    def test_actual_single_wrapper_both_scopes_and_stops(self):
        for relation in ('on','beside'):
            r=self.wrapper_case(relation);self.assertTrue(r['scientific_route_pass']);self.assertTrue(r['meter_audit']['pass'])
            self.assertEqual((r['trajectory_queries'],r['fresh_scene_attempts'],r['action_scenes_observed']),(4,1,1));self.assertFalse(r['whole_root_qualification_complete'])
            for reason in ('first_action','cleanup','suffix','missing_checks'):
                r=self.wrapper_case(relation,reason);self.assertFalse(r['scientific_route_pass']);self.assertTrue(r['meter_audit']['pass']);self.assertEqual(r['fresh_scene_attempts'],1)
    def test_one_scene_cap_reconciliation(self):
        r={'trajectory_queries':4,'fresh_scene_attempts':2,'action_scenes_observed':1,'collection_attempts':0,'ik_problem_attempts':0}
        counts={'solver_problems':4,'fresh_scenes':2,'action_scenes':1,'collection_attempts':0}
        events=[{'kind':'CHARGE','resource':k,'amount':n,'total':n,'method':'MotionGen.plan_single'} for k,n in counts.items() if n]
        self.assertFalse(runner_bridge.reconcile(r,counts,events)['pass'])
