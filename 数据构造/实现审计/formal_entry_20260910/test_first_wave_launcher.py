"""CPU fake Guard/child boundary tests; never runs nvidia-smi or GPU children."""
import json,tempfile,sys,hashlib
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,'/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
from first_wave_launcher import launch_wave,validate_manifest,verify_nfs_lock,_failure_evidence,_cohort_pointer_snapshot,_attempt_pointer_context,_recovery_can_rebind_gpu
from scene_plan import generate,resolve
from file_source_pin import inventory,bundle_hash


class FakeHost:
    def __init__(self,mode='pass'):self.mode=mode;self.snapshots=0;self.used=[];self.released=[]
    def snapshot(self):
        self.snapshots+=1
        return {'gpus':[{'physical_index':i,'gpu_uuid':'GPU-'+str(i),'independently_fresh_idle':i!=0 and not(self.mode=='external_after' and i in self.used),'compute_processes':[]} for i in range(8)]}
    def acquire(self,index,uuid):return {'index':index,'uuid':uuid}
    def release(self,lease):self.released.append(lease['index']);return {'released':True}
    def run(self,job,card,directory):
        self.used.append(card['physical_index']);output=Path(job['output'])
        if self.mode=='unknown':
            folder=output/'r_pc';folder.mkdir(parents=True)
            (folder/'cohort_pointer.json').write_text(json.dumps({'status':'STARTED','root_relative':'root'}))
        elif self.mode!='cli_error':
            for r in ('r_pc','r_inv_path','r_inv_motion'):
                folder=output/r/'root';folder.mkdir(parents=True)
                receipt={'status':'accepted','cleanup_records':[{'scene_created':True,'phase':phase} for phase in ['pristine',*[f'task_physical_feasibility:{p}' for p in ('red','green','blue')],'canonical_prefix_reference',*[f'suffix_preflight:{p}' for p in ('red','green','blue')],*[f'strict_prefix_branch:{p}' for p in ('red','green','blue')]]],'canonical_prefix_reference_execution_count':1,'suffix_prefix_replay_count':3,'branch_prefix_replay_count':3,'branch_execution_attempt_count':3,'planner_query_count_total':4}
                (folder/'root_receipt.json').write_text(json.dumps(receipt))
        return {'returncode':2 if self.mode=='cli_error' else 0,'owned_cleanup_pass':True,'host_process_visibility':True,'lease_seconds':2,'synthetic_cpu_backend':True}


def manifest_at(directory):
    files=inventory();pin={'source_files':files,'source_bundle_sha256':bundle_hash(files)}
    caps={'fresh_scenes':132,'action_scenes':84,'collection_attempts':36,'solver_problems':768,'gpu_lease_seconds':14400}
    jobs=[]
    for i in range(2):
        spec=resolve(generate()['slots'][i]);sp=directory/f'spec{i}.json';ap=directory/f'auth{i}.json'
        sp.write_text(json.dumps(spec));ap.write_text(json.dumps({**pin,'gpu_execution_authorized':True,'spec_sha256':spec['spec_sha256'],'copy_destination':str(directory/('copy'+str(i))),'job_limits':{'timeout_seconds':6500,'cleanup_grace_seconds':600,'gpu_reservation_seconds':7200}}))
        jobs.append({'job_id':'job'+str(i),'root_id':spec['root_id'],'spec_path':str(sp),'authorization_path':str(ap),'spec_file_sha256':hashlib.sha256(sp.read_bytes()).hexdigest(),'authorization_file_sha256':hashlib.sha256(ap.read_bytes()).hexdigest(),'output':str(directory/('output'+str(i))),'reservation':{k:v//2 for k,v in caps.items()},'timeout_seconds':6500,'cleanup_grace_seconds':600})
    return {**pin,'task_id':'explicit_cpu_launcher_fixture','execution_authorized':True,'allowed_physical_gpu_indices':list(range(8)),'root_ids':['F1_000001','F1_000002'],'budget_caps':caps,'jobs':jobs}


class TestLauncher(unittest.TestCase):
    def test_failure_evidence_separates_physical_and_engineering(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            d=Path(td); root=d/'r_pc/root'; root.mkdir(parents=True)
            (root/'root_receipt.json').write_text(json.dumps({'status':'failed_execution','error':'recovery actual regenerated prefix/current/anchor differs','budget_counts':{'execution_attempt_count':0}}))
            detail=_failure_evidence(d,{'returncode':1})
            self.assertEqual(detail['category'],'recovery_consistency_error')
            self.assertFalse(detail['reserve_eligible'])
            physical={'status':'failed_verifier','branch_receipts':[{'status':'failed_independent_cell','independent_cell_gate':{'failure_class':'PHYSICAL_FAILURE'}}],'budget_counts':{'execution_attempt_count':1}}
            (root/'root_receipt.json').write_text(json.dumps(physical))
            detail=_failure_evidence(d,{'returncode':1})
            self.assertEqual(detail['category'],'physical_failure')
            self.assertTrue(detail['reserve_eligible'])

    def test_ascii_locale_reads_chinese_failure_pointer_without_reserve(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            d=Path(td); base=d/'r_pc'; base.mkdir(parents=True)
            (base/'cohort_pointer.json').write_text(json.dumps({'status':'EXCEPTION','root_relative':'root','diagnostic':'中文恢复失败'}),encoding='utf-8')
            root=base/'root';root.mkdir()
            (root/'root_receipt.json').write_text(json.dumps({'status':'failed_execution','error':'中文 source 编码失败','budget_counts':{'execution_attempt_count':0}},ensure_ascii=False),encoding='utf-8')
            detail=_failure_evidence(d,{'returncode':1})
            self.assertEqual(detail['category'],'engineering_error')
            self.assertFalse(detail['reserve_eligible'])

    def test_failure_evidence_isolated_to_current_attempt(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            d=Path(td);base=d/'r_pc';root=base/'root';root.mkdir(parents=True)
            old={'status':'failed_verifier','branch_receipts':[{'status':'failed_independent_cell','independent_cell_gate':{'failure_class':'PHYSICAL_FAILURE'}}],'budget_counts':{'execution_attempt_count':1}}
            (root/'root_receipt.json').write_text(json.dumps(old),encoding='utf-8')
            (base/'cohort_pointer.json').write_text(json.dumps({'status':'FAILED','attempt':1,'root_relative':'root'}),encoding='utf-8')
            before=_cohort_pointer_snapshot(d)
            # A new launcher attempt that creates no terminal must not borrow
            # the old physical receipt to consume a reserve.
            context=_attempt_pointer_context(d,before,attempt_id='job:attempt:2')
            detail=_failure_evidence(d,{'returncode':1},attempt_context=context)
            self.assertEqual(detail['category'],'resource_unknown');self.assertFalse(detail['reserve_eligible']);self.assertEqual(detail['current_attempt_evidence'],[])
            # Start a separate attempt with an engineering history receipt;
            # only the newly created recovery terminal may classify it.
            (root/'root_receipt.json').write_text(json.dumps({'status':'failed_execution','error':'old UnicodeDecodeError','budget_counts':{'execution_attempt_count':0}}),encoding='utf-8')
            before=_cohort_pointer_snapshot(d)
            new=base/'recovery_2/root';new.mkdir(parents=True)
            physical={'status':'failed_verifier','branch_receipts':[{'status':'failed_independent_cell','independent_cell_gate':{'failure_class':'PHYSICAL_FAILURE'}}],'budget_counts':{'execution_attempt_count':1}}
            (new/'root_receipt.json').write_text(json.dumps(physical),encoding='utf-8')
            (base/'cohort_pointer.json').write_text(json.dumps({'status':'FAILED','attempt':2,'root_relative':'recovery_2/root'}),encoding='utf-8')
            context=_attempt_pointer_context(d,before,attempt_id='job:attempt:2')
            detail=_failure_evidence(d,{'returncode':1},attempt_context=context)
            self.assertEqual(detail['category'],'physical_failure');self.assertTrue(detail['reserve_eligible']);self.assertEqual(len(detail['current_attempt_evidence']),1);self.assertTrue(detail['root_history']['receipt_paths'])

    def test_gpu_rebind_allowed_only_before_physical_usage(self):
        manifest={'scope':'F1_MOTION_RECOVERY','recovery_contract':{'allow_gpu_rebind_if_no_physical':True}}
        clean={'attempts':[{'physical_started':False,'actual':{'fresh_scenes':0,'action_scenes':0,'collection_attempts':0,'solver_problems':0}}]}
        self.assertTrue(_recovery_can_rebind_gpu(manifest,clean))
        used={'attempts':[{'physical_started':True,'actual':{'fresh_scenes':1,'action_scenes':0,'collection_attempts':0,'solver_problems':0}}]}
        self.assertFalse(_recovery_can_rebind_gpu(manifest,used))
        self.assertFalse(_recovery_can_rebind_gpu({**manifest,'scope':'F1_FULL_PRODUCTION'},clean))

    def test_false_authorization_never_snapshots(self):
        host=FakeHost()
        with self.assertRaises(PermissionError):launch_wave({'execution_authorized':False},Path(__file__).parent/'unused',host)
        self.assertEqual(host.snapshots,0)
    def test_fresh_two_idle_cards_and_actual_native_accounting(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            d=Path(td);m=manifest_at(d);host=FakeHost('external_after')
            with patch('first_wave_launcher.verify_completed_job',return_value={'pass':True,'explicit_cpu_boundary':True}), patch('execution_cli.copy_only',return_value={'pass':True,'explicit_cpu_boundary':True}):result=launch_wave(m,d/'state',host)
            self.assertEqual(result['state']['status'],'COMPLETE');self.assertEqual(set(host.used),{1,2})
            self.assertEqual(result['state']['budget']['consumed'],{'fresh_scenes':66,'action_scenes':42,'collection_attempts':18,'solver_problems':24,'gpu_lease_seconds':sum(j['lease_seconds'] for j in result['results'])})
            self.assertFalse(any(result['state']['budget']['reserved'].values()))
            self.assertTrue(all(j['owned_cleanup_pass'] for j in result['results']))
            self.assertTrue(all(not j['device_idle_observed'] for j in result['results']))
            self.assertTrue(all((d/'state/jobs'/j/'attempt_1/end_and_cleanup_evidence.json').exists() for j in ('job0','job1')))
    def test_cli_error_only_measured_lease_and_unknown_retains_reservation(self):
        for mode in ('cli_error','unknown'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
                d=Path(td);m=manifest_at(d);result=launch_wave(m,d/'state',FakeHost(mode));budget=result['state']['budget']
                if mode=='cli_error':
                    self.assertGreater(budget['consumed']['gpu_lease_seconds'],0);self.assertLess(budget['consumed']['gpu_lease_seconds'],100)
                    self.assertEqual(budget['consumed']['fresh_scenes'],0)
                    self.assertFalse(any(budget['reserved'].values()))
                else:
                    self.assertEqual(result['state']['status'],'UNRESOLVED')
                    self.assertEqual(budget['reserved'],m['budget_caps'])
                    self.assertFalse(any(budget['consumed'].values()))
    def test_zero_exit_missing_independent_result_is_failed(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            d=Path(td);result=launch_wave(manifest_at(d),d/'state',FakeHost())
            self.assertEqual(result['state']['status'],'FAILED')
            self.assertTrue(all(j['independent_completion']['pass'] is False for j in result['results']))
            self.assertEqual(result['state']['budget']['consumed']['fresh_scenes'],66)
            self.assertFalse(any(result['state']['budget']['reserved'].values()))
            second=FakeHost()
            with self.assertRaises(RuntimeError):launch_wave(manifest_at(d),d/'state',second)
            self.assertEqual(second.snapshots,0)
    def test_failed_prefix_attempt_is_charged_not_success_only(self):
        from first_wave_launcher import usage_from_receipts
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            d=Path(td);root=d/'r_pc/root';root.mkdir(parents=True)
            (root/'root_receipt.json').write_text(json.dumps({'status':'failed_planner','cleanup_records':[{'scene_created':True,'phase':phase} for phase in ['pristine','task_physical_feasibility:red','task_physical_feasibility:green','task_physical_feasibility:blue','canonical_prefix_reference']],'canonical_prefix_reference_execution_count':1,'suffix_prefix_replay_count':0,'branch_prefix_replay_count':0,'branch_execution_attempt_count':0,'planner_query_count_total':1}))
            counts=usage_from_receipts(d,3)
            self.assertEqual(counts,{'fresh_scenes':5,'action_scenes':1,'collection_attempts':0,'solver_problems':1,'gpu_lease_seconds':3})
            receipt=json.loads((root/'root_receipt.json').read_text());receipt['cleanup_records'].append({'scene_created':True,'phase':'strict_prefix_branch:F1-red'})
            (root/'root_receipt.json').write_text(json.dumps(receipt))
            self.assertEqual(usage_from_receipts(d,3)['collection_attempts'],1)
            self.assertEqual(receipt['branch_execution_attempt_count'],0)
            del receipt['cleanup_records'][-1]['phase']
            (root/'root_receipt.json').write_text(json.dumps(receipt))
            with self.assertRaises(RuntimeError):usage_from_receipts(d,3)
    def test_owned_gpu_pid_remaining_keeps_ownership_unresolved(self):
        class OwnedGpuRemains(FakeHost):
            def snapshot(self):
                s=super().snapshot()
                for c in s['gpus']:
                    if c['physical_index'] in self.used:c['compute_processes']=[{'pid':999}]
                return s
            def run(self,*args):
                result=super().run(*args);result['owned_process_tree']=[{'pid':999,'start':'fixture'}];return result
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            d=Path(td);host=OwnedGpuRemains();result=launch_wave(manifest_at(d),d/'state',host)
            self.assertEqual(result['state']['status'],'UNRESOLVED');self.assertEqual(host.released,[])
            self.assertTrue(all(j['reservation_retained'] for j in result['results']))
    def test_frozen_job_bytes_reject_resigned_config_mutation(self):
        from scene_plan import hash_json
        from first_wave_launcher import read_bound_job_configs
        for kind in ('spec','authorization'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
                d=Path(td);manifest=manifest_at(d);job=manifest['jobs'][0]
                if kind=='spec':
                    path=Path(job['spec_path']);value=json.loads(path.read_text())
                    value['seed']+=1;value['spec_sha256']=hash_json({k:v for k,v in value.items() if k!='spec_sha256'})
                else:
                    path=Path(job['authorization_path']);value=json.loads(path.read_text());value['copy_destination']=str(d/'changed_copy')
                path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):read_bound_job_configs(job)
                host=FakeHost()
                with self.assertRaises(ValueError):launch_wave(manifest,d/'state',host)
                self.assertEqual(host.snapshots,0)
    def test_timeout_includes_cleanup_and_reap(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            m=manifest_at(Path(td));m['jobs'][0]['timeout_seconds']=6600
            with self.assertRaises(ValueError):validate_manifest(m)
    def test_two_process_nfs_lock(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:self.assertTrue(all(verify_nfs_lock(td).values()))

if __name__=='__main__':unittest.main()
