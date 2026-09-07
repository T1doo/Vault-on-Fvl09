from unittest.mock import patch
import unittest
from goal_pilot48_v1.inside_qualification_runtime_v1 import test_cpu as fixtures
from . import runtime,runner_bridge

class WrapperTests(fixtures.Tests):
    @classmethod
    def setUpClass(cls):super().setUpClass();cls.spec=runtime.build_spec()
    def case(self,failure=None):
        with patch.object(fixtures,'runner_bridge',runner_bridge),patch.object(runtime,'inside_run',side_effect=lambda *a,**k:fixtures.runtime.inside_run(*a,**k)):return super().case(failure)

class IssuerTests(unittest.TestCase):
    def test_pure_new_parent_bound_issuer_no_budget_write(self):
        from goal_pilot48_v1.runtime import issue_inside_carry as issuer
        before=(issuer.ROOT/'budget_ledger.jsonl').read_bytes();job='p48_f2_inside_carry_revision1_cpu'
        r=issuer.build_manifest(job,{'kind':'RESERVE','job_id':job,'reserved':issuer.CAPS,'event_sha256':'CPU-not-written'})
        self.assertEqual(before,(issuer.ROOT/'budget_ledger.jsonl').read_bytes());self.assertEqual(r['parent_job_id'],'p48_f2_inside_qualification_001')
        self.assertTrue(r['approved']);self.assertTrue(r['physical_execution_authorized']);self.assertEqual(r['reserved']['solver_problems'],5)
        self.assertFalse(r['final_inside_target_changed']);self.assertFalse(r['other_four_targets_changed']);self.assertIn('/inside_qualification_runtime_v3/',r['jobs'][0]['runtime_file'])
    def test_old_namespace_wrong_budget_rejected(self):
        from goal_pilot48_v1.runtime import issue_inside_carry as issuer
        with self.assertRaises(ValueError):issuer.build_manifest('p48_f2_inside_qualification_001',{})
        with self.assertRaises(ValueError):issuer.build_manifest('p48_f2_inside_carry_revision1_cpu',{})
