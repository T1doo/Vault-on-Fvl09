"""Original orchestrator CPU fixture; not real F4 qualification/collection."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from ..runtime_v2.meter import Meter
from .entry import RootWriter,orchestrator,disk_finalizer,P
from . import runtime as r
from .accounting import count_queries

class Tests(unittest.TestCase):
    def test_native_batch_N_and_frozen_replay_not_new_calls(self):
        replay=SimpleNamespace(planner_query_count=0,planner_queries=[{'query_id':13,'replayed_from_frozen_suffix_artifact':True}])
        self.assertEqual(count_queries(replay)['solver_problems'],0)
        actual=SimpleNamespace(planner_query_count=2,planner_queries=[{'query_id':1,'query_type':'batched_grasp_target_selection','batch_size':10,'ordered_goal_poses':[[0]*7]*10},{'query_id':2}])
        self.assertEqual(count_queries(actual)['solver_problems'],11)
        actual.planner_query_count=3
        with self.assertRaises(ValueError):count_queries(actual)
    def test_intermediate_receipts_immutable_final_branch_matches_root(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            root=Path(directory);writer=RootWriter(root);path=root/'branches/F4-ABC/receipt.json'
            writer(path,{'program_id':'F4-ABC','first_post_prefix_divergence_step':10})
            writer(path,{'program_id':'F4-ABC','first_post_prefix_divergence_step':10,'status':'accepted'})
            self.assertFalse(path.exists())
            final={'program_id':'F4-ABC','first_post_prefix_divergence_step':12,'status':'accepted'}
            writer(root/'root_receipt.json',{'branch_receipts':[final]})
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')),final)
            self.assertEqual(len(list((path.parent/'receipt_history').glob('*.json'))),2)
            with self.assertRaises(FileExistsError):writer(root/'root_receipt.json',{'branch_receipts':[]})
    def test_real_original_orchestrator_entry_and_three_collection_requests(self):
        # Reuse the repository's existing F1-labelled synthetic adapter solely
        # to exercise the generic orchestrator IO/control flow. It is not a
        # newly dispatched F1 job and asserts no F4 scientific feasibility.
        path=P/'tests/controlled_multi_future/test_root_orchestrator_v1_2.py'
        spec=importlib.util.spec_from_file_location('root_CPU_existing_fixture',path)
        fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
        adapter=fixture.StrictPrefixSyntheticAdapter();adapter._sealed_implementation_source_sha256=r.SOURCE_SHA
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            out=Path(directory)/'root';meter=Meter(Path(directory)/'meter',r.CAPS)
            meter.configure_collection_contract({'implementation_source_sha256':r.SOURCE_SHA,'jobs':[{'family':'F4','requires_live_meter':True,'resource_caps':r.CAPS}]})
            executor,writer=orchestrator(adapter,out,implementation_version='CPU_SYNTHETIC_NO_F4_CLAIM')
            programs=adapter.build_programs(None)
            with meter.instrument_adapter(adapter,source_profile_sha256=r.SOURCE_SHA):
                result=executor.run_nonformal_root(output_dir=out,
                    planned_root_slot_spec={'slot_id':'CPU_synthetic_root','family':'F1','seed':17,'origin':'CPU_fixture'},
                    realization_spec_by_program={p['program_id']:{'realization':'r_pc','formal_data':False,'stage0_data':False} for p in programs})
            meter.close()
            self.assertEqual(result['status'],'accepted',result.get('error'))
            self.assertEqual(meter.counts['collection_attempts'],3)
            for branch in result['branch_receipts']:
                disk=json.loads((out/'branches'/branch['program_id']/'receipt.json').read_text(encoding='utf-8'))
                self.assertEqual(disk,branch)
            self.assertEqual(result['root_finalization']['computed_first_post_prefix_divergence_step'],3)
            self.assertEqual(len(list((out/'suffix_artifacts').glob('*/frozen_suffix_artifact.json'))),3)
            self.assertFalse(writer.pending)
    def test_disk_finalizer_not_replaced_by_status_boolean(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            result=disk_finalizer({'root_receipt':{'status':'accepted'},'development_root_pass':True},{},directory)
            self.assertFalse(result['accepted'])
    def test_no_real_template_evidence_means_no_root(self):
        class FakeMeter:
            closed=False;counts={k:0 for k in r.CAPS}
        with self.assertRaises(KeyError):r.run({'jobs':[{'resource_caps':r.CAPS,'requires_live_meter':True}]},meter=FakeMeter())

if __name__=='__main__':unittest.main(verbosity=2)
