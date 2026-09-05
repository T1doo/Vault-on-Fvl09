import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from cmf_downstream_cpu.collector import IsolatedTwoPhaseRootOrchestrator
from cmf_downstream_cpu.collector_publication import audit_completed_root,register_completed_root
from controlled_multi_future.families import F1ObjectSelection

P=Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin/tests/controlled_multi_future/test_root_orchestrator_v1_2.py')
s=importlib.util.spec_from_file_location('sealed_collector_fixture',P);fixtures=importlib.util.module_from_spec(s);s.loader.exec_module(fixtures)

class CollectorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp');self.output=Path(self.tmp.name)/'root'
    def tearDown(self):self.tmp.cleanup()
    def run_collector(self,adapter=None):
        adapter=adapter or fixtures.StrictPrefixSyntheticAdapter()
        programs=F1ObjectSelection().checked_provisional_programs()
        result=IsolatedTwoPhaseRootOrchestrator(adapter).run_nonformal_root(output_dir=self.output,
            planned_root_slot_spec={'slot_id':'cpu-root-17','family':'F1','seed':17,'origin':'synthetic_cpu_test'},
            realization_spec_by_program={p['program_id']:{'realization':'r_pc','formal_data':False,'stage0_data':False} for p in programs})
        return result
    def test_actual_collector_immediate_suffix_divergence(self):
        class Immediate(fixtures.StrictPrefixSyntheticAdapter):
            def execute_frozen_suffix_spec(self,scene,program,execution_spec,replay,realization):
                r=super().execute_frozen_suffix_spec(scene,program,execution_spec,replay,realization)
                r['streams']['controller_effective_setpoint'][2,0]={'F1-red':1.,'F1-green':2.,'F1-blue':3.}[program['program_id']]
                r['streams']['requested_command']=r['streams']['controller_effective_setpoint'].copy()
                return r
        root=self.run_collector(Immediate());self.assertEqual(root['status'],'accepted');self.assertEqual(root['root_finalization']['computed_first_post_prefix_divergence_step'],2)
    def test_actual_incomplete_branch_never_registered(self):
        adapter=fixtures.StrictPrefixSyntheticAdapter();adapter.verifier_error_program='F1-red'
        root=self.run_collector(adapter);self.assertNotEqual(root['status'],'accepted');self.assertFalse((self.output/'publication_index.json').exists())
    def test_actual_collector_delayed_divergence_publishes_matching_final_receipts(self):
        root=self.run_collector();self.assertEqual(root['status'],'accepted',root.get('error'))
        self.assertEqual(root['root_finalization']['computed_first_post_prefix_divergence_step'],3)
        for b in root['branch_receipts']:
            directory=self.output/'branches'/b['program_id']
            provisional=json.loads((directory/'receipt.provisional.json').read_text())
            final=json.loads((directory/'receipt.json').read_text())
            self.assertEqual(provisional['executed_prefix']['first_post_prefix_divergence_step'],2)
            self.assertEqual(final,b);self.assertEqual(final['executed_prefix']['canonical_prefix_end_step'],2)
        self.assertTrue((self.output/'publication_index.json').is_file())
        audit_completed_root(self.output)
        before=(self.output/'publication_index.json').read_bytes();register_completed_root(self.output)
        self.assertEqual(before,(self.output/'publication_index.json').read_bytes())
    def test_actual_finalization_interruption_cannot_register(self):
        import cmf_downstream_cpu.collector as collector
        real=collector.publish_final_branch;calls=[0]
        def fail(directory,branch):
            calls[0]+=1
            if calls[0]==2:raise OSError('injected final branch publication interruption')
            return real(directory,branch)
        with patch.object(collector,'publish_final_branch',side_effect=fail):root=self.run_collector()
        self.assertNotEqual(root['status'],'accepted');self.assertFalse((self.output/'publication_index.json').exists())
    def test_actual_disk_branch_mismatch_rejected(self):
        self.run_collector();p=next((self.output/'branches').glob('*/receipt.json'));d=json.loads(p.read_text());d['executed_prefix']['first_post_prefix_divergence_step']=2;p.write_text(json.dumps(d))
        with self.assertRaises(ValueError):audit_completed_root(self.output)

if __name__=='__main__':unittest.main()
