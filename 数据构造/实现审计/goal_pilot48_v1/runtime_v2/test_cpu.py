"""Dispatcher end-to-end CPU fixtures; install never imports GPU classes."""
import json
import ast
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from . import job_runner,budget,manifest_contract
from .meter import Meter
from ..collection_meter_review_v1.test_cpu import Adapter,Context,CURRENT

class FakeMeter(Meter):
    instances=[]
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.instances.append(self)
    def install(self):return self

class Tests(unittest.TestCase):
    def dispatch(self,directory,run,*,live=True,family='F4',collection=3):
        out=Path(directory)/'run'
        job=dict(job_id='CPU_FIXTURE',family=family,kind='F3_MICRO' if not live else 'ROOT',requires_live_meter=live,
            output_namespace=str(out),runtime_module='CPU_RUNTIME_NOT_IMPORTABLE',
            resource_caps=dict(solver_problems=0,fresh_scenes=0,action_scenes=0,collection_attempts=collection))
        manifest=dict(manifest_sha256='CPU_FIXTURE',implementation_source_sha256=CURRENT,jobs=[job])
        with patch.object(job_runner,'load_manifest',return_value=manifest),patch.object(job_runner,'Meter',FakeMeter),patch.object(job_runner.importlib,'import_module',return_value=SimpleNamespace(run=run)):
            code=job_runner.main(['--manifest',str(out/'not_published.json')])
        return code,json.loads((out/'goal_terminal.json').read_text(encoding='utf-8')),FakeMeter.instances[-1]
    def test_root_three_requests_and_factory_failure_both_charged(self):
        for fail in (False,True):
            with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
                adapter=Adapter(fail_factory=fail);adapter.family='F4'
                def run(manifest,*,meter):
                    with meter.instrument_adapter(adapter,source_profile_sha256=CURRENT):
                        for pid in ('F4-ABC','F4-ACB','F4-BAC'):
                            try:
                                with adapter.scene({'slot_id':'CPU_ROOT','family':'F4'},phase='strict_prefix_branch:'+pid,program={'program_id':pid}):pass
                            except ValueError:break
                    return dict(scene_attempts=0,collection_attempts=1 if fail else 3,accounting_complete=True,**{'pass':True})
                code,result,meter=self.dispatch(directory,run)
                self.assertEqual(code,0);self.assertEqual(result['resource_counts']['collection_attempts'],1 if fail else 3)
                self.assertTrue(meter.closed);self.assertNotIn('scene',vars(adapter))
                with self.assertRaises(RuntimeError):meter.charge('collection_attempts')
    def test_two_families_factory_restoration_and_profile_fail_closed(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            meter=Meter(Path(directory)/'meter',dict(solver_problems=0,fresh_scenes=0,action_scenes=0,collection_attempts=2))
            meter.configure_collection_contract({'implementation_source_sha256':CURRENT,'jobs':[{'family':'F4','requires_live_meter':True,'resource_caps':meter.caps}]})
            adapters=[]
            def original(cell,out):
                a=Adapter();a.family=cell['family'];adapters.append(a);return a
            pipeline=SimpleNamespace(make_adapter=original)
            with meter.instrument_collector_factory(pipeline,profile_for_cell=lambda cell:CURRENT):
                for family in ('F2','F4'):
                    a=pipeline.make_adapter({'family':family},None);pid=family+'-CPU'
                    with a.scene({'family':family,'slot_id':'CPU_'+family},phase='strict_prefix_branch:'+pid,program={'program_id':pid}):pass
            self.assertIs(pipeline.make_adapter,original)
            self.assertTrue(all('scene' not in vars(a) for a in adapters));self.assertEqual(meter.counts['collection_attempts'],2)
            meter.close()
            with self.assertRaises(RuntimeError):
                with meter.instrument_adapter(adapters[0],source_profile_sha256=CURRENT):pass
    def test_legacy_F3_not_passed_live_meter(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            def run(manifest):return dict(scene_attempts=0,trajectory_queries=0,accounting_complete=True,**{'pass':True})
            code,result,meter=self.dispatch(directory,run,live=False,family='F3',collection=0)
            self.assertEqual(code,0);self.assertTrue(result['pass']);self.assertTrue(meter.closed)
    def test_collection_runtime_without_hook_is_rejected(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            def run(manifest,*,meter):return dict(scene_attempts=0,collection_attempts=0,accounting_complete=True,**{'pass':True})
            code,result,_=self.dispatch(directory,run)
            self.assertEqual(code,1);self.assertFalse(result['accounting_complete'])
    def test_new_F1_jobs_explicitly_rejected(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            with self.assertRaises(ValueError):self.dispatch(directory,lambda *a,**kw:None,family='F1')
    def test_same_goal_budget_and_new_guard_paths(self):
        root=Path(__file__).resolve().parents[1]
        self.assertEqual(budget.ROOT,root);self.assertEqual(manifest_contract.ROOT,root)
        self.assertEqual(manifest_contract.RUNTIME,root/'runtime_v2')
        old=(root/'runtime/budget.py').read_bytes();new=(root/'runtime_v2/budget.py').read_bytes()
        self.assertEqual(old,new)
        # Same authoritative ledger/lock, never a new budget under runtime_v2.
        self.assertFalse((root/'runtime_v2/budget_ledger.jsonl').exists())
        self.assertFalse((root/'runtime_v2/budget.lock').exists())
    def test_guard_safety_functions_unchanged_from_frozen_runtime(self):
        root=Path(__file__).resolve().parents[1]
        def functions(path):
            tree=ast.parse(path.read_text(encoding='utf-8'))
            return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
        before=functions(root/'runtime/guarded_launcher.py');after=functions(root/'runtime_v2/guarded_launcher.py')
        self.assertEqual(set(before),set(after))
        for name in before:
            if name not in ('main','_write_new'):self.assertEqual(before[name],after[name],name)
        # Main changes only namespace-qualified imports, not Guard logic.
        old=ast.parse((root/'runtime/guarded_launcher.py').read_text(encoding='utf-8'))
        new=ast.parse((root/'runtime_v2/guarded_launcher.py').read_text(encoding='utf-8'))
        oldmain=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        newmain=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        for node in ast.walk(newmain):
            if isinstance(node,ast.ImportFrom) and node.module.startswith('goal_pilot48_v1.runtime_v2.'):
                node.module=node.module.rsplit('.',1)[-1]
        self.assertEqual(ast.dump(oldmain,include_attributes=False),ast.dump(newmain,include_attributes=False))
    def test_manifest_keeps_all_original_checks_with_only_namespace_and_F1_gate(self):
        root=Path(__file__).resolve().parents[1]
        old=(root/'runtime/manifest_contract.py').read_text(encoding='utf-8')
        new=(root/'runtime_v2/manifest_contract.py').read_text(encoding='utf-8')
        # Safety-significant checks must remain verbatim; added gates may only
        # restrict F1/new unmetered collection, never loosen old permissions.
        for phrase in ('Goal authority/source','reservation binding','job reservation no longer active','Guard parent','Guard environment','lease not held','task cleanup not verified','Goal accounting incomplete','Goal cap exceeded','exit mismatch'):
            self.assertIn(phrase,old);self.assertIn(phrase,new)

if __name__=='__main__':unittest.main(verbosity=2)
