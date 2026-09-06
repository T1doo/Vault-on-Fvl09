"""Issuer and real generic preflight CPU coverage; never reserve/publish a job."""
import ast
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from .test_cpu import Tests as RuntimeTests
from goal_pilot48_v1.runtime import issue_f4_b_stage_a as issuer

def stub(job='p48_f4_b_stage_a_cpu_test'):
    return dict(kind='RESERVE',job_id=job,reserved=dict(issuer.CAPS),event_sha256='synthetic_CPU_only_no_reservation')

class IssuerTests(unittest.TestCase):
    def test_build_manifest_has_complete_fixed_binding_and_does_not_write_ledger(self):
        ledger=issuer.ROOT/'budget_ledger.jsonl';before=ledger.read_bytes()
        m=issuer.build_manifest('p48_f4_b_stage_a_cpu_test',stub())
        self.assertEqual(before,ledger.read_bytes())
        job=m['jobs'][0]
        self.assertEqual(m['reserved'],issuer.CAPS);self.assertEqual(job['timeout_seconds'],1800)
        self.assertEqual(m['reserved']['gpu_lease_seconds'],1980)
        self.assertFalse(m['physical_execution_authorized']);self.assertFalse(m['pilot_input_authorized'])
        self.assertEqual(job['resource_caps'],dict(solver_problems=156,fresh_scenes=1,action_scenes=0,collection_attempts=0))
        self.assertEqual(job['runtime_module'],'goal_pilot48_v1.f4_b_runtime_v2.runtime')
        self.assertEqual(m['B_lineage']['scene_seed'],2026090604)
        self.assertFalse(m['B_lineage']['A_success_reused_as_B_qualification'])
        self.assertEqual(m['allowed_physical_gpu_indices'],list(range(8)))
        for folder in (issuer.ROOT/'f4_b_runtime_v1',issuer.ROOT/'f4_b_runtime_v2',issuer.ROOT/'runtime'):
            for path in folder.glob('*.py'):self.assertEqual(m['source_files'][str(path)],issuer.sha(path))
        for path in (issuer.PARENT,issuer.A/'F4_PILOT_B_NEW_LAYOUT_CPU_PROPOSAL_V1_20260906.json',
                     issuer.P/'assets/objects/008_tray/collision/base0.glb',issuer.ROOT/'USER_GOAL_SOURCE.md'):
            self.assertEqual(m['input_files'][str(path)],issuer.sha(path))
        self.assertFalse((issuer.ROOT/'jobs/p48_f4_b_stage_a_cpu_test.json').exists())

    def test_namespace_and_wrong_reservation_rejected(self):
        with self.assertRaises(ValueError):issuer.build_manifest('p48_f3_bad',stub())
        bad=stub();bad['reserved']['solver_problems']=155
        with self.assertRaises(ValueError):issuer.build_manifest('p48_f4_b_stage_a_cpu_test',bad)
        existing=issuer.W/'Robotwin2/datasets/p48_f4_b_stage_a_cpu_test_meter'
        original=Path.exists
        with patch.object(Path,'exists',lambda p:p==existing or original(p)):
            with self.assertRaises(FileExistsError):issuer.assert_fresh('p48_f4_b_stage_a_cpu_test')

    def test_changed_parent_hash_never_reblessed(self):
        with tempfile.TemporaryDirectory(dir=issuer.W/'Robotwin2/tmp') as directory:
            path=Path(directory)/'cpu-fixture.json'
            from realization_utf8_io_v1 import write_new
            write_new(path,{'fixture':True})
            with self.assertRaises(ValueError):issuer._inherit({},path,'0'*64)
        tree=ast.parse(Path(issuer.__file__).read_text(encoding='utf-8'))
        forbidden={'reserve','write_new','exec_command','subprocess','Popen'}
        calls=[n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        self.assertFalse(forbidden.intersection(calls))

    def test_real_generic_preflight_routes_tests_only_no_live_reservation(self):
        path=issuer.ROOT/'runtime/job_runner.py'
        runtime_dir=str(path.parent)
        oldpath=list(sys.path);sys.path.insert(0,runtime_dir)
        try:
            spec=importlib.util.spec_from_file_location('f4_cpu_generic_preflight',path)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            # Only parser/dispatch is under test here. Authority validation is
            # mocked because no real reservation may be created by this test.
            fake={'jobs':[{'job_id':'p48_f4_b_stage_a_cpu_test','test_module':'goal_pilot48_v1.f4_b_runtime_v2.test_cpu'}]}
            with patch.object(module,'load_manifest',return_value=fake),patch.object(module.Meter,'install',side_effect=AssertionError('GPU meter must not install in CPU preflight')):
                self.assertEqual(module.main(['--manifest',str(issuer.ROOT/'jobs/CPU_NOT_PUBLISHED.json'),'--preflight-only']),0)
        finally:sys.path[:]=oldpath

if __name__=='__main__':unittest.main(verbosity=2)
