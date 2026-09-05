"""Read-only diagnosis and proposed receipt views; never adopts or overwrites data."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch
import numpy as np

WORKSPACE=Path('/nfs_share/lijunhui')
AUDIT=WORKSPACE/'Vault-on-Fvl09/数据构造/实现审计'
OUTPUT=WORKSPACE/'Robotwin2/datasets/cmf_f4_v22_authorized_root1'
FIELD='first_post_prefix_divergence_step'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def canonical(d):
    return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def resolve_view(original, root_branch, computed, *, original_sha, expected_sha):
    if original_sha!=expected_sha:raise ValueError('original file hash changed')
    if type(computed) is not int or computed<original['executed_prefix']['canonical_prefix_end_step']:
        raise ValueError('invalid computed divergence')
    if root_branch['executed_prefix'][FIELD]!=computed:raise ValueError('raw/root divergence mismatch')
    proposed=copy.deepcopy(original)
    proposed['executed_prefix'][FIELD]=computed
    if proposed!=root_branch:raise ValueError('differences exceed single approved-for-review field')
    return proposed

def negative_tests(original, root_branch, computed, digest):
    tests=[]
    variants=[]
    variants.append(('wrong_original_hash',original,root_branch,computed,'0'*64,digest))
    variants.append(('wrong_computed_divergence',original,root_branch,computed+1,digest,digest))
    changed=copy.deepcopy(root_branch);changed['status']='failed'
    variants.append(('extra_status_change',original,changed,computed,digest,digest))
    changed=copy.deepcopy(root_branch);changed['executed_prefix']['canonical_prefix_end_step']+=1
    variants.append(('canonical_P_change',original,changed,computed,digest,digest))
    variants.append(('invalid_bool_divergence',original,root_branch,True,digest,digest))
    for name,a,b,c,d,e in variants:
        try:resolve_view(a,b,c,original_sha=d,expected_sha=e)
        except ValueError:tests.append({'name':name,'rejected':True})
        else:tests.append({'name':name,'rejected':False})
    return tests

def audit():
    from controlled_multi_future.root_orchestrator_v1_1 import resolve_first_post_prefix_divergence
    from controlled_multi_future.root_orchestrator_v1_2 import _step_hashes
    root_path=OUTPUT/'development_root/root_receipt.json';job_path=OUTPUT/'job_terminal.json'
    root=json.loads(root_path.read_text());job=json.loads(job_path.read_text())
    root_rows=root['branch_receipts'];ids=['F4-ABC','F4-ACB','F4-BAC']
    if [r['program_id'] for r in root_rows]!=ids:raise ValueError('branch order')
    originals=[];arrays=[];inventory=[];paths=[];boundary=None
    for pid in ids:
        directory=OUTPUT/'development_root/branches'/pid
        path=directory/'receipt.json';original=json.loads(path.read_text());originals.append(original);paths.append(path)
        raw=directory/'raw/raw_streams.npz'
        with np.load(raw,allow_pickle=False) as data:arrays.append(np.asarray(data['stream__controller_effective_setpoint'],dtype=np.float64))
        p=original['executed_prefix']['canonical_prefix_end_step']
        if boundary is not None and p!=boundary:raise ValueError('inconsistent canonical P')
        boundary=p
        if _step_hashes(arrays[-1][p:])!=original['executed_prefix']['post_prefix_action_step_sha256']:raise ValueError('raw step hashes changed')
        for x in (path,raw,directory/'raw/manifest.json',directory/'raw/manifest.sha256.json',directory/'video/trajectory.mp4'):
            inventory.append({'path':str(x),'file_sha256':sha(x),'bytes':x.stat().st_size})
    for x in (root_path,job_path):inventory.append({'path':str(x),'file_sha256':sha(x),'bytes':x.stat().st_size})
    hashes=[_step_hashes(a) for a in arrays]
    computed=next(i for i in range(max(map(len,hashes))) if len({h[i] if i<len(h) else '<ended>' for h in hashes})>1)
    from_receipts=resolve_first_post_prefix_divergence(copy.deepcopy(originals))
    if computed!=from_receipts or computed!=root['root_finalization']['computed_first_post_prefix_divergence_step']:raise ValueError('independent divergence mismatch')
    replacements={};overlays=[]
    for path,old,new in zip(paths,originals,root_rows):
        digest=next(x['file_sha256'] for x in inventory if x['path']==str(path))
        view=resolve_view(old,new,computed,original_sha=sha(path),expected_sha=digest)
        replacements[path.resolve()]=view
        overlays.append({'original_path':str(path),'original_file_sha256':digest,'json_pointer':'/executed_prefix/'+FIELD,
            'old_value':old['executed_prefix'][FIELD],'proposed_value':computed,'resolved_view_canonical_sha256':canonical(view),
            'canonical_prefix_end_step_unchanged':boundary})
    tests=negative_tests(originals[0],root_rows[0],computed,sha(paths[0]))
    runtime=AUDIT/'f4_development_root_runtime_v2_2'
    source=runtime/'job_runner.py'
    if sha(source)!='7b47e1a7e3ad9fd0db528e23ee9d870029d527c5b2f47a3550fc545d3a257463':raise ValueError('sealed finalizer changed')
    sys.path.insert(0,str(runtime))
    spec=importlib.util.spec_from_file_location('f4_resolution_readonly_finalizer',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original_reader=module._read_mapping
    def reader(path,label):
        resolved=Path(path).resolve()
        if resolved in replacements:return copy.deepcopy(replacements[resolved])
        return original_reader(path,label)
    manifest=json.loads((AUDIT/'F4_V2_2_APPROVED_ROOT1_MANIFEST_20260905.json').read_text())
    with patch.object(module,'_read_mapping',side_effect=reader):
        diagnostic=module.finalize_f4_root_result(job['result'],manifest['jobs'][0],output=OUTPUT)
    unchanged=all(sha(x['path'])==x['file_sha256'] for x in inventory)
    result={'schema_version':'cmf_f4_single_field_receipt_resolution_cpu_proposal_v1',
       'status':'PHYSICAL_AND_RAW_PASS_TERMINAL_RECEIPT_SYNC_FAILED_CPU_RESOLUTION_PROPOSED',
       'original_job_pass':job['pass'],'original_accepted_roots':job['accepted_development_root_count'],
       'canonical_P_unchanged':boundary,'raw_first_divergence':computed,'receipt_step_hash_first_divergence':from_receipts,
       'post_prefix_initial_common_steps':computed-boundary,'proposed_views':overlays,'negative_tests':tests,
       'diagnostic_only_finalizer_accepted':diagnostic['accepted'],'diagnostic_finalizer_checks':diagnostic['checks'],
       'diagnostic_finalizer_receipt_sha256':diagnostic['receipt_sha256'],'source_file_sha256':sha(source),
       'original_artifacts':inventory,'original_artifacts_unchanged':unchanged,
       'adoption_authorized':False,'original_terminal_superseded':False,'GPU_executions':0,'new_trajectories':0,
       'proposal_accepts_development_root':False,'stage1_authorized':False,'formal_authorized':False}
    result['pass']=unchanged and all(x['rejected'] for x in tests) and diagnostic['accepted'] is True
    result['receipt_sha256']=canonical(result)
    return result

if __name__=='__main__':print(json.dumps(audit(),sort_keys=True,indent=2,ensure_ascii=False))
