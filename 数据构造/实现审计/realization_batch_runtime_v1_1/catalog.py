"""Exact parent-root pairing and existing F1/F4 adapter construction."""
import copy,json,hashlib
from pathlib import Path
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计'
SOURCE_SHA='3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7'
AUTH=A/'EXTERNAL_EXECUTION_DECISION_MODEL_REALIZATION_20260905_V1.json'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def canonical(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def check(p,key='receipt_sha256'):
    d=read(p);v=dict(d);h=v.pop(key)
    if canonical(v)!=h:raise ValueError('hash: '+str(p))
    return d
def seal(d):return {**d,'receipt_sha256':canonical(d)}

def parent_roots():
    report=read(A/'F1_BATCH_GENERATION_PILOT_V1_REPORT.json')
    batch=Path(report['scope_receipt_path']).parent/'root_attempts'
    roots={}
    for label,row in zip(('F1_A_path','F1_B_motion'),report['roots'][:2]):
        receipt=batch/row['root_id']/'f1_batch_pilot_root_receipt.json'
        if sha(receipt)!=row['receipt_file_sha256']:raise ValueError('F1 parent acceptance')
        roots[label]=batch/row['root_id']/'root'
    pub=check(A/'F4_ROOT1_ACCEPTED_VIA_RESOLUTION_PUBLICATION_V1.json')
    if sha(pub['acceptance_path'])!=pub['acceptance_file_sha256']:raise ValueError('F4 acceptance')
    roots['F4_A_path']=W/'Robotwin2/datasets/cmf_f4_v22_authorized_root1/development_root'
    return roots

def build_catalog():
    cohorts=[];dependencies={}
    for name,directory in parent_roots().items():
        frozen=read(directory/'candidate_frozen_root_spec.json');family=name[:2]
        variant='r_inv_motion' if name=='F1_B_motion' else 'r_inv_path'
        cells=[]
        for program in frozen['programs']:
            pid=program['program_id'];suffix=directory/'suffix_artifacts'/pid/'frozen_suffix_artifact.json';s=read(suffix)
            targets=copy.deepcopy(s['execution_spec']['targets'])
            changed=[i for i,t in enumerate(targets) if (t['segment_id'] in ('carry_hub_low','carry_hub_high','safe_horizontal') if family=='F1' else t['segment_id'].endswith('_carry_mid'))]
            if len(changed)!=3:raise ValueError('unexpected variable transport set')
            if variant=='r_inv_path':
                for i in changed:targets[i]['pose'][2]+=.015
            branch=directory/'branches'/pid/'receipt.json'
            if family=='F4':
                branch=W/'Robotwin2/datasets/f4_root1_receipt_resolution_v1_1/branches'/(pid+'.resolved.json')
            cell={'cell_id':name+'__'+pid,'family':family,'cohort':name,'program':program,'program_sha256':canonical(program),
                'parent_root':str(directory),'parent_root_id':frozen['planned_root_slot_spec']['slot_id'],'variant':variant,
                'candidate_universe_sha256':frozen['candidate_universe_sha256'],'source_suffix':str(suffix),'source_suffix_file_sha256':sha(suffix),
                'source_branch':str(branch),'source_branch_file_sha256':sha(branch),'targets':targets,'targets_sha256':canonical(targets),'changed_indices':changed,
                'query_cap':len(targets) if variant=='r_inv_path' else 0,'scene_cap':1,'attempt_cap':1,
                'motion_uses_frozen_parent_controls':variant=='r_inv_motion','path_delta_z_m':.015 if variant=='r_inv_path' else 0.,
                'nominal_duration_scale':1.10 if variant=='r_inv_motion' else 1.,'minimum_realized_path_delta_z_m':.0075 if variant=='r_inv_path' else 0.}
            cells.append(cell)
            for p in (suffix,suffix.parent/'suffix_controls.npz',branch,directory/'branches'/pid/'trace_source.npz'):
                dependencies[str(p)]=sha(p)
        for n in ('candidate_frozen_root_spec.json','planned_root_slot_spec.json','reference_current_hashes.json','reference_anchor.json','canonical_prefix_artifact/canonical_prefix_artifact.json','canonical_prefix_artifact/prefix_arrays.npz'):
            p=directory/n;dependencies[str(p)]=sha(p)
        cohorts.append({'cohort':name,'family':family,'variant':variant,'cells':cells,'query_cap':sum(c['query_cap'] for c in cells),'scene_cap':3})
    if cohorts[0]['cells'][0]['parent_root']==cohorts[1]['cells'][0]['parent_root']:raise ValueError('A/B parent conflation')
    return seal({'schema_version':'cmf_nine_realization_catalog_v1','cohorts':cohorts,'dependencies':dependencies,
        'max_cells':9,'derived_query_cap':sum(c['query_cap'] for g in cohorts for c in g['cells']),'approved_query_cap':156,'fresh_scene_cap':9,
        'stage1_authorized':False,'formal_data':False,'automatic_retry':False,'implementation_source_sha256':SOURCE_SHA})

def make_adapter(cell,output):
    if cell['family']=='F1':
        import sys
        if str(A) not in sys.path:sys.path.insert(1,str(A))
        from realization_parent_f1_bridge_cpu_v1 import load_parent_adapter
        adapter,binding=load_parent_adapter(output)
        adapter._cmf_parent_namespace_binding=binding
        return adapter
    from controlled_multi_future.real_sapien_adapter_f4_qualified_root_v1 import RoboTwinRealSapienF4QualifiedDevelopmentRootV1Adapter
    from controlled_multi_future.f4_full_program_physical_v1 import build_f4_full_program_physical_spec_v1
    from controlled_multi_future.planner_qualification_manifests_v2_3 import build_f4_program_panel_manifest_v1_1
    job=read(A/'F4_V2_2_APPROVED_ROOT1_MANIFEST_20260905.json')['jobs'][0];panel=build_f4_program_panel_manifest_v1_1();specs={}
    for pid,record in job['source_planner_terminals'].items():
        if sha(record['path'])!=record['file_sha256']:raise ValueError('F4 binding source')
        e=read(record['path']);specs[pid]=build_f4_full_program_physical_spec_v1(panel['source_candidate'],panel['candidates'][0],e['terminal'],
          program_id=pid,slot_id=e['spec']['slot_id'],planner_reset_nonce=e['spec']['planner_reset_nonce'],isolation_gate_receipt_sha256=job['isolation_gate_receipt_sha256'])
    return RoboTwinRealSapienF4QualifiedDevelopmentRootV1Adapter(output_root=Path(output),expected_implementation_source_sha256=SOURCE_SHA,
       planned_spec=specs['F4-ABC']['legacy_scene_spec'],full_program_specs=specs)

def source_branch(cell):
    if sha(cell['source_branch'])!=cell['source_branch_file_sha256']:raise ValueError('branch source changed')
    value=read(cell['source_branch']);return value['payload'] if 'payload' in value else value
