"""CPU-reviewed namespaced parent adapter; deliberately no GPU execution CLI."""
import copy,importlib,importlib.util,json,sys
from pathlib import Path
from types import SimpleNamespace
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计'
if 'catalog' not in sys.modules:sys.path.insert(0,str(A/'realization_batch_runtime_v1'))
from catalog import sha,read,seal,parent_roots,source_branch,build_catalog
OLD_SHA='9873bbe87ed44f7d54003e831ddf9015159036da8078e5cab29ccdc9fcd9fc72'
SOURCE=W/'Robotwin2/tmp/cmf_f1_parent_317387b/数据构造/实现审计/代码审阅快照/controlled_multi_future'
PROJECT=W/'Robotwin2/project/RoboTwin';NAME='cmf_parent_f1_9873'

def load_parent_adapter(output):
    if NAME not in sys.modules:
        spec=importlib.util.spec_from_file_location(NAME,SOURCE/'__init__.py',submodule_search_locations=[str(SOURCE)])
        module=importlib.util.module_from_spec(spec);sys.modules[NAME]=module;spec.loader.exec_module(module)
    base=importlib.import_module(NAME+'.real_sapien_adapter_v1_1')
    if base.implementation_source_sha256()!=OLD_SHA:raise ValueError('parent source bytes changed')
    lock_path=A/'source_locks/controlled_multi_future_post_stage0_f1_batch_pilot_v1/post_stage0_f1_batch_pilot_v1_run4.source_lock.json'
    lock=read(lock_path)['snapshot'];bindings={}
    for category in ('asset_hashes','config_hashes','critical_source_hashes'):
        for relative,digest in lock[category].items():
            p=PROJECT/relative
            if sha(p)!=digest:raise ValueError('parent dependency changed: '+relative)
            bindings[str(p)]=digest
    # Explicit workspace relocation outside the immutable source tree; preserve
    # original file hash and separately report the actual runtime path mapping.
    base.PROJECT_ROOT=PROJECT
    module=importlib.import_module(NAME+'.real_sapien_adapter_f1_batch_v1')
    adapter=module.RoboTwinRealSapienF1BatchPilotAdapterV1(family='F1',output_root=Path(output),expected_implementation_source_sha256=OLD_SHA)
    return adapter,seal({'schema_version':'cmf_parent_F1_namespace_binding_cpu_v1','module_namespace':NAME,
        'source_directory':str(SOURCE),'source_sha256':OLD_SHA,'source_file_bytes_modified':False,
        'path_relocation':{'module':NAME+'.real_sapien_adapter_v1_1','attribute':'PROJECT_ROOT','value':str(PROJECT)},
        'parent_dependency_file_hashes':bindings,'gpu_execution_authorized':False,'scene_created':False})

def run_cpu():
    adapter,binding=load_parent_adapter(W/'Robotwin2/tmp/parent_bridge_unused_scene')
    hasher=importlib.import_module(NAME+'.current_hasher')
    suffix=importlib.import_module(NAME+'.frozen_suffix_artifact_v1')
    from controlled_multi_future import current_hasher as current
    rows=[]
    catalog=build_catalog()
    for group in catalog['cohorts'][:2]:
        for cell in group['cells']:
            parent=Path(cell['parent_root']);ref=read(parent/'reference_current_hashes.json');config=ref['reconstruction_spec_audit']['simulation_configuration']
            fixture=SimpleNamespace(_cmf_setup_kwargs={'static_friction':.5,'dynamic_friction':.5,'restitution':0.},
                scene=SimpleNamespace(get_timestep=lambda:0.004000000189989805),_cmf_canonical_settle_steps=60,
                _cmf_sealed_implementation_source_sha256=OLD_SHA,_cmf_sealed_source_binding='validated_authorization_receipt',
                _cmf_adapter_version='RoboTwinRealSapienF1BatchPilotAdapterV1')
            actual=adapter._simulation_configuration(fixture)
            assert actual==config
            assert current.hash_json(actual)==ref['reconstruction_spec_components']['simulation_configuration_sha256']
            assert hasher.hash_json(actual)==current.hash_json(actual)
            manifest,_,controls=suffix.load_frozen_suffix_artifact(Path(cell['source_suffix']).parent)
            original=source_branch(cell)
            assert adapter.verify(None,cell['program'],{'semantic_verifier':original['verifier']['family_semantic_verifier']})['pass']
            rows.append({'cell_id':cell['cell_id'],'simulation_configuration_cpu_equal':True,'original_suffix_loaded':True,
                'original_family_verifier_cpu_pass':True,'control_segments':len(controls),'scene_created':False})
    from controlled_multi_future.real_sapien_adapter_v1_1 import implementation_source_sha256
    assert implementation_source_sha256()=='3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7'
    return seal({'schema_version':'cmf_parent_F1_bridge_cpu_review_v1','binding':binding,'rows':rows,'pass':True,
        'six_cells_cpu_verified':True,'active_source_unchanged':True,'old_reference_bytes_unchanged':True,
        'live_current_or_anchor_verified':False,'gpu_runs':0,'source_compatibility_acceptance_overlay':False,
        'remaining_before_new_gpu':['wire namespaced adapter into a new versioned full collector','preserve complete mismatch capture before comparison','test full collector dispatch and disk IO under parent namespace','freeze recovery budget and obtain exact first-cell replacement / remaining-cell resume scope']})

if __name__=='__main__':print(json.dumps(run_cpu(),sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False))
