import copy,unittest,types
from unittest.mock import patch
import numpy as np
from .analyze import analyze,load,D,clearance,sphere_clearance,target_from_actual
from . import runtime
from goal_pilot48_v1.f2_controlled_inside_runtime_v2.test_cpu import Tests as Fixtures

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=analyze();cls.model=load(D/'model_005_carried_full.json');cls.original=load(D/'inside_result.json')['spec']
        Fixtures.setUpClass();cls.f=Fixtures
    def test_real_frame_native_sphere_and_necessary_reach_evidence(self):
        r=self.report;self.assertLess(r['exact_goal_transform_replay_position_error_m'],2e-6)
        self.assertTrue(r['native_continuous_straight_carry']['pass']);self.assertTrue(r['actual_fitted_buffered_sphere_straight_carry']['pass'])
        self.assertAlmostEqual(r['actual_fitted_buffered_sphere_straight_carry']['minimum_separating_axis_gap_m'],.004256561615514243)
        self.assertEqual(r['actual_fitted_buffered_sphere_straight_carry']['fitted_spheres'],189)
        self.assertFalse(r['URDF_necessary_reach_bounds']['failed_extra_lift']['excluded_by_general_triangle_bound'])
        self.assertLess(r['URDF_necessary_reach_bounds']['revised']['norm_from_base_m'],r['URDF_necessary_reach_bounds']['failed_extra_lift']['norm_from_base_m'])
    def test_only_target_zero_changed_no_new_height(self):
        f=self.f;kw=dict(actual_eef_pose=f.eef,actual_can_pose=f.can,actual_box_pose=f.box,neutral_eef_pose=f.neutral,certificate=f.c,lineage=f.lineage)
        old=runtime.old_build(**kw);new=runtime.build_targets(**kw)
        self.assertEqual(old['targets'][1:],new['targets'][1:]);self.assertEqual(old['target_actor_pose'],new['target_actor_pose']);self.assertEqual(old['binding_sha256'],new['binding_sha256'])
        self.assertEqual(new['targets'][0]['pose'][2:],new['source_actual_state']['eef'][2:]);self.assertEqual(new['caps']['solver_problems'],5)
    def test_native_blocked_sweep_and_unregistered_height_rejected(self):
        m=copy.deepcopy(self.model);spec=self.original;target=target_from_actual(spec)
        next(s for s in m['world']['shapes'] if s['name']=='box__0')['solver_pose'][2]+=.02
        self.assertFalse(clearance(m['world'],m['can'],m['base'],spec,target)['pass']);self.assertFalse(sphere_clearance(m,spec,target)['pass'])
        target['pose'][2]+=.001
        with self.assertRaises(ValueError):clearance(m['world'],m['can'],m['base'],spec,target)
    def test_actual_backend_checks_fresh_model_before_solver(self):
        b=runtime.LiveBackend.__new__(runtime.LiveBackend);b.plans={};b.spec=copy.deepcopy(self.original);b.spec['targets'][0]=target_from_actual(b.spec)
        with patch.object(runtime.supported.LiveBackend,'install_carried_fullworld',return_value=self.model):r=b.install_carried_fullworld()
        self.assertTrue(r['pass']);self.assertTrue(r['actual_planner_path_native_screen_still_required'])
        m=copy.deepcopy(self.model);next(s for s in m['world']['shapes'] if s['name']=='box__0')['solver_pose'][2]+=.02
        with patch.object(runtime.supported.LiveBackend,'install_carried_fullworld',return_value=m):self.assertFalse(b.install_carried_fullworld()['pass'])
    def test_actual_runtime_reaches_new_target_builder_and_backend(self):
        import controlled_multi_future.family_runners_v3_3 as original
        import goal_pilot48_v1.f2_inside_native_floor_v1.certificate as cert
        f=self.f;scene=types.SimpleNamespace(planner_query_count=0,can=object(),box=object(),robot=types.SimpleNamespace(left_original_pose=f.neutral))
        with patch.object(original.F2ControllerV3_3,'validate_replayed_prefix_physical',return_value={'pass':True}),patch.object(original,'_arm_eef_pose',return_value=f.eef),patch.object(original,'_pose',side_effect=lambda a:f.can if a is scene.can else f.box),patch.object(cert,'build_live_certificate',return_value=f.c),patch.object(runtime,'build_targets',wraps=runtime.build_targets) as build,patch.object(runtime,'LiveBackend',side_effect=ImportError('CPU_CARRY_REVISION_BACKEND')):
            r=runtime.run(scene,{},output='CPU-no-output',current_sha256=f.lineage['reference_current']['aggregate_sha256'],initial_anchor_sha256=f.lineage['initial_anchor_sha256'])
        self.assertEqual(build.call_count,1);self.assertFalse(r['pass']);self.assertEqual(r['error']['message'],'CPU_CARRY_REVISION_BACKEND');self.assertEqual(r['carry_waypoint_revision'],1)
