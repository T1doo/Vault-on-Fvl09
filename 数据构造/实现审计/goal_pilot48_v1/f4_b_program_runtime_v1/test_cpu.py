"""CPU fixtures only, never accepted/published GPU qualification evidence."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ..f4_b_runtime_v1.test_cpu import fixture_stage_a
from ..f4_b_runtime_v1.binding import seal,runtime_spec,payload
from realization_utf8_io_v1 import write_new
from . import runtime as r

class Tests(unittest.TestCase):
    def rows(self):
        batch=[dict(query_id=i+1,query_type='batched_grasp_target_selection',batch_size=10,ordered_goal_poses=[[0]*7]*10) for i in range(12)]
        return batch+[dict(query_id=i+13) for i in range(30)]
    def test_actual_N_150_not_42(self):
        self.assertEqual(r.query_accounting(self.rows(),42)['solver_problems'],150)
        bad=self.rows();bad[0]['batch_size']=9
        with self.assertRaises(ValueError):r.query_accounting(bad,42)
        with self.assertRaises(ValueError):r.query_accounting(self.rows()[:-1],42)
    def input_fixture(self,directory):
        evidence=fixture_stage_a()
        manifest=seal(dict(jobs=[dict(runtime_module='goal_pilot48_v1.f4_b_runtime_v2.runtime')]),'manifest_sha256')
        terminal=seal(dict(runtime_result=dict(evidence=evidence,qualification_pass=True,independent_meter={'pass':True},result={'current':{'aggregate_sha256':'CPU_CURRENT'}}),
            resource_counts=dict(solver_problems=135,fresh_scenes=1,action_scenes=0,collection_attempts=0),
            accounting_complete=True,manifest_sha256=manifest['manifest_sha256'],**{'pass':True}))
        guard=seal(dict(manifest_sha256=manifest['manifest_sha256'],child_exit_code=0,task_owned_cleanup_pass=True))
        job=dict(b_payload_sha256=payload()['receipt_sha256'],planned_scene_spec_sha256=runtime_spec('f4_stage_b_planner',stage_a=evidence)['planned_scope_spec_sha256'])
        for field,value in [('evidence',evidence),('goal_terminal',terminal),('guard_terminal',guard),('manifest',manifest)]:
            path=Path(directory)/(field+'.json');write_new(path,value)
            job['source_stage_a_'+field+'_path']=str(path);job['source_stage_a_'+field+'_file_sha256']=r.sha(path)
        return job
    def test_published_lineage_and_downstream_B_scene_required(self):
        with tempfile.TemporaryDirectory(dir=r.W/'Robotwin2/tmp') as directory:
            job=self.input_fixture(directory)
            evidence,spec,current=r.prerequisites(job)
            self.assertEqual(spec['seed'],2026090604);self.assertEqual(current['aggregate_sha256'],'CPU_CURRENT')
            bad=deepcopy(job);bad['b_payload_sha256']='OLD_A'
            with self.assertRaises(ValueError):r.prerequisites(bad)
            bad=deepcopy(job);bad['source_stage_a_guard_terminal_file_sha256']='0'*64
            with self.assertRaises(ValueError):r.prerequisites(bad)
    def test_no_real_input_cannot_open_scene(self):
        with tempfile.TemporaryDirectory(dir=r.W/'Robotwin2/tmp') as directory:
            job=dict(resource_caps=r.CAPS,planner_reset_nonce_base=123,output_namespace=str(Path(directory)/'no_scene'))
            with patch.object(r,'make_adapter',side_effect=AssertionError('must not create adapter')):
                with self.assertRaises(KeyError):r.run({'jobs':[job]})
            self.assertFalse(Path(job['output_namespace']).exists())
    def execute_fake_panel(self,directory,fail_first=False):
        out=Path(directory)/'run';meter=out.parent/(out.name+'_meter');meter.mkdir()
        count=1 if fail_first else 3;solver=5 if fail_first else 450
        events=[dict(kind='CHARGE',resource='fresh_scenes',amount=count,total=count),dict(kind='CHARGE',resource='solver_problems',amount=solver,total=solver)]
        with (meter/'events.jsonl').open('xb') as f:f.write(('\n'.join(json.dumps(e) for e in events)+'\n').encode('utf-8'))
        job=dict(job_id='CPU_FIXTURE',resource_caps=r.CAPS,planner_reset_nonce_base=100,output_namespace=str(out))
        calls=[]
        def one(**kw):
            calls.append(kw['program_id'])
            return dict(program_pass=not fail_first,scene_attempts=1,accounting_complete=True,
                accounting={'solver_problems':5 if fail_first else 150},error=None,
                cleanup={'cleanup_safety_pass':True,'orphan_process_count':0})
        with patch.object(r,'prerequisites',return_value=(None,{'fixture':True},{})),patch.object(r,'stage_a_source_inputs',return_value={'fixture':True}),patch.object(r,'run_one',side_effect=one):
            result=r.run({'jobs':[job]})
        return result,calls
    def test_three_programs_reconcile_450_three_scenes(self):
        with tempfile.TemporaryDirectory(dir=r.W/'Robotwin2/tmp') as directory:
            result,calls=self.execute_fake_panel(directory)
            self.assertEqual(calls,list(r.PROGRAMS));self.assertTrue(result['pass']);self.assertTrue(result['program_panel_pass'])
            self.assertEqual(result['independent_meter']['counts']['solver_problems'],450)
    def test_first_required_failure_stops_remaining_and_no_physical_gate(self):
        with tempfile.TemporaryDirectory(dir=r.W/'Robotwin2/tmp') as directory:
            result,calls=self.execute_fake_panel(directory,True)
            self.assertEqual(calls,['F4-ABC']);self.assertTrue(result['pass']);self.assertFalse(result['scientific_route_pass'])
            self.assertEqual(result['skipped_programs'],['F4-ACB','F4-BAC'])
    def test_exact_terminal_envelope_matches_isolation_builder(self):
        source=fixture_stage_a()
        for pid,stage in [('F4-ABC','A_ONLY'),('F4-ACB','C_ONLY'),('F4-BAC','B_ONLY')]:
            slot='CPU_FIXTURE-'+pid.lower();spec=r.planner_spec(pid,slot_id=slot+'-planner-source',planner_reset_nonce=1)
            terminal=seal(dict(spec_sha256=spec['spec_sha256'],candidate_sha256=spec['candidate_sha256'],program_id=pid,
                robot_kinematic_table_world_planner_pass=True,physical_execution_count=0))
            physical=r.physical_spec(terminal,stage_a=source,program_id=pid,slot_id=slot,planner_reset_nonce=1,isolation_stage=stage)
            self.assertEqual(physical['legacy_scene_spec']['seed'],2026090604)

if __name__=='__main__':unittest.main(verbosity=2)
