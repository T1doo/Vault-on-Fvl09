"""Actual launcher/CLI/finalizer/export/copy with a labelled synthetic simulator boundary."""
import contextlib,hashlib,io,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import first_wave_launcher as launcher
from test_first_wave_launcher import FakeHost,manifest_at
TMP=Path('/nfs_share/lijunhui/Robotwin2/tmp')
class CpuPipelineHost(FakeHost):
 synthetic_cpu_backend=True
 def run(self,job,card,directory):
  from execution_cli import main
  from fixture_f1_backend import make_backend
  self.used.append(card['physical_index']);argv=['--spec',job['spec_path'],'--authorization',job['authorization_path'],'--output',job['output'],'--collect-only']
  if job.get('launch_mode')=='resume':argv.append('--resume')
  code=0;error=None
  try:
   with patch('native_f1.native_adapter',getattr(self,'factory',make_backend)),contextlib.redirect_stdout(io.StringIO()):
    result=main(argv)
   code=0 if result['pass'] else 1
  except BaseException as exc:code=1;error=str(exc)
  return {'returncode':code,'error':error,'owned_cleanup_pass':True,'host_process_visibility':True,'lease_seconds':1,'launched':True,'synthetic_cpu_backend':True}
class RealPipelineRecoveryTests(unittest.TestCase):
 def test_copy_failure_then_cpu_only_recovery_preserves_real_saved_raw(self):
  import f1_portable_export,portable_v2
  with tempfile.TemporaryDirectory(dir=TMP,prefix='real-launcher-copy-') as td:
   d=Path(td);m=manifest_at(d);m.update(test_only=True,cpu_copy_recovery_authorized=True,max_copy_workers=1)
   for j in m['jobs']:
    ap=Path(j['authorization_path']);a=json.loads(ap.read_text());a['implementation_source_sha256']='explicit-synthetic-native-source';ap.write_text(json.dumps(a));j['authorization_file_sha256']=hashlib.sha256(ap.read_bytes()).hexdigest();j['root_budget_caps']={**j['reservation'],'gpu_lease_seconds':14400}
   host=CpuPipelineHost();original_copy=f1_portable_export.copy_root
   with patch('f1_portable_export.copy_root',side_effect=OSError('injected only copy failure')):first=launcher.launch_wave(m,d/'state',host,ready_job_ids=['job0'])
   job=first['state']['jobs']['job0'];self.assertEqual(job['status'],'COPY_FAILED',job);self.assertTrue(job['root_collection_verified']);self.assertTrue(job['owned_cleanup_pass']);self.assertTrue(job['release_confirmed']);self.assertFalse(any(first['state']['budget']['reserved'].values()))
   raws={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (d/'output0').glob('**/raw/raw_streams.npz')};self.assertEqual(len(raws),9)
   accepted_report=d/'output0/independent_structure.json';accepted_hash=hashlib.sha256(accepted_report.read_bytes()).hexdigest()
   before=first['state']['budget'];host.snapshots=0
   with patch.object(host,'snapshot',side_effect=AssertionError('CPU-only retry used GPU snapshot')),patch.object(host,'run',side_effect=AssertionError('CPU-only retry reran robot')):
    recovered=launcher.launch_wave(m,d/'state',host,copy_only_job_ids=['job0']);again=launcher.launch_wave(m,d/'state',host,copy_only_job_ids=['job0'])
   self.assertEqual(recovered['state']['jobs']['job0']['status'],'PASS');self.assertEqual(before,recovered['state']['budget']);self.assertTrue(again['results'][0]['idempotent'])
   self.assertEqual(raws,{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in raws});self.assertEqual(hashlib.sha256(accepted_report.read_bytes()).hexdigest(),accepted_hash)
   root=d/'copy0';group=json.loads((root/'root_manifest.json').read_text());self.assertEqual(len(group['cells']),9);portable_v2.read_root(root)
 def test_actual_launcher_partial_failure_and_resume_keeps_accepted_bytes(self):
  from fixture_f1_backend import make_backend
  class PartialHost(CpuPipelineHost):
   def __init__(self):super().__init__();self.failed=False;self.executed=[]
   def factory(self,**kwargs):
    backend=make_backend(**kwargs);original=backend.execute_frozen_suffix_spec
    def execute(scene,program,execution_spec,replay,realization_spec):
     self.executed.append((kwargs['realization'],program['program_id']))
     if not self.failed and kwargs['realization']=='r_pc' and program['program_id']=='F1-green':
      self.failed=True;raise RuntimeError('explicit synthetic transient control failure')
     return original(scene,program,execution_spec,replay,realization_spec)
    backend.execute_frozen_suffix_spec=execute;return backend
  with tempfile.TemporaryDirectory(dir=TMP,prefix='actual-launcher-resume-') as td:
   d=Path(td);m=manifest_at(d);m.update(test_only=True,cpu_copy_recovery_authorized=True,recovery_policy={'max_gpu_attempts':2,'allowed_failure_classes':['physical_infeasible','transient_execution']})
   for j in m['jobs']:
    ap=Path(j['authorization_path']);auth=json.loads(ap.read_text());auth['implementation_source_sha256']='explicit-synthetic-native-source';ap.write_text(json.dumps(auth));j['authorization_file_sha256']=hashlib.sha256(ap.read_bytes()).hexdigest();j['root_budget_caps']={**j['reservation'],'gpu_lease_seconds':14400}
   host=PartialHost();first=launcher.launch_wave(m,d/'state',host,ready_job_ids=['job0']);job=first['state']['jobs']['job0'];self.assertEqual(job['status'],'FAILED',job);self.assertEqual(job['failure_class'],'transient_execution',job)
   raw=d/'output0/r_pc/root/branches/F1-red/raw/raw_streams.npz';sha=hashlib.sha256(raw.read_bytes()).hexdigest();self.assertFalse((d/'output0/r_pc/root/branches/F1-blue').exists())
   req={'job0':{'request_id':'actual-resume-1','failure_class':'transient_execution','mode':'resume'}};resumed=launcher.launch_wave(m,d/'state',host,ready_job_ids=['job0'],recovery_requests=req)
   self.assertEqual(resumed['state']['jobs']['job0']['status'],'PASS',resumed['state']['jobs']['job0']);self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(),sha);self.assertEqual(host.executed.count(('r_pc','F1-red')),1);self.assertEqual(resumed['state']['jobs']['job0']['attempt_count'],2)
   before=host.snapshots;again=launcher.launch_wave(m,d/'state',host,ready_job_ids=['job0'],recovery_requests=req);self.assertTrue(again['idempotent']);self.assertEqual(host.snapshots,before)

if __name__=='__main__':unittest.main()

class SourceCompatibilityPipelineTests(unittest.TestCase):
 def test_source_only_review_rebind_preserves_accepted_cell(self):
  import file_source_pin
  from fixture_f1_backend import make_backend
  class Partial(CpuPipelineHost):
   def __init__(self):super().__init__();self.failed=False
   def factory(self,**kwargs):
    backend=make_backend(**kwargs);original=backend.execute_frozen_suffix_spec
    def execute(scene,program,execution_spec,replay,realization_spec):
     if not self.failed and kwargs['realization']=='r_pc' and program['program_id']=='F1-green':self.failed=True;raise RuntimeError('explicit fixture failure')
     return original(scene,program,execution_spec,replay,realization_spec)
    backend.execute_frozen_suffix_spec=execute;return backend
  with tempfile.TemporaryDirectory(dir=TMP,prefix='source-compatible-pipeline-') as td:
   d=Path(td);marker=d/'isolated_runtime_version.py';marker.write_text('# explicitly synthetic version one\n');original_paths=file_source_pin.runtime_paths()
   with patch('file_source_pin.runtime_paths',return_value=original_paths|{marker}):
    manifest=manifest_at(d);manifest.update(test_only=True,cpu_copy_recovery_authorized=True,recovery_policy={'max_gpu_attempts':2,'allowed_failure_classes':['transient_execution']})
    for job in manifest['jobs']:
     ap=Path(job['authorization_path']);auth=json.loads(ap.read_text());auth['implementation_source_sha256']='explicit-synthetic-native-source';ap.write_text(json.dumps(auth));job['authorization_file_sha256']=hashlib.sha256(ap.read_bytes()).hexdigest();job['root_budget_caps']={**job['reservation'],'gpu_lease_seconds':14400}
    host=Partial();first=launcher.launch_wave(manifest,d/'state',host,ready_job_ids=['job0']);self.assertEqual(first['state']['jobs']['job0']['status'],'FAILED')
    job=manifest['jobs'][0];spec=json.loads(Path(job['spec_path']).read_text());oldauth=json.loads(Path(job['authorization_path']).read_text());raw=d/'output0/r_pc/root/branches/F1-red/raw/raw_streams.npz';manifest_path=raw.parent/'manifest.json';capture=Path(json.loads(manifest_path.read_text())['provenance']['formal_current_capture_path']);saved_sha=hashlib.sha256(raw.read_bytes()).hexdigest()
    marker.write_text('# explicitly synthetic version two; physics code unchanged\n');new_files=file_source_pin.inventory();new_bundle=file_source_pin.bundle_hash(new_files);request={'job0':{'request_id':'explicit-reviewed-source-resume','mode':'resume','failure_class':'transient_execution'}};snapshots=host.snapshots
    with self.assertRaises(ValueError):launcher.launch_wave(manifest,d/'state',host,ready_job_ids=['job0'],recovery_requests=request)
    self.assertEqual(host.snapshots,snapshots)
    accepted={'program_id':'F1-red','realization_id':'r_pc','raw_path':str(raw),'raw_sha256':saved_sha,'manifest_path':str(manifest_path),'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'capture_path':str(capture),'capture_sha256':hashlib.sha256(capture.read_bytes()).hexdigest()};changed=[str(marker)];assessment={str(marker):'explicit synthetic source marker only; scene, code behavior and scientific spec unchanged'}
    proof={'schema':'f1_source_compatibility_v1','status':'CPU_REVIEWED_APPLICABLE','root_id':job['root_id'],'spec_sha256':spec['spec_sha256'],'old_source_sha256':oldauth['implementation_source_sha256'],'new_source_sha256':oldauth['implementation_source_sha256'],'old_source_bundle_sha256':oldauth['source_bundle_sha256'],'new_source_bundle_sha256':new_bundle,'scientific_contract_unchanged':True,'changed_files':changed,'affected_contracts':assessment,'accepted_cells':[accepted]};pp=d/'reviewed_root_compatibility.json';pp.write_text(json.dumps(proof));pb={'path':str(pp),'sha256':hashlib.sha256(pp.read_bytes()).hexdigest()}
    ap=d/'reviewed_new_authorization.json';ap.write_text(json.dumps({**oldauth,'source_files':new_files,'source_bundle_sha256':new_bundle,'source_compatibility_receipt':pb}));replacement={**job,'authorization_path':str(ap),'authorization_file_sha256':hashlib.sha256(ap.read_bytes()).hexdigest()}
    appendix={'schema':'f1_runtime_compatibility_appendix_v1','status':'CPU_REVIEWED_APPLICABLE','manifest_sha256':launcher.hash_json(manifest),'old_source_bundle_sha256':manifest['source_bundle_sha256'],'source_files':new_files,'source_bundle_sha256':new_bundle,'changed_files':changed,'affected_contracts':assessment,'jobs':[replacement]};path=d/'reviewed_compatibility_appendix.json';path.write_text(json.dumps(appendix));binding={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    resumed=launcher.launch_wave(manifest,d/'state',host,ready_job_ids=['job0'],recovery_requests=request,compatibility_ref=binding);self.assertEqual(resumed['state']['jobs']['job0']['status'],'PASS',resumed['state']['jobs']['job0']);self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(),saved_sha);self.assertEqual(resumed['state']['contract_sha256'],launcher.hash_json(manifest))
