"""Preflight covers runtime CPU tests plus issuance/accounting; no reservation."""
import ast
import copy
import tempfile
import unittest
from types import SimpleNamespace
import numpy as np
from .test_cpu import ContractTests, StateTests
from .contract import W, A
from .runner_bridge import reconcile_meter
from goal_pilot48_v1.runtime import issue_f2_inward as issuer
from goal_pilot48_v1.runtime.meter import Meter

def result():
    return {'ik_problem_attempts': 3, 'trajectory_queries': 4, 'fresh_scene_attempts': 1, 'accounting_complete': True,
            'physical_execution_count': 0, 'collection_calls': 0, 'new_raw_trajectories': 0, 'new_roots': 0}

def events():
    rows = [{'kind': 'CHARGE', 'resource': 'fresh_scenes', 'amount': 1, 'total': 1}]
    for i in range(7):
        rows.append({'kind': 'CHARGE', 'resource': 'solver_problems', 'amount': 1, 'total': i + 1,
                     'method': 'IKSolver.solve_single' if i < 3 else 'MotionGen.plan_single'})
    return rows

class IssuerTests(unittest.TestCase):
    def test_build_does_not_reserve_and_all_sources_are_bound(self):
        # Byte comparison of live ledger verifies that CPU construction did
        # not reserve, reconcile or alter active user-goal state.
        ledger = issuer.ROOT / 'budget_ledger.jsonl'
        before = ledger.read_bytes()
        job = 'p48_f2_issuer_cpu_test'
        m = issuer.build_manifest(job, {'kind': 'RESERVE', 'job_id': job, 'reserved': dict(issuer.CAPS), 'event_sha256': 'synthetic_cpu_only'})
        self.assertEqual(before, ledger.read_bytes())
        self.assertEqual(m['jobs'][0]['timeout_seconds'], 1800)
        self.assertEqual(m['reserved']['gpu_lease_seconds'], 1980)
        self.assertEqual(m['jobs'][0]['resource_caps'], {'solver_problems': 7, 'fresh_scenes': 1, 'action_scenes': 0, 'collection_attempts': 0})
        self.assertFalse(m['physical_execution_authorized'])
        self.assertEqual(m['allowed_physical_gpu_indices'], list(range(8)))
        for folder in (issuer.ROOT / 'f2_inward_runtime_v1', A / 'f2_f3_model_bridge_v1_1'):
            for p in folder.glob('*.py'):
                self.assertEqual(m['source_files'][str(p)], issuer.sha(p))
        for p in (A / 'f2_inward_binding_and_route_state_v1.py', A / 'f2_controlled_insertion_route_gate_run1_runtime_v1/job_runner.py', A / 'support_pair_collision_v1/policy.py'):
            self.assertIn(str(p), m['source_files'])
        for p in (A / 'F2_INWARD_NEW_BINDING_ROUTE_STATE_CONTRACT_V1_20260906.json', issuer.ROOT / 'USER_GOAL_SOURCE.md'):
            self.assertIn(str(p), m['input_files'])

    def test_wrong_reservation_rejected(self):
        with self.assertRaises(ValueError):
            issuer.build_manifest('p48_f2_cpu_bad', {'kind': 'RESERVE', 'job_id': 'p48_f2_cpu_bad', 'reserved': {}})

    def test_meter_3_plus_4_and_unknown_negative(self):
        self.assertTrue(reconcile_meter(result(), events())['pass'])
        broken = result(); broken['trajectory_queries'] = None
        self.assertFalse(reconcile_meter(broken, events())['pass'])
        rows = events(); rows[-1]['method'] = 'IKSolver.solve_single'
        self.assertFalse(reconcile_meter(result(), rows)['pass'])
        rows = events(); rows.pop()
        self.assertFalse(reconcile_meter(result(), rows)['pass'])

    def test_charge_counter_or_action_mismatch_rejected(self):
        rows = events(); rows[-1]['total'] = 100
        with self.assertRaises(ValueError): reconcile_meter(result(), rows)
        rows = events(); rows.append({'kind': 'CHARGE', 'resource': 'action_scenes', 'amount': 1, 'total': 1})
        self.assertFalse(reconcile_meter(result(), rows)['pass'])

    def test_real_meter_nested_solver_does_not_double_charge(self):
        with tempfile.TemporaryDirectory(dir=W / 'Robotwin2/tmp', prefix='f2_meter_cpu_') as tmp:
            meter = Meter(tmp, {'solver_problems': 7, 'fresh_scenes': 1, 'action_scenes': 0, 'collection_attempts': 0})
            goal = SimpleNamespace(position=np.zeros((1, 3)))
            ik = meter.solver(lambda goal_pose: True, kind='IKSolver.solve_single')
            plan = meter.solver(lambda goal_pose: ik(goal_pose), kind='MotionGen.plan_single')
            for _ in range(3): ik(goal)
            for _ in range(4): plan(goal)
            self.assertEqual(meter.counts['solver_problems'], 7)
            with self.assertRaises(RuntimeError): ik(goal)
            meter.close()

    def test_generic_runner_fresh_scene_field_and_f2_bridge_dispatch(self):
        text = (issuer.ROOT / 'runtime/job_runner.py').read_text(encoding='utf-8')
        self.assertIn("result.get('scene_attempts',result.get('fresh_scene_attempts'))", text)
        self.assertIn("result.get('accounting_complete')", text)
        tree = ast.parse((issuer.ROOT / 'f2_inward_runtime_v1/runner_bridge.py').read_text(encoding='utf-8'))
        self.assertTrue(any(isinstance(n, ast.FunctionDef) and n.name == 'reconcile_meter' for n in ast.walk(tree)))

if __name__ == '__main__':
    unittest.main()
