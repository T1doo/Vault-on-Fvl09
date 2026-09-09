"""CPU-only physical copy and package-only reader. No simulator imports."""
import argparse, hashlib, json, os, shutil, time
from pathlib import Path
import numpy as np

def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

def safe(root, relative):
    p=Path(relative)
    if p.is_absolute() or '..' in p.parts: raise ValueError('nonportable path')
    full=root/p
    if not full.resolve().is_relative_to(root.resolve()) or full.is_symlink(): raise ValueError('path escape')
    return full

def verify(package):
    package=Path(package); m=json.loads((package/'portable_manifest.json').read_text())
    for f in m['files']:
        p=safe(package,f['relative_copy_path'])
        if not p.is_file() or digest(p)!=f['file_hash']: raise ValueError('missing/corrupt '+str(p))
    return m

def read(package):
    package=Path(package);m=verify(package)
    # Original paths are audit strings only and never used to open files.
    by={f['role']:safe(package,f['relative_copy_path']) for f in m['files']}
    with np.load(by['rgb'],allow_pickle=False) as z: rgb={k:z[k].copy() for k in z.files}
    state=json.loads(by['state'].read_text())
    with np.load(by['trace'],allow_pickle=False) as z:
        q=z['joint_qpos']; future=z['controller_effective_setpoint'][1:].copy()
        if future.shape!=(len(q)-1,26): raise ValueError('N/N+1 mismatch')
    supervision=json.loads((package/'supervision.json').read_text())
    inputs={'rgb':rgb,'state':np.r_[state['joint_qpos'],state['joint_qvel']], 'future':future,'candidate_set':m['candidates']}
    if inputs['state'].shape!=(76,) or not np.isfinite(future).all(): raise ValueError('invalid arrays')
    if supervision['target'] not in inputs['candidate_set']: raise ValueError('candidate mismatch')
    return {'inputs':inputs,'supervision':supervision,'audit':m}

def copy_cell(index_path,key,destination):
    if key!='F2-A-v2:beside:r_pc':raise ValueError('this bounded sample exporter only supports the reviewed F2-A beside cell')
    index=json.loads(Path(index_path).read_text());e=next(x for x in index['cells'] if x['cell_key']==key)
    dest=Path(destination)
    if dest.exists(): raise FileExistsError(dest)
    staging=dest.parent/'.staging-cell';staging.mkdir(parents=True,exist_ok=True)
    c=json.loads(Path(e['source']['cell_receipt']['path']).read_text())
    root=json.loads(Path(e['source']['root_receipt']['path']).read_text())
    sources={role:Path(e['source'][field]['path']) for role,field in [('trace','trace'),('cell_receipt','cell_receipt'),('cell_finalizer','independent_cell_finalizer'),('prefix','prefix_artifact'),('root_receipt','root_receipt')]}
    for role,name in [('rgb','rgb.npz'),('state','state.json'),('anchor','anchor.json'),('capture','capture_metadata.json')]:sources[role]=Path(e['source']['current_bundle']['files'][name]['path'])
    sources['reconciliation']=Path(index_path).parent/'P4_F2A_ROOT_FINALIZER_RECONCILIATION.json'
    sources['eligibility']=Path(index_path).parent/'P4_CURRENT_RESEARCH_ELIGIBILITY.json'
    sources['root_finalizer']=Path(e['source']['root_receipt']['path']).parent/'independent_root_finalizer_v2.json'
    files=[];started=time.monotonic()
    for role,source in sources.items():
        if not source.resolve().is_relative_to('/nfs_share/lijunhui') or source.is_symlink():raise ValueError('source escape')
        h=digest(source);relative=f'original/{role}{source.suffix}';target=safe(staging,relative);target.parent.mkdir(exist_ok=True)
        if not target.exists() or digest(target)!=h:
            temp=target.with_suffix(target.suffix+'.partial');shutil.copyfile(source,temp)
            with temp.open('rb') as f:os.fsync(f.fileno())
            if digest(temp)!=h or digest(source)!=h:raise ValueError('copy/source changed')
            os.replace(temp,target)
        if source.stat().st_ino==target.stat().st_ino and source.stat().st_dev==target.stat().st_dev:raise ValueError('not independent')
        files.append({'role':role,'original_path':str(source),'relative_copy_path':relative,'file_hash':h,'bytes':source.stat().st_size,'source_id':key})
    target=next(x for x in c['candidate_set'] if x['program_id']==c['program_id'])
    (staging/'supervision.json').write_text(json.dumps({'target':target},ensure_ascii=False,indent=2))
    files.append({'role':'supervision','original_path':None,'relative_copy_path':'supervision.json','file_hash':digest(staging/'supervision.json'),'bytes':(staging/'supervision.json').stat().st_size,'source_id':key})
    # Include exact source spec via immutable root receipt; derived candidate data separately.
    m={'schema':'portable_cell_v1','qualification':'scoped_pilot_reference','cell_key':key,'candidates':c['candidate_set'],'files':files,'original_path_fallback':False,'trace_action_rule':'discard initial placeholder exactly once; state[0] is t0','source_scene_spec':root['scene_spec'],'video_required':False}
    (staging/'portable_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
    shutil.copyfile(__file__,staging/'reader.py')
    read(staging);os.rename(staging,dest)
    return {'package':str(dest),'copied_bytes':sum(f['bytes'] for f in files),'file_count':len(files),'elapsed_seconds':time.monotonic()-started,'physical_independent_copy':True,'cross_device_backup':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['copy','verify','read']);p.add_argument('package');p.add_argument('--index');p.add_argument('--cell');a=p.parse_args()
    if a.operation=='copy':print(json.dumps(copy_cell(a.index,a.cell,a.package)))
    else:
        x=read(a.package);print(json.dumps({'pass':True,'state_shape':list(x['inputs']['state'].shape),'future_shape':list(x['inputs']['future'].shape),'rgb_shapes':{k:list(v.shape) for k,v in x['inputs']['rgb'].items()},'candidate_count':len(x['inputs']['candidate_set']),'target_in_inputs':'target' in x['inputs']}))
