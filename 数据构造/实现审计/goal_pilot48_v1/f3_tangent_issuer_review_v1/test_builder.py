"""In-memory reservation only: never reserve/publish or launch a GPU."""
import ast,copy,inspect,unittest
from pathlib import Path
from unittest.mock import patch
from goal_pilot48_v1.runtime import issue_tangent_micro as issuer

class Tests(unittest.TestCase):
    def reservation(self,job='p48_f3_tangent_micro_cpu_builder_probe'):
        return dict(kind='RESERVE',job_id=job,reserved=dict(issuer.CAPS),event_sha256='0'*64)
    def test_real_evidence_build_is_pure_and_keeps_every_parent_dependency(self):
        job='p48_f3_tangent_micro_cpu_builder_probe';statepaths=[issuer.ROOT/n for n in ('STATE.json','budget_ledger.jsonl','attempts.jsonl')]
        before={str(p):issuer.sha(p) for p in statepaths};m=issuer.build_manifest(job,self.reservation())
        self.assertEqual(before,{str(p):issuer.sha(p) for p in statepaths});self.assertFalse((issuer.ROOT/'jobs'/(job+'.json')).exists())
        parent=issuer.read(issuer.ROOT/'jobs/p48_f3_micro_006.json')
        for field in ('source_files','input_files'):
            for p,h in parent[field].items():self.assertEqual(m[field][p],h)
        self.assertEqual(m['jobs'][0]['test_module'],'goal_pilot48_v1.f3_runtime_v5.test_all')
        self.assertEqual(m['jobs'][0]['kind'],'F3_MICRO')
        self.assertEqual(m['jobs'][0]['timeout_seconds'],900);self.assertEqual(m['reserved'],issuer.CAPS)
        self.assertEqual(m['recipe_spec_path'],parent['recipe_spec_path']);self.assertEqual(m['route_spec_path'],parent['route_spec_path'])
        self.assertEqual(m['allowed_physical_gpu_indices'],list(range(8)));self.assertEqual(m['high_level_start_state_check_cap'],6)
        self.assertEqual(m['current_cpu_audit_receipt_sha256'],issuer.EXPECTED_CPU_RECEIPT)
    def test_missing_or_wrong_budget_rejected_before_dependencies(self):
        with patch.object(issuer,'prerequisites',side_effect=AssertionError('must reject first')):
            for reservation in ({},dict(self.reservation(),reserved={})): 
                with self.assertRaises(ValueError):issuer.build_manifest('p48_f3_tangent_micro_cpu_builder_probe',reservation)
    def test_old_job_namespace_rejected(self):
        with self.assertRaises(ValueError):issuer.build_manifest('p48_f3_micro_006',self.reservation())
    def test_no_mutator_calls_in_pure_builder(self):
        tree=ast.parse(inspect.getsource(issuer))
        called={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
        self.assertFalse(called & {'reserve','atomic','write_new','Popen','exec_command'})
    def test_current_CPU_hash_mismatch_rejected(self):
        real_read=issuer.read
        def read(p):
            d=real_read(p)
            if str(p).endswith('CPU_AUDIT_V1_1.json'):d['receipt_sha256']='f'*64
            return d
        with patch.object(issuer,'read',side_effect=read):
            with self.assertRaisesRegex(ValueError,'self-hash changed'):issuer.prerequisites()
if __name__=='__main__':unittest.main()
