"""CPU-only issuer, inherited source hashes and actual resource-resolution chain."""
import ast
from pathlib import Path
import unittest
from unittest.mock import patch
from .test_cpu import Tests as BindingTests
from .test_terminal import Tests as TerminalTests
from goal_pilot48_v1.runtime_v3.test_replay_operator import Tests as ReplayTests
from goal_pilot48_v1.f4_b_acceptance_audit_v2.test_cpu import Tests as AcceptanceTests
from goal_pilot48_v1.runtime import issue_f4_b_motion as issuer

class IssuerTests(unittest.TestCase):
    def test_real_manifest_inputs_caps_v3_and_no_writes(self):
        job='p48_f4_b_motion_cpu_test';ledger=issuer.ROOT/'budget_ledger.jsonl';before=ledger.read_bytes()
        m=issuer.build_manifest(job,dict(kind='RESERVE',job_id=job,reserved=issuer.CAPS,event_sha256='CPU_only_no_reservation'))
        self.assertEqual(before,ledger.read_bytes());j=m['jobs'][0]
        self.assertEqual(j['resource_caps'],dict(solver_problems=0,fresh_scenes=3,action_scenes=3,collection_attempts=3))
        self.assertEqual(j['timeout_seconds'],3600);self.assertEqual(m['reserved']['gpu_lease_seconds'],3780)
        self.assertTrue(j['requires_live_meter']);self.assertEqual(Path(m['guard_script_path']).parent,issuer.ROOT/'runtime_v3')
        self.assertFalse(m['source_root_original_goal_pass']);self.assertTrue(m['current_recovery_pending_until_new_artifact_audit'])
        for folder in (issuer.ROOT/'runtime_v2',issuer.ROOT/'runtime_v3',issuer.ROOT/'f4_b_motion_runtime_v1',issuer.ROOT/'f4_b_motion_runtime_v2'):
            for p in folder.glob('*.py'):self.assertEqual(m['source_files'][str(p)],issuer.sha(p))
        for p in (issuer.ROOT/'f4_b_acceptance_audit_v1/action_resolution.py',issuer.ROOT/'f4_b_acceptance_audit_v1/audit.py',
                  issuer.ROOT/'f4_b_acceptance_audit_v1/current_recovery.py',issuer.ROOT/'f4_b_acceptance_audit_v2/audit.py',
                  issuer.ROOT/'runtime/reconcile_root_resolution.py'):
            self.assertEqual(m['source_files'][str(p)],issuer.sha(p))
        self.assertEqual(m['source_root_resource_acceptance_receipt_sha256'],'48b92d6753431b6ef59b96004a391c70c3b8dc9635e4d393484cde64da0d7daa')
        self.assertFalse((issuer.ROOT/'jobs'/(job+'.json')).exists())
    def test_missing_used_namespace_and_no_mutators(self):
        job='p48_f4_b_motion_cpu_test';target=issuer.W/'Robotwin2/datasets'/(job+'_meter');exists=Path.exists
        with patch.object(Path,'exists',lambda p:p==target or exists(p)):
            with self.assertRaises(FileExistsError):issuer.assert_fresh(job)
        tree=ast.parse(Path(issuer.__file__).read_text(encoding='utf-8'))
        self.assertFalse({'reserve','write_new','Popen'}&{n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)})
    def test_changed_inherited_v2_source_rejected_before_issuing(self):
        from goal_pilot48_v1.runtime_v3.migration import bindings
        p=issuer.ROOT/'runtime_v2/meter.py'
        with self.assertRaises(ValueError):bindings({'source_files':{str(p):'0'*64},'input_files':{}})

if __name__=='__main__':unittest.main(verbosity=2)
