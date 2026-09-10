"""CPU-only immutable provenance copies; model reader never opens origin paths.
Legacy archives deliberately cannot masquerade as complete formal packages.
"""
import fcntl, hashlib, json, os, shutil, uuid, importlib.util, re
from pathlib import Path
import numpy as np
WORKSPACE=Path('/nfs_share/lijunhui')
REQUIRED={'trace','rgb','state','anchor','capture','prefix','cell_receipt','cell_finalizer','root_receipt','root_finalizer','supervision','source_index','reader','reader_contract'}

def anchor_rules():
 path=Path(__file__).with_name('anchor_equivalence.py')
 spec=importlib.util.spec_from_file_location('_bundled_anchor_equivalence',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def safe(root,relative):
 root=Path(root);p=Path(relative)
 if p.is_absolute() or '..' in p.parts:raise ValueError('unsafe relative path')
 out=root/p
 for q in [out,*out.parents]:
  if q==root.parent:break
  if q.is_symlink():raise ValueError('symlink forbidden')
 if not out.resolve().is_relative_to(root.resolve()):raise ValueError('escape')
 return out

def origin(path):
 p=Path(path)
 if not p.is_absolute() or not p.is_relative_to(WORKSPACE):raise ValueError('origin outside workspace')
 return safe(WORKSPACE,str(p.relative_to(WORKSPACE)))

def write_json(p,d):
 with Path(p).open('w') as f:json.dump(d,f,ensure_ascii=False,sort_keys=True,indent=2);f.flush();os.fsync(f.fileno())

def adapt(index_path,key,expected_index_hash):
 index_path=origin(index_path)
 if digest(index_path)!=expected_index_hash:raise ValueError('index hash mismatch')
 idx=json.loads(index_path.read_text());e=next(x for x in idx.get('cells',idx.get('entries',[])) if x.get('cell_key',x.get('reference_id'))==key)
 sources={};modern='cell_key' in e
 def add(role,x):
  if not x.get('exists',True) or not x.get('file_sha256'):raise ValueError('missing indexed '+role)
  sources[role]={'path':x['path'],'sha256':x['file_sha256']}
 if modern:
  for role,field in [('trace','trace'),('cell_receipt','cell_receipt'),('cell_finalizer','independent_cell_finalizer'),('prefix','prefix_artifact'),('root_receipt','root_receipt')]:add(role,e['source'][field])
  for role,name in [('rgb','rgb.npz'),('state','state.json'),('anchor','anchor.json'),('capture','capture_metadata.json')]:add(role,e['source']['current_bundle']['files'][name])
  sources['root_finalizer']={'path':str(Path(sources['root_receipt']['path']).parent/'independent_root_finalizer_v2.json'),'sha256':e['root_status']['root_finalizer_sha256']}
 else:
  for role,x in e['source']['files'].items():add(role,x)
 if modern:
  for role,x in {**e['source'].get('additional_evidence',{}),**e.get('native_sources',{})}.items():add(role,x)
 sources['source_index']={'path':str(index_path),'sha256':expected_index_hash}
 # Bind all source bytes before parsing any untrusted mutable receipt.
 for role,x in sources.items():
  if digest(origin(x['path']))!=x['sha256']:raise ValueError('indexed source mismatch '+role)
 spec={'schema':'portable_cell_v2','cell_key':key,'family':e['family'],'program_id':e['program_id'],'realization_id':e['realization_id'],'sources':sources,'index_sha256':expected_index_hash,'adapter':'modern' if modern else 'legacy','eligibility':'scoped_pilot' if modern else 'historical_development','formal_eligible':False,'trace_layout':e.get('trace_layout','N_plus_1_initial_placeholder'),'synthetic':e.get('synthetic',False)}
 if modern:
  c=json.loads(origin(sources['cell_receipt']['path']).read_text());spec['root_id']=c['root_id'];spec['scene_spec_sha256']=c['scene_spec_sha256'];spec['candidates']=c['candidate_set'];spec['target']=next(x for x in c['candidate_set'] if x['program_id']==e['program_id'])
  with np.load(origin(sources['rgb']['path']),allow_pickle=False) as z:spec['rgb_contract']={k:{'shape':list(z[k].shape),'dtype':str(z[k].dtype)} for k in z.files}
 if not modern:spec=add_legacy_dependencies(spec)
 return spec

def verify(package):
 p=Path(package);m=json.loads(safe(p,'portable_manifest.json').read_text())
 if m.get('schema')!='portable_cell_v2':raise ValueError('version mismatch')
 roles=[x['role'] for x in m['files']]
 if len(set(roles))!=len(roles):raise ValueError('duplicate role')
 for x in m['files']:
  if digest(safe(p,x['path']))!=x['sha256']:raise ValueError('copy hash mismatch '+x['role'])
 by={x['role']:x for x in m['files']}
 if 'source_index' not in by or by['source_index']['sha256']!=m['index_sha256']:raise ValueError('index binding mismatch')
 for role,src in m['sources'].items():
  if role not in by or by[role]['sha256']!=src['sha256']:raise ValueError('source-copy binding mismatch')
 return m

def read(package):
 p=Path(package);m=verify(p);by={x['role']:safe(p,x['path']) for x in m['files']}
 if m['adapter']=='legacy':return read_legacy(p,m,by)
 if not REQUIRED<=by.keys():raise ValueError('incomplete evidence: '+','.join(sorted(REQUIRED-by.keys())))
 idx=json.loads(by['source_index'].read_text());indexed=next((e for e in idx.get('cells',[]) if e['cell_key']==m['cell_key']),None)
 if indexed is None:raise ValueError('cell not in source index')
 for k in ['family','program_id','realization_id','root_id']:
  if indexed[k]!=m[k]:raise ValueError('source index identity mismatch')
 for role,field in [('trace','trace'),('cell_receipt','cell_receipt'),('cell_finalizer','independent_cell_finalizer'),('root_receipt','root_receipt'),('prefix','prefix_artifact')]:
  if indexed['source'][field]['file_sha256']!=digest(by[role]):raise ValueError('indexed role mismatch '+role)
 for role,x in {**indexed['source'].get('additional_evidence',{}),**indexed.get('native_sources',{})}.items():
  if role not in by or digest(by[role])!=x['file_sha256']:raise ValueError('indexed native evidence mismatch '+role)
 if indexed['root_status']['root_finalizer_sha256']!=digest(by['root_finalizer']):raise ValueError('indexed root finalizer mismatch')
 for role,name in [('rgb','rgb.npz'),('state','state.json'),('anchor','anchor.json'),('capture','capture_metadata.json')]:
  if indexed['source']['current_bundle']['files'][name]['file_sha256']!=digest(by[role]):raise ValueError('indexed current mismatch '+role)
 s=json.loads(by['state'].read_text());c=json.loads(by['cell_receipt'].read_text());sup=json.loads(by['supervision'].read_text())
 for k in ['family','program_id','realization_id']:
  if c[k]!=m[k]:raise ValueError('cell identity mismatch')
 if c['candidate_set']!=m['candidates'] or c['root_id']!=m['root_id'] or c['scene_spec_sha256']!=m['scene_spec_sha256']:raise ValueError('receipt contract mismatch')
 if sup!={'target':m['target'],'cell_key':m['cell_key']} or sup['target'] not in m['candidates'] or sup['target']['program_id']!=c['program_id']:raise ValueError('supervision identity mismatch')
 capture=json.loads(by['capture'].read_text())
 if m['family']=='F1':
  if not {'anchor_rules','anchor_contract'}<=by.keys():raise ValueError('anchor equivalence rules absent')
  rule=anchor_rules();rule.validate_contract(json.loads(by['anchor_contract'].read_text()))
  binding={k:capture.get(k) for k in rule.CONTRACT['binding_fields']}
  if binding['root_id']!=m['root_id'] or binding['spec_sha256']!=m['scene_spec_sha256']:raise ValueError('anchor capture identity mismatch')
  rule.validate_anchor(json.loads(by['anchor'].read_text()),binding)
  original_capture=by.get('native_capture',by.get('original_capture_path'))
  if original_capture is not None:
   recorded=capture.get('original_capture',{})
   if recorded.get('file_sha256')!=digest(original_capture):raise ValueError('original capture link mismatch')
   original=json.loads(original_capture.read_text())
   if any(original.get(k)!=binding[k] for k in rule.CONTRACT['binding_fields']):raise ValueError('normalized capture source binding mismatch')
  original_anchor=by.get('native_anchor',by.get('original_anchor_path'))
  if original_anchor is not None and digest(original_anchor)!=digest(by['anchor']):raise ValueError('original anchor bytes were rewritten')
 if {name+'__rgb' for name in capture['required_camera_names']}!=set(m['rgb_contract']):raise ValueError('required camera contract mismatch')
 for name,contract in m['rgb_contract'].items():
  if any(contract[k]!=capture['camera_images'][name.removesuffix('__rgb')][k] for k in ['shape','dtype']):raise ValueError('capture camera metadata mismatch')
 with np.load(by['rgb'],allow_pickle=False) as z:
  if set(z.files)!=set(m['rgb_contract']):raise ValueError('camera set mismatch')
  rgb={k:z[k].copy() for k in z.files}
  for k,a in rgb.items():
   if a.dtype!=np.uint8 or list(a.shape)!=m['rgb_contract'][k]['shape'] or str(a.dtype)!=m['rgb_contract'][k]['dtype'] or a.ndim!=3 or a.shape[-1]!=3:raise ValueError('RGB contract')
 with np.load(by['trace'],allow_pickle=False) as z:
  q=z['joint_qpos'];v=z['joint_qvel'];a=z['controller_effective_setpoint'];state=np.r_[s['joint_qpos'],s['joint_qvel']]
  if q.shape!=v.shape or q.shape[1:]!=(38,) or not np.array_equal(q[0],s['joint_qpos']) or not np.array_equal(v[0],s['joint_qvel']):raise ValueError('state row0 mismatch')
  if m['trace_layout']=='N_plus_1_initial_placeholder':
   if len(a)!=len(q):raise ValueError('placeholder shape')
   future=a[1:].copy()
  elif m['trace_layout']=='N_actions':future=a.copy()
  else:raise ValueError('unknown action layout')
  if future.shape!=(len(q)-1,26) or state.shape!=(76,) or not all(np.isfinite(x).all() for x in [q,v,future,state]):raise ValueError('invalid numeric arrays')
 cf=json.loads(by['cell_finalizer'].read_text());rf=json.loads(by['root_finalizer'].read_text())
 if cf['cell']!=m['cell_key'] or cf['trace_sha256']!=digest(by['trace']) or rf['root_id']!=m['root_id'] or rf['scene_spec_sha256']!=m['scene_spec_sha256']:raise ValueError('finalizer data binding mismatch')
 if cf not in rf['cell_finalizers']:raise ValueError('cell absent from root finalizer')
 for role in ['cell_finalizer','root_finalizer']:
  if json.loads(by[role].read_text()).get('pass') is not True:raise ValueError('finalizer did not pass')
 return {'inputs':{'rgb':rgb,'state':state,'future':future,'candidate_set':m['candidates']},'supervision':sup,'audit':m}

def copy_cell(spec,destination,fault=None,max_bytes=2_000_000_000):
 dest=origin(destination);dest.parent.mkdir(parents=True,exist_ok=True)
 fingerprint=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()
 with (dest.parent/('.'+dest.name+'.lock')).open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if dest.exists():
   m=verify(dest)
   if m['spec_sha256']!=fingerprint:raise ValueError('published version mismatch')
   return {'package':str(dest),'idempotent':True,'bytes':sum(x['bytes'] for x in m['files'])}
  if sum(origin(x['path']).stat().st_size for x in spec['sources'].values())>max_bytes:raise ValueError('copy budget exceeded')
  stage=None
  for candidate in sorted(dest.parent.glob('.'+dest.name+'.staging-*')):
   if (candidate/'portable_manifest.json').is_file():
    try:previous=verify(candidate)
    except (ValueError,OSError):continue
    if previous['spec_sha256']==fingerprint:stage=candidate;break
  if stage is None:stage=dest.parent/('.'+dest.name+'.staging-'+uuid.uuid4().hex);stage.mkdir()
  files=[]
  for role,x in spec['sources'].items():
   src=origin(x['path']);expected=x['sha256']
   if digest(src)!=expected:raise ValueError('pre-copy source mismatch')
   rel='files/'+role+src.suffix;out=safe(stage,rel);out.parent.mkdir(exist_ok=True)
   if not out.exists() or digest(out)!=expected:shutil.copyfile(src,out)
   with out.open('rb') as f:os.fsync(f.fileno())
   if digest(src)!=expected or digest(out)!=expected:raise ValueError('source/copy changed')
   if os.path.samestat(src.stat(),out.stat()):raise ValueError('not independent copy')
   files.append({'role':role,'path':rel,'sha256':expected,'bytes':out.stat().st_size})
   if fault=='copy_mid':raise RuntimeError('injected copy_mid')
  if 'target' in spec:
   write_json(stage/'supervision.json',{'target':spec['target'],'cell_key':spec['cell_key']});files.append({'role':'supervision','path':'supervision.json','sha256':digest(stage/'supervision.json'),'bytes':(stage/'supervision.json').stat().st_size})
  shutil.copyfile(__file__,stage/'reader.py');write_json(stage/'reader_contract.json',{'schema':'portable_cell_v2','action_layout':spec['trace_layout'],'required_roles':sorted(REQUIRED),'original_path_fallback':False})
  for role,name in [('reader','reader.py'),('reader_contract','reader_contract.json')]:files.append({'role':role,'path':name,'sha256':digest(stage/name),'bytes':(stage/name).stat().st_size})
  if spec.get('family')=='F1' and spec['adapter']=='modern':
   rule=anchor_rules();shutil.copyfile(Path(__file__).with_name('anchor_equivalence.py'),stage/'anchor_equivalence.py');write_json(stage/'anchor_contract.json',rule.contract())
   for role,name in [('anchor_rules','anchor_equivalence.py'),('anchor_contract','anchor_contract.json')]:files.append({'role':role,'path':name,'sha256':digest(stage/name),'bytes':(stage/name).stat().st_size})
  m={**spec,'files':files,'spec_sha256':fingerprint};write_json(stage/'portable_manifest.json',m);verify(stage)
  read(stage)
  if fault=='rename_pre':raise RuntimeError('injected rename_pre')
  os.rename(stage,dest)
  if fault=='rename_post':raise RuntimeError('injected rename_post')
  return {'package':str(dest),'idempotent':False,'bytes':sum(x['bytes'] for x in files),'strict_read':True}

def _package_files(package,m):
 return {x['role']:safe(Path(package),x['path']) for x in m['files']}

def _arrays(path):
 with np.load(path,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}

def validate_root_cells(cell_packages,expected_slots):
 if len(cell_packages)!=9 or len(set(expected_slots))!=9:raise ValueError('nine distinct slots required')
 manifests=[read(p)['audit'] for p in cell_packages]
 if {m['cell_key'] for m in manifests}!=set(expected_slots):raise ValueError('slot set mismatch')
 programs={m['program_id'] for m in manifests};realizations={'r_pc','r_inv_path','r_inv_motion'}
 if len(programs)!=3 or {(m['program_id'],m['realization_id']) for m in manifests}!={(p,r) for p in programs for r in realizations}:raise ValueError('root must be exact 3 by 3 matrix')
 for field in ['root_id','scene_spec_sha256','family','candidates']:
  if any(m[field]!=manifests[0][field] for m in manifests):raise ValueError('mixed root contract '+field)
 rule=anchor_rules();files=[_package_files(p,m) for p,m in zip(cell_packages,manifests)];reference=files[0]
 for by in files:
  if not rule.arrays_equal(_arrays(reference['rgb']),_arrays(by['rgb'])):raise ValueError('root RGB array mismatch')
  if json.loads(reference['state'].read_text())!=json.loads(by['state'].read_text()):raise ValueError('root current state mismatch')
 anchors=[]
 for by in files:
  left=json.loads(reference['anchor'].read_text());right=json.loads(by['anchor'].read_text())
  if manifests[0]['family']=='F1':
   rmeta=json.loads(reference['capture'].read_text());cmeta=json.loads(by['capture'].read_text());rb={k:rmeta.get(k) for k in rule.CONTRACT['binding_fields']};cb={k:cmeta.get(k) for k in rule.CONTRACT['binding_fields']}
   rb['capture_sha256']=rmeta.get('original_capture',{}).get('file_sha256',digest(reference['capture']));cb['capture_sha256']=cmeta.get('original_capture',{}).get('file_sha256',digest(by['capture']))
   compatibility=None
   if 'source_compatibility' in by:
    compatibility=json.loads(by['source_compatibility'].read_text())
    if 'source_compatibility' not in reference or digest(reference['source_compatibility'])!=digest(by['source_compatibility']):raise ValueError('root compatibility evidence mismatch')
   report=rule.compare_anchors(left,right,reference_binding=rb,candidate_binding=cb,compatibility=compatibility)
   if not report['equivalent']:raise ValueError('root anchor not equivalent: '+str(report['failures']))
   anchors.append(report)
  elif left!=right:raise ValueError('root non-F1 anchor payload mismatch')
 pc=[by for by,m in zip(files,manifests) if m['realization_id']=='r_pc']
 if any(not rule.arrays_equal(_arrays(pc[0]['prefix']),_arrays(x['prefix'])) for x in pc):raise ValueError('strict r_pc prefix array mismatch')
 return manifests,anchors

def semantic_relative_paths(manifests):
 candidates=manifests[0]['candidates'];mapping={}
 for i,c in enumerate(candidates,1):
  role=c.get('target_role') or c['program_id'];slug=re.sub(r'[^A-Za-z0-9_-]+','_',str(role)).strip('_')
  if not slug:raise ValueError('empty semantic name')
  mapping[c['program_id']]=f'intent{i:02d}_{slug}'
 return [mapping[m['program_id']]+'/'+m['realization_id'] for m in manifests]

def read_root(root):
 root=Path(root);entry=json.loads(safe(root,'group_manifest.json').read_text())
 if json.loads(safe(root,'root_manifest.json').read_text())!=entry:raise ValueError('root/group identity mismatch')
 for name,h in entry['common_files'].items():
  if digest(safe(root,name))!=h:raise ValueError('common rule integrity mismatch')
 paths=[safe(root,x) for x in entry['relative_cell_paths']];manifests,_=validate_root_cells(paths,list(entry['cells']))
 if {m['cell_key']:m['spec_sha256'] for m in manifests}!=entry['cells']:raise ValueError('published nested cell mismatch')
 for field in ['root_id','family','scene_spec_sha256','candidates']:
  if entry.get(field)!=manifests[0][field]:raise ValueError('root header/nested identity mismatch: '+field)
 if entry.get('synthetic') is not any(m.get('synthetic',False) for m in manifests):raise ValueError('root synthetic declaration mismatch')
 if entry.get('formal_eligible') is not False:raise ValueError('copy schema cannot promote formal eligibility')
 return entry

def publish_root(root_directory,cell_packages,expected_slots,registry,fault=None):
 """Per-root atomic publish and idempotent registry; never compare anchor file SHA.
 root/intentNN_semantic/realization contains each original capture independently.
 """
 root=origin(root_directory);registry=origin(registry);manifests,anchors=validate_root_cells(cell_packages,expected_slots)
 relative=semantic_relative_paths(manifests) if manifests[0]['family']=='F1' else ['cell_'+str(i) for i in range(9)]
 entry={'schema':'portable_semantic_root_v3','root':str(root),'root_id':manifests[0]['root_id'],'family':manifests[0]['family'],'scene_spec_sha256':manifests[0]['scene_spec_sha256'],'cells':{m['cell_key']:m['spec_sha256'] for m in manifests},'synthetic':any(m.get('synthetic',False) for m in manifests),'formal_eligible':False,'relative_cell_paths':relative,'candidates':manifests[0]['candidates'],'anchor_equivalence':anchors,'pass':True}
 common={'common/reader.py':Path(__file__),'common/anchor_equivalence.py':Path(__file__).with_name('anchor_equivalence.py')}
 entry['common_files']={name:digest(path) for name,path in common.items()};entry['anchor_contract_version']=anchor_rules().VERSION
 entry['common_files']['common/anchor_contract.json']=hashlib.sha256(json.dumps(anchor_rules().contract(),ensure_ascii=False,sort_keys=True,indent=2).encode()).hexdigest()
 root.parent.mkdir(parents=True,exist_ok=True);registry.parent.mkdir(parents=True,exist_ok=True)
 with (root.parent/('.'+root.name+'.lock')).open('a') as f:
  fcntl.flock(f,fcntl.LOCK_EX)
  if root.exists():
   saved=read_root(root)
   if saved!=entry:raise ValueError('root version mismatch')
  else:
   stage=None
   for candidate in sorted(root.parent.glob('.'+root.name+'.staging-*')):
    candidate=origin(candidate)
    journal=candidate/'copy_journal.json'
    if journal.is_file() and json.loads(journal.read_text())==entry:stage=candidate;break
   if stage is None:
    stage=root.parent/('.'+root.name+'.staging-'+uuid.uuid4().hex);stage.mkdir();write_json(stage/'copy_journal.json',entry)
   for i,package in enumerate(cell_packages):
    target=safe(stage,relative[i]);target.mkdir(parents=True,exist_ok=True);cm=verify(package)
    for item in cm['files']:
     source=safe(Path(package),item['path']);out=safe(target,item['path']);out.parent.mkdir(parents=True,exist_ok=True)
     if not out.exists() or digest(out)!=item['sha256']:
      temporary=out.with_suffix(out.suffix+'.partial');shutil.copyfile(source,temporary)
      if digest(temporary)!=item['sha256']:raise ValueError('partial root copy hash')
      os.replace(temporary,out)
     if digest(out)!=item['sha256']:raise ValueError('root copy mismatch')
     if os.path.samestat(source.stat(),out.stat()):raise ValueError('root copy is hard-linked source')
     if fault=='copy_mid':raise RuntimeError('injected copy_mid')
    shutil.copyfile(safe(Path(package),'portable_manifest.json'),target/'portable_manifest.json');read(target)
   for name,source in common.items():out=safe(stage,name);out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,out)
   write_json(stage/'common'/'anchor_contract.json',anchor_rules().contract());entry['common_files']['common/anchor_contract.json']=digest(stage/'common'/'anchor_contract.json')
   write_json(stage/'group_manifest.json',entry);write_json(stage/'root_manifest.json',entry);read_root(stage)
   if fault=='rename_pre':raise RuntimeError('injected rename_pre')
   os.rename(stage,root)
   if fault=='rename_post':raise RuntimeError('injected rename_post')
  with registry.with_suffix('.lock').open('a') as rf:
   fcntl.flock(rf,fcntl.LOCK_EX);d=json.loads(registry.read_text()) if registry.exists() else {}
   if str(root) in d and d[str(root)]!=entry:raise ValueError('registry version mismatch')
   if fault=='index':raise RuntimeError('injected index')
   d[str(root)]=entry;tmp=registry.with_suffix('.'+uuid.uuid4().hex+'.tmp');write_json(tmp,d);os.replace(tmp,registry)
 return entry

def semantic_hash(d):
 return hashlib.sha256(json.dumps(d,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def add_legacy_dependencies(spec):
 src=spec['sources'];root=origin(src['root_receipt']['path']).parent;r=json.loads(origin(src['root_receipt']['path']).read_text());b=json.loads(origin(src['branch_receipt']['path']).read_text())
 def linked(role,name,hash_field,expected):
  path=origin(root/name);d=json.loads(path.read_text());payload={k:v for k,v in d.items() if k!=hash_field and not (role=='prefix_metadata' and k in ['prefix_arrays_npz_sha256'])}
  if d.get(hash_field)!=expected or semantic_hash(payload)!=expected:raise ValueError('legacy semantic link '+role)
  src[role]={'path':str(path),'sha256':digest(path),'semantic_expected':expected,'parent_role':'root_receipt' if role!='anchor' else 'branch_receipt'};return d
 frozen=linked('frozen_spec','candidate_frozen_root_spec.json','frozen_spec_sha256',r['candidate_prefix_link']['candidate_frozen_root_spec_sha256'])
 anchor=linked('anchor','reference_anchor.json','anchor_sha256',b['anchor_equivalence']['reference_sha256'])
 prefix=linked('prefix_metadata','canonical_prefix_artifact/canonical_prefix_artifact.json','artifact_sha256',r['canonical_prefix_artifact_sha256'])
 path=origin(root/'canonical_prefix_artifact'/prefix['prefix_arrays_file'])
 if digest(path)!=prefix['prefix_arrays_npz_sha256']:raise ValueError('legacy prefix arrays hash')
 src['prefix']={'path':str(path),'sha256':prefix['prefix_arrays_npz_sha256'],'parent_role':'prefix_metadata'}
 spec['root_id']=frozen['planned_root_slot_spec'].get('root_id',frozen['planned_root_slot_spec'].get('root_slot_id'));spec['scene_spec_sha256']=semantic_hash(frozen['planned_root_slot_spec']);spec['candidates']=frozen['programs'];spec['target']=next(x for x in frozen['programs'] if x['program_id']==spec['program_id']);spec['legacy_evidence_roles']={'cell_finalizer':'branch_receipt.verifier','root_finalizer':'root_receipt.root_finalization','capture':'current_json','state':'current_arrays.robot_qpos/qvel','rgb':'current_arrays','anchor':'anchor','prefix':'prefix'}
 spec['rgb_contract']={k:{'shape':[240,320,3],'dtype':'uint8'} for k in ['head_rgb','left_wrist_rgb','right_wrist_rgb']}
 return spec

def read_legacy(package,m,by):
 required={'trace','current_arrays','current_json','anchor','prefix','prefix_metadata','branch_receipt','root_receipt','frozen_spec','source_index','supervision'}
 if not required<=by.keys():raise ValueError('legacy evidence incomplete')
 idx=json.loads(by['source_index'].read_text());e=next((e for e in idx['entries'] if e['reference_id']==m['cell_key']),None)
 if e is None or any(e[k]!=m[k] for k in ['family','program_id','realization_id']):raise ValueError('legacy index identity mismatch')
 for role,x in e['source']['files'].items():
  if role not in by or digest(by[role])!=x['file_sha256']:raise ValueError('legacy indexed source mismatch '+role)
 b=json.loads(by['branch_receipt'].read_text());r=json.loads(by['root_receipt'].read_text());f=json.loads(by['frozen_spec'].read_text());sup=json.loads(by['supervision'].read_text())
 for role,field,expected in [('frozen_spec','frozen_spec_sha256',r['candidate_prefix_link']['candidate_frozen_root_spec_sha256']),('anchor','anchor_sha256',b['anchor_equivalence']['reference_sha256']),('prefix_metadata','artifact_sha256',r['canonical_prefix_artifact_sha256'])]:
  obj=json.loads(by[role].read_text());payload={k:v for k,v in obj.items() if k!=field and not (role=='prefix_metadata' and k=='prefix_arrays_npz_sha256')}
  if obj[field]!=expected or semantic_hash(payload)!=expected:raise ValueError('legacy copied semantic binding '+role)
 if json.loads(by['prefix_metadata'].read_text())['prefix_arrays_npz_sha256']!=digest(by['prefix']):raise ValueError('copied prefix hash mismatch')
 if b['program_id']!=m['program_id'] or f['programs']!=m['candidates'] or sup!={'target':m['target'],'cell_key':m['cell_key']} or m['target'] not in f['programs'] or m['target']['program_id']!=b['program_id']:raise ValueError('legacy candidate identity')
 if b['verifier'].get('pass') is not True:raise ValueError('legacy verifier fail')
 if r['root_finalization']['accepted'] is not True or b['status'] not in ['accepted','ACCEPTED']:raise ValueError('legacy finalizer status')
 with np.load(by['current_arrays'],allow_pickle=False) as z:
  rgb={k:z[k].copy() for k in m['rgb_contract']};q=z['robot_qpos'];v=z['robot_qvel']
  if q.shape==(76,) and v.shape==(76,):
   if not np.array_equal(q[:38],q[38:]) or not np.array_equal(v[:38],v[38:]):raise ValueError('non-identical duplicated articulation storage')
   q=q[:38];v=v[:38]
  state=np.r_[q,v]
 for k,a in rgb.items():
  if a.dtype!=np.uint8 or list(a.shape)!=m['rgb_contract'][k]['shape']:raise ValueError('legacy RGB contract')
 with np.load(by['trace'],allow_pickle=False) as z:
  tq=z['joint_qpos'];tv=z['joint_qvel'];a=z['controller_effective_setpoint'];future=a[1:].copy()
  if not np.array_equal(tq[0],q) or not np.array_equal(tv[0],v):raise ValueError('legacy state row0 mismatch')
  if state.shape!=(76,) or future.shape!=(len(tq)-1,26) or not all(np.isfinite(x).all() for x in [state,tq,tv,future]):raise ValueError('legacy shape/finite')
  with np.load(by['prefix'],allow_pickle=False) as z2:
   prefix=z2['effective_setpoint_actions']
   if not np.array_equal(future[:len(prefix)],prefix):raise ValueError('legacy actual prefix mismatch')
 return {'inputs':{'rgb':rgb,'state':state,'future':future,'candidate_set':m['candidates']},'supervision':sup,'audit':m}
