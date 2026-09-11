"""Whole F1 CPU integration. Only simulator/host GPU mechanics are substituted."""
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
import f1_full_production as full


class SyntheticHost:
    synthetic_cpu_backend=True
    def __init__(self):self.snapshots=0;self.started=[];self.released=[]
    def snapshot(self):
        self.snapshots+=1
        return {'gpus':[{'physical_index':i,'gpu_uuid':f'GPU-{i}','independently_fresh_idle':True,'compute_processes':[]} for i in range(8)]}
    def acquire(self,index,uuid):return {'index':index,'uuid':uuid}
    def release(self,lease):self.released.append(lease['index']);return {'released':True}
    def run(self,job,card,directory):
        import family_entry
        self.started.append(job['root_id'])
        spec=json.loads(Path(job['spec_path']).read_text());auth=json.loads(Path(job['authorization_path']).read_text())
        auth['resume']=job.get('launch_mode')=='resume'
        result=family_entry.run_family_root(spec=spec,output=Path(job['output']),authorization=auth)
        full.write(Path(job['output'])/'execution_result.json',result)
        return {'returncode':0 if result['pass'] else 1,'owned_cleanup_pass':True,'host_process_visibility':True,
                'lease_seconds':1,'synthetic_cpu_backend':True,'owned_process_tree':[]}


def fixture_package(directory):
    full.prepare(directory/'package')
    manifest=json.loads((directory/'package/manifest.json').read_text())
    manifest.update(execution_authorized=True,test_only=True,task_id='explicit_synthetic_f1_full_fixture',
                    copy_family_root=str(directory/'copy'))
    for job in manifest['jobs']:
        job['output']=str(directory/'raw'/job['root_id'])
        auth_path=Path(job['authorization_path']);auth=json.loads(auth_path.read_text())
        auth.update(gpu_execution_authorized=True,copy_destination=str(directory/'copy'/job['root_id']))
        full.write(auth_path,auth);job['authorization_file_sha256']=full.sha(auth_path)
    return manifest


class FullFamily(unittest.TestCase):
    def test_failure_taxonomy_does_not_upgrade_legacy_or_mixed_attempts(self):
        self.assertIsNone(full.failure_category({'failure_class':'transient_execution'}))
        self.assertEqual(full.failure_category({'failure_category':'physical_failure'}), 'physical_failure')
        self.assertIsNone(full.physical_failure_attempts({'attempts':[{'failure_category':'engineering_error'}, {'failure_category':'physical_failure'}]}))
        self.assertEqual(full.physical_failure_attempts({'attempts':[{'failure_category':'physical_failure'}, {'failure_category':'physical_failure'}]}), 2)
        self.assertFalse(full.reserve_eligible_for_record({'failure_category':'engineering_error','attempts':[{'failure_category':'engineering_error'},{'failure_category':'engineering_error'}]}))
        self.assertFalse(full.reserve_eligible_for_record({'failure_category':'physical_failure','attempts':[{'failure_category':'engineering_error'},{'failure_category':'physical_failure'}]}))
        self.assertTrue(full.reserve_eligible_for_record({'failure_category':'physical_failure','attempts':[{'failure_category':'physical_failure'},{'failure_category':'physical_failure'}]}))

    def test_false_real_entry_no_snapshot_or_state(self):
        with tempfile.TemporaryDirectory(dir=full.HERE) as td:
            directory=Path(td);host=SyntheticHost()
            with self.assertRaises(PermissionError):full.run({'execution_authorized':False},directory/'state',backend=host)
            self.assertEqual(host.snapshots,0);self.assertFalse((directory/'state').exists())

    def test_call_chain_budget_not_firstwave_times_five(self):
        b=full.budget()
        self.assertEqual(b['total_caps'],dict(zip(full.COUNTERS,(924,588,252,5376,201600))))
        self.assertEqual(b['sections']['ten_primary_normal']['collection_attempts'],90)
        self.assertEqual(b['sections']['four_reserve_normal']['collection_attempts'],36)
        self.assertTrue(b['first_eighteen_included_in_ninety'])
        self.assertEqual(b['timeout_seconds']+b['cleanup_grace_seconds']+b['lease_overhead_seconds'],7200)

    def test_full_queue_real_disk_gates_copy_auto18to90_no_f2(self):
        from fixture_f1_backend import make_backend
        with tempfile.TemporaryDirectory(dir=full.HERE) as td:
            d=Path(td);manifest=fixture_package(d);host=SyntheticHost()
            with patch('native_f1.native_adapter',make_backend):
                state=full.run(manifest,d/'state',backend=host)
            self.assertEqual(state['status'],'COMPLETE',state)
            self.assertEqual(host.started[:2],manifest['root_ids'][:2])
            self.assertEqual(sorted(host.started),manifest['root_ids'])
            self.assertEqual(len(state['accepted_by_primary']),10)
            self.assertEqual(state['family_audit']['cells'],90)
            self.assertTrue(state['family_audit']['synthetic']);self.assertFalse(state['family_audit']['research_eligible'])
            self.assertFalse(state['next_family_dispatched'])
            self.assertEqual([x['event'] for x in state['events']],['FIRST_18_AUTOMATIC_GATE_PASSED'])
            self.assertFalse(any(state['family_audit']['budget']['reserved'].values()))
            before=len(host.started)
            self.assertEqual(full.run(manifest,d/'state',backend=host)['status'],'COMPLETE')
            self.assertEqual(len(host.started),before)
            import csv
            with (d/'copy/dataset_index.csv').open() as stream:rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),90);self.assertEqual(len({x['cell_key'] for x in rows}),90)
            swapped=copy.deepcopy(state)
            swapped['accepted_by_primary']['F1_000003']='F1_000004'
            swapped['accepted_by_primary']['F1_000004']='F1_000003'
            with self.assertRaises(ValueError):full.publish_family(manifest,swapped,{j['root_id']:j for j in manifest['jobs']},d/'state')
            evidence=os.environ.get('F1_TEST_EVIDENCE_PATH')
            if evidence:
                full.write(evidence,{'synthetic':True,'physical_collection_increment':0,'GPU_initialized':False,
                    'source_bundle_sha256':manifest['source_bundle_sha256'],'simulated_roots_complete':10,'simulated_cells_verified':len(rows),
                    'automatic_gate_events':state['events'],'next_family_dispatched':state['next_family_dispatched'],
                    'simulated_budget':state['family_audit']['budget'],'accepted_by_primary':state['accepted_by_primary'],
                    'root_digests':state['family_audit']['roots'],'fixture_files':'TemporaryDirectory; regenerate using this test',
                    'repeat_run_started_no_new_child':len(host.started)==before,'wrong_primary_mapping_rejected':True})

    def test_unresolved_first_wave_never_advances(self):
        with tempfile.TemporaryDirectory(dir=full.HERE) as td:
            d=Path(td);m=fixture_package(d);host=SyntheticHost()
            full.write(d/'state/launcher/STATE.json',{'jobs':{m['jobs'][0]['job_id']:{'status':'UNRESOLVED'}}})
            state=full.run(m,d/'state',backend=host)
            self.assertEqual(state['status'],'STOPPED_SHARED_OR_UNRESOLVED');self.assertEqual(host.snapshots,0)
            self.assertEqual(state['events'],[])

    def test_completion_requires_ten_distinct_full_roots(self):
        with self.assertRaises(ValueError):full.publish_family({'root_ids':[f'F1_{i:06d}' for i in range(1,11)]},
                                                              {'accepted_by_primary':{}},{},full.HERE)

    def test_activated_reserve_enters_real_launcher_and_preserves_binding(self):
        import scene_plan as scenes
        from first_wave_launcher import validate_manifest
        with tempfile.TemporaryDirectory(dir=full.HERE) as td:
            d=Path(td);manifest=fixture_package(d)
            plan=json.loads(Path(manifest['planned_plan_path']).read_text())
            activation=scenes.activate_reserves(plan,d/'state/activation.json',{'F1_000001':'FAILED','F1_000002':'PASSED'})
            jobs=full._activation_jobs(manifest,d/'state',activation)
            self.assertEqual(len(jobs),1);self.assertEqual(jobs[0]['root_id'],'F1_000011')
            spec=json.loads(Path(jobs[0]['spec_path']).read_text())
            self.assertEqual(spec['activation_receipt_hash'],jobs[0]['activation_receipt']['sha256'])
            self.assertEqual(spec['original_primary_slot_id'],'F1_000001')
            self.assertEqual(len(validate_manifest(manifest,jobs)),11)
            original=Path(jobs[0]['authorization_path']).read_bytes()
            again=full._activation_jobs(manifest,d/'state',activation,jobs)
            self.assertEqual(again,jobs);self.assertEqual(Path(jobs[0]['authorization_path']).read_bytes(),original)
            self.assertTrue(Path(jobs[0]['output']).is_relative_to(d))
            wrong=copy.deepcopy(jobs);wrong[0]['root_id']='F1_000012'
            with self.assertRaises(ValueError):validate_manifest(manifest,wrong)

    def test_wrong_initial_gate_and_duplicate_job_rejected(self):
        with tempfile.TemporaryDirectory(dir=full.HERE) as td:
            m=fixture_package(Path(td))
            bad=copy.deepcopy(m);bad['first_wave_root_ids']=['F1_000008','F1_000009']
            with self.assertRaises(ValueError):full.validate_package(bad)
            bad=copy.deepcopy(m);bad['jobs'][1]['job_id']=bad['jobs'][0]['job_id']
            with self.assertRaises(ValueError):full.validate_package(bad)

    def test_reserve_rank_restart_inherits_and_never_extra_target(self):
        import scene_plan as s
        plan=s.generate()
        with tempfile.TemporaryDirectory(dir=full.HERE) as td:
            path=Path(td)/'activation.json'
            a=s.activate_reserves(plan,path,{'F1_000002':'FAILED','F1_000001':'FAILED'})
            b=s.activate_reserves(plan,path,{'F1_000001':'FAILED','F1_000002':'FAILED'})
            self.assertEqual(a,b)
            self.assertEqual([(r['primary_root_id'],r['reserve_root_id']) for r in a['records']],
                             [('F1_000001','F1_000011'),('F1_000002','F1_000012')])
            c=s.activate_reserves(plan,path,{'F1_000012':'PASSED','F1_000011':'FAILED'})
            self.assertEqual(c['records'][-1]['reserve_root_id'],'F1_000013')
            self.assertEqual(c['records'][-1]['split'],'train');self.assertEqual(c['records'][-1]['difficulty'],'clear')
            s.activate_reserves(plan,path,{'F1_000013':'PASSED'})
            self.assertEqual(len(json.loads(path.read_text())['records']),3)

if __name__=='__main__':unittest.main()
