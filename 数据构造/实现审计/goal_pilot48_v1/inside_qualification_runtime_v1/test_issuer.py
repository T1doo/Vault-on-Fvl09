import unittest
from goal_pilot48_v1.runtime import issue_inside_qualification as issuer

class Tests(unittest.TestCase):
    def test_public_issuer_fail_closed_even_with_reservation(self):
        with self.assertRaises(PermissionError):issuer.build_manifest('p48_f2_inside_qualification_cpu',{'kind':'RESERVE','reserved':issuer.CAPS})
    def test_preview_no_issuance_no_reservation_no_ledger_write(self):
        ledger=issuer.ROOT/'budget_ledger.jsonl';before=ledger.read_bytes()
        result=issuer.build_preview('p48_f2_inside_qualification_cpu')
        self.assertEqual(before,ledger.read_bytes());self.assertNotIn('reserved',result);self.assertNotIn('reservation_event_sha256',result)
        self.assertEqual(result['issuance'],'CPU_ONLY_NONISSUED_PREVIEW');self.assertFalse(result['gpu_execution_authorized']);self.assertEqual(result['jobs'][0]['resource_caps']['solver_problems'],5)
        for flag in ('approved','physical_execution_authorized','pilot_input_authorized','collection_authorized'):
            self.assertIs(result[flag],False)
    def test_dependency_hash_conflict_rejected(self):
        p=str(issuer.PARENT)
        with self.assertRaises(ValueError):issuer.merge_checked({p:'bad'},{p:issuer.sha(p)})
