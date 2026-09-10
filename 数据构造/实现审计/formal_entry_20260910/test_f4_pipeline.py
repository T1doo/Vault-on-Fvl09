import sys,json,tempfile,unittest,hashlib,subprocess
from pathlib import Path
from unittest.mock import patch
import numpy as np
HERE=Path(__file__).resolve().parent
LIVE='/nfs_share/lijunhui/Robotwin2/project/RoboTwin'
if LIVE not in sys.path:sys.path.insert(0,LIVE)
import scene_plan as s
import native_f4 as native
import fixture_f4_backend as fixture
import family_entry
import file_source_pin
import formal_export
import portable_v2

class F4Pipeline(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='f4-lifecycle-synthetic-',dir='/nfs_share/lijunhui/Robotwin2/tmp');self.base=Path(self.tmp.name);self.spec=s.resolve(next(x for x in s.generate()['slots'] if x['family']=='F4'));self.spec['synthetic']=True;self.spec['spec_sha256']=s.hash_json({k:v for k,v in self.spec.items() if k!='spec_sha256'});self.events=[]
  q=self.base/'qualification.json';q.write_text(json.dumps(fixture.fixture_qualification(self.spec)));files=file_source_pin.inventory();self.authorization={'gpu_execution_authorized':True,'synthetic_fixture':True,'spec_sha256':self.spec['spec_sha256'],'source_files':files,'source_bundle_sha256':file_source_pin.bundle_hash(files),'implementation_source_sha256':'f'*64,'f4_qualification':{'path':str(q),'sha256':hashlib.sha256(q.read_bytes()).hexdigest()}}
 def tearDown(self):self.tmp.cleanup()
 def run_fixture(self,fail=None):
  def boundary(spec,realization,output,source_sha,qualification):return fixture.make_backend(spec,realization,output,source_sha,qualification,events=self.events,fail_program=fail if realization=='r_pc' else None)
  with patch.object(native,'native_adapter',boundary):return family_entry.run_family_root(spec=self.spec,output=self.base/'root',authorization=self.authorization)
 def test_whole_nine_to_independent_semantics_export_copy(self):
  result=self.run_fixture();self.assertTrue(result['pass'],result);self.assertFalse(result['research_eligible']);self.assertFalse(result['native_physical_evidence']);self.assertEqual(len(self.events),9);self.assertTrue(result['independent_semantic_recomputed']);self.assertTrue(result['full_terminal_equivalence']['pass'])
  cells=[]
  for realization in native.REALIZATIONS:
   root=family_entry.cohort_root(self.base/'root',realization)
   for program in native.PROGRAMS:
    branch=root/'branches'/program;raw=branch/'raw';m=json.loads((raw/'manifest.json').read_text());capture=Path(m['provenance']['formal_current_capture_path']);cells.append({'program_id':program,'realization_id':realization,'raw_path':str(raw/'raw_streams.npz'),'capture_path':str(capture),'current_arrays_path':str(capture.parent/'current.npz'),'anchor_path':str(capture.parent/'anchor.json'),'prefix_artifact_path':str(root/'canonical_prefix_artifact/prefix_arrays.npz'),'branch_receipt_path':str(branch/'receipt.json'),'root_receipt_path':str(root/'root_receipt.json'),'source_result_path':str(self.base/'root/f4_native_result.json')})
  index=formal_export.seal_native_source(self.base/'export',self.spec,cells,result);entry=formal_export.copy_sealed_root(index,self.base/'package');self.assertTrue(entry['synthetic']);self.assertFalse(entry['formal_eligible']);self.assertEqual(len(entry['cells']),9)
  for relative in entry['relative_cell_paths']:
   payload=portable_v2.read(self.base/'package'/relative);self.assertEqual(payload['inputs']['state'].shape,(76,));self.assertTrue(payload['audit']['synthetic']);self.assertEqual(len(payload['inputs']['candidate_set']),3)
  script='''import sys,json,pathlib,importlib.util,numpy
base=pathlib.Path(sys.argv[1]);package=base/'package';manifest=json.loads((package/'root_manifest.json').read_text());reader=package/manifest['relative_cell_paths'][0]/'reader.py';spec=importlib.util.spec_from_file_location('bundled_reader',reader);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def deny(event,args):
 if event=='open' and isinstance(args[0],(str,bytes)):
  path=pathlib.Path(args[0]).resolve()
  if any(path.is_relative_to(base/name) for name in ['root','export','package_cells']):raise PermissionError('original fixture source inaccessible')
sys.addaudithook(deny)
for relative in manifest['relative_cell_paths']:
 payload=module.read(package/relative)
 assert payload['audit']['synthetic'] is True and payload['inputs']['state'].shape==(76,)
print(len(manifest['relative_cell_paths']))
'''
  check=subprocess.run([sys.executable,'-c',script,str(self.base)],capture_output=True,text=True);self.assertEqual(check.returncode,0,check.stderr);self.assertEqual(check.stdout.strip(),'9')
  self.assertFalse({'torch','sapien','curobo'}&set(sys.modules))
 def test_failure_stops_and_recovery_only_missing_cells(self):
  with self.assertRaises((RuntimeError,ValueError)):self.run_fixture(fail='F4-ACB')
  self.assertTrue(all(r=='r_pc' for r,p in self.events));self.assertEqual(self.events.count(('r_pc','F4-ABC')),1);self.authorization.update(recovery_authorized=True,owned_cleanup_reconciled=True)
  result=self.run_fixture();self.assertTrue(result['pass'],result);self.assertFalse(result['research_eligible']);self.assertEqual(self.events.count(('r_pc','F4-ABC')),1);self.assertEqual(self.events.count(('r_pc','F4-ACB')),2)
if __name__=='__main__':unittest.main()
