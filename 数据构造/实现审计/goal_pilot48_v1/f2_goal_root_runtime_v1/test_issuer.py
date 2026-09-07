import unittest
from unittest.mock import patch
from .test_cpu import PrefixTests
from .test_lifecycle import LifecycleTests
from goal_pilot48_v1.runtime import issue_f2_prefix as issuer

class IssuerTests(unittest.TestCase):
    def test_real_build_no_reserve_and_live_meter_bound(self):
        ledger=issuer.ROOT/'budget_ledger.jsonl';before=ledger.read_bytes();name='p48_f2_prefix_cpu_preview'
        m=issuer.build_manifest(name,dict(kind='RESERVE',job_id=name,reserved=dict(issuer.CAPS),event_sha256='CPU-not-reservation'))
        self.assertEqual(before,ledger.read_bytes());self.assertEqual(m['reserved'],issuer.CAPS)
        self.assertTrue(m['jobs'][0]['requires_live_meter']);self.assertIn('/runtime_v2/',m['runner_script_path'])
        self.assertEqual(m['jobs'][0]['runtime_module'],'goal_pilot48_v1.f2_goal_root_runtime_v1.runner_bridge')
        self.assertFalse(m['whole_root_execution_authorized']);self.assertFalse(m['old_inside_success_inherited'])
        self.assertEqual(m['jobs'][0]['resource_caps']['collection_attempts'],0)
    def test_dependency_conflict_rejected(self):
        p=str(issuer.PARENT)
        with self.assertRaises(ValueError):issuer.merge({p:issuer.sha(p)},{p:'changed'})
    def test_used_namespace_rejected_before_dependency_read(self):
        name='p48_f2_prefix_cpu_used'
        with patch.object(issuer.Path,'exists',return_value=True),patch.object(issuer,'checked') as read:
            with self.assertRaises(FileExistsError):issuer.build_manifest(name,dict(kind='RESERVE',job_id=name,reserved=dict(issuer.CAPS),event_sha256='CPU'))
            read.assert_not_called()

if __name__=='__main__':unittest.main()
