import unittest
from .test_cpu import RouteTests,StateTests
from goal_pilot48_v1.runtime import issue_f2_u_route as issuer

class IssuerTests(unittest.TestCase):
    def test_actual_build_no_ledger_change(self):
        ledger=issuer.ROOT/'budget_ledger.jsonl';before=ledger.read_bytes();name='p48_f2_u_route_cpu_preflight'
        m=issuer.build_manifest(name,{'kind':'RESERVE','job_id':name,'reserved':dict(issuer.CAPS),'event_sha256':'synthetic_cpu_only'})
        self.assertEqual(before,ledger.read_bytes())
        p=issuer.checked(issuer.PARENT,'manifest_sha256')
        self.assertEqual(m['new_layout_lineage'],p['new_layout_lineage'])
        self.assertEqual(m['reserved'],issuer.CAPS)
        self.assertEqual(m['jobs'][0]['timeout_seconds'],1800)
        self.assertEqual(m['endpoint_route_revision'],1)
        self.assertEqual(m['layout_revision_preserved'],1)
        self.assertEqual(m['endpoint_route_lineage']['fresh_IK_goals'],['C','U_new','D_new'])
        self.assertFalse(m['endpoint_route_lineage']['reuse_D_to_skip_fresh_check'])
        self.assertEqual(m['endpoint_route_lineage']['parent_D_full_valid_solutions'],4)
        self.assertEqual(m['jobs'][0]['runtime_module'],'goal_pilot48_v1.f2_inward_runtime_v3.runner_bridge')
        self.assertEqual(m['runner_script_path'],p['runner_script_path'])
        self.assertEqual(m['guard_script_sha256'],p['guard_script_sha256'])
    def test_dependency_conflict_and_changed_bytes_rejected(self):
        path=str(issuer.PARENT);good=issuer.sha(path)
        with self.assertRaisesRegex(ValueError,'conflict'):issuer.merge_verified({path:good},{path:'bad'})
        with self.assertRaisesRegex(ValueError,'parent dependency changed'):issuer.merge_verified({path:'bad'},{})
        with self.assertRaisesRegex(ValueError,'addition dependency changed'):issuer.merge_verified({},{path:'bad'})
    def test_wrong_reservation_rejected_before_issuance(self):
        with self.assertRaises(ValueError):issuer.build_manifest('p48_f2_u_route_bad',{'kind':'RESERVE','job_id':'p48_f2_u_route_bad','reserved':{}})

if __name__=='__main__':unittest.main()
