"""Independent adversarial CPU checks. No simulator import or execution."""
import copy
import tempfile
import unittest
from pathlib import Path
import scene_plan as scene
TMP=Path('/nfs_share/lijunhui/Robotwin2/tmp')
class IndependentSceneTests(unittest.TestCase):
 def test_fifty_six_slots_and_family_balance(self):
  r=scene.validate_plan(scene.generate());self.assertEqual((r['primary'],r['reserve']),(40,16))
  for c in r['F2_position_counts'].values():self.assertEqual(sorted(c.values()),[3,3,4])
 def test_original_review_counterexamples(self):
  mutations=[lambda s:s['parameters'].update(scale_multiplier=-1),lambda s:s['parameters'].update(translation_xy_m=[float('nan'),0]),lambda s:s['parameters'].update(translation_xy_m=[float('inf'),0]),lambda s:s['parameters'].update(remark='distinct'),lambda s:s['realizations'].append('r_pc')]
  for change in mutations:
   p=scene.generate();change(p['slots'][0])
   with self.assertRaises(ValueError):scene.validate_plan(p)
 def test_nested_configuration_not_aliased(self):
  p=scene.generate();p['slots'][0]['realizations'].append('bad');p['slots'][0]['parameters']['translation_xy_m'][0]=99
  self.assertEqual(len(p['slots'][1]['realizations']),3);self.assertEqual(len(scene.generate()['slots'][0]['realizations']),3);self.assertNotEqual(p['slots'][1]['parameters']['translation_xy_m'][0],99)
 def test_policy_rank_are_frozen(self):
  for k,v in [('near_duplicate_threshold_m',100),('reserve_policy','finish_order')]:
   p=scene.generate();p[k]=v
   with self.assertRaises(ValueError):scene.validate_plan(p)
  p=scene.generate();p['slots'][1]['rank']=1
  with self.assertRaises(ValueError):scene.validate_plan(p)
 def test_identity_ignores_metadata(self):
  a=scene.resolve(scene.generate()['slots'][0]);b=copy.deepcopy(a);b['root_id']='arbitrary';b['seed']=9876;b['roles'][0]['material_source']='different prose'
  self.assertEqual(scene.physical_signature(a),scene.physical_signature(b));self.assertTrue(scene.near_duplicate(a,b))
 def test_rehashed_wrong_program_step_rejected(self):
  for family in scene.FAMILIES:
   spec=scene.resolve(next(x for x in scene.generate()['slots'] if x['family']==family));spec['programs'][0]['steps'][0]['object']='wrong_subject';spec['spec_sha256']=scene.hash_json({k:v for k,v in spec.items() if k!='spec_sha256'})
   with self.assertRaises(ValueError):scene.validate_resolved(spec)
 def test_background_motion_cannot_evade_near_duplicate(self):
  for family in scene.FAMILIES:
   a=scene.resolve(next(x for x in scene.generate()['slots'] if x['family']==family));b=copy.deepcopy(a)
   for r in b['roles']:
    if r['role'].startswith('similar') or r['role']=='background' or 'marker' in r['role']:r['pose'][0]+=.12
   self.assertTrue(scene.near_duplicate(a,b))
 def test_reserve_reverse_completion_and_restart(self):
  plan=scene.generate()
  with tempfile.TemporaryDirectory(dir=TMP,prefix='independent-reserve-') as td:
   p=Path(td);first={'F1_000002':'FAILED','F1_000001':'FAILED'};a=scene.activate_reserves(plan,p/'a.json',first);b=scene.activate_reserves(plan,p/'b.json',dict(reversed(list(first.items()))));self.assertEqual(a,b)
   self.assertEqual([r['primary_root_id'] for r in a['records']],['F1_000001','F1_000002']);self.assertEqual([r['rank'] for r in a['records']],[1,2]);self.assertEqual(scene.activate_reserves(plan,p/'a.json',first),a)
   recovery={r['reserve_root_id']:('FAILED' if r['rank']==1 else 'PASSED') for r in a['records']};resumed=scene.activate_reserves(plan,p/'a.json',recovery)
   self.assertEqual(resumed['records'][-1]['rank'],3);self.assertEqual(resumed['records'][-1]['primary_root_id'],'F1_000001');self.assertEqual(plan['slots'][10]['split'],'inherit_failed_slot');self.assertEqual(resumed['records'][-1]['resolved_spec']['difficulty'],'clear')
 def test_reserve_partial_barrier_rejected(self):
  with tempfile.TemporaryDirectory(dir=TMP,prefix='independent-reserve-') as td:
   with self.assertRaises(ValueError):scene.activate_reserves(scene.generate(),Path(td)/'a.json',{'F1_000002':'FAILED'})
 def test_reserve_remaining_before_first_rejected(self):
  with tempfile.TemporaryDirectory(dir=TMP,prefix='independent-reserve-') as td:
   terminals={f'F1_{i:06d}':'FAILED' if i==3 else 'PASSED' for i in range(3,11)}
   with self.assertRaises(ValueError):scene.activate_reserves(scene.generate(),Path(td)/'a.json',terminals,wave='remaining')
class IndependentPortableTests(unittest.TestCase):
 """Reuse only synthetic input builder; calls/mutations/assertions are independent."""
 def setUp(self):
  import portable_v2
  from test_portable_v2 import PortableTests
  self.p=portable_v2;self.fixture=PortableTests();self.fixture.setUp();self.package=self.fixture.base/'independent-out';self.fixture.copy(self.fixture.spec,self.package)
 def tearDown(self):self.fixture.tearDown()
 def manifest(self):
  import json
  return json.loads((self.package/'portable_manifest.json').read_text())
 def test_untampered_model_shapes(self):
  d=self.p.read(self.package);self.assertEqual(d['inputs']['state'].shape,(76,));self.assertEqual(d['inputs']['future'].shape,(2,26));self.assertNotIn('target',d['inputs'])
 def test_candidate_mutation_rejected(self):
  m=self.manifest();m['candidates'][0]['reference']='wrong_facility';m['target']=m['candidates'][0];sup=self.package/'supervision.json';self.p.write_json(sup,{'target':m['target'],'cell_key':m['cell_key']})
  next(x for x in m['files'] if x['role']=='supervision')['sha256']=self.p.digest(sup);self.p.write_json(self.package/'portable_manifest.json',m)
  with self.assertRaises(ValueError):self.p.read(self.package)
 def test_unindexed_finalizer_replacement_rejected(self):
  import json
  m=self.manifest();row=next(x for x in m['files'] if x['role']=='root_finalizer');file=self.package/row['path'];d=json.loads(file.read_text());d['unindexed_extra']='changed';self.p.write_json(file,d);row['sha256']=self.p.digest(file);m['sources']['root_finalizer']['sha256']=row['sha256'];self.p.write_json(self.package/'portable_manifest.json',m)
  with self.assertRaises(ValueError):self.p.read(self.package)
 def test_duplicate_role_and_missing_anchor(self):
  m=self.manifest();m['files'].append(copy.deepcopy(m['files'][0]));self.p.write_json(self.package/'portable_manifest.json',m)
  with self.assertRaises(ValueError):self.p.read(self.package)
  m['files'].pop();m['files']=[x for x in m['files'] if x['role']!='anchor'];self.p.write_json(self.package/'portable_manifest.json',m)
  with self.assertRaises(ValueError):self.p.read(self.package)
 def test_missing_camera_metadata_not_enough(self):
  m=self.manifest();m['rgb_contract']={};self.p.write_json(self.package/'portable_manifest.json',m)
  with self.assertRaises(ValueError):self.p.read(self.package)
 def test_source_changed_no_publication(self):
  (self.fixture.src/'state.json').write_text('{}');destination=self.fixture.base/'must-not-publish'
  with self.assertRaises(ValueError):self.p.copy_cell(self.fixture.spec,destination)
  self.assertFalse(destination.exists())
 def test_nine_real_keys_and_corrupt_published_resume(self):
  import json
  cells=[]
  for i,cf in enumerate(self.fixture.cfs):
   pr=['inside','on','beside'][i//3];re=['r_pc','r_inv_path','r_inv_motion'][i%3];spec=copy.deepcopy(self.fixture.spec);spec.update(cell_key='synthetic:'+pr+':'+re,program_id=pr,realization_id=re,target={'program_id':pr})
   c=json.loads((self.fixture.src/'cell_receipt.json').read_text());c.update(program_id=pr,realization_id=re);self.p.write_json(self.fixture.src/'cell_receipt.json',c);self.p.write_json(self.fixture.src/'cell_finalizer.json',cf)
   for role in ['cell_receipt','cell_finalizer']:spec['sources'][role]['sha256']=self.p.digest(self.fixture.src/(role+'.json'))
   destination=self.fixture.base/('nine-'+str(i));self.fixture.copy(spec,destination);cells.append(destination)
  keys=[x['cell'] for x in self.fixture.cfs];root=self.fixture.base/'nine-root';registry=self.fixture.base/'registry.json'
  entry=self.p.publish_root(root,cells,keys,registry);self.assertEqual(len(entry['cells']),9)
  nested=root/'cell_0';m=json.loads((nested/'portable_manifest.json').read_text());trace=nested/next(x['path'] for x in m['files'] if x['role']=='trace');trace.write_bytes(b'corrupted published copy')
  with self.assertRaises(ValueError):self.p.publish_root(root,cells,keys,registry)
 def test_nine_copies_one_cell_rejected(self):
  with self.assertRaises(ValueError):self.p.publish_root(self.fixture.base/'bad-root',[self.package]*9,[str(i) for i in range(9)],self.fixture.base/'index.json')

class IndependentNativePreflightTests(unittest.TestCase):
 def test_mutated_spec_and_missing_source_fail_before_native_import(self):
  import sys
  sys.path.insert(0,'/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
  from native_f2f3 import compatible_spec,run_native_root
  for family in ['F2','F3']:
   spec=scene.resolve(next(x for x in scene.generate()['slots'] if x['family']==family));native=compatible_spec(spec);self.assertEqual(native['root_id'],spec['root_id'])
   changed=copy.deepcopy(spec);changed['roles'][0]['pose'][0]+=.001
   with self.assertRaises(ValueError):compatible_spec(changed)
   with tempfile.TemporaryDirectory(dir=TMP,prefix='independent-native-') as td:
    output=Path(td)/'no-native'
    with self.assertRaises(ValueError):run_native_root(spec,output,{'gpu_execution_authorized':True,'spec_sha256':spec['spec_sha256']})
    self.assertFalse(output.exists())
  self.assertNotIn('native_scenes',sys.modules);self.assertNotIn('sapien',sys.modules);self.assertNotIn('torch',sys.modules)
 def test_unsupported_geometry_cannot_diverge_from_verifier(self):
  import sys
  sys.path.insert(0,'/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
  from native_f2f3 import compatible_spec
  for role in ['box','scale','stand']:
   spec=scene.resolve(next(x for x in scene.generate()['slots'] if x['family']=='F2'));item=next(x for x in spec['roles'] if x['role']==role);item['size']=[v*1.5 for v in item['size']];spec['spec_sha256']=scene.hash_json({k:v for k,v in spec.items() if k!='spec_sha256'})
   with self.assertRaises(ValueError):compatible_spec(spec)
 def test_required_asset_bindings_cannot_be_omitted(self):
  import sys
  sys.path.insert(0,'/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
  from native_f2f3 import compatible_spec
  spec=scene.resolve(next(x for x in scene.generate()['slots'] if x['family']=='F2'));spec['asset_bindings']={};spec['spec_sha256']=scene.hash_json({k:v for k,v in spec.items() if k!='spec_sha256'})
  with self.assertRaises(ValueError):compatible_spec(spec)

class ZIndependentUnifiedCliTests(unittest.TestCase):
 def test_unified_cli_real_dispatch_independent_finalizer_and_copy(self):
  import sys,json,contextlib,io
  from unittest.mock import patch
  sys.path.insert(0,'/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
  from execution_cli import main
  from fixture_f1_backend import make_backend
  from test_family_entry import fixture_authorization
  import portable_v2
  with tempfile.TemporaryDirectory(dir=TMP,prefix='independent-unified-cli-') as td:
   base=Path(td);spec=scene.resolve(scene.generate()['slots'][0]);auth=fixture_authorization(spec);auth['copy_destination']=str(base/'copy');auth['job_limits']={'timeout_seconds':1,'cleanup_grace_seconds':1,'gpu_reservation_seconds':2}
   (base/'spec.json').write_text(json.dumps(spec));(base/'auth.json').write_text(json.dumps(auth))
   with patch('native_f1.native_adapter',make_backend),contextlib.redirect_stdout(io.StringIO()):result=main(['--spec',str(base/'spec.json'),'--authorization',str(base/'auth.json'),'--output',str(base/'run')])
   self.assertTrue(result['pass']);self.assertFalse(result['research_eligible']);self.assertFalse(result['native_physical_evidence']);self.assertEqual(len(result['copy']['cells']),9);self.assertTrue(result['copy']['synthetic'])
   for rel in result['copy']['relative_cell_paths']:
    payload=portable_v2.read(base/'copy'/rel);self.assertEqual(payload['inputs']['state'].shape,(76,));self.assertNotIn('target',payload['inputs'])

if __name__=='__main__':unittest.main()
