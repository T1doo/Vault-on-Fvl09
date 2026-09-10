"""Targeted CPU-only recovery/accounting fault injection; fake host never snapshots GPUs."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import first_wave_launcher as launcher
from test_first_wave_launcher import FakeHost,manifest_at
TMP=Path('/nfs_share/lijunhui/Robotwin2/tmp')

class RecoveryHost(FakeHost):
 def __init__(self):super().__init__();self.calls=0
 def run(self,job,card,directory):
  self.calls+=1;self.used.append(card['physical_index']);out=Path(job['output'])/'r_pc'
  target=out/'root' if self.calls==1 else out/'recovery_2'/'root';target.mkdir(parents=True)
  receipt={'status':'failed_planner','cleanup_records':[{'scene_created':True,'phase':'strict_prefix_branch:F1-red'}],'canonical_prefix_reference_execution_count':1,'suffix_prefix_replay_count':0,'branch_prefix_replay_count':0,'branch_execution_attempt_count':0,'planner_query_count_total':3}
  (target/'root_receipt.json').write_text(json.dumps(receipt))
  return {'returncode':1,'owned_cleanup_pass':True,'host_process_visibility':True,'lease_seconds':1,'launch_mode':job['launch_mode']}

class LauncherRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=TMP,prefix='launcher-recovery-');self.base=Path(self.temp.name);self.manifest=manifest_at(self.base)
  self.manifest['recovery_policy']={'max_gpu_attempts':2,'allowed_failure_classes':['physical_infeasible','transient_execution']}
  self.manifest['cpu_copy_recovery_authorized']=True
  for job in self.manifest['jobs']:job['root_budget_caps']={**job['reservation'],'gpu_lease_seconds':14400}
 def tearDown(self):self.temp.cleanup()
 def first(self,host=None):return launcher.launch_wave(self.manifest,self.base/'state',host or FakeHost(),ready_job_ids=['job0'])
 def test_resume_reuses_shared_budget_and_command_idempotent(self):
  host=RecoveryHost();one=self.first(host);first=one['state']['jobs']['job0'];self.assertEqual(first['failure_class'],'physical_infeasible');self.assertEqual(first['attempt_count'],1)
  raw=self.base/'output0/r_pc/root/root_receipt.json';before=raw.read_bytes()
  request={'job0':{'request_id':'recover-1','mode':'resume','failure_class':'physical_infeasible'}}
  two=launcher.launch_wave(self.manifest,self.base/'state',host,ready_job_ids=['job0'],recovery_requests=request)
  self.assertEqual(host.calls,2);self.assertEqual(two['state']['jobs']['job0']['attempt_count'],2);self.assertEqual(raw.read_bytes(),before)
  self.assertEqual(two['state']['budget']['consumed']['fresh_scenes'],2);self.assertEqual(two['state']['budget']['consumed']['solver_problems'],6)
  before_snaps=host.snapshots;again=launcher.launch_wave(self.manifest,self.base/'state',host,ready_job_ids=['job0'],recovery_requests=request);self.assertTrue(again['idempotent']);self.assertEqual(host.snapshots,before_snaps)
  request['job0']['request_id']='recover-2'
  with self.assertRaises(ValueError):launcher.launch_wave(self.manifest,self.base/'state',host,ready_job_ids=['job0'],recovery_requests=request)
 def test_source_or_spec_mutation_blocks_resume(self):
  host=RecoveryHost();self.first(host);job=self.manifest['jobs'][0];Path(job['spec_path']).write_text('{}');count=host.snapshots
  with self.assertRaises(ValueError):launcher.launch_wave(self.manifest,self.base/'state',host,ready_job_ids=['job0'],recovery_requests={'job0':{'request_id':'r','mode':'resume','failure_class':'physical_infeasible'}})
  self.assertEqual(host.snapshots,count)
 def test_acquire_followed_by_state_write_failure_preserves_clock(self):
  original=launcher.evidence
  def fail(path,data):
   if Path(path).name=='pre_snapshot.json':raise OSError('injected after acquire')
   return original(path,data)
  host=FakeHost()
  with patch('first_wave_launcher.evidence',fail):result=self.first(host)
  folder=self.base/'state/jobs/job0/attempt_1';start=json.loads((folder/'lease_acquired.json').read_text());end=json.loads((folder/'lease_terminal.json').read_text())
  self.assertTrue(start['gpu_uuid']);self.assertEqual(start['host'],end['acquired']['host']);self.assertTrue(end['release_confirmed']);self.assertGreaterEqual(end['lease_seconds'],0);self.assertEqual(host.used,[]);self.assertFalse(any(result['state']['budget']['reserved'].values()))
 def test_usage_failure_and_coordinator_restart_settle_once(self):
  with patch('first_wave_launcher.usage_from_receipts',side_effect=RuntimeError('injected parser failure')):result=self.first()
  self.assertEqual(result['state']['status'],'UNRESOLVED');folder=self.base/'state/jobs/job0/attempt_1';self.assertTrue((folder/'lease_terminal.json').is_file());self.assertFalse(any(result['state']['budget']['consumed'].values()))
  fixed=launcher.reconcile_saved_attempts(self.manifest,self.base/'state');self.assertEqual(fixed['budget']['consumed']['fresh_scenes'],33);self.assertFalse(any(fixed['budget']['reserved'].values()))
  again=launcher.reconcile_saved_attempts(self.manifest,self.base/'state');self.assertEqual(again['budget'],fixed['budget'])
 def test_post_snapshot_failure_keeps_measured_terminal(self):
  class PostFails(FakeHost):
   def snapshot(self):
    if self.used:raise OSError('injected post snapshot error')
    return super().snapshot()
  result=self.first(PostFails());folder=self.base/'state/jobs/job0/attempt_1';end=json.loads((folder/'lease_terminal.json').read_text());self.assertTrue(end['release_confirmed']);self.assertTrue(end['owned_cleanup_pass']);self.assertTrue(end['post_snapshot_error']);self.assertEqual(result['state']['budget']['consumed']['fresh_scenes'],33)
 def test_settle_failure_recovers_exact_saved_usage(self):
  from controlled_multi_future.redesign_f2_f3_v2.execution_ledger_v2 import ExecutionLedgerV2
  with patch.object(ExecutionLedgerV2,'settle',side_effect=OSError('injected settle fail')):result=self.first()
  folder=self.base/'state/jobs/job0/attempt_1';self.assertTrue((folder/'actual_usage.json').is_file());self.assertTrue((folder/'lease_terminal.json').is_file());self.assertEqual(result['state']['status'],'UNRESOLVED')
  recovered=launcher.reconcile_saved_attempts(self.manifest,self.base/'state');self.assertEqual(recovered['budget']['consumed']['fresh_scenes'],33)
 def test_unconfirmed_release_retains_unknown_not_current_time(self):
  class NoRelease(FakeHost):
   def release(self,lease):return {'released':False,'reason':'injected unconfirmed release'}
  result=self.first(NoRelease());folder=self.base/'state/jobs/job0/attempt_1';end=json.loads((folder/'lease_terminal.json').read_text());self.assertIsNone(end['ended']);self.assertIsNone(end['lease_seconds']);self.assertEqual(result['state']['status'],'UNRESOLVED')
  with self.assertRaises(RuntimeError):launcher.reconcile_saved_attempts(self.manifest,self.base/'state')
 def test_backend_exception_without_cleanup_not_assumed_no_child(self):
  class Crash(FakeHost):
   def run(self,*args):raise RuntimeError('unknown child state')
  host=Crash();result=self.first(host);self.assertEqual(host.released,[]);self.assertEqual(result['state']['status'],'UNRESOLVED')
 def test_copy_only_does_not_construct_backend_or_snapshot(self):
  result=self.first();path=self.base/'state/STATE.json';state=json.loads(path.read_text());job=state['jobs']['job0'];job.update(status='COPY_FAILED',root_collection_verified=True);path.write_text(json.dumps(state))
  class ForbiddenHost(FakeHost):
   def snapshot(self):raise AssertionError('copy-only must not snapshot')
   def acquire(self,*a):raise AssertionError('copy-only must not acquire')
  before=copy.deepcopy(result['state']['budget'])
  with patch('execution_cli.copy_only',return_value={'pass':True}),patch('first_wave_launcher.verify_completed_job',return_value={'pass':True}):
   copied=launcher.launch_wave(self.manifest,self.base/'state',ForbiddenHost(),copy_only_job_ids=['job0'])
   repeated=launcher.launch_wave(self.manifest,self.base/'state',ForbiddenHost(),copy_only_job_ids=['job0'])
  self.assertEqual(copied['state']['budget'],before);self.assertTrue(repeated['results'][0]['idempotent']);self.assertEqual(copied['state']['jobs']['job0']['status'],'PASS')
if __name__=='__main__':unittest.main()

class CompatibilityTests(unittest.TestCase):
 def test_reviewed_source_rebind_and_re_signed_science_rejected(self):
  from file_source_pin import inventory,bundle_hash
  import hashlib
  with tempfile.TemporaryDirectory(dir=TMP,prefix='compatibility-fixture-') as td:
   base=Path(td);manifest=manifest_at(base);new_files=inventory();changed=str(Path(launcher.__file__).resolve());old_files=dict(new_files);old_files[changed]='0'*64
   manifest.update(source_files=old_files,source_bundle_sha256=bundle_hash(old_files))
   original=manifest['jobs'][0];oldauth=json.loads(Path(original['authorization_path']).read_text());oldauth.update(source_files=old_files,source_bundle_sha256=bundle_hash(old_files),implementation_source_sha256='old-fixture-source')
   Path(original['authorization_path']).write_text(json.dumps(oldauth));original['authorization_file_sha256']=hashlib.sha256(Path(original['authorization_path']).read_bytes()).hexdigest()
   spec=json.loads(Path(original['spec_path']).read_text());proof={'schema':'f1_source_compatibility_v1','status':'CPU_REVIEWED_APPLICABLE','root_id':original['root_id'],'spec_sha256':spec['spec_sha256'],'old_source_sha256':'old-fixture-source','new_source_sha256':'new-fixture-source','old_source_bundle_sha256':bundle_hash(old_files),'new_source_bundle_sha256':bundle_hash(new_files),'scientific_contract_unchanged':True,'changed_files':[changed],'affected_contracts':{changed:'explicit synthetic source-only fixture; science unchanged'},'accepted_cells':[]}
   proofpath=base/'proof.json';proofpath.write_text(json.dumps(proof));binding={'path':str(proofpath),'sha256':hashlib.sha256(proofpath.read_bytes()).hexdigest()}
   auth={**oldauth,'source_files':new_files,'source_bundle_sha256':bundle_hash(new_files),'implementation_source_sha256':'new-fixture-source','source_compatibility_receipt':binding};ap=base/'newauth.json';ap.write_text(json.dumps(auth));replacement={**original,'authorization_path':str(ap),'authorization_file_sha256':hashlib.sha256(ap.read_bytes()).hexdigest()}
   appendix={'schema':'f1_runtime_compatibility_appendix_v1','status':'CPU_REVIEWED_APPLICABLE','manifest_sha256':launcher.hash_json(manifest),'old_source_bundle_sha256':bundle_hash(old_files),'source_files':new_files,'source_bundle_sha256':bundle_hash(new_files),'changed_files':[changed],'affected_contracts':proof['affected_contracts'],'jobs':[replacement]}
   path=base/'appendix.json';path.write_text(json.dumps(appendix));ref={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
   validated=launcher.validate_compatibility(manifest,base/'state',ref);self.assertEqual(validated['applicable_job_ids'],['job0']);self.assertEqual(validated['source_bundle_sha256'],bundle_hash(new_files));self.assertEqual(manifest['source_files'][changed],'0'*64)
   badspec=copy.deepcopy(spec);badspec['seed']+=1;badspec['spec_sha256']=launcher.hash_json({k:v for k,v in badspec.items() if k!='spec_sha256'});sp=base/'changed_spec.json';sp.write_text(json.dumps(badspec));appendix['jobs'][0]['spec_path']=str(sp);appendix['jobs'][0]['spec_file_sha256']=hashlib.sha256(sp.read_bytes()).hexdigest();path.write_text(json.dumps(appendix));ref['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
   with self.assertRaises(ValueError):launcher.validate_compatibility(manifest,base/'state',ref)

class LateEdgeTests(unittest.TestCase):
 def test_current_failure_not_old_history_and_stale_pass(self):
  with tempfile.TemporaryDirectory(dir=TMP,prefix='classify-fixture-') as td:
   root=Path(td);base=root/'r_pc';(base/'root').mkdir(parents=True);(base/'root/root_receipt.json').write_text(json.dumps({'status':'failed_planner'}));(base/'recovery_2/root').mkdir(parents=True);(base/'recovery_2/root/root_receipt.json').write_text(json.dumps({'status':'failed_verifier'}));(base/'cohort_pointer.json').write_text(json.dumps({'status':'failed_verifier','root_relative':'recovery_2/root'}));(root/'checkpoint.json').write_text(json.dumps({'status':'FAILED','active_realization':'r_pc'}));(root/'independent_structure.json').write_text(json.dumps({'pass':True}))
   self.assertEqual(launcher._classify(root,{'returncode':1}),'shared_interface_error')
   (base/'root/root_receipt.json').write_text(json.dumps({'status':'failed_verifier'}));(base/'recovery_2/root/root_receipt.json').write_text(json.dumps({'status':'failed_planner'}));self.assertEqual(launcher._classify(root,{'returncode':1}),'physical_infeasible')
 def test_busy_without_child_defers_and_does_not_consume_attempt(self):
  class Busy(FakeHost):
   def __init__(self):super().__init__();self.acquire_count=0
   def acquire(self,*args):
    self.acquire_count+=1
    if self.acquire_count==1:raise BlockingIOError('busy project lease')
    return super().acquire(*args)
  with tempfile.TemporaryDirectory(dir=TMP,prefix='busy-fixture-') as td:
   d=Path(td);m=manifest_at(d);m['jobs'][0]['root_budget_caps']={**m['jobs'][0]['reservation'],'gpu_lease_seconds':14400};host=Busy();first=launcher.launch_wave(m,d/'state',host,ready_job_ids=['job0']);self.assertEqual(first['state']['jobs']['job0']['status'],'DEFERRED_READY');self.assertEqual(first['state']['jobs']['job0']['attempt_count'],0);self.assertEqual(host.used,[]);self.assertFalse(any(first['state']['budget']['consumed'].values()))
   second=launcher.launch_wave(m,d/'state',host,ready_job_ids=['job0']);self.assertEqual(second['state']['jobs']['job0']['attempt_count'],1);self.assertEqual(second['state']['budget']['consumed']['fresh_scenes'],33)
 def test_outer_prelease_rejection_has_receipt(self):
  with tempfile.TemporaryDirectory(dir=TMP,prefix='prelease-fixture-') as td:
   d=Path(td);m=manifest_at(d);m['jobs'][0]['root_budget_caps']={**m['jobs'][0]['reservation'],'gpu_lease_seconds':1};host=FakeHost();result=launcher.launch_wave(m,d/'state',host,ready_job_ids=['job0']);self.assertEqual(result['state']['jobs']['job0']['status'],'FAILED');self.assertEqual(host.used,[]);self.assertTrue(list((d/'state/jobs/job0').glob('outer_exception_*.json')))

class NativeTerminalClassificationTests(unittest.TestCase):
 def test_real_terminal_enum_is_finite_and_shared_failures_stop(self):
  with tempfile.TemporaryDirectory(dir=TMP,prefix='terminal-enum-') as td:
   root=Path(td);r=root/'r_pc/root';r.mkdir(parents=True)
   mapping={'failed_task_physical_feasibility':'physical_infeasible','failed_planner':'physical_infeasible','failed_execution':'transient_execution','failed_family_suffix_gate':'shared_interface_error','failed_canonical_prefix_reference':'shared_interface_error','failed_prefix_replay_gate':'shared_interface_error','failed_cleanup_uncertain':'shared_interface_error','failed_candidate_mutation':'shared_interface_error','failed_required_video':'shared_interface_error','future_unknown_enum':'unknown'}
   for status,expected in mapping.items():
    (r/'root_receipt.json').write_text(json.dumps({'status':status}));self.assertEqual(launcher._classify(root,{'returncode':1}),expected,status)
   (r/'root_receipt.json').write_text(json.dumps({'status':'failed_verifier','branch_receipts':[{'status':'failed_execution'}]}));self.assertEqual(launcher._classify(root,{'returncode':1}),'transient_execution')
   (r/'root_receipt.json').write_text(json.dumps({'status':'failed_verifier','branch_receipts':[{'status':'failed_independent_cell'}]}));self.assertEqual(launcher._classify(root,{'returncode':1}),'shared_interface_error')

class PersistenceFinalizersTests(unittest.TestCase):
 def test_child_end_write_failure_never_skips_owned_reap(self):
  from types import SimpleNamespace
  import os
  class Process:
   pid=999001
   returncode=None
   reaped=False
   waited=False
   def poll(self):
    if self.returncode is not None:self.reaped=True
    return self.returncode
   def wait(self,timeout=None):self.waited=True;self.reaped=True;return self.returncode
   def kill(self):self.returncode=-9
  process=Process();killed=[];original=launcher.evidence
  def persist(path,value):
   if Path(path).name=='child_end.json':raise OSError('injected diagnostic write failure')
   return original(path,value)
  def ps(*args,**kwargs):return SimpleNamespace(stdout='' if process.reaped else '999001 1 999001 Mon Jan 1 00:00:00 2026 python\n')
  def kill(pid,sig):killed.append(pid);process.returncode=-sig
  with tempfile.TemporaryDirectory(dir=TMP,prefix='reap-fixture-') as td:
   with patch('first_wave_launcher.subprocess.Popen',return_value=process),patch('first_wave_launcher.subprocess.run',side_effect=ps),patch('first_wave_launcher.os.kill',side_effect=kill),patch('first_wave_launcher.evidence',side_effect=persist),patch('first_wave_launcher.time.sleep',return_value=None):
    r=launcher.HostBackend().run({'spec_path':'fixture','authorization_path':'fixture','output':td,'timeout_seconds':0,'cleanup_grace_seconds':4},{'gpu_uuid':'GPU-fixture','physical_index':1},Path(td))
   self.assertTrue(process.waited);self.assertTrue(r['owned_cleanup_pass']);self.assertIn(999001,killed);self.assertTrue(any(x['file']=='child_end.json' for x in r['persistence_errors']))
 def test_release_write_failure_still_preserves_measured_terminal(self):
  with tempfile.TemporaryDirectory(dir=TMP,prefix='release-write-') as td:
   d=Path(td);m=manifest_at(d);original=launcher.evidence
   def persist(path,value):
    if Path(path).name=='lease_release.json':raise OSError('release receipt write failed')
    return original(path,value)
   with patch('first_wave_launcher.evidence',side_effect=persist):r=launcher.launch_wave(m,d/'state',FakeHost(),ready_job_ids=['job0'])
   folder=d/'state/jobs/job0/attempt_1';end=json.loads((folder/'lease_terminal.json').read_text());self.assertTrue(end['release_confirmed']);self.assertIsInstance(end['lease_seconds'],int);self.assertTrue((folder/'lease_persistence_errors.json').is_file());self.assertFalse(any(r['state']['budget']['reserved'].values()))
