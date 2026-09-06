"""Direct original-runner lifecycle exercised with CPU-only fake scene/planner."""
from copy import deepcopy
import json
import locale
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from . import runtime as r

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.spec=r.runtime_spec()
    def meter_fixture(self,output,solver,action=0):
        path=Path(output).parent/(Path(output).name+'_meter')/'events.jsonl';path.parent.mkdir()
        rows=[dict(kind='CHARGE',resource='fresh_scenes',amount=1,total=1)]
        if solver:rows.append(dict(kind='CHARGE',resource='solver_problems',amount=solver,total=solver))
        if action:rows.append(dict(kind='CHARGE',resource='action_scenes',amount=action,total=action))
        with path.open('xb') as stream:stream.write(('\n'.join(json.dumps(x) for x in rows)+'\n').encode('utf-8'))
        return path
    def fixture(self, *, fail_chain=False, visibility=True, seed=r.SEED, cleanup=True):
        spec=deepcopy(self.spec)
        scene=SimpleNamespace(robot=SimpleNamespace(communication_flag=False),a=object(),role_actors={},
            _cmf_setup_kwargs={'seed':seed},_cmf_render_device_binding_v1={'pass':True})
        def initialize(*a,**kw):scene.planner_queries=[];scene.planner_query_count=0
        scene.initialize_trace=initialize
        class Context:
            cleanup_receipt=dict(scene_instance_id='CPU_FIXTURE_ONLY',cleanup_safety_pass=cleanup,orphan_process_count=0)
            def __enter__(self):return SimpleNamespace(scene=scene)
            def __exit__(self,*args):return False
        adapter=SimpleNamespace(planned_spec=spec,scene=lambda *a,**kw:Context(),
            capture_current=lambda scene:{'note':'CPU当前帧'},
            audit_current_rendered_visibility=lambda *a,**kw:{'pass':visibility})
        def build(scene,spec):
            for _ in range(12):
                scene.planner_query_count+=1
                scene.planner_queries.append(dict(query_id=scene.planner_query_count,
                    query_type='batched_grasp_target_selection',batch_size=10,ordered_goal_poses=[[0]*7]*10))
            return [dict(segment_id=role+'_'+segment,pose=[0,0,1,1,0,0,0]) for role in r.ROLES for segment in r.SEGMENTS],{}
        def plan(scene,targets,**kw):
            rows=[]
            for index,target in enumerate(targets):
                scene.planner_query_count+=1
                scene.planner_queries.append(dict(query_id=scene.planner_query_count,source=target['segment_id']))
                rows.append(dict(segment_id=target['segment_id'],planner_status='Fail' if fail_chain and index==0 else 'Success'))
                if fail_chain:break
            return dict(pass_=False,**{'pass':not fail_chain},segment_receipts=rows,planner_query_count=len(rows),controls=[{}]*len(rows))
        changes=dict(build_f4_stage_a_targets_v1=build,_plan_chain=plan,_planner_reset=lambda *a,**kw:{'cpu_fixture':True})
        return spec,adapter,changes
    def execute_fixture(self, directory, **kwargs):
        spec,adapter,changes=self.fixture(**kwargs)
        state=dict(context_enter_attempts=0,scene_entered=False,query_rows=[],api_count=None,actual_seed=None)
        run,writer=r.make_stage_runner(adapter,Path(directory)/'stage_a',state,overrides=changes)
        result=run.run(output_dir=Path(directory)/'stage_a',planned_spec=spec)
        return result,state,writer,r.qualify(result,state,spec)
    def test_original_runner_success_135_real_N_and_two_exclusive_files(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            result,state,writer,evidence=self.execute_fixture(directory)
            self.assertTrue(result['pass']);self.assertTrue(evidence['pass'])
            self.assertEqual(evidence['goal_problem_accounting']['solver_problems'],135)
            self.assertEqual(evidence['planner_query_count'],27)
            self.assertEqual(len(writer.paths),2);self.assertNotEqual(*writer.paths)
            self.assertFalse((Path(directory)/'stage_a/receipt.json').exists())
    def test_finite_planner_failure_has_complete_count_but_no_qualification(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            _,_,_,evidence=self.execute_fixture(directory,fail_chain=True)
            self.assertFalse(evidence['pass']);self.assertEqual(evidence['goal_problem_accounting']['solver_problems'],121)
    def test_visibility_failure_never_calls_planner(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            _,state,_,evidence=self.execute_fixture(directory,visibility=False)
            self.assertTrue(state['counter_bootstrap']['initialized'])
            self.assertFalse(evidence['pass'])
            self.assertEqual(evidence['goal_problem_accounting']['solver_problems'],0)
    def test_real_seed_and_cleanup_gates(self):
        for kwargs in ({'seed':2026091401},{'cleanup':False}):
            with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
                _,_,_,evidence=self.execute_fixture(directory,**kwargs)
                self.assertFalse(evidence['pass'])
    def test_changed_batch_N_or_missing_receipt_is_infrastructure(self):
        row=dict(query_id=1,query_type='batched_grasp_target_selection',batch_size=9,ordered_goal_poses=[[0]*7]*9)
        with self.assertRaises(ValueError):r.count_problem_rows([row],1)
        with self.assertRaises(ValueError):r.count_problem_rows([],1)
        with self.assertRaises(ValueError):r.count_problem_rows([{'query_id':2}],1)
    def test_utf8_under_C_locale_exclusive_preserves_old(self):
        old=locale.setlocale(locale.LC_CTYPE)
        try:
            locale.setlocale(locale.LC_CTYPE,'C')
            with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
                writer=r.ExclusiveLegacyWriter(Path(directory));path=Path(directory)/'receipt.json'
                writer(path,{'status':'running','说明':'新布局B'})
                before=Path(writer.paths[0]).read_bytes()
                with self.assertRaises(FileExistsError):writer(path,{'status':'running','说明':'覆盖'})
                self.assertEqual(Path(writer.paths[0]).read_bytes(),before)
                self.assertEqual(json.loads(before)['说明'],'新布局B')
        finally:locale.setlocale(locale.LC_CTYPE,old)
    def test_generic_run_rejects_A_before_scene_or_output(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            out=Path(directory)/'not_created'
            job=dict(resource_caps=r.CAPS,b_payload_sha256='A',planned_scene_spec_sha256='A',output_namespace=str(out))
            with patch.object(r,'source_inputs',return_value={'payload_sha256':'B'}):
                with self.assertRaises(ValueError):r.run({'jobs':[job]})
            self.assertFalse(out.exists())
    def test_generic_run_distinguishes_complete_scientific_failure(self):
        spec,adapter,changes=self.fixture(fail_chain=True)
        inputs={'payload_sha256':r.payload()['receipt_sha256']}
        real_factory=r.make_stage_runner
        def factory(a,d,s):return real_factory(a,d,s,overrides=changes)
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            self.meter_fixture(Path(directory)/'run',121)
            job=dict(resource_caps=r.CAPS,b_payload_sha256=inputs['payload_sha256'],
                planned_scene_spec_sha256=spec['planned_scope_spec_sha256'],output_namespace=str(Path(directory)/'run'))
            with patch.object(r,'source_inputs',return_value=inputs),patch.object(r,'make_adapter',return_value=adapter),patch.object(r,'make_stage_runner',side_effect=factory):
                result=r.run({'jobs':[job]})
            self.assertTrue(result['pass']);self.assertTrue(result['accounting_complete'])
            self.assertFalse(result['scientific_route_pass']);self.assertEqual(result['scene_attempts'],1)
            self.assertEqual(result['local_solver_accounting']['solver_problems'],121)
            self.assertTrue(result['independent_meter']['pass'])
    def test_independent_meter_missing_action_or_wrong_total_rejected(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            with self.assertRaises(FileNotFoundError):r.independent_meter_counts(Path(directory)/'none')
            self.meter_fixture(Path(directory)/'acted',135,action=1)
            with self.assertRaises(ValueError):r.independent_meter_counts(Path(directory)/'acted')
    def test_generic_success_cannot_publish_when_meter_counts_only_python_calls(self):
        spec,adapter,changes=self.fixture()
        inputs={'payload_sha256':r.payload()['receipt_sha256']};real_factory=r.make_stage_runner
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            out=Path(directory)/'run';self.meter_fixture(out,27)
            job=dict(resource_caps=r.CAPS,b_payload_sha256=inputs['payload_sha256'],
                planned_scene_spec_sha256=spec['planned_scope_spec_sha256'],output_namespace=str(out))
            with patch.object(r,'source_inputs',return_value=inputs),patch.object(r,'make_adapter',return_value=adapter),patch.object(r,'make_stage_runner',side_effect=lambda a,d,s:real_factory(a,d,s,overrides=changes)):
                result=r.run({'jobs':[job]})
            self.assertFalse(result['pass']);self.assertFalse(result['accounting_complete'])
            self.assertFalse(result['scientific_route_pass'])
            evidence=json.loads((out/'source_stage_a_evidence.json').read_text(encoding='utf-8'))
            self.assertFalse(evidence['pass']);self.assertIn('ACCOUNTING_STOP',evidence['status'])

if __name__=='__main__':unittest.main(verbosity=2)
