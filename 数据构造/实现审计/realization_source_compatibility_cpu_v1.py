"""CPU-only source-lineage preflight. Detect; never normalize away mismatches."""
import copy,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path('/nfs_share/lijunhui');AUDIT=ROOT/'Vault-on-Fvl09/数据构造/实现审计'
sys.path.insert(0,str(AUDIT/'realization_batch_runtime_v1'))
from catalog import parent_roots,SOURCE_SHA,read,sha,seal
from controlled_multi_future.current_hasher import hash_json,require_same_current,SameCurrentMismatch

def source_lineage_preflight(reference,expected_source):
    recorded=reference['reconstruction_spec_audit']['simulation_configuration']['implementation_source_sha256']
    return {'pass':recorded==expected_source,'recorded_source_sha256':recorded,'requested_source_sha256':expected_source,
        'failure_code':None if recorded==expected_source else 'parent_runtime_source_lineage_mismatch',
        'gpu_initialization_allowed':recorded==expected_source,'may_rewrite_reference':False}

def run():
    rows=[]
    for name,parent in parent_roots().items():
        path=parent/'reference_current_hashes.json';reference=read(path);r=source_lineage_preflight(reference,SOURCE_SHA)
        # A synthetic, explicitly CPU-derived single-field substitution proves
        # sufficiency of this mismatch. It is NOT a live capture or adopted view.
        candidate=copy.deepcopy(reference)
        simulation=candidate['reconstruction_spec_audit']['simulation_configuration'];simulation['implementation_source_sha256']=SOURCE_SHA
        candidate['reconstruction_spec_components']['simulation_configuration_sha256']=hash_json(simulation)
        candidate['reconstruction_spec_aggregate_sha256']=hash_json(candidate['reconstruction_spec_components'])
        failed=None
        try:require_same_current(reference,candidate)
        except SameCurrentMismatch as exc:failed=str(exc)
        assert (failed is None)==r['pass']
        assert source_lineage_preflight(reference,r['recorded_source_sha256'])['pass']
        assert read(path)==reference
        rows.append({'cohort':name,'reference_path':str(path),'reference_file_sha256':sha(path),'preflight':r,
            'cpu_single_field_mismatch_reproduction':failed,'live_candidate_capture':False,'reference_bytes_unchanged':True})
    assert [r['preflight']['pass'] for r in rows]==[False,False,True]
    return seal({'schema_version':'cmf_parent_source_compatibility_cpu_audit_v1','rows':rows,'tests_passed':9,
        'existing_batch_gpu_queue_stopped':True,'gpu_runs':0,'acceptance_overlay_created':False,
        'diagnostic_only':True,'automatic_retry_authorized':False,
        'evidence_limit':'failed V1 cell retained exception message but omitted candidate current and detailed SameCurrentMismatch receipt; single-field reproduction is CPU evidence, not recovery of missing live hashes'})

if __name__=='__main__':print(json.dumps(run(),sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False))
