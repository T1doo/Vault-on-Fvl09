import json,tempfile,unittest
from pathlib import Path
import numpy as np
import formal_export as f
import portable_v2 as p

class ExportTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory(prefix='formal-export-fixture-',dir='/nfs_share/lijunhui/Robotwin2/tmp');self.base=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def spec(self,family):
  ids={'F1':['F1-red','F1-green','F1-blue'],'F4':['F4-ABC','F4-ACB','F4-BAC'],'F2':['inside','on','beside']}[family]
  return {'root_id':'synthetic-'+family,'family':family,'spec_sha256':'synthetic-spec-'+family,'programs':[{'program_id':x,'steps':[{'synthetic':True}]} for x in ids],'synthetic':True,'cameras':{'required':['head_camera'],'width':2,'height':2}}
 def native_source(self,family):
  spec=self.spec(family);root=self.base/family;root.mkdir();result={'root_id':spec['root_id'],'pass':True,'synthetic':True};p.write_json(root/'source_result.json',result);p.write_json(root/'native_root.json',{'accepted':True,'synthetic':True});np.savez(root/'prefix.npz',effective_setpoint_actions=np.zeros((1,26)));cells=[]
  for pr in spec['programs']:
   for re in ['r_pc','r_inv_path','r_inv_motion']:
    d=root/(pr['program_id']+'-'+re);d.mkdir();np.savez(d/'raw.npz',stream__realized_qpos=np.zeros((4,38)),stream__realized_qvel=np.zeros((4,38)),stream__controller_effective_setpoint=np.zeros((3,26)));np.savez(d/'current.npz',head_camera=np.zeros((2,2,3),dtype=np.uint8),robot_qpos=np.zeros(76),robot_qvel=np.zeros(76));p.write_json(d/'capture.json',{'spec_sha256':spec['spec_sha256'],'npz_sha256':p.digest(d/'current.npz'),'synthetic':True});p.write_json(d/'anchor.json',{'synthetic':True,'robot_qpos':[0.]*38});p.write_json(d/'branch.json',{'program_id':pr['program_id'],'verifier':{'pass':True,'synthetic':True},'raw_manifest':{'raw_streams_npz_sha256':p.digest(d/'raw.npz')}})
    cells.append({'program_id':pr['program_id'],'realization_id':re,'raw_path':str(d/'raw.npz'),'capture_path':str(d/'capture.json'),'current_arrays_path':str(d/'current.npz'),'anchor_path':str(d/'anchor.json'),'prefix_artifact_path':str(root/'prefix.npz'),'branch_receipt_path':str(d/'branch.json'),'root_receipt_path':str(root/'native_root.json'),'source_result_path':str(root/'source_result.json')})
  return spec,root,cells,result
 def test_two_native_families_nine_cell_seal_copy_read(self):
  for family in ['F1','F4']:
   spec,root,cells,result=self.native_source(family);before={c['raw_path']:p.digest(c['raw_path']) for c in cells};index=f.seal_native_source(root,spec,cells,result);entry=f.copy_sealed_root(index,self.base/(family+'-package'));self.assertTrue(entry['synthetic']);self.assertFalse(entry['formal_eligible'])
   for relative in entry['relative_cell_paths']:
    payload=p.read(self.base/(family+'-package')/relative);self.assertEqual(payload['inputs']['future'].shape,(3,26));self.assertEqual(payload['inputs']['state'].shape,(76,));self.assertNotIn('target',payload['inputs']);self.assertTrue(payload['audit']['synthetic'])
   self.assertTrue(all(p.digest(path)==h for path,h in before.items()))
 def test_native_wrong_source_result_and_incomplete_matrix_refuse(self):
  spec,root,cells,result=self.native_source('F1')
  with self.assertRaises(ValueError):f.seal_native_source(root,spec,cells[:8],result)
  self.assertFalse((root/'source_seal').exists());p.write_json(root/'source_result.json',{'pass':False})
  with self.assertRaises(ValueError):f.seal_native_source(root,spec,cells,result)
  self.assertFalse((root/'source_seal').exists())
 def test_modern_full_seal_copy_chain(self):
  spec=self.spec('F2');root=self.base/'modern';root.mkdir();np.savez(root/'prefix.npz',effective_setpoint=np.zeros((2,26)));cells=[];checks=[]
  for pr in spec['programs']:
   for re in ['r_pc','r_inv_path','r_inv_motion']:
    d=root/(pr['program_id']+'-'+re);cur=d/'current';cur.mkdir(parents=True);np.savez(d/'trace.npz',joint_qpos=np.zeros((4,38)),joint_qvel=np.zeros((4,38)),controller_effective_setpoint=np.zeros((4,26)));np.savez(cur/'rgb.npz',head_camera__rgb=np.zeros((2,2,3),dtype=np.uint8));p.write_json(cur/'state.json',{'joint_qpos':[0.]*38,'joint_qvel':[0.]*38});p.write_json(cur/'anchor.json',{'synthetic':True});p.write_json(cur/'capture_metadata.json',{'required_camera_names':['head_camera'],'camera_images':{'head_camera':{'shape':[2,2,3],'dtype':'uint8'}}});c={'root_id':spec['root_id'],'family':'F2','program_id':pr['program_id'],'realization_id':re,'scene_spec_sha256':spec['spec_sha256'],'candidate_set':spec['programs'],'trace_path':str(d/'trace.npz'),'prefix_artifact_path':str(root/'prefix.npz')};cf={'cell':spec['root_id']+':'+pr['program_id']+':'+re,'trace_sha256':p.digest(d/'trace.npz'),'pass':True,'synthetic':True};p.write_json(d/'cell_receipt.json',c);p.write_json(d/'independent_finalizer_v2.json',cf);cells.append(c);checks.append(cf)
  result={'root_id':spec['root_id'],'scene_spec_sha256':spec['spec_sha256'],'cell_finalizers':checks,'pass':True,'synthetic':True};index=f.seal_modern_source(root,spec,cells,result);entry=f.copy_sealed_root(index,self.base/'modern-package');self.assertEqual(len(entry['cells']),9);self.assertTrue(entry['synthetic'])
if __name__=='__main__':unittest.main()
