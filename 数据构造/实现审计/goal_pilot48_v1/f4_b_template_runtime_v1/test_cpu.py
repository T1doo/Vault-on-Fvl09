"""CPU fixtures only; never manufacture real passing isolation/template data."""
from copy import deepcopy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from ..f4_b_isolation_runtime_v1.test_cpu import Tests as IsolationFixture,append_queries
from ..f4_b_runtime_v1.test_cpu import fixture_stage_a
from ..f4_b_runtime_v1.stages import planner_spec
from ..f4_b_runtime_v1.binding import runtime_spec,seal
from . import runtime as r

def final():
    return {**{name:[0,0,.8,1,0,0,0] for name in ('common_x_pose','A_pose','B_pose','C_pose','executing_eef_pose')},
            'executing_gripper_open':True,'execution_arm':'left'}
def rows():
    return [dict(program_id=pid,physical_pass=True,current={'aggregate_sha256':'CPU_CURRENT'},anchor={'anchor_sha256':'CPU_ANCHOR'},
        result={'physical_result':{'final_state_equivalence_payload':final()}}) for pid in r.PROGRAMS]

class Tests(unittest.TestCase):
    def test_original_final_equivalence_and_current_anchor_gates(self):
        original=rows();self.assertTrue(r.equivalence(original)['final_state_equivalence']['equivalent'])
        bad=deepcopy(original);bad[1]['current']['aggregate_sha256']='different'
        self.assertFalse(r.equivalence(bad)['same_current_pass'])
        bad=deepcopy(original);bad[1]['anchor']['anchor_sha256']='different'
        self.assertFalse(r.equivalence(bad)['same_anchor_pass'])
        bad=deepcopy(original);bad[1]['result']['physical_result']['final_state_equivalence_payload']['A_pose'][0]=.031
        self.assertFalse(r.equivalence(bad)['final_state_equivalence']['equivalent'])
        for row in original:row['result']['physical_result']['final_state_equivalence_payload']={}
        self.assertFalse(r.equivalence(original)['final_state_equivalence']['equivalent'])
    def test_missing_or_failed_program_not_equivalent(self):
        self.assertFalse(r.equivalence(rows()[:2])['final_state_equivalence']['equivalent'])
        value=rows();value[2]['physical_pass']=False
        self.assertFalse(r.equivalence(value)['same_current_pass'])
    def test_template_epochs_count160_not150(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            scene=IsolationFixture().fake_scene([]);rec=r.TemplateEpochRecorder(scene,directory)
            scene.initialize_trace(None);append_queries(scene,0,10)
            scene.initialize_trace(None);append_queries(scene,12,30);rec.close()
            self.assertEqual(rec.accounting('F4-ABC')['solver_problems'],160)
            self.assertEqual([e['planner_api_calls'] for e in rec.epochs],[10,42])
    def test_private_clone_calls_full_executor_preserves_bootstrap(self):
        from types import SimpleNamespace
        stage_a=fixture_stage_a();spec=runtime_spec('f4_stage_b_planner',stage_a=stage_a)
        ps=planner_spec('F4-ABC',slot_id='CPU_B-planner-source',planner_reset_nonce=1)
        terminal=seal(dict(spec_sha256=ps['spec_sha256'],candidate_sha256=ps['candidate_sha256'],program_id='F4-ABC',robot_kinematic_table_world_planner_pass=True,physical_execution_count=0))
        source=dict(spec=ps,terminal=terminal,physical_micro_slot_id='CPU_B');prior=seal({'CPU_FIXTURE':True})
        calls=[];scene=IsolationFixture().fake_scene(calls)
        class Context:
            cleanup_receipt=dict(cleanup_safety_pass=True,orphan_process_count=0)
            def __enter__(self):return SimpleNamespace(scene=scene)
            def __exit__(self,*a):calls.append('cleanup');return False
        adapter=SimpleNamespace(scene=lambda *a,**kw:Context(),capture_current=lambda scene:(calls.append('current') or {'aggregate_sha256':'CPU'}),
            capture_anchor=lambda scene:(calls.append('anchor') or {'anchor_sha256':'CPU'}))
        def execute(scene,physical,**kw):
            calls.append('full_executor');self.assertEqual(physical['planner_query_limit'],42)
            self.assertEqual(physical['role_sequence'],['A','B','C'])
            scene.initialize_trace(None);append_queries(scene,0,10)
            scene.initialize_trace(None);append_queries(scene,12,30)
            return dict(full_program_physically_qualified=True,physical_result={'final_state_equivalence_payload':final()})
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            # Patch is process-local CPU fixture only; production functions are
            # untouched by bound_executor's private globals and AST clone.
            with patch.object(r.isolation,'make_adapter',return_value=adapter),patch('controlled_multi_future.f4_full_program_physical_v1.run_f4_full_program_physical_v1',side_effect=execute):
                fn=r.bound_executor(source,stage_a,prior)
                result=fn('F4-ABC',source,stage_a,spec,{'aggregate_sha256':'CPU'},Path(directory)/'run')
            self.assertEqual(calls[:4],['current','anchor','initialize','full_executor'])
            self.assertTrue(result['physical_pass']);self.assertEqual(result['accounting']['solver_problems'],160)
    def test_missing_true_isolation_cannot_execute(self):
        with patch.object(r,'bound_executor',side_effect=AssertionError('must not build executor')):
            with self.assertRaises(KeyError):r.run({'jobs':[{'resource_caps':r.CAPS}]})

if __name__=='__main__':unittest.main(verbosity=2)
