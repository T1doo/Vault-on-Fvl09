"""Explicit append-only CPU acceptance of the approved existing F4 root."""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np

W=Path('/nfs_share/lijunhui')
A=W/'Vault-on-Fvl09/数据构造/实现审计'
O=W/'Robotwin2/datasets/cmf_f4_v22_authorized_root1'
DEST=W/'Robotwin2/datasets/f4_root1_receipt_resolution_v1'
AUTH=A/'EXTERNAL_EXECUTION_DECISION_F4_ADOPTION_F2_F3_20260905_V1.json'
PROPOSAL=A/'F4_ROOT1_DIVERGENCE_RECEIPT_RESOLUTION_CPU_V1.json'
PUB=A/'F4_V2_2_ROOT1_TERMINAL_PUBLICATION_20260905.json'
IDS=['F4-ABC','F4-ACB','F4-BAC']
FIELD='first_post_prefix_divergence_step'
TOKEN='APPROVE_F4_ROOT1_CPU_ONLY_RECEIPT_RESOLUTION_V1'

def sha(path):
    path=Path(path).resolve()
    if not path.is_relative_to(W):raise ValueError('outside workspace')
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(8*1024*1024),b''):h.update(c)
    return h.hexdigest()

def canonical(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def checked(path,key='receipt_sha256'):
    d=read(path);p=dict(d);h=p.pop(key,None)
    if h!=canonical(p):raise ValueError('self hash mismatch: '+str(path))
    return d
def seal(d):
    d=copy.deepcopy(d);d['receipt_sha256']=canonical(d);return d
def write_new(path,d):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(d,f,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)

def authorization():
    d=checked(AUTH);external=d['authoritative_message']
    if sha(external['path'])!=external['file_sha256']:raise ValueError('external decision source')
    f=d['decision']['f4']
    if f['decision']!=TOKEN or f['authorized'] is not True:raise PermissionError('exact F4 approval')
    if f['source_manifest_sha256']!='13ca428e61a81c6cff36fd77ee6aae3e9e6c6d9f1d70358512827d9582b9d1a8':raise ValueError('source run')
    if f['programs']!=IDS or f['canonical_prefix_end_step']!=2851:raise ValueError('program/P scope')
    if f['permitted_patch']!={'json_pointer':'/executed_prefix/'+FIELD,'original_value':2851,'resolved_value':2926,'branch_count':3}:raise ValueError('patch scope')
    for k in ('maximum_gpu_executions','maximum_scene_creations','maximum_planner_queries','maximum_physical_executions','maximum_new_trajectories','maximum_formal_trajectories'):
        if type(f[k]) is not int or f[k]!=0:raise ValueError('CPU-only scope')
    if f['maximum_existing_roots_adopted']!=1 or f['maximum_existing_trajectories_adopted']!=3:raise ValueError('adoption scope')
    return d,f

def load_original_branch(pid,digest):
    if pid not in IDS:raise ValueError('program')
    p=O/'development_root/branches'/pid/'receipt.json'
    if sha(p)!=digest:raise ValueError('original branch SHA')
    d=read(p)
    if type(d['executed_prefix'][FIELD]) is not int or d['executed_prefix'][FIELD]!=2851:raise ValueError('original field')
    if d['executed_prefix']['canonical_prefix_end_step']!=2851:raise ValueError('P changed')
    return d

def derive(original,root_branch,computed):
    if type(computed) is not int or computed!=2926:raise ValueError('raw-derived divergence')
    result=copy.deepcopy(original);result['executed_prefix'][FIELD]=computed
    if result!=root_branch:raise ValueError('change exceeds approved single field')
    return result

def validate_resolution(r):
    auth,f=authorization()
    p=dict(r);h=p.pop('receipt_sha256',None)
    if h!=canonical(p) or r['authorization_receipt_sha256']!=auth['receipt_sha256']:raise ValueError('resolution integrity/authority')
    if r['original_branch_file_sha256']!=f['original_branch_file_sha256']:raise ValueError('branch binding')
    if r['raw_first_divergence']!=2926 or r['canonical_P']!=2851:raise ValueError('divergence/P')
    return f

def load_resolved_branch(path,pid,*,resolution_path,root_branch):
    r=checked(resolution_path);f=validate_resolution(r)
    if Path(path).resolve()!=O/'development_root/branches'/pid/'receipt.json':raise ValueError('original path')
    original=load_original_branch(pid,f['original_branch_file_sha256'][pid])
    record=checked(DEST/'branches'/(pid+'.resolved.json'))
    if record['resolution_sha256']!=r['receipt_sha256'] or record['original_file_sha256']!=f['original_branch_file_sha256'][pid]:raise ValueError('resolved lineage')
    if record['original_path']!=str(path):raise ValueError('resolved source path')
    expected=derive(original,root_branch,r['raw_first_divergence'])
    if record['payload']!=expected or canonical(record['payload'])!=record['derived_content_sha256']:raise ValueError('resolved content')
    return record['payload']

def dependencies_and_recompute():
    from controlled_multi_future.root_orchestrator_v1_2 import _step_hashes
    from controlled_multi_future.root_orchestrator_v1_1 import resolve_first_post_prefix_divergence
    from controlled_multi_future.canonical_prefix_artifact_v1 import load_canonical_prefix_artifact
    from controlled_multi_future.frozen_suffix_artifact_v1 import load_frozen_suffix_artifact
    auth,f=authorization();proposal=checked(PROPOSAL);publication=checked(PUB)
    if proposal['receipt_sha256']!=f['cpu_resolution_proposal_receipt_sha256']:raise ValueError('approved proposal')
    if publication['receipt_sha256']!='e1bc38bd288a56dbc1cd0f4b14959f86795a8b5c2aca75e9216d3b8795e00b45':raise ValueError('sealed publication')
    for b in proposal['original_artifacts']+publication['artifacts']:
        if sha(b['path'])!=b['file_sha256']:raise ValueError('sealed dependency changed: '+b['path'])
    root=read(O/'development_root/root_receipt.json');job=checked(O/'job_terminal.json')
    if job['pass'] is not False:raise ValueError('original failed terminal changed')
    if sha(O/'development_root'/root['append_only_event_log'])!=root['append_only_event_log_sha256']:raise ValueError('event log')
    prefix,_=load_canonical_prefix_artifact(O/'development_root/canonical_prefix_artifact')
    if prefix['artifact_sha256']!=root['canonical_prefix_artifact_sha256']:raise ValueError('prefix artifact binding')
    originals=[];arrays=[]
    for pid,b in zip(IDS,root['branch_receipts']):
        if b['program_id']!=pid:raise ValueError('root order')
        original=load_original_branch(pid,f['original_branch_file_sha256'][pid]);originals.append(original)
        suffix,_,_=load_frozen_suffix_artifact(O/'development_root/suffix_artifacts'/pid)
        if suffix['artifact_sha256']!=b['suffix_artifact']['artifact_sha256']:raise ValueError('suffix binding')
        trace=O/'development_root/branches'/pid/'trace_source.npz'
        if sha(trace)!=original['raw_manifest']['trace_source_sha256']:raise ValueError('source trace')
        with np.load(O/'development_root/branches'/pid/'raw/raw_streams.npz',allow_pickle=False) as z:
            actions=np.asarray(z['stream__controller_effective_setpoint'],dtype=np.float64)
        if _step_hashes(actions[2851:])!=original['executed_prefix']['post_prefix_action_step_sha256']:raise ValueError('raw suffix hashes')
        arrays.append(actions)
    hashes=[_step_hashes(a) for a in arrays]
    if not hashes[0][:2851]==hashes[1][:2851]==hashes[2][:2851]:raise ValueError('raw canonical prefix')
    divergence=next(i for i in range(max(map(len,hashes))) if len({h[i] if i<len(h) else '<ended>' for h in hashes})>1)
    receipt_divergence=resolve_first_post_prefix_divergence(copy.deepcopy(originals))
    if divergence!=2926 or receipt_divergence!=2926 or root['root_finalization']['computed_first_post_prefix_divergence_step']!=2926:raise ValueError('independent divergence')
    guard=checked(A/'f4v22a1/guards/f4-infrastructure-corrected-development-root-v2.terminal.json')
    if guard['child_exit_code']!=1 or guard['task_owned_cleanup_pass'] is not True or guard['cleanup_errors'] or not guard['lease_released'] or not guard['cache_removed']:raise ValueError('original cleanup evidence')
    files=list(O.rglob('*'))+list((A/'f4v22a1/guards').iterdir())+[AUTH,PROPOSAL,PUB,Path(auth['authoritative_message']['path'])]
    inventory=[{'path':str(p),'file_sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(set(files)) if p.is_file()]
    return auth,f,root,job,inventory,originals,divergence

def audit_f4_root_with_resolution():
    from finalizer import finalize_f4_root_result
    if (DEST/'acceptance.json').exists():
        accepted=checked(DEST/'acceptance.json')
        for b in accepted['dependencies']:
            if sha(b['path'])!=b['file_sha256']:raise ValueError('accepted dependency changed')
        return {'already_registered':True,'new_registrations':0,'acceptance_receipt_sha256':accepted['receipt_sha256']}
    if DEST.exists():raise FileExistsError('partial resolution namespace; do not overwrite')
    auth,f,root,job,inventory,originals,divergence=dependencies_and_recompute()
    root_id=job['manifest_sha256']+':'+root['planned_root_slot_spec_sha256']
    resolution=seal({'schema_version':'cmf_f4_root1_receipt_resolution_v1','decision':TOKEN,'authorization_receipt_sha256':auth['receipt_sha256'],
       'original_root_identity':root_id,'original_branch_file_sha256':f['original_branch_file_sha256'],'canonical_P':2851,
       'raw_first_divergence':divergence,'receipt_step_hash_divergence':2926,'root_finalization_divergence':2926,
       'first_divergence_is_not_H_reveal_or_full_intent_identifiability':True,'permitted_patch':f['permitted_patch'],
       'dependencies':inventory,'source_files':{str(p):sha(p) for p in Path(__file__).parent.glob('*.py')},'GPU_executions':0,'new_trajectories':0})
    write_new(DEST/'resolution.json',resolution)
    for pid,original,root_branch in zip(IDS,originals,root['branch_receipts']):
        payload=derive(original,root_branch,divergence)
        record=seal({'schema_version':'cmf_f4_resolved_branch_view_v1','program_id':pid,'original_path':str(O/'development_root/branches'/pid/'receipt.json'),
          'original_file_sha256':f['original_branch_file_sha256'][pid],'resolution_sha256':resolution['receipt_sha256'],
          'derived_content_sha256':canonical(payload),'payload':payload})
        write_new(DEST/'branches'/(pid+'.resolved.json'),record)
    by_id={b['program_id']:b for b in root['branch_receipts']}
    def loader(path,pid):return load_resolved_branch(path,pid,resolution_path=DEST/'resolution.json',root_branch=by_id[pid])
    manifest=read(A/'F4_V2_2_APPROVED_ROOT1_MANIFEST_20260905.json')
    final=finalize_f4_root_result(job['result'],manifest['jobs'][0],output=O,branch_loader=loader)
    unchanged=all(sha(b['path'])==b['file_sha256'] for b in inventory)
    if final['accepted'] is not True or not unchanged:raise ValueError('full post-resolution acceptance failed')
    acceptance=seal({'schema_version':'cmf_f4_post_resolution_acceptance_v1','original_root_identity':root_id,
      'original_job_pass':False,'original_child_exit_code':1,'original_terminal_modified':False,'original_artifacts_unchanged':unchanged,
      'receipt_resolution_pass':True,'post_resolution_acceptance':True,'accepted_via':'APPEND_ONLY_RECEIPT_RESOLUTION',
      'resolution_receipt_sha256':resolution['receipt_sha256'],'authorization_receipt_sha256':auth['receipt_sha256'],
      'finalizer':final,'dependencies':inventory,'accepted_existing_development_roots':1,'accepted_existing_development_trajectories':3,
      'new_GPU_executions':0,'new_trajectories':0,'stage1_authorized':False,'formal_trajectories':0,'registration_key':root_id})
    write_new(DEST/'acceptance.json',acceptance)
    return {'already_registered':False,'new_registrations':1,'acceptance_receipt_sha256':acceptance['receipt_sha256'],
            'post_resolution_acceptance':True,'accepted_existing_roots':1,'accepted_existing_trajectories':3}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
    if args.check_only:
        a,f,r,j,inv,b,d=dependencies_and_recompute();print(json.dumps({'pass':True,'dependencies':len(inv),'raw_divergence':d,'output_created':False}))
    else:print(json.dumps(audit_f4_root_with_resolution(),sort_keys=True))
