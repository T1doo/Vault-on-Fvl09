import json,tempfile,unittest,subprocess,sys
from pathlib import Path
from copy import deepcopy
import numpy as np
import portable_v2 as p
import anchor_equivalence as rules

def anchor():
 return {'schema_version':'physical_anchor_v2','model_visible':False,'robot_qpos':[0.]*38,'robot_qvel':[0.]*38,'robot_drive_target':[0.]*38,'gripper_joint_qpos':[0.]*4,'actor_states':{'subject':{'pose':[0,0,.8,1,0,0,0],'linear_velocity':[0,0,0],'angular_velocity':[0,0,0],'sleep_state':False}},'facility_poses':{'table':[0,0,.74,1,0,0,0]},'physics_config':{'dt':.004},'source_commit':'synthetic-fixture','metadata':{'frame':'world'}}
BIND={'root_id':'F1_fixture','spec_sha256':'a'*64,'source_bundle_sha256':'b'*64}
class AnchorTests(unittest.TestCase):
 def test_representation_and_tolerance(self):
  a=anchor();b=json.loads(json.dumps(a,indent=4));b['actor_states']['subject']['pose'][0]+=5e-7;b['robot_qpos']*=2;b['robot_qvel']*=2;b['robot_drive_target']*=2
  self.assertTrue(rules.compare_anchors(a,b,reference_binding=BIND,candidate_binding=BIND)['equivalent']);b['actor_states']['subject']['pose'][0]=2e-6;self.assertFalse(rules.compare_anchors(a,b,reference_binding=BIND,candidate_binding=BIND)['equivalent'])
 def test_missing_wrongroot_wrongsource_rejected(self):
  a=anchor()
  for key in ['robot_drive_target','actor_states','physics_config']:
   b=deepcopy(a);b.pop(key);self.assertFalse(rules.compare_anchors(a,b,reference_binding=BIND,candidate_binding=BIND)['equivalent'])
  for key,value in [('root_id','other'),('source_bundle_sha256','c'*64),('spec_sha256','d'*64)]:
   b={**BIND,key:value};self.assertFalse(rules.compare_anchors(a,a,reference_binding=BIND,candidate_binding=b)['equivalent'])
 def test_reviewed_source_only_provenance_exception(self):
  left=anchor();right=deepcopy(left);left['physics_config']['implementation_source_sha256']='1'*64;right['physics_config']['implementation_source_sha256']='2'*64
  lb={**BIND,'capture_sha256':'3'*64};rb={**BIND,'source_bundle_sha256':'c'*64,'capture_sha256':'4'*64}
  receipt={'schema':'f1_source_compatibility_v1','status':'CPU_REVIEWED_APPLICABLE','root_id':BIND['root_id'],'spec_sha256':BIND['spec_sha256'],'old_source_sha256':'1'*64,'new_source_sha256':'2'*64,'old_source_bundle_sha256':'b'*64,'new_source_bundle_sha256':'c'*64,'scientific_contract_unchanged':True,'changed_files':['capture.py'],'affected_contracts':{'capture.py':'same physical and semantic contract; metadata wiring fix'},'accepted_cells':[{'capture_sha256':'3'*64}]}
  self.assertFalse(rules.compare_anchors(left,right,reference_binding=lb,candidate_binding=rb)['equivalent'])
  self.assertTrue(rules.compare_anchors(left,right,reference_binding=lb,candidate_binding=rb,compatibility=receipt)['equivalent'])
  right['physics_config']['dt']=.005;self.assertFalse(rules.compare_anchors(left,right,reference_binding=lb,candidate_binding=rb,compatibility=receipt)['equivalent']);right['physics_config']['dt']=.004
  bad={**receipt,'accepted_cells':[]};self.assertFalse(rules.compare_anchors(left,right,reference_binding=lb,candidate_binding=rb,compatibility=bad)['equivalent'])
 def test_nonfinite_and_changed_contract_rejected(self):
  a=anchor();a['robot_qpos'][0]=float('nan');self.assertFalse(rules.compare_anchors(a,a,reference_binding=BIND,candidate_binding=BIND)['equivalent']);c=rules.contract();c['tolerances']['position_norm_m']=1
  with self.assertRaises(ValueError):rules.validate_contract(c)

class CopyTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp',prefix='f1-anchor-copy-');self.base=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def packages(self,compatibility=False):
  source=self.base/'source';source.mkdir();candidates=[{'program_id':'F1-'+r,'target_role':r,'steps':[{'op':'place','object':r,'reference':'common_box','relation':'inside'}]} for r in ['red','green','blue']];rows=[];cfs=[];cells=[]
  np.savez(source/'unused.npz',a=np.zeros(1))
  for i,(pr,re) in enumerate((p,r) for p in candidates for r in ['r_pc','r_inv_path','r_inv_motion']):
   d=source/str(i);cur=d/'current';cur.mkdir(parents=True);save=np.savez_compressed if i%2 else np.savez;save(d/'trace.npz',joint_qpos=np.zeros((3,38)),joint_qvel=np.zeros((3,38)),controller_effective_setpoint=np.zeros((3,26)));save(d/'prefix.npz',effective_setpoint_actions=np.zeros((1,26)));save(cur/'rgb.npz',head_camera__rgb=np.zeros((2,2,3),dtype=np.uint8));p.write_json(cur/'state.json',{'joint_qpos':[0.]*38,'joint_qvel':[0.]*38});a=anchor();a['physics_config'].update({'implementation_source_sha256':('1' if i==0 else '2')*64} if compatibility else {});a['actor_states']['subject']['pose'][0]+=(i%2)*5e-7;(cur/'anchor.json').write_text(json.dumps(a,indent=i%4));p.write_json(cur/'capture_metadata.json',{**BIND,**({'source_bundle_sha256':('b' if i==0 else 'c')*64} if compatibility else {}),'required_camera_names':['head_camera'],'camera_images':{'head_camera':{'shape':[2,2,3],'dtype':'uint8'}}});key=BIND['root_id']+':'+pr['program_id']+':'+re;c={'root_id':BIND['root_id'],'family':'F1','program_id':pr['program_id'],'realization_id':re,'scene_spec_sha256':BIND['spec_sha256'],'candidate_set':candidates};p.write_json(d/'cell_receipt.json',c);cf={'cell':key,'trace_sha256':p.digest(d/'trace.npz'),'pass':True,'synthetic':True};p.write_json(d/'independent_finalizer_v2.json',cf);cfs.append(cf);cells.append((key,d,c))
  p.write_json(source/'root_receipt.json',{'synthetic':True});p.write_json(source/'independent_root_finalizer_v2.json',{'root_id':BIND['root_id'],'scene_spec_sha256':BIND['spec_sha256'],'pass':True,'cell_finalizers':cfs})
  def ref(path):return {'path':str(path),'file_sha256':p.digest(path),'exists':True}
  for key,d,c in cells:
   rows.append({'cell_key':key,'root_id':c['root_id'],'family':'F1','program_id':c['program_id'],'realization_id':c['realization_id'],'synthetic':True,'source':{'trace':ref(d/'trace.npz'),'cell_receipt':ref(d/'cell_receipt.json'),'independent_cell_finalizer':ref(d/'independent_finalizer_v2.json'),'prefix_artifact':ref(d/'prefix.npz'),'root_receipt':ref(source/'root_receipt.json'),'current_bundle':{'files':{n:ref(d/'current'/n) for n in ['rgb.npz','state.json','anchor.json','capture_metadata.json']}}},'root_status':{'root_finalizer_sha256':p.digest(source/'independent_root_finalizer_v2.json')}})
  if compatibility:
   receipt={'schema':'f1_source_compatibility_v1','status':'CPU_REVIEWED_APPLICABLE','root_id':BIND['root_id'],'spec_sha256':BIND['spec_sha256'],'old_source_sha256':'1'*64,'new_source_sha256':'2'*64,'old_source_bundle_sha256':'b'*64,'new_source_bundle_sha256':'c'*64,'scientific_contract_unchanged':True,'changed_files':['capture.py'],'affected_contracts':{'capture.py':'same semantic/physics contract'},'accepted_cells':[{'capture_sha256':rows[0]['source']['current_bundle']['files']['capture_metadata.json']['file_sha256']}]}
   path=source/'compatibility.json';p.write_json(path,receipt)
   for row in rows:row['native_sources']={'source_compatibility':ref(path)}
  index=source/'source_index.json';p.write_json(index,{'cells':rows});packages=[]
  for i,row in enumerate(rows):
   spec=p.adapt(str(index),row['cell_key'],p.digest(index));dest=self.base/'cells'/str(i);p.copy_cell(spec,dest);packages.append(dest)
  return packages,[r['cell_key'] for r in rows],index
 def test_semantic_layout_source_denied_and_interruption_recovery(self):
  packages,keys,index=self.packages();before={x:p.digest(x) for x in (self.base/'source').rglob('*') if x.is_file()};dest=self.base/'release/F1_fixture';registry=self.base/'release/registry.json'
  for fault in ['copy_mid','rename_pre','rename_post','index']:
   with self.assertRaises(RuntimeError):p.publish_root(dest,packages,keys,registry,fault=fault)
  entry=p.publish_root(dest,packages,keys,registry);self.assertEqual(p.publish_root(dest,packages,keys,registry),entry);self.assertTrue((dest/'group_manifest.json').is_file());self.assertTrue((dest/'common').is_dir());self.assertIn('intent01_red/r_pc',entry['relative_cell_paths']);self.assertEqual(len(entry['anchor_equivalence']),9);self.assertTrue(all(p.digest(x)==h for x,h in before.items()))
  script="""import sys,pathlib,importlib.util,numpy
base=pathlib.Path(sys.argv[1]);root=base/'release/F1_fixture';spec=importlib.util.spec_from_file_location('bundle_reader',root/'common/reader.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def deny(event,args):
 if event=='open' and isinstance(args[0],(str,bytes)):
  path=pathlib.Path(args[0]).resolve()
  if path.is_relative_to(base/'source') or path.is_relative_to(base/'cells'):raise PermissionError('source disabled')
sys.addaudithook(deny);assert len(m.read_root(root)['cells'])==9
"""
  run=subprocess.run([sys.executable,'-c',script,str(self.base)],capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stderr)
 def test_reviewed_source_compatibility_survives_copy(self):
  packages,keys,index=self.packages(compatibility=True);root=self.base/'release/F1_fixture';entry=p.publish_root(root,packages,keys,self.base/'registry.json');self.assertTrue(entry['pass']);self.assertTrue(p.read_root(root)['pass'])
 def test_replaced_source_fails_without_republishing(self):
  packages,keys,index=self.packages();doc=json.loads(index.read_text());trace=Path(doc['cells'][0]['source']['trace']['path']);trace.write_bytes(b'changed')
  with self.assertRaises(ValueError):p.adapt(index,keys[0],p.digest(index))

 def test_root_headers_bind_nested_identity_and_qualification(self):
  packages,keys,index=self.packages();root=self.base/'release/F1_fixture';entry=p.publish_root(root,packages,keys,self.base/'registry.json')
  wrong_candidates=deepcopy(entry['candidates']);wrong_candidates[0]['target_role']='wrong_visible_identity'
  mutations={'root_id':'F1_wrong_root','family':'F4','scene_spec_sha256':'d'*64,'candidates':wrong_candidates,'synthetic':False,'formal_eligible':True}
  for field,value in mutations.items():
   with self.subTest(field=field):
    altered={**entry,field:value}
    for name in ['group_manifest.json','root_manifest.json']:p.write_json(root/name,altered)
    with self.assertRaises(ValueError):p.read_root(root)
  for name in ['group_manifest.json','root_manifest.json']:p.write_json(root/name,entry)
  self.assertTrue(p.read_root(root)['pass'])
