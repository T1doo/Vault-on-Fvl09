"""No CUDA/Scene construction. Run as a package with audit PYTHONPATH."""
import ast
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from .contract import A, W, build_contract, validate_contract, digest
from .state_machine import Budget, open_named_qpos, run_route
from .collision import support_witness, F2PairWorld

class StateTests(unittest.TestCase):
    def test_caps(self):
        b = Budget()
        for _ in range(3): b.reserve('ik')
        with self.assertRaises(ValueError): b.reserve('ik')
        for _ in range(4): b.reserve('trajectory')
        with self.assertRaises(ValueError): b.reserve('trajectory')

    def test_no_route_on_endpoint_failure(self):
        b = Budget()
        def forbidden(*a): raise AssertionError('callback reached')
        r = run_route([0, 0], {}, endpoints_pass=False, budget=b, plan=forbidden, merge=forbidden, screen=forbidden, release=forbidden)
        self.assertFalse(r['pass']); self.assertEqual(b.trajectory, 0)

    def run_case(self, bad_release=False, bad_screen=False):
        calls = []
        def plan(goal, q, ordinal):
            calls.append(q.copy())
            return {'status': 'Success', 'position': [q + np.array([1, 0])]}
        def release(q):
            q[1] = 9
            return q, {'pass': True, 'attached_can_present': bad_release, 'released_can_present': True}
        result = run_route([0, 0], dict.fromkeys(('U_new', 'D_new', 'N'), [0] * 7), endpoints_pass=True, budget=Budget(),
                           plan=plan, merge=lambda q, end: end, screen=lambda c, i: {'pass': not bad_screen}, release=release)
        return result, calls

    def test_full_state_continuity_and_release(self):
        r, calls = self.run_case()
        self.assertTrue(r['pass'])
        np.testing.assert_array_equal(calls, [[0, 0], [1, 0], [2, 9], [3, 9]])

    def test_attached_to_neutral_rejected(self):
        r, calls = self.run_case(bad_release=True)
        self.assertFalse(r['pass']); self.assertEqual(len(calls), 2)

    def test_native_failure_stops_before_next_query(self):
        r, calls = self.run_case(bad_screen=True)
        self.assertFalse(r['pass']); self.assertEqual(len(calls), 1)

    def test_actual_named_open_mapping(self):
        q, changed = open_named_qpos([8, 3, 4], ['arm', 'fingerB', 'fingerA'], [('fingerA', 1, 0), ('fingerB', -1, .002)], [-.01, .045])
        np.testing.assert_allclose(q, [8, -.043, .045])
        self.assertEqual(set(changed), {'fingerA', 'fingerB'})
        with self.assertRaises(ValueError): open_named_qpos([0], ['arm'], [('absent', 1, 0)], [0, 1])

class ContractTests(unittest.TestCase):
    def test_live_new_contract_and_old_target_negative(self):
        c = build_contract()
        self.assertTrue(validate_contract(c))
        self.assertEqual(c['inward_contract']['IK_cap'], 3)
        broken = copy.deepcopy(c)
        broken['beside_targets'][1]['pose'][0] += .1
        broken['beside_targets_sha256'] = digest(broken['beside_targets'])
        with self.assertRaises(ValueError): validate_contract(broken)

    def test_no_action_or_collection_dispatch(self):
        root = Path(__file__).parent
        forbidden = {'_execute_control', '_execute_planned_segment', 'set_gripper', 'step', 'collect', 'record_physical_scene', 'warmup'}
        for file in root.glob('*.py'):
            if file.name.startswith('test_'): continue
            tree = ast.parse(file.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = getattr(node.func, 'attr', getattr(node.func, 'id', None))
                    self.assertNotIn(name, forbidden, (file.name, name))

    def test_actual_native_support_and_no_f3_witness(self):
        d = W / 'Robotwin2/datasets/f2_endpoint_constraint_remaining_v1_1'
        capture = json.loads((d / 'live_model_capture.json').read_text(encoding='utf-8'))
        export = json.loads((d / 'world_geometry.json').read_text(encoding='utf-8'))
        c = build_contract()
        witness = support_witness(export, capture['can_shapes'], c['beside_template_actor_pose'], capture['actual_base_world_pose'])
        self.assertTrue(witness['pass'])
        self.assertFalse(witness['physical_support_observed'])
        self.assertNotIn('hold', witness)
        class Fake:
            def __init__(self, names): self.names = names
            def get_obstacle_names(self): return self.names
        names = [s['name'] for s in export['shapes']]
        reduced = [n for n in names if n != witness['support_name']]
        checker = F2PairWorld(Fake(names), Fake(reduced), names=['fl_link7', 'attached_can'], witness=witness, buffer_factory=lambda x: None)
        self.assertEqual(checker.attached, 'attached_can')
        with self.assertRaises(ValueError):
            F2PairWorld(Fake(names), Fake([]), names=['fl_link7', 'attached_can'], witness=witness, buffer_factory=lambda x: None)
        fake_f3 = {'hold': {'frames': 250}, 'receipt_sha256': 'bad'}
        with self.assertRaises(ValueError):
            F2PairWorld(Fake(names), Fake(reduced), names=['fl_link7', 'attached_can'], witness=fake_f3, buffer_factory=lambda x: None)

    def test_runtime_initialization_failure_is_terminal(self):
        from . import runtime
        with tempfile.TemporaryDirectory(dir=W / 'Robotwin2/tmp', prefix='inward_cpu_') as tmp:
            out = Path(tmp) / 'job'
            with patch.object(runtime, 'build_contract', side_effect=ImportError('test native library unavailable')):
                r = runtime.run({'jobs': [{'output_namespace': str(out)}], 'manifest_sha256': 'cpu-test'})
            self.assertFalse(r['pass']); self.assertEqual(r['fresh_scene_attempts'], 0)
            self.assertEqual(r['ik_problem_attempts'], 0)
            self.assertEqual(r['physical_execution_count'], 0)
            self.assertEqual(r['error']['type'], 'ImportError')
            self.assertTrue((out / 'job_terminal.json').exists())

if __name__ == '__main__':
    unittest.main()
