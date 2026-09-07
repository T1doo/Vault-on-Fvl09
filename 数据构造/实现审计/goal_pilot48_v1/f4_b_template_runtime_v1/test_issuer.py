"""Template issuer CPU checks; actual source qualification is read-only."""
import ast
from pathlib import Path
import unittest
from unittest.mock import patch
from .test_cpu import Tests as TemplateTests
from goal_pilot48_v1.runtime import issue_f4_b_template as issuer
from goal_pilot48_v1.runtime_v2.test_cpu import Tests as DispatcherTests

class IssuerTests(unittest.TestCase):
    def test_missing_source_never_builds_passing_manifest(self):
        job='p48_f4_b_template_cpu_missing'
        with patch.object(issuer,'evidence_bindings',side_effect=FileNotFoundError('not completed')):
            with self.assertRaises(FileNotFoundError):issuer.build_manifest(job,dict(kind='RESERVE',job_id=job,reserved=issuer.CAPS,event_sha256='CPU_fixture'))
        self.assertFalse((issuer.ROOT/'jobs'/(job+'.json')).exists())
    def test_real_isolation_source_and_runtime_v2_manifest(self):
        source=issuer.W/'Robotwin2/datasets'/issuer.SOURCE_JOB/'goal_terminal.json'
        if not source.exists():self.skipTest('actual isolation not completed; no fixture qualification substituted')
        fields,paths=issuer.evidence_bindings()
        evidence=issuer.read(paths['source_isolation_evidence'])
        self.assertEqual(evidence['status'],'B_ALL_FIVE_ISOLATION_PASS')
        ledger=issuer.ROOT/'budget_ledger.jsonl';before=ledger.read_bytes();job='p48_f4_b_template_cpu_test'
        m=issuer.build_manifest(job,dict(kind='RESERVE',job_id=job,reserved=issuer.CAPS,event_sha256='CPU_fixture_not_reserved'))
        self.assertEqual(before,ledger.read_bytes())
        self.assertEqual(m['jobs'][0]['resource_caps'],dict(solver_problems=480,fresh_scenes=3,action_scenes=3,collection_attempts=0))
        self.assertFalse(m['jobs'][0]['requires_live_meter'])
        self.assertEqual(m['jobs'][0]['timeout_seconds'],3600);self.assertEqual(m['reserved']['gpu_lease_seconds'],3780)
        for role in ('guard','runner'):
            self.assertEqual(Path(m[role+'_script_path']).parent,issuer.ROOT/'runtime_v2')
        parent=issuer.read(paths['source_isolation_manifest'])
        for field in ('source_files','input_files'):
            for path,h in parent[field].items():self.assertEqual(m[field][path],h)
        self.assertFalse((issuer.ROOT/'jobs'/(job+'.json')).exists())
    def test_no_mutators_or_used_namespace(self):
        tree=ast.parse(Path(issuer.__file__).read_text(encoding='utf-8'))
        self.assertFalse({'reserve','write_new','Popen'}&{n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)})
        job='p48_f4_b_template_cpu_test';target=issuer.ROOT/'jobs'/(job+'.json');exists=Path.exists
        with patch.object(Path,'exists',lambda p:p==target or exists(p)):
            with self.assertRaises(FileExistsError):issuer.assert_fresh(job)

if __name__=='__main__':unittest.main(verbosity=2)
