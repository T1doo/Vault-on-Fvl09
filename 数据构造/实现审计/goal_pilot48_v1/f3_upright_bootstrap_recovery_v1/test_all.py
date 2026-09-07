"""CPU-only exact frozen nested-MRO regression, with complete prior preflight."""
import ast
import inspect
import types
import unittest
from unittest.mock import patch
from . import runtime
from goal_pilot48_v1.f3_upright_qualification_runtime_v1 import context


def fixture(counts, meter, fail=False):
    class BaseTask:
        def _init_task_env_(self, **kwargs):
            meter.setup_depth += 1
            try:
                self.setup_scene()
                self.together_open_gripper()
                if fail:
                    raise ValueError('initialization fixture failure')
            finally:
                meter.setup_depth -= 1
        def setup_scene(self):
            self.scene = types.SimpleNamespace(step=lambda: None)
        def together_open_gripper(self):
            self.move()
        def move(self):
            pass
        def take_dense_action(self):
            pass
    class AuditScene(BaseTask):
        def setup_demo(self, **kwargs):
            super()._init_task_env_(**kwargs)
    # Execute the real frozen wrapper class, not a hand-written imitation.
    tree = ast.parse(inspect.getsource(context.make))
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == 'CountedUpright']
    if len(nodes) != 1:
        raise AssertionError('frozen MRO class changed')
    env = dict(base_scene=AuditScene, counts=counts)
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), context.__file__, 'exec'), env)
    return env['CountedUpright']()


class Tests(unittest.TestCase):
    def test_exact_old_mro_reproduces_rejection(self):
        meter = types.SimpleNamespace(setup_depth=0)
        counts = context.Counts()
        scene = fixture(counts, meter)
        with self.assertRaisesRegex(RuntimeError, 'before current'):
            scene.setup_demo()
        self.assertEqual((counts.scenes, counts.actions, counts.setup_depth, meter.setup_depth), (1, 0, 0, 0))

    def test_repaired_mro_setup_only_then_real_actions(self):
        meter = types.SimpleNamespace(setup_depth=0)
        counts = runtime.Counts(meter)
        scene = fixture(counts, meter)
        scene.setup_demo()
        self.assertEqual((counts.scenes, counts.actions, counts.initialization_action_calls, meter.setup_depth), (1, 0, 1, 0))
        counts.setup_depth = 999
        with self.assertRaisesRegex(RuntimeError, 'before current'):
            scene.move()
        scene.trace = [object()]
        scene.move()
        scene.take_dense_action()
        self.assertEqual(counts.actions, 1)

    def test_setup_exception_unwinds_and_no_pretrace_leak(self):
        meter = types.SimpleNamespace(setup_depth=0)
        counts = runtime.Counts(meter)
        scene = fixture(counts, meter, fail=True)
        with self.assertRaisesRegex(ValueError, 'fixture failure'):
            scene.setup_demo()
        self.assertEqual(meter.setup_depth, 0)
        with self.assertRaisesRegex(RuntimeError, 'before current'):
            scene.take_dense_action()

    def test_invalid_actual_depth_fails_closed(self):
        for depth in (None, -1, 1.0, True):
            with self.subTest(depth=depth), self.assertRaisesRegex(RuntimeError, 'actual live-meter'):
                runtime.Counts(types.SimpleNamespace(setup_depth=depth)).action(types.SimpleNamespace(trace=[1]))

    def test_private_factory_preserves_frozen_globals(self):
        def stub(manifest, *, meter):
            return base.Counts()  # resolved from private function globals
        old = runtime.hd.base.Counts
        meter = types.SimpleNamespace(setup_depth=0)
        with patch.object(runtime.hd, 'run', stub):
            counts = runtime.private_hd_runner(meter)({}, meter=meter)
        self.assertIs(counts.live_meter, meter)
        self.assertIs(runtime.hd.base.Counts, old)

    def test_scope_rejects_before_runner(self):
        with patch.object(runtime, 'private_hd_runner') as run:
            with self.assertRaises(ValueError):
                runtime.run({}, meter=object())
            run.assert_not_called()


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite([tests])
    suite.addTests(loader.loadTestsFromName('goal_pilot48_v1.runtime.test_upright_hd_preflight'))
    return suite
