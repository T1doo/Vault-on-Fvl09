"""Atomic source sealing and four-family lossless native/modern export.

Original receipts/raw bytes are preserved. Native normalization is explicitly
labelled derived export evidence, not a newly executed or reverified trajectory.
"""
import json,hashlib,os,uuid,shutil
from pathlib import Path
from copy import deepcopy
import numpy as np
import portable_v2 as p

def ref(path):
 path=p.origin(path);return {'path':str(path),'exists':path.is_file(),'file_sha256':p.digest(path),'bytes':path.stat().st_size}
def state38(x):
 x=np.asarray(x)
 if x.shape[-1:]==(38,):return x.copy()
 if x.shape[-1:]==(76,) and np.array_equal(x[...,:38],x[...,38:]):return x[...,:38].copy()
 raise ValueError('not exact duplicated 38DOF storage')
def validate_matrix(spec,cells,result):
 expected={(x['program_id'],r) for x in spec['programs'] for r in ['r_pc','r_inv_path','r_inv_motion']}
 if len(spec['programs'])!=3 or len(expected)!=9 or len(cells)!=9 or {(c['program_id'],c['realization_id']) for c in cells}!=expected or result.get('pass') is not True:raise ValueError('root needs verified exact 3x3 cells')
 if result.get('root_id')!=spec['root_id']:raise ValueError('result root identity')

def inputs_from_modern(cell,spec):
 current=Path(cell['trace_path']).parent/'current';state=json.loads((current/'state.json').read_text(encoding='utf-8'))
 if cell['scene_spec_sha256']!=spec['spec_sha256'] or cell['candidate_set']!=spec['programs'] or cell['root_id']!=spec['root_id']:raise ValueError('formal candidate/spec mismatch')
 with np.load(current/'rgb.npz',allow_pickle=False) as z:rgb={k:z[k].copy() for k in z.files}
 required={n+'__rgb' for n in spec['cameras']['required']}
 if set(rgb)!=required or any(v.shape!=(spec['cameras']['height'],spec['cameras']['width'],3) or v.dtype!=np.uint8 for v in rgb.values()):raise ValueError('model camera contract')
 with np.load(cell['trace_path'],allow_pickle=False) as z:
  if not np.array_equal(z['joint_qpos'][0],state['joint_qpos']) or not np.array_equal(z['joint_qvel'][0],state['joint_qvel']):raise ValueError('state row0')
  actions=z['controller_effective_setpoint'];layout=cell.get('trace_layout','N_plus_1_initial_placeholder')
  if layout=='N_plus_1_initial_placeholder':future=actions[1:].copy()
  elif layout=='N_actions':future=actions.copy()
  else:raise ValueError('unknown action layout')
  if future.shape!=(len(z['joint_qpos'])-1,26):raise ValueError('trace action layout')
 q=np.r_[state['joint_qpos'],state['joint_qvel']]
 if q.shape!=(76,) or not np.isfinite(q).all() or not np.isfinite(future).all():raise ValueError('finite state/action')
 target=next(x for x in spec['programs'] if x['program_id']==cell['program_id'])
 return {'inputs':{'rgb':rgb,'state':q,'future':future,'candidate_set':spec['programs']},'supervision':{'target':target},'audit':{'trace':ref(cell['trace_path']),'spec_sha256':spec['spec_sha256']}}

def _make_index(seal,spec,cells,result):
 root_path=seal/'root_receipt.json';rf=seal/'independent_root_finalizer_v2.json';p.write_json(rf,result);p.write_json(root_path,{'schema':'formal_root_source_v2','root_id':spec['root_id'],'family':spec['family'],'scene_spec':spec,'scene_spec_sha256':spec['spec_sha256'],'cells':cells,'accepted':True,'qualification':'source acceptance only; no scientific Stage1 promotion','formal_data':False,'synthetic':spec.get('synthetic',False)})
 rows=[]
 for c in cells:
  inputs_from_modern(c,spec);directory=Path(c['trace_path']).parent;current=directory/'current';key=f"{spec['root_id']}:{c['program_id']}:{c['realization_id']}"
  cf=json.loads((directory/'independent_finalizer_v2.json').read_text(encoding='utf-8'))
  if cf.get('cell')!=key or cf.get('trace_sha256')!=p.digest(c['trace_path']) or cf.get('pass')is not True or cf not in result['cell_finalizers']:raise ValueError('cell finalizer trace/root membership')
  rows.append({'cell_key':key,'root_id':spec['root_id'],'family':spec['family'],'program_id':c['program_id'],'realization_id':c['realization_id'],'trace_layout':c.get('trace_layout','N_plus_1_initial_placeholder'),'synthetic':spec.get('synthetic',False),'source':{'trace':ref(c['trace_path']),'cell_receipt':ref(directory/'cell_receipt.json'),'independent_cell_finalizer':ref(directory/'independent_finalizer_v2.json'),'prefix_artifact':ref(c['prefix_artifact_path']),'root_receipt':ref(root_path),'current_bundle':{'files':{n:ref(current/n) for n in ['rgb.npz','state.json','anchor.json','capture_metadata.json']}},'additional_evidence':c.get('additional_evidence',{})},'root_status':{'root_finalizer_sha256':p.digest(rf)}})
 index=seal/'source_index.json';p.write_json(index,{'schema':'formal_source_index_v2','synthetic':spec.get('synthetic',False),'cells':rows});return index

def _relocate(value,old,new):
 if isinstance(value,dict):return {k:_relocate(v,old,new) for k,v in value.items()}
 if isinstance(value,list):return [_relocate(v,old,new) for v in value]
 if isinstance(value,str) and value.startswith(str(old)+'/'):return str(new)+value[len(str(old)):]
 return value

def _publish_seal(stage,destination,spec,cells,result):
 # Relocate derived receipt references before computing final hashes. Source files
 # outside staging retain original paths. Only new exporter-owned bytes change.
 final_cells=_relocate(cells,stage,destination)
 for c,fc in zip(cells,final_cells):
  if Path(c['trace_path']).is_relative_to(stage):p.write_json(Path(c['trace_path']).parent/'cell_receipt.json',fc)
 # Index computes bytes while they still exist at staging, then path strings alone
 # are relocated. Index itself is hashed only after publication by the caller.
 index=_make_index(stage,spec,cells,result);idx=json.loads(index.read_text(encoding='utf-8'));p.write_json(index,_relocate(idx,stage,destination));root=json.loads((stage/'root_receipt.json').read_text(encoding='utf-8'));root=_relocate(root,stage,destination);p.write_json(stage/'root_receipt.json',root)
 # Root receipt hash changed with relocated paths; refresh indexed expected value.
 idx=json.loads(index.read_text(encoding='utf-8'))
 for e in idx['cells']:e['source']['root_receipt']['file_sha256']=p.digest(stage/'root_receipt.json');e['source']['root_receipt']['bytes']=(stage/'root_receipt.json').stat().st_size
 p.write_json(index,idx)
 if destination.exists():raise FileExistsError('sealed source exists')
 os.rename(stage,destination);return destination/'source_index.json'

def seal_modern_source(output,spec,cells,result):
 output=p.origin(output);validate_matrix(spec,cells,result)
 for c in cells:inputs_from_modern(c,spec)
 destination=output/'source_seal';output.mkdir(parents=True,exist_ok=True)
 if destination.exists():raise FileExistsError('sealed source exists')
 stage=output/('.source-seal-'+uuid.uuid4().hex);stage.mkdir()
 return _publish_seal(stage,destination,spec,cells,result)

def seal_native_source(output,spec,cells,result):
 """F1/F4 native raw schema -> explicitly lossless normalized export files.

 cells name actual raw/capture/anchor/prefix and original branch/root receipts.
 Source result must have already passed the native independent acceptance gates.
 """
 output=p.origin(output);validate_matrix(spec,cells,result)
 if spec['family'] not in ['F1','F4']:raise ValueError('native legacy schema adapter only F1/F4')
 destination=output/'source_seal'
 if destination.exists():raise FileExistsError('sealed source exists')
 output.mkdir(parents=True,exist_ok=True);stage=output/('.source-seal-'+uuid.uuid4().hex);stage.mkdir();normalized=[];finalizers=[]
 for index,c in enumerate(cells):
  required=['raw_path','capture_path','current_arrays_path','anchor_path','prefix_artifact_path','branch_receipt_path','root_receipt_path','source_result_path']
  refs={k:ref(c[k]) for k in required};branch=json.loads(Path(c['branch_receipt_path']).read_text(encoding='utf-8'));meta=json.loads(Path(c['capture_path']).read_text(encoding='utf-8'))
  if branch.get('program_id')!=c['program_id'] or branch.get('verifier',{}).get('pass')is not True or branch.get('raw_manifest',{}).get('raw_streams_npz_sha256')!=refs['raw_path']['file_sha256']:raise ValueError('native original branch/raw evidence')
  if meta.get('spec_sha256')!=spec['spec_sha256'] or meta.get('npz_sha256')!=refs['current_arrays_path']['file_sha256']:raise ValueError('native capture binding')
  source_result=json.loads(Path(c['source_result_path']).read_text(encoding='utf-8'))
  if source_result!=result:raise ValueError('source result bytes not supplied result')
  directory=stage/('cell_'+str(index));current=directory/'current';current.mkdir(parents=True)
  with np.load(c['current_arrays_path'],allow_pickle=False) as z:
   rgb={name+'__rgb':z[name].copy() for name in spec['cameras']['required']};q=state38(z['robot_qpos']);v=state38(z['robot_qvel'])
  with np.load(c['raw_path'],allow_pickle=False) as z:
   # Native raw actions are already N; never discard their first action.
   tq=state38(z['stream__realized_qpos']);tv=state38(z['stream__realized_qvel']);a=z['stream__controller_effective_setpoint'].copy()
  if not np.array_equal(tq[0],q) or not np.array_equal(tv[0],v) or a.shape!=(len(tq)-1,26):raise ValueError('native action/state row0 schema')
  np.savez_compressed(directory/'trace.npz',joint_qpos=tq,joint_qvel=tv,controller_effective_setpoint=a);np.savez_compressed(current/'rgb.npz',**rgb);p.write_json(current/'state.json',{'joint_qpos':q.tolist(),'joint_qvel':v.tolist()});shutil.copyfile(c['anchor_path'],current/'anchor.json');p.write_json(current/'capture_metadata.json',{'required_camera_names':spec['cameras']['required'],'camera_images':{name:{'shape':list(rgb[name+'__rgb'].shape),'dtype':str(rgb[name+'__rgb'].dtype)} for name in spec['cameras']['required']},'derivation':'lossless native capture extraction; original metadata in additional evidence','original_capture':refs['capture_path'],**{k:meta.get(k) for k in ['root_id','spec_sha256','source_bundle_sha256']}})
  cell={'root_id':spec['root_id'],'family':spec['family'],'program_id':c['program_id'],'realization_id':c['realization_id'],'scene_spec_sha256':spec['spec_sha256'],'candidate_set':spec['programs'],'trace_path':str(directory/'trace.npz'),'trace_layout':'N_actions','prefix_artifact_path':c['prefix_artifact_path'],'additional_evidence':{'original_'+k:refs[k] for k in required},'derivation':'native raw lossless export; original receipts unchanged'}
  inputs_from_modern(cell,spec);cf={'cell':f"{spec['root_id']}:{c['program_id']}:{c['realization_id']}",'trace_sha256':p.digest(directory/'trace.npz'),'pass':True,'derivation':'export numeric checks plus original source-bound semantic acceptance','original_source_result_sha256':refs['source_result_path']['file_sha256']};p.write_json(directory/'cell_receipt.json',cell);p.write_json(directory/'independent_finalizer_v2.json',cf);finalizers.append(cf);normalized.append(cell)
 wrapper={'root_id':spec['root_id'],'scene_spec_sha256':spec['spec_sha256'],'pass':True,'cell_finalizers':finalizers,'derivation':'lossless export wrapper; original independent result included per cell','original_result_sha256':hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()}
 return _publish_seal(stage,destination,spec,normalized,wrapper)

def copy_sealed_root(index,destination):
 index=p.origin(index);destination=p.origin(destination);d=json.loads(index.read_text(encoding='utf-8'));expected=p.digest(index);packages=[]
 for c in d['cells']:
  spec=p.adapt(str(index),c['cell_key'],expected);cell_dest=destination.parent/(destination.name+'_cells')/c['cell_key'].replace(':','__');p.copy_cell(spec,str(cell_dest));packages.append(str(cell_dest))
 return p.publish_root(str(destination),packages,[c['cell_key'] for c in d['cells']],str(destination.parent/'registry.json'))
