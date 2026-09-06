"""CPU lifecycle/trace-reset fixtures only; no physical qualification claimed."""
from pathlib import Path
import json
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from ..f4_b_runtime_v1.test_cpu import fixture_stage_a
from ..f4_b_runtime_v1.binding import runtime_spec,seal
from ..f4_b_runtime_v1.stages import planner_spec
from . import runtime as r

def append_queries(scene,batch,singles):
    for _ in range(batch):
        scene.planner_query_count+=1
        scene.planner_queries.append(dict(query_id=scene.planner_query_count,query_type='batched_grasp_target_selection',batch_size=10,ordered_goal_poses=[[0]*7]*10))
    for _ in range(singles):
        scene.planner_query_count+=1;scene.planner_queries.append(dict(query_id=scene.planner_query_count))

class Tests(unittest.TestCase):
    def fake_scene(self,calls):
        scene=SimpleNamespace(common_x=object(),role_actors={},robot=SimpleNamespace(communication_flag=False))
        def init(*a,**kw):calls.append('initialize');scene.planner_query_count=0;scene.planner_queries=[];scene.trace=[{'CPU_fixture':True}]
        def save(path):
            with Path(path).open('xb') as f:f.write(b'CPU fixture, not a scientific NPZ')
        scene.initialize_trace=init;scene.save_trace=save;return scene
    def test_trace_reset_preserves_ten_prefix_queries_and_raw_epochs(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            scene=self.fake_scene([]);original=scene.initialize_trace;rec=r.EpochRecorder(scene,directory)
            scene.initialize_trace(None);append_queries(scene,0,10)
            scene.initialize_trace(None);append_queries(scene,12,10)
            rec.close();self.assertIs(scene.initialize_trace,original)
            accounting=rec.accounting('A_ONLY')
            self.assertEqual(accounting['solver_problems'],140)
            self.assertEqual([e['planner_api_calls'] for e in rec.epochs],[10,22])
            self.assertEqual(len(list(Path(directory).glob('trace_epoch_*.npz'))),2)
    def test_ab_ac_are150_and_total720(self):
        totals=[]
        for stage in r.STAGES:
            with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
                scene=self.fake_scene([]);rec=r.EpochRecorder(scene,directory)
                scene.initialize_trace(None);append_queries(scene,0,10)
                scene.initialize_trace(None);append_queries(scene,12,10 if stage in r.STAGES[:3] else 20)
                rec.close();totals.append(rec.accounting(stage)['solver_problems'])
        self.assertEqual(totals,[140,140,140,150,150]);self.assertEqual(sum(totals),720)
    def test_missing_native_receipt_rejected_but_original_method_restored(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            scene=self.fake_scene([]);original=scene.initialize_trace;rec=r.EpochRecorder(scene,directory)
            scene.initialize_trace(None);scene.planner_query_count=1
            with self.assertRaises(ValueError):rec.close()
            self.assertIs(scene.initialize_trace,original)
    def test_run_one_bootstrap_before_original_executor(self):
        calls=[];scene=self.fake_scene(calls);stage_a=fixture_stage_a();spec=runtime_spec('f4_stage_b_planner',stage_a=stage_a)
        ps=planner_spec('F4-ABC',slot_id='CPU_B-planner-source',planner_reset_nonce=1)
        terminal=seal(dict(spec_sha256=ps['spec_sha256'],candidate_sha256=ps['candidate_sha256'],program_id='F4-ABC',robot_kinematic_table_world_planner_pass=True,physical_execution_count=0))
        source=dict(spec=ps,terminal=terminal,physical_micro_slot_id='CPU_B')
        class Context:
            cleanup_receipt=dict(cleanup_safety_pass=True,orphan_process_count=0)
            def __enter__(self):return SimpleNamespace(scene=scene)
            def __exit__(self,*a):calls.append('cleanup');return False
        adapter=SimpleNamespace(scene=lambda *a,**kw:Context(),
            capture_current=lambda scene:(calls.append('current') or {'aggregate_sha256':'CPU_B'}),
            capture_anchor=lambda scene:(calls.append('anchor') or {'CPU_fixture':True}))
        def execute(scene,*a,**kw):
            calls.append('executor');assert scene.trace and scene.planner_query_count==0
            scene.initialize_trace(None);append_queries(scene,0,10)
            scene.initialize_trace(None);append_queries(scene,12,10)
            return {'stage_physically_qualified':True,'CPU_fixture':True}
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            with patch.object(r,'make_adapter',return_value=adapter),patch('controlled_multi_future.f4_bounded_physical_micro_v1.run_f4_bounded_physical_micro_v1',side_effect=execute):
                row=r.run_one('A_ONLY',source,stage_a,spec,{'aggregate_sha256':'CPU_B'},Path(directory)/'run')
            self.assertEqual(calls[:4],['current','anchor','initialize','executor'])
            self.assertTrue(row['physical_pass']);self.assertEqual(row['accounting']['solver_problems'],140)
            self.assertEqual(calls[-1],'cleanup')
    def test_no_published_programs_never_create_scene(self):
        with patch.object(r,'make_adapter',side_effect=AssertionError('must not instantiate')):
            with self.assertRaises(KeyError):r.run({'jobs':[{'resource_caps':r.CAPS}]})
    def test_independent_meter_checks_prefix_N_and_collection_zero(self):
        for solver,collection,expected in ((140,0,True),(130,0,False),(140,1,False)):
            with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
                out=Path(directory)/'run';meter=Path(directory)/'run_meter';meter.mkdir()
                events=[dict(kind='CHARGE',resource=k,amount=n,total=n) for k,n in
                    [('fresh_scenes',1),('action_scenes',1),('solver_problems',solver)] ]
                if collection:events.append(dict(kind='CHARGE',resource='collection_attempts',amount=1,total=1))
                with (meter/'events.jsonl').open('xb') as f:f.write(('\n'.join(json.dumps(e) for e in events)+'\n').encode('utf-8'))
                rows=[dict(accounting_complete=True,accounting={'solver_problems':140},scene_attempts=1,physical_attempted=True,physical_pass=True)]
                if expected:self.assertTrue(r.reconcile(out,rows)['pass'])
                else:
                    with self.assertRaises(ValueError):r.reconcile(out,rows)

if __name__=='__main__':unittest.main(verbosity=2)
