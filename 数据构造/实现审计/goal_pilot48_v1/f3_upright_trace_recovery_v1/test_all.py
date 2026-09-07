import json
import types
import unittest
from unittest.mock import patch
from . import runtime
from .capability_audit import inventory, structural_classes, A

class Tests(unittest.TestCase):
    def classes(self):
        env = structural_classes()
        env['create_actor'] = lambda *args, **kwargs: None
        env['_entity'] = lambda actor: actor
        trace = type('TraceF3RuntimeV2', (env['DenseTraceMixin'], env['F3Scene']), {})
        return env, trace

    def test_live_source_inventory_and_old_plain_base_rejected(self):
        report = inventory()
        self.assertEqual(report['required_method_providers']['_contacts'], 'DenseTraceMixin')
        env, trace = self.classes()
        with self.assertRaises(ValueError):
            runtime.require_trace_base(env['F3Scene'])
        self.assertIs(runtime.require_trace_base(trace), trace)

    def test_actual_upright_factory_retains_trace_methods(self):
        from goal_pilot48_v1.f3_upright_design_v1.scene import make_scene_class
        spec = json.loads((A/'goal_pilot48_v1/f3_upright_design_v1/design_spec.json').read_text(encoding='utf-8'))
        env, trace = self.classes()
        derived = make_scene_class(spec, base_class=trace, pose_factory=lambda p:p)
        runtime.require_trace_base(derived)
        self.assertTrue(issubclass(derived, env['DenseTraceMixin']))

    def test_actual_contact_method_callable_before_trace_initialization(self):
        _, trace = self.classes()
        scene = trace.__new__(trace)
        scene.trace_contact_actor = types.SimpleNamespace(get_name=lambda:'bottle')
        scene.trace_arm = 'left'
        scene.robot = types.SimpleNamespace(left_gripper=[],left_fix_gripper_name=[])
        scene.scene = types.SimpleNamespace(get_contacts=lambda:[])
        self.assertEqual(scene._contacts(), ([],0,0.0))

    def test_actual_video_finalizer_calls_recorder_and_removes_hook(self):
        _, trace = self.classes()
        scene = trace.__new__(trace)
        calls = []
        scene._cmf_development_video_recorder = types.SimpleNamespace(close=lambda s, **kw:calls.append(kw) or {'frames':1})
        self.assertEqual(scene.finish_development_video_capture(), {'frames':1})
        self.assertEqual(len(calls), 1)
        self.assertFalse(hasattr(scene,'_cmf_development_video_recorder'))

    def test_compiled_factory_binds_required_trace_base(self):
        fn = runtime.compiled_make()
        self.assertIn('_require_trace_base', fn.__code__.co_names)
        self.assertIn(('base_class',), fn.__code__.co_consts)

    def test_scope_cannot_silently_reuse_two_scene_authority(self):
        with patch.object(runtime,'private_hd_runner') as runner:
            with self.assertRaises(ValueError):
                runtime.run({},meter=object())
            runner.assert_not_called()

def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite([tests])
    suite.addTests(loader.loadTestsFromName('goal_pilot48_v1.f3_upright_bootstrap_recovery_v1.test_all'))
    return suite
