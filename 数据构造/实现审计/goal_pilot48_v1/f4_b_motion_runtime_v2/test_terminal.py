"""End-to-end generic terminal CPU fixtures; false current audit cannot pass science."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from . import runtime
from goal_pilot48_v1.runtime_v3 import job_runner
from goal_pilot48_v1.runtime_v3.meter import Meter
from goal_pilot48_v1.collection_meter_review_v1.test_cpu import Adapter,CURRENT
from realization_utf8_io_v1 import write_new

class CPUMeter(Meter):
    def install(self):return self

class Tests(unittest.TestCase):
    def case(self,*,component_pass=True,current_exists=True,reported_collection=3,missing_trace=None):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            out=Path(directory)/'run'
            inner_writer=[None]
            m={'manifest_sha256':'CPU_FIXTURE','implementation_source_sha256':CURRENT,'jobs':[dict(job_id='CPU_MOTION',family='F4',kind='F4_B_MOTION_THREE',requires_live_meter=True,
                runtime_module='CPU_MODULE',output_namespace=str(out),resource_caps=dict(solver_problems=0,fresh_scenes=3,action_scenes=3,collection_attempts=3))]}
            def inner(manifest,*,meter):
                out.mkdir();adapter=Adapter();adapter.family='F4'
                with meter.instrument_adapter(adapter,source_profile_sha256=CURRENT):
                    for pid in ('F4-ABC','F4-ACB','F4-BAC'):
                        meter.charge('fresh_scenes');meter.charge('action_scenes')
                        with adapter.scene({'slot_id':'CPU_B','family':'F4'},phase='strict_prefix_branch:'+pid,program={'program_id':pid}):pass
                        trace=out/'branches'/pid/'trace_source.npz';trace.parent.mkdir(parents=True)
                        if pid!=missing_trace:
                            with trace.open('xb') as f:f.write(b'CPU fixture not scientific trace')
                if current_exists:
                    (out/'current').mkdir()
                    with (out/'current/current_arrays.npz').open('xb') as f:f.write(b'CPU fixture')
                    reference={'aggregate_sha256':'CPU_sealed','model_visible_components':{'RGB_hash':'CPU_sealed'}}
                    write_new(Path(directory)/'CPU_parent/reference_current_hashes.json',reference)
                    write_new(out/'current/current.json',{'parent_root':str(Path(directory)/'CPU_parent'),'current':reference})
                inner_writer[0](out/'publication_index.json',runtime.seal({'publication_complete':True,'CPU_fixture':True}))
                return dict(scene_attempts=3,collection_attempts=reported_collection,accounting_complete=True,
                    scientific_route_pass=True,accepted_variant_trajectory_count=3,**{'pass':True})
            check={'pass':component_pass,'unique_articulation_dofs':38,'model_visible_robot_state_dimension':76}
            original_bind=runtime.bound_function
            def bind(function,**overrides):
                if function is runtime.old.run:
                    inner_writer[0]=overrides['write_new'];return inner
                return original_bind(function,**overrides)
            with patch.object(runtime,'bound_function',side_effect=bind),patch.object(runtime,'current_audit',return_value=check),patch.object(job_runner,'load_manifest',return_value=m),patch.object(job_runner,'Meter',CPUMeter),patch.object(job_runner.importlib,'import_module',return_value=SimpleNamespace(run=runtime.run)):
                code=job_runner.main(['--manifest',str(Path(directory)/'CPU_not_published.json')])
            result=json.loads((out/'runtime_terminal.json').read_text(encoding='utf-8'))
            result['_CPU_test_final_index_present']=(out/'publication_index.json').exists()
            result['_CPU_test_pipeline_index_present']=(out/'pipeline_publication_index.json').exists()
            return code,json.loads((out/'goal_terminal.json').read_text(encoding='utf-8')),result
    def test_false_return_without_exception_blocks_scientific_success(self):
        code,goal,result=self.case(component_pass=False)
        self.assertEqual(code,0);self.assertTrue(goal['accounting_complete'])
        self.assertFalse(result['scientific_route_pass']);self.assertEqual(result['accepted_variant_trajectory_count'],0)
        self.assertFalse(result['current_component_audit']['current_component_validation_pass'])
        self.assertFalse(result['_CPU_test_final_index_present']);self.assertTrue(result['_CPU_test_pipeline_index_present'])
    def test_missing_current_blocks_science_but_preserves_counted_attempts(self):
        code,goal,result=self.case(current_exists=False)
        self.assertEqual(code,0);self.assertEqual(goal['resource_counts']['collection_attempts'],3)
        self.assertFalse(result['scientific_route_pass']);self.assertEqual(result['current_component_audit']['error']['type'],'CurrentArtifactMissing')
        self.assertFalse(result['_CPU_test_final_index_present'])
    def test_counter_disagreement_blocks_generic_terminal(self):
        code,goal,result=self.case(reported_collection=2)
        self.assertEqual(code,1);self.assertFalse(goal['accounting_complete']);self.assertFalse(goal['pass'])
    def test_complete_components_allow_original_science_but_not_pilot_registration(self):
        code,goal,result=self.case()
        self.assertEqual(code,0);self.assertTrue(result['scientific_route_pass'])
        self.assertFalse(result['source_root_original_goal_pass']);self.assertFalse(result['pilot_cells_modified'])
        self.assertTrue(result['shared_current_reference_publication_required'])
        self.assertTrue(result['_CPU_test_final_index_present'])
        self.assertTrue(result['current_component_audit']['complete_program_realization_matrix'])
        self.assertEqual(len(result['current_component_audit']['checked_current_sources']),6)
    def test_any_missing_new_trace_blocks_science_and_final_publication(self):
        for pid in ('F4-ABC','F4-ACB','F4-BAC'):
            with self.subTest(program_id=pid):
                code,goal,result=self.case(missing_trace=pid)
                self.assertEqual(code,0);self.assertTrue(goal['accounting_complete'])
                self.assertFalse(result['scientific_route_pass']);self.assertEqual(result['accepted_variant_trajectory_count'],0)
                audit=result['current_component_audit']
                self.assertTrue(audit['available_current_components_pass']);self.assertFalse(audit['complete_program_realization_matrix'])
                self.assertEqual(len(audit['checked_current_sources']),5)
                self.assertEqual(audit['error']['type'],'CurrentAuditMatrixIncomplete')
                self.assertFalse(result['_CPU_test_final_index_present']);self.assertTrue(result['_CPU_test_pipeline_index_present'])

if __name__=='__main__':unittest.main(verbosity=2)
