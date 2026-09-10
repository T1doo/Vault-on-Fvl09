"""Additive native F1 model view + independent portable copies; raw stays untouched."""
import json,shutil
from pathlib import Path
import numpy as np
import portable_v2 as portable
from family_entry import cohort_root,export_native_cell,state38


def reference(path):
    path=portable.origin(path)
    return {'path':str(path),'file_sha256':portable.digest(path),'exists':True,'bytes':path.stat().st_size}


def write_once(path,value):
    path=Path(path)
    if path.exists():
        if json.loads(path.read_text())!=value:raise ValueError('existing export JSON differs '+str(path))
        return
    temporary=path.with_suffix(path.suffix+'.tmp');portable.write_json(temporary,value);temporary.replace(path)


def arrays_once(path,**arrays):
    path=Path(path)
    if path.exists():
        with np.load(path,allow_pickle=False) as old:
            if set(old.files)!=set(arrays) or any(not np.array_equal(old[k],v) for k,v in arrays.items()):raise ValueError('existing export arrays differ')
        return
    temporary=path.with_suffix('.partial.npz');np.savez_compressed(temporary,**arrays);temporary.replace(path)


def verify_index(index):
    value=json.loads(Path(index).read_text())
    def visit(x):
        if isinstance(x,dict):
            if 'path' in x and 'file_sha256' in x:
                if portable.digest(portable.origin(x['path']))!=x['file_sha256']:raise ValueError('sealed export indexed source changed')
            for v in x.values():visit(v)
        elif isinstance(x,list):
            for v in x:visit(v)
    visit(value)
    for cell in value['cells']:
        root=Path(cell['source']['root_receipt']['path']).parent
        if portable.digest(root/'independent_root_finalizer_v2.json')!=cell['root_status']['root_finalizer_sha256']:raise ValueError('sealed root finalizer changed')
    return value


def seal_source(output,spec,result):
    output=portable.origin(output);destination=output/'portable_source'
    if result.get('pass') is not True or len(result.get('cells',[]))!=9:
        raise ValueError('nine independently checked cells required')
    journal={'spec_sha256':spec['spec_sha256'],'source_finalizer_sha256':portable.digest(output/'independent_structure.json')}
    if destination.exists():
        index=destination/'source_index.json'
        if index.exists():
            value=verify_index(index)
            if value['spec_sha256']!=spec['spec_sha256'] or json.loads((destination/'export_journal.json').read_text())!=journal:raise ValueError('different frozen export')
            return index
        if not (destination/'export_journal.json').exists() or json.loads((destination/'export_journal.json').read_text())!=journal:
            raise ValueError('unowned or changed partial export')
    else:destination.mkdir()
    write_once(destination/'export_journal.json',journal)
    root_receipt=destination/'root_receipt.json';root_finalizer=destination/'independent_root_finalizer_v2.json'
    source_result=output/'independent_structure.json'
    if json.loads(source_result.read_text())!=result:raise ValueError('root finalizer source changed')
    cells=[];checks=[]
    for cell in result['cells']:
        program,realization=cell['cell_key'].split(':')
        payload=export_native_cell(spec=spec,output=output,program_id=program,realization=realization)
        native_raw=cohort_root(output,realization)/'branches'/program/'raw/raw_streams.npz'
        native_manifest=native_raw.parent/'manifest.json';manifest=json.loads(native_manifest.read_text())
        capture=Path(manifest['provenance']['formal_current_capture_path'])
        folder=destination/(program+'__'+realization);folder.mkdir(exist_ok=True);current=folder/'current';current.mkdir(exist_ok=True)
        state=payload['inputs']['state'];rgb=payload['inputs']['rgb']
        arrays_once(current/'rgb.npz',**{k+'__rgb':v for k,v in rgb.items()})
        write_once(current/'state.json',{'joint_qpos':state[:38].tolist(),'joint_qvel':state[38:].tolist()})
        if (current/'anchor.json').exists():
            if portable.digest(current/'anchor.json')!=portable.digest(capture.parent/'anchor.json'):raise ValueError('export anchor changed')
        else:shutil.copyfile(capture.parent/'anchor.json',current/'anchor.json')
        write_once(current/'capture_metadata.json',{'required_camera_names':list(rgb),'camera_images':{k:{'shape':list(v.shape),'dtype':str(v.dtype)} for k,v in rgb.items()},'capture_source':json.loads(capture.read_text()).get('capture_source','native_original_t0'),'original_capture':reference(capture),'rendered_again':False,**{k:json.loads(capture.read_text()).get(k) for k in ['root_id','spec_sha256','source_bundle_sha256']}})
        with np.load(native_raw,allow_pickle=False) as z:
            q=np.array([state38(row) for row in z['stream__realized_qpos']]);v=np.array([state38(row) for row in z['stream__realized_qvel']])
            future=z['stream__controller_effective_setpoint'].copy()
        trace=folder/'trace.npz';arrays_once(trace,joint_qpos=q,joint_qvel=v,controller_effective_setpoint=future)
        with np.load(trace,allow_pickle=False) as z:
            if not np.array_equal(z['controller_effective_setpoint'],payload['inputs']['future']):raise ValueError('additive export modified actual future')
        key=f"{spec['root_id']}:{program}:{realization}"
        receipt={'root_id':spec['root_id'],'family':'F1','program_id':program,'realization_id':realization,'scene_spec_sha256':spec['spec_sha256'],'candidate_set':spec['programs'],'source_native_raw':reference(native_raw),'source_native_manifest':reference(native_manifest),'source_branch_receipt':reference(native_raw.parent.parent/'receipt.json'),'synthetic':manifest['provenance'].get('synthetic') is True,'trace_layout':'N_actions','no_new_rollout':True}
        write_once(folder/'cell_receipt.json',receipt)
        semantics=native_raw.parent.parent/'independent_f1_semantics.json'
        if json.loads(semantics.read_text()).get('pass') is not True:raise ValueError('source independent semantics changed')
        check={'cell':key,'trace_sha256':portable.digest(trace),'pass':True,'source_semantic_finalizer':reference(semantics),'source_raw':reference(native_raw),'view_future_exact':True,'synthetic':receipt['synthetic']}
        checks.append(check);write_once(folder/'independent_finalizer_v2.json',check)
        prefix=cohort_root(output,realization)/'canonical_prefix_artifact/prefix_arrays.npz'
        cells.append({'cell_key':key,'root_id':spec['root_id'],'family':'F1','program_id':program,'realization_id':realization,
            'synthetic':receipt['synthetic'],'trace_layout':'N_actions',
            'source':{'trace':reference(trace),'cell_receipt':reference(folder/'cell_receipt.json'),
                'independent_cell_finalizer':reference(folder/'independent_finalizer_v2.json'),'prefix_artifact':reference(prefix),
                'current_bundle':{'files':{n:reference(current/n) for n in ['rgb.npz','state.json','anchor.json','capture_metadata.json']}}},
            'native_sources':{'native_raw':reference(native_raw),'native_manifest':reference(native_manifest),
                'native_branch_receipt':reference(native_raw.parent.parent/'receipt.json'),'native_semantics':reference(semantics),'native_capture':reference(capture),'native_anchor':reference(capture.parent/'anchor.json')}})
    compatibility=result.get('source_compatibility_receipt')
    if compatibility:
        path=portable.origin(compatibility['path'])
        if portable.digest(path)!=compatibility['sha256']:raise ValueError('compatibility receipt changed')
        for cell in cells:cell['native_sources']['source_compatibility']=reference(path)
    write_once(root_receipt,{'root_id':spec['root_id'],'family':'F1','scene_spec_sha256':spec['spec_sha256'],'source_finalizer':reference(source_result),'accepted':result['research_eligible'],'synthetic':not result['native_physical_evidence'],'new_trajectory_count':0})
    write_once(root_finalizer,{'root_id':spec['root_id'],'scene_spec_sha256':spec['spec_sha256'],'pass':result['pass'],'synthetic':not result['native_physical_evidence'],'cell_finalizers':checks,'source_finalizer':reference(source_result)})
    for cell in cells:
        cell['source']['root_receipt']=reference(root_receipt);cell['root_status']={'root_finalizer_sha256':portable.digest(root_finalizer)}
    index=destination/'source_index.json';write_once(index,{'schema':'native_f1_additive_source_v1','spec_sha256':spec['spec_sha256'],'cells':cells,'synthetic':not result['native_physical_evidence']})
    return index


def copy_root(index,destination,*,fault=None,registry_path=None,expected_index_sha256=None):
    index=portable.origin(index);destination=portable.origin(destination);document=verify_index(index);packages=[]
    expected=portable.digest(index)
    if expected_index_sha256 is not None and expected!=expected_index_sha256:raise ValueError('sealed index version mismatch')
    for cell in document['cells']:
        spec=portable.adapt(str(index),cell['cell_key'],portable.digest(index))
        spec['trace_layout']=cell['trace_layout'];spec['synthetic']=cell['synthetic']
        for name,ref in cell['native_sources'].items():spec['sources'][name]={'path':ref['path'],'sha256':ref['file_sha256']}
        folder=destination.parent/(destination.name+'_cells')/cell['cell_key'].replace(':','__')
        portable.copy_cell(spec,str(folder),fault='copy_mid' if fault=='cell_copy_mid' and not packages else None);packages.append(str(folder))
    return portable.publish_root(str(destination),packages,[c['cell_key'] for c in document['cells']],str(registry_path or destination.parent/'registry.json'),fault='copy_mid' if fault=='root_copy_mid' else fault)
