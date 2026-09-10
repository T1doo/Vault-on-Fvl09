import json,tempfile,unittest
from pathlib import Path
import numpy as np
import portable_v2 as p

class PortableTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp',prefix='portable-v2-test-');self.base=Path(self.tmp.name);self.src=self.base/'src';self.src.mkdir();self.spec={'schema':'portable_cell_v2','cell_key':'synthetic:inside:r_pc','root_id':'synthetic','scene_spec_sha256':'fixture-spec','index_sha256':'','family':'F2','program_id':'inside','realization_id':'r_pc','adapter':'modern','eligibility':'synthetic_fixture','synthetic':True,'formal_eligible':False,'sources':{},'candidates':[{'program_id':x} for x in ['inside','on','beside']],'target':{'program_id':'inside'},'rgb_contract':{'head__rgb':{'shape':[2,2,3],'dtype':'uint8'}},'trace_layout':'N_plus_1_initial_placeholder'}
  np.savez(self.src/'trace.npz',joint_qpos=np.zeros((3,38)),joint_qvel=np.zeros((3,38)),controller_effective_setpoint=np.zeros((3,26)))
  np.savez(self.src/'rgb.npz',head__rgb=np.zeros((2,2,3),dtype=np.uint8))
  for role,data in {'state':{'joint_qpos':[0.]*38,'joint_qvel':[0.]*38},'cell_receipt':{'family':'F2','program_id':'inside','realization_id':'r_pc'},'anchor':{'fixture':True},'capture':{'required_camera_names':['head'],'camera_images':{'head':{'shape':[2,2,3],'dtype':'uint8'}}},'root_receipt':{'fixture':True},'source_index':{'fixture':True},'cell_finalizer':{'pass':True,'synthetic':True},'root_finalizer':{'pass':True,'synthetic':True}}.items():p.write_json(self.src/(role+'.json'),data)
  np.savez(self.src/'prefix.npz',effective_setpoint_actions=np.zeros((2,26)))
  c={'family':'F2','program_id':'inside','realization_id':'r_pc','root_id':'synthetic','scene_spec_sha256':'fixture-spec','candidate_set':self.spec['candidates']};p.write_json(self.src/'cell_receipt.json',c)
  self.cfs=[{'pass':True,'cell':'synthetic:'+pr+':'+re,'trace_sha256':p.digest(self.src/'trace.npz')} for pr in ['inside','on','beside'] for re in ['r_pc','r_inv_path','r_inv_motion']]
  p.write_json(self.src/'cell_finalizer.json',self.cfs[0]);p.write_json(self.src/'root_finalizer.json',{'pass':True,'root_id':'synthetic','scene_spec_sha256':'fixture-spec','cell_finalizers':self.cfs})
  self.spec['index_sha256']=p.digest(self.src/'source_index.json')
  for x in self.src.iterdir():self.spec['sources'][x.stem]={'path':str(x),'sha256':p.digest(x)}
 def copy(self,spec,dest,**kwargs):
  e={k:spec[k] for k in ['cell_key','family','program_id','realization_id','root_id']};e['source']={};e['root_status']={'root_finalizer_sha256':spec['sources']['root_finalizer']['sha256']}
  for role,field in [('trace','trace'),('cell_receipt','cell_receipt'),('cell_finalizer','independent_cell_finalizer'),('root_receipt','root_receipt'),('prefix','prefix_artifact')]:e['source'][field]={'file_sha256':spec['sources'][role]['sha256']}
  e['source']['current_bundle']={'files':{name:{'file_sha256':spec['sources'][role]['sha256']} for role,name in [('rgb','rgb.npz'),('state','state.json'),('anchor','anchor.json'),('capture','capture_metadata.json')]}}
  p.write_json(self.src/'source_index.json',{'cells':[e]});spec['index_sha256']=p.digest(self.src/'source_index.json');spec['sources']['source_index']['sha256']=spec['index_sha256']
  return p.copy_cell(spec,dest,**kwargs)
 def tearDown(self):self.tmp.cleanup()
 def test_copy_and_idempotence(self):
  d=self.base/'out';self.copy(self.spec,d);self.assertEqual(p.read(d)['inputs']['future'].shape,(2,26));self.assertTrue(self.copy(self.spec,d)['idempotent'])
 def test_source_mismatch(self):
  (self.src/'state.json').write_text('{}')
  with self.assertRaises(ValueError):self.copy(self.spec,self.base/'out')
 def test_faults_recovery(self):
  for fault in ['copy_mid','rename_pre','rename_post']:
   d=self.base/fault
   with self.assertRaises(RuntimeError):self.copy(self.spec,d,fault=fault)
   self.assertEqual(d.exists(),fault=='rename_post');self.copy(self.spec,d);p.read(d)
 def test_version_mismatch(self):
  d=self.base/'out';self.copy(self.spec,d);s={**self.spec,'revision':2}
  with self.assertRaises(ValueError):self.copy(s,d)
 def test_mandatory_supervision(self):
  d=self.base/'out';self.copy(self.spec,d);m=json.loads((d/'portable_manifest.json').read_text());m['files']=[x for x in m['files'] if x['role']!='supervision'];p.write_json(d/'portable_manifest.json',m)
  with self.assertRaises(ValueError):p.read(d)
 def test_row0_finite_and_camera(self):
  for name in ['row0','nan','camera','target']:
   spec=json.loads(json.dumps(self.spec));dest=self.base/name
   if name=='row0':p.write_json(self.src/'state.json',{'joint_qpos':[1.]*38,'joint_qvel':[0.]*38})
   elif name=='nan':p.write_json(self.src/'state.json',{'joint_qpos':[float('nan')]*38,'joint_qvel':[0.]*38})
   elif name=='camera':spec['rgb_contract']['other']=spec['rgb_contract'].pop('head__rgb')
   else:spec['target']={'program_id':'on'}
   spec['sources']['state']['sha256']=p.digest(self.src/'state.json')
   with self.assertRaises(ValueError):self.copy(spec,dest)
   p.write_json(self.src/'state.json',{'joint_qpos':[0.]*38,'joint_qvel':[0.]*38})
 def test_action_layout(self):
  s=json.loads(json.dumps(self.spec));s['trace_layout']='N_actions';np.savez(self.src/'trace.npz',joint_qpos=np.zeros((3,38)),joint_qvel=np.zeros((3,38)),controller_effective_setpoint=np.zeros((2,26)));s['sources']['trace']['sha256']=p.digest(self.src/'trace.npz');cf={**self.cfs[0],'trace_sha256':p.digest(self.src/'trace.npz')};p.write_json(self.src/'cell_finalizer.json',cf);p.write_json(self.src/'root_finalizer.json',{'pass':True,'root_id':'synthetic','scene_spec_sha256':'fixture-spec','cell_finalizers':[cf]});s['sources']['cell_finalizer']['sha256']=p.digest(self.src/'cell_finalizer.json');s['sources']['root_finalizer']['sha256']=p.digest(self.src/'root_finalizer.json');self.copy(s,self.base/'n');self.assertEqual(len(p.read(self.base/'n')['inputs']['future']),2)
 def test_nine_root_atomic_registry(self):
  cells=[]
  for i in range(9):
   pr=['inside','on','beside'][i//3];re=['r_pc','r_inv_path','r_inv_motion'][i%3];s=json.loads(json.dumps(self.spec));s.update(cell_key='synthetic:'+pr+':'+re,program_id=pr,realization_id=re,target={'program_id':pr});c=json.loads((self.src/'cell_receipt.json').read_text());c.update(program_id=pr,realization_id=re);p.write_json(self.src/'cell_receipt.json',c);p.write_json(self.src/'cell_finalizer.json',self.cfs[i]);s['sources']['cell_receipt']['sha256']=p.digest(self.src/'cell_receipt.json');s['sources']['cell_finalizer']['sha256']=p.digest(self.src/'cell_finalizer.json');d=self.base/('cell'+str(i));self.copy(s,d);cells.append(d)
  slots=[x['cell'] for x in self.cfs]
  for fault in ['rename_pre','rename_post','index']:
   root=self.base/('root-'+fault);reg=self.base/(fault+'.json')
   with self.assertRaises(RuntimeError):p.publish_root(root,cells,slots,reg,fault=fault)
   p.publish_root(root,cells,slots,reg);p.publish_root(root,cells,slots,reg);self.assertEqual(len(json.loads(reg.read_text())),1)
if __name__=='__main__':unittest.main()
