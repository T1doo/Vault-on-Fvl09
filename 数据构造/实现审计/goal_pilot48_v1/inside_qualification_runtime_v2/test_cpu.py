from unittest.mock import patch
import unittest
from goal_pilot48_v1.inside_qualification_runtime_v1 import test_cpu as fixtures
from . import runtime,runner_bridge

class WrapperTests(fixtures.Tests):
    def case(self,failure=None):
        with patch.object(fixtures,'runner_bridge',runner_bridge),patch.object(runtime,'inside_run',side_effect=lambda *a,**k:fixtures.runtime.inside_run(*a,**k)):
            return super().case(failure)
    @classmethod
    def setUpClass(cls):
        super().setUpClass();cls.spec=runtime.build_spec()

class IssuerTests(unittest.TestCase):
    def test_pure_approved_builder_keeps_parent_unchanged(self):
        from goal_pilot48_v1.runtime import issue_inside_supported as issuer
        ledger=issuer.ROOT/'budget_ledger.jsonl';before=ledger.read_bytes();job='p48_f2_inside_qualification_supported_cpu'
        r=issuer.build_manifest(job,{'kind':'RESERVE','job_id':job,'reserved':issuer.CAPS,'event_sha256':'CPU-reservation-fixture-not-written'})
        self.assertEqual(before,ledger.read_bytes());self.assertEqual(r['issuance'],'ISSUED_UNDER_USER_GOAL');self.assertEqual(r['reserved']['solver_problems'],5)
        self.assertEqual(r['contact_design_approval']['approval_sha256'],issuer.APPROVAL_SHA)
        for flag in ('approved','physical_execution_authorized','gpu_execution_authorized'):
            self.assertIs(r[flag],True)
        self.assertIs(r['collection_authorized'],False)
        self.assertIs(r['physical_Gates_changed'],True)
        self.assertIs(r['physical_numeric_thresholds_changed'],False)
        self.assertIn('/inside_qualification_runtime_v2/',r['jobs'][0]['runtime_file'])
    def test_missing_approval_or_wrong_reservation_rejected(self):
        from goal_pilot48_v1.runtime import issue_inside_supported as issuer
        with self.assertRaises(ValueError):issuer.build_manifest('p48_f2_inside_qualification_cpu',{})
        with patch.object(issuer,'verify_approval',side_effect=ValueError('missing explicit approval')):
            with self.assertRaises(ValueError):issuer.build_manifest('p48_f2_inside_qualification_cpu',{})
