"""Pure construction fixtures until real template completes; no qualification fabrication."""
import ast
from pathlib import Path
import unittest
from unittest.mock import patch
from .test_cpu import Tests as RootTests
from .test_accounting_integrity import *
from goal_pilot48_v1.runtime import issue_f4_b_root as issuer

class IssuerTests(unittest.TestCase):
    def test_missing_template_cannot_build_or_issue(self):
        job='p48_f4_b_root_cpu_missing'
        with patch.object(issuer,'evidence_bindings',side_effect=FileNotFoundError('template not complete')):
            with self.assertRaises(FileNotFoundError):issuer.build_manifest(job,dict(kind='RESERVE',job_id=job,reserved=issuer.CAPS,event_sha256='CPU_only'))
        self.assertFalse((issuer.ROOT/'jobs'/(job+'.json')).exists())
    def test_timing_is_bounded_from_real_history_not_A_qualification(self):
        timing=issuer.timeout_derivation()
        self.assertAlmostEqual(timing['historical_elapsed_seconds'],2167.0496196746826)
        self.assertEqual(timing['new_child_timeout_seconds'],5400)
        self.assertEqual(timing['new_lease_seconds'],5580)
        self.assertFalse(timing['A_physical_qualification_reused'])
    def test_builder_fields_and_current_hardened_sources_CPU_fixture(self):
        # Only evidence_bindings is mocked; no passing real template is created.
        parent=issuer.ROOT/'jobs/p48_f4_b_template_001.json'
        if not parent.exists():self.skipTest('template manifest not yet published')
        fields={'b_payload_sha256':'CPU_FIXTURE','b_scene_spec_sha256':'CPU_FIXTURE'}
        paths={'source_template_manifest':parent}
        job='p48_f4_b_root_cpu_fields';before=(issuer.ROOT/'budget_ledger.jsonl').read_bytes()
        with patch.object(issuer,'evidence_bindings',return_value=(fields,paths)):
            m=issuer.build_manifest(job,dict(kind='RESERVE',job_id=job,reserved=issuer.CAPS,event_sha256='CPU_fixture_no_reservation'))
        self.assertEqual(before,(issuer.ROOT/'budget_ledger.jsonl').read_bytes())
        self.assertEqual(m['jobs'][0]['resource_caps'],dict(solver_problems=460,fresh_scenes=11,action_scenes=7,collection_attempts=3))
        self.assertTrue(m['jobs'][0]['requires_live_meter']);self.assertEqual(Path(m['guard_script_path']).parent,issuer.ROOT/'runtime_v2')
        for name in ('accounting.py','test_accounting_integrity.py'):
            path=issuer.ROOT/'f4_b_root_runtime_v1'/name
            self.assertEqual(m['source_files'][str(path)],issuer.sha(path))
        self.assertFalse((issuer.ROOT/'jobs'/(job+'.json')).exists())
    def test_namespace_and_no_mutators(self):
        job='p48_f4_b_root_cpu_test';target=issuer.W/'Robotwin2/datasets'/(job+'_meter');exists=Path.exists
        with patch.object(Path,'exists',lambda p:p==target or exists(p)):
            with self.assertRaises(FileExistsError):issuer.assert_fresh(job)
        tree=ast.parse(Path(issuer.__file__).read_text(encoding='utf-8'))
        self.assertFalse({'reserve','write_new','Popen'}&{n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)})

if __name__=='__main__':unittest.main(verbosity=2)
