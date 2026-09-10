import copy,json,tempfile,unittest
from pathlib import Path
from unittest import mock
import scene_plan, file_source_pin,native_f2f3,native_cells,fixture_modern_backend
from controlled_multi_future.redesign_f2_f3_v2.canonical import atomic_write_json,sha256_file
class ModernPipeline(unittest.TestCase):
 def run_family(self,f):
  spec=scene_plan.resolve(next(s for s in scene_plan.generate()['slots'] if s['family']==f));spec['synthetic']=True;spec['spec_sha256']=scene_plan.hash_json({k:v for k,v in spec.items() if k!='spec_sha256'})
  with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as tmp:
   t=Path(tmp);source=file_source_pin.inventory();e=t/'qualification_evidence.json';atomic_write_json(e,{'synthetic':True});q=t/'qualification.json';atomic_write_json(q,{'spec_sha256':spec['spec_sha256'],'programs':[p['program_id'] for p in spec['programs']],'pass':True,'source_files':source,'evidence':[{'path':str(e),'sha256':sha256_file(e)} for _ in range(6)],'synthetic':True})
   auth={'gpu_execution_authorized':True,'spec_sha256':spec['spec_sha256'],'source_files':source,'source_bundle_sha256':file_source_pin.bundle_hash(source),'qualification':{'path':str(q),'sha256':sha256_file(q)},'copy_destination':str(t/'copy')}
   # Only the physical cell engine is replaced. Native root state machine,
   # disk finalizers, source seal, portable copy/reader remain the real functions.
   with mock.patch.object(native_cells,'_f2_cell',fixture_modern_backend.cell),mock.patch.object(native_cells,'_f3_cell',fixture_modern_backend.cell):
    result=native_f2f3.run_native_root(spec,t/'root',auth)
   self.assertTrue(result['pass'],result['checks'])
   self.assertTrue(result['copy']['synthetic']);self.assertFalse(result['physics_verified'])
   self.assertEqual(len(result['cell_finalizers']),9)
   from portable_v2 import read
   self.assertEqual(read(t/'copy/cell_0')['inputs']['state'].shape,(76,))
 def test_f2_full_root(self):self.run_family('F2')
 def test_f3_full_root(self):self.run_family('F3')
if __name__=='__main__':unittest.main()
