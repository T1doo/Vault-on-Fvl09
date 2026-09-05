"""CPU integration against immutable real F1/F4 artifacts; no scene creation."""
import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from catalog import W,build_catalog,source_branch,make_adapter
from pipeline import segment_window,variations_from_trace
from retiming import retime
from controlled_multi_future.frozen_suffix_artifact_v1 import load_frozen_suffix_artifact

class RealArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.catalog=build_catalog()

    def test_parent_pairing_and_budget(self):
        groups=self.catalog['cohorts']
        self.assertEqual([g['query_cap'] for g in groups],[33,0,90])
        self.assertEqual(self.catalog['derived_query_cap'],123)
        self.assertNotEqual(groups[0]['cells'][0]['parent_root_id'],groups[1]['cells'][0]['parent_root_id'])
        self.assertEqual(sum(len(g['cells']) for g in groups),9)

    def test_original_family_verifiers(self):
        for g in self.catalog['cohorts']:
            for cell in g['cells']:
                adapter=make_adapter(cell,W/'Robotwin2/tmp/cmf_cpu_unused_scene')
                original=source_branch(cell)
                result={'semantic_verifier':original['verifier']['family_semantic_verifier']}
                self.assertTrue(adapter.verify(None,cell['program'],result)['pass'])

    def test_real_segments_match_control_sample_counts(self):
        for g in self.catalog['cohorts']:
            for cell in g['cells']:
                _,_,controls=load_frozen_suffix_artifact(Path(cell['source_suffix']).parent)
                with np.load(Path(cell['parent_root'])/'branches'/cell['program']['program_id']/'trace_source.npz',allow_pickle=False) as z:
                    queries=json.loads(str(z['planner_queries_json'].item()))
                    for i in cell['changed_indices']:
                        start,end,n=segment_window(z['planner_query_id'],z['planner_goal_active'],queries,cell['targets'][i]['segment_id'])
                        self.assertEqual(n,len(controls[i]['position']))
                        # SAPIEN stores its 250 Hz timestep as float32; the
                        # timestamps integrate that actual value, not exact .004.
                        self.assertAlmostEqual(float(z['timestamp'][end]-z['timestamp'][start]),n*float(np.float32(1/250.)),places=9)

    def test_retiming_real_controls_boundaries(self):
        for cell in self.catalog['cohorts'][1]['cells']:
            _,_,controls=load_frozen_suffix_artifact(Path(cell['source_suffix']).parent)
            for i in cell['changed_indices']:
                c=controls[i];new,r=retime(c,cell['targets'][i]['segment_id'])
                self.assertGreater(len(new['position']),len(c['position']))
                self.assertTrue(r['position_endpoints_equal']);self.assertTrue(r['velocity_endpoints_equal'])
                self.assertEqual(new['position'].shape,new['velocity'].shape)
                self.assertEqual(new['position'].dtype,c['position'].dtype)
                self.assertAlmostEqual(r['new_execution_duration_s']/r['old_execution_duration_s'],r['actual_execution_interval_scale'])
                self.assertFalse(np.array_equal(new['position'],c['position']))

    def test_retiming_analytic_derivative(self):
        n=101;t=np.arange(n)/250.
        c={'position':t[:,None].repeat(6,axis=1),'velocity':np.ones((n,6)),'dt':.004}
        new,r=retime(c,'transport');m=len(new['position']);u=np.linspace(0,1,m);scale=(m-1)/(n-1)
        expected=(1+(scale-1)*(1-6*u+6*u*u))/scale
        np.testing.assert_allclose(new['velocity'][:,0],expected,atol=1e-12)
        np.testing.assert_allclose(np.gradient(new['position'][:,0],.004)[1:-1],new['velocity'][1:-1,0],atol=2e-5)

    def test_retiming_rejects_bad_arrays_and_dt(self):
        c={'position':np.ones((20,6)),'velocity':np.zeros((20,6))}
        for bad in ({**c,'dt':.005},{**c,'position':np.full((20,6),np.nan)},{**c,'velocity':np.zeros((19,6))}):
            with self.assertRaises(ValueError):retime(bad,'transport')
        with self.assertRaises(ValueError):retime(c,'transport',factor=1.2)

    def test_segment_window_rejects_missing_discontinuous_and_duplicate(self):
        ids=np.array([[-1,-1],[2,-1],[2,-1],[2,-1]]);active=ids>=0;q=[{'arm':'left','source':'x','query_id':2}]
        self.assertEqual(segment_window(ids,active,q,'x'),(0,3,3))
        with self.assertRaises(ValueError):segment_window(ids,active,q,'absent')
        with self.assertRaises(ValueError):segment_window(ids,active,q+q,'x')
        active[2,0]=False
        with self.assertRaises(ValueError):segment_window(ids,active,q,'x')

    def test_unchanged_real_trace_not_path_variation(self):
        cell=self.catalog['cohorts'][0]['cells'][0]
        parent=source_branch(cell)
        with np.load(Path(cell['parent_root'])/'branches'/cell['program']['program_id']/'trace_source.npz',allow_pickle=False) as z:
            scene=SimpleNamespace(planner_queries=json.loads(str(z['planner_queries_json'].item())),trace=[{'eef':e,'timestamp':t,'planner_query_id':i,'planner_goal_active':a} for e,t,i,a in zip(z['eef_pose'],z['timestamp'],z['planner_query_id'],z['planner_goal_active'])])
        result={'semantic_verifier':parent['verifier']['family_semantic_verifier']}
        self.assertFalse(variations_from_trace(cell,result,scene,[])['pass'])
        for row in scene.trace:row['eef']=row['eef'].copy();row['eef'][2]+=.015
        self.assertTrue(variations_from_trace(cell,result,scene,[])['pass'])

    def test_actual_raw_writer_loader(self):
        from controlled_multi_future.probes.pipeline_dry_run import SyntheticAdapter,F1ObjectSelection
        from controlled_multi_future.raw_writer import write_raw_attempt,verify_raw_artifact_integrity
        data=SyntheticAdapter().rollout(None,F1ObjectSelection().checked_provisional_programs()[0],{'realization':'r_pc','formal_data':False,'stage0_data':False})
        with tempfile.TemporaryDirectory(dir=W/'Robotwin2/tmp',prefix='cmf_cpu_raw_') as tmp:
            write_raw_attempt(Path(tmp)/'raw',data['streams'],data['audit_streams'],data['provenance'])
            self.assertTrue(verify_raw_artifact_integrity(Path(tmp)/'raw')['pass'])

    def test_real_retimed_suffix_disk_roundtrip(self):
        from controlled_multi_future.frozen_suffix_artifact_v1 import build_frozen_suffix_artifact,write_frozen_suffix_artifact
        for cell in self.catalog['cohorts'][1]['cells']:
            m,arrays,controls=load_frozen_suffix_artifact(Path(cell['source_suffix']).parent)
            spec=copy.deepcopy(m['execution_spec']);transforms=[]
            for i in cell['changed_indices']:
                controls[i],r=retime(controls[i],cell['targets'][i]['segment_id']);transforms.append(r)
            spec['realization_control_transforms']=transforms
            out,a=build_frozen_suffix_artifact(root_slot_id=cell['parent_root_id'],family='F1',program_id=cell['program']['program_id'],
                candidate_universe_sha256=m['candidate_universe_sha256'],prefix_artifact_sha256=m['prefix_artifact_sha256'],
                actual_prefix_end_qpos=arrays['actual_prefix_end_qpos'],execution_spec=spec,controls=controls,planner_query_receipts=m['planner_query_receipts'])
            with tempfile.TemporaryDirectory(dir=W/'Robotwin2/tmp',prefix='cmf_cpu_suffix_') as tmp:
                write_frozen_suffix_artifact(Path(tmp)/'suffix',out,a)
                disk,_,loaded=load_frozen_suffix_artifact(Path(tmp)/'suffix')
                self.assertEqual(disk['execution_spec']['realization_control_transforms'],transforms)
                for original,new in zip(controls,loaded):
                    np.testing.assert_array_equal(original['position'],new['position']);np.testing.assert_array_equal(original['velocity'],new['velocity'])

    def test_counter_failure_retained_and_global_stop(self):
        from unittest.mock import patch
        from pipeline import collect_cell
        cell=self.catalog['cohorts'][2]['cells'][0]
        scene=SimpleNamespace(planner_query_count=0)
        class Context:
            cleanup_receipt={'cleanup_safety_pass':True,'orphan_process_count':0,'scene_instance_id':'cpu_fixture'}
            def __enter__(self):return SimpleNamespace(scene=scene)
            def __exit__(self,*exc):return False
        def fail_capture(s):s.planner_query_count=3;raise RuntimeError('CPU injected failure after counted calls')
        adapter=SimpleNamespace(scene=lambda *a,**k:Context(),capture_current=fail_capture)
        with tempfile.TemporaryDirectory(dir=W/'Robotwin2/tmp',prefix='cmf_cpu_failure_') as tmp,patch('pipeline.make_adapter',return_value=adapter):
            b=collect_cell(cell,Path(tmp)/'cell',shared_current_dir=Path(tmp)/'current')
            self.assertEqual(b['planner_query_delta'],3);self.assertTrue(b['accounting_complete']);self.assertTrue(b['global_stop'])
            self.assertEqual(b['status'],'failed_infrastructure')
            self.assertTrue((Path(tmp)/'cell/receipt.provisional.json').is_file())

    def test_actual_cohort_two_phase_publication(self):
        from job_runner import finalize_cohort
        from pipeline import write_new
        for cohort in (self.catalog['cohorts'][0],self.catalog['cohorts'][2]):
            branches=[source_branch(c) for c in cohort['cells']]
            # Old collector kept cleanup on the root; new cells embed it.
            original_root=json.loads((Path(cohort['cells'][0]['parent_root'])/'root_receipt.json').read_text())
            records=original_root['cleanup_records']
            for b in branches:
                candidates=[r for r in records if b['program_id'] in r['scene_instance_id'] and 'strict_prefix_branch' in r['scene_instance_id']]
                self.assertEqual(len(candidates),1);b['cleanup']=candidates[0]
            with tempfile.TemporaryDirectory(dir=W/'Robotwin2/tmp',prefix='cmf_cpu_publication_') as tmp:
                directory=Path(tmp)
                for b in branches:write_new(directory/'branches'/b['program_id']/'receipt.provisional.json',b)
                before={b['program_id']:(directory/'branches'/b['program_id']/'receipt.provisional.json').read_bytes() for b in branches}
                result=finalize_cohort(cohort,directory,branches)
                self.assertEqual(result['status'],'accepted')
                self.assertTrue((directory/'publication_index.json').is_file())
                root=json.loads((directory/'root_receipt.json').read_text())
                for b in root['branch_receipts']:
                    self.assertEqual(json.loads((directory/'branches'/b['program_id']/'receipt.json').read_text()),b)
                    self.assertEqual((directory/'branches'/b['program_id']/'receipt.provisional.json').read_bytes(),before[b['program_id']])

if __name__=='__main__':unittest.main(verbosity=2)
