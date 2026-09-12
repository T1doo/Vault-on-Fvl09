import sys,json,hashlib,shutil
from pathlib import Path
base=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910');sys.path[:0]=[str(base),'/nfs_share/lijunhui/Robotwin2/project/RoboTwin']
from scene_plan import hash_json
from first_wave_launcher import validate_manifest,recovery_cpu_preflight
from controlled_multi_future.redesign_f2_f3_v2.execution_ledger_v2 import ExecutionLedgerV2
old=base/'F1_FULL_PRODUCTION/F1_MOTION_RECOVERY_ATTEMPT8_CANDIDATE_20260912';new=base/'F1_FULL_PRODUCTION/F1_MOTION_RECOVERY_ATTEMPT8_APPROVED_20260912'
osd=Path('/nfs_share/lijunhui/Robotwin2/datasets/f1_motion_recovery_20260911_attempt8_candidate/recovery_state');sd=Path('/nfs_share/lijunhui/Robotwin2/datasets/f1_motion_recovery_20260911_attempt8_approved/recovery_state')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not new.exists() and not sd.exists(),'authorization already initialized'
new.mkdir();sd.mkdir(parents=True)
manifest=read(old/'manifest.json');parent=hash_json(manifest);auth=read(old/'specs/F1_000013.authorization.json');job=manifest['jobs'][0];jid=job['job_id']
for name in ['F1_000013.spec.json']:shutil.copyfile(old/'specs'/name,(new/'specs'/name) if (new/'specs').mkdir(exist_ok=True) is None else new/'specs'/name)
proof=Path(auth['source_compatibility_receipt']['path']);newproof=new/'evidence/SOURCE_COMPATIBILITY.json';newproof.parent.mkdir();shutil.copyfile(proof,newproof)
request=read(old/'evidence/F1_000013_ATTEMPT8_REQUEST_CANDIDATE.json');request.update(execution_authorized=True,authorization_status='USER_APPROVED_ATTEMPT8_ONLY',auto_start=False)
approval='用户明确批准 attempt8：仅 F1_000013 green/blue motion，复用 red；总cap 28/15/3/64/7200，已有18/9/1/0/1699不清零；预留10/6/2/64/5501；timeout5200 cleanup100 overhead100；禁止attempt9。'
auth.update(gpu_execution_authorized=True,approval_basis=approval,authorization_id='f1-motion-recovery-F1_000013-attempt8-approved')
auth['source_compatibility_receipt']={'path':str(newproof),'sha256':sha(newproof)}
auth['job_limits']={'timeout_seconds':5200,'cleanup_grace_seconds':100,'gpu_reservation_seconds':5501}
auth['recovery_context'].update(attempt8_execution_authorized=True,attempt8_auto_start=False,physical_authorization_status='USER_APPROVED_ATTEMPT8_ONLY',direct_user_approval_text=approval,authorization_receipt=str(new/'evidence/EXECUTION_AUTHORIZATION.json'),attempt_timeout_profile={'timeout_seconds':5200,'cleanup_grace_seconds':100,'lease_overhead_seconds':100},pending_collection_cells=request['missing_cells'],reuse_required_cells=['F1-red:r_inv_motion'])
write(new/'specs/F1_000013.authorization.json',auth)
job.update(timeout_seconds=5200,authorization_path=str(new/'specs/F1_000013.authorization.json'),authorization_file_sha256=sha(new/'specs/F1_000013.authorization.json'),spec_path=str(new/'specs/F1_000013.spec.json'),spec_file_sha256=sha(new/'specs/F1_000013.spec.json'),source_bundle_sha256=auth['source_bundle_sha256'])
manifest.update(execution_authorized=True,cpu_copy_recovery_authorized=True,parent_contract_sha256=parent)
manifest['contract_ancestors']=list(dict.fromkeys(manifest['contract_ancestors']+[read(old/'manifest.json')['parent_contract_sha256']]))
manifest['recovery_contract'].update(attempt8_execution_authorized=True,attempt8_auto_start=False,physical_authorization_status='USER_APPROVED_ATTEMPT8_ONLY',attempt8_reason=approval,pending_collection_cells=request['missing_cells'],reuse_required_cells=['F1-red:r_inv_motion'],compatibility_binding_sha256=sha(newproof))
manifest['package_paths'].update(execution_authorization=str(new/'evidence/EXECUTION_AUTHORIZATION.json'),execution_source_compatibility=str(newproof),candidate_source_compatibility=str(proof))
write(new/'manifest.json',manifest);contract=hash_json(manifest)
state=read(osd/'STATE.json');state.update(contract_sha256=contract,status='DEFERRED_READY',candidate_only=False,attempt8_authorized=True,attempt8_execution_authorized=True,attempt8_auto_start=False,authorization_contract_sha256=contract)
state['jobs'][jid]['pending_recovery_request']=request
state['recovery_requests']={jid:request}
shutil.copyfile(osd/'execution_ledger.jsonl',sd/'execution_ledger.jsonl')
ledger=ExecutionLedgerV2(sd/'execution_ledger.jsonl',contract_sha256=contract,task_id=manifest['task_id'],caps=manifest['budget_caps'],parent_contract_sha256=parent,ancestor_contract_sha256s=manifest['contract_ancestors']);totals=ledger.totals()
assert totals['consumed']==dict(fresh_scenes=18,action_scenes=9,collection_attempts=1,solver_problems=0,gpu_lease_seconds=1699) and not any(totals['reserved'].values())
event=ledger.append(event_type='BUDGET_CAP_AMENDMENT',reserved_after=totals['reserved'],consumed_after=totals['consumed'],metadata={'parent_contract_sha256':parent,'reason':approval},idempotency_key='attempt8-direct-approval:'+contract)
state['attempt8_authorization_event']=event['event_id'];write(sd/'STATE.json',state);write(sd/'namespace_binding.json',{'task_id':manifest['task_id'],'contract_sha256':contract});write(sd/'recovery_request.json',{jid:request});write(new/'evidence/RECOVERY_REQUEST.json',{jid:request})
write(new/'evidence/EXECUTION_AUTHORIZATION.json',{'approval_basis':approval,'contract_sha256':contract,'state_path':str(sd/'STATE.json'),'state_sha256':sha(sd/'STATE.json'),'ledger_event':event,'execution_authorized':True,'logical_attempt':8,'forbid_attempt9':True})
validate_manifest(manifest)
write(new/'evidence/VALIDATE_MANIFEST.json',{'pass':True,'contract_sha256':contract,'execution_authorized':True,'timeout_seconds':5200,'cleanup_seconds':100,'overhead_seconds':100,'reservation_seconds':5501})
result=recovery_cpu_preflight(manifest=manifest,job=job,state_dir=sd,state=state,request=request)
write(new/'evidence/CPU_PREFLIGHT.json',result);write(sd/'cpu_preflight_attempt8.json',result)
print(json.dumps({'manifest':str(new/'manifest.json'),'state_dir':str(sd),'contract':contract,'validate_manifest':True,'preflight':result['pass']}))
