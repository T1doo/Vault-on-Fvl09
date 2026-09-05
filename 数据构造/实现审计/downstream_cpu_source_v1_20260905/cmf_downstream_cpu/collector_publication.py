"""Finalized plain branch receipts and last-step root index for isolated collector."""
import copy,json
from pathlib import Path
from .io import sha,seal,write_new,publish_identical_or_new,load
from controlled_multi_future.canonical_artifact import canonical_jsonable
from controlled_multi_future.root_orchestrator_v1_1 import finalize_three_branch_root_v1_1

def publish_final_branch(directory,branch):
    directory=Path(directory);path=directory/'branches'/branch['program_id']/'receipt.json'
    write_new(path,canonical_jsonable(branch))

def audit_completed_root(directory):
    directory=Path(directory);root=json.loads((directory/'root_receipt.json').read_text())
    if root['status']!='accepted' or len(root['branch_receipts'])!=3:raise ValueError('root not complete')
    branches=[]
    for embedded in root['branch_receipts']:
        path=directory/'branches'/embedded['program_id']/'receipt.json';actual=json.loads(path.read_text())
        if actual!=embedded:raise ValueError('disk/embedded finalized branch mismatch')
        if actual.get('verifier',{}).get('pass') is not True:raise ValueError('branch verifier failed')
        branches.append(actual)
    cleanup=all(x.get('cleanup_safety_pass') is True and x.get('orphan_process_count')==0 for x in root['cleanup_records'])
    f=finalize_three_branch_root_v1_1(copy.deepcopy(branches),reference_current_sha256=branches[0]['reference_current_sha256'],root_cleanup_pass=cleanup)
    if f.get('accepted') is not True or root['root_finalization'].get('accepted') is not True:raise ValueError('root finalizer failed')
    return root

def register_completed_root(directory):
    directory=Path(directory);root=audit_completed_root(directory)
    index=seal({'schema_version':'cmf_collector_publication_index_v1','planned_root_slot_spec_sha256':root['planned_root_slot_spec_sha256'],
        'root_receipt_file_sha256':sha(directory/'root_receipt.json'),'publication_complete':True,'stage_authorization_granted':False,
        'branch_files':{b['program_id']:sha(directory/'branches'/b['program_id']/'receipt.json') for b in root['branch_receipts']}})
    publish_identical_or_new(directory/'publication_index.json',index)
    return index
