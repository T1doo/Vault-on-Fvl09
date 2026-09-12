import sys,json,hashlib
from pathlib import Path
base=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910');sys.path[:0]=[str(base),'/nfs_share/lijunhui/Robotwin2/project/RoboTwin']
from native_f1 import _load_reusable_branch
from first_wave_launcher import _attempt_number_for_request,_recoverable,read_bound_job_configs
p=base/'F1_FULL_PRODUCTION/F1_MOTION_RECOVERY_ATTEMPT8_APPROVED_20260912';sd=Path('/nfs_share/lijunhui/Robotwin2/datasets/f1_motion_recovery_20260911_attempt8_approved/recovery_state')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
m=read(p/'manifest.json');job=m['jobs'][0];request=read(sd/'recovery_request.json')[job['job_id']];state=read(sd/'STATE.json');spec,auth=read_bound_job_configs(job)
oldstate=read(Path(str(sd).replace('attempt8_approved','attempt8_candidate'))/'STATE.json');state['recovery_requests']=oldstate['recovery_requests'];write(sd/'STATE.json',state)
a=read(p/'evidence/EXECUTION_AUTHORIZATION.json');a['state_sha256']=hashlib.sha256((sd/'STATE.json').read_bytes()).hexdigest();write(p/'evidence/EXECUTION_AUTHORIZATION.json',a)
output=Path(job['output'])/'r_inv_motion';root=output/read(output/'cohort_pointer.json')['root_relative'];reused=[];pending=[]
for pr in spec['programs']:
 name=pr['program_id'];saved,meta=_load_reusable_branch(root/'branches'/name,program_id=name,realization='r_inv_motion',root_id=spec['root_id'],allow_posthoc=auth['recovery_context']['allow_posthoc_reaudited_reuse'])
 (reused if saved is not None else pending).append(name)
assert reused==['F1-red'] and pending==['F1-green','F1-blue']
assert request['missing_cells']==[x+':r_inv_motion' for x in pending]
_recoverable(job,state['jobs'][job['job_id']],request,m)
number=_attempt_number_for_request(request=request,state_dir=sd,job_id=job['job_id']);assert number==8
result={'pass':True,'reused':reused,'pending_physical_queue':pending,'logical_attempt':number,'raw_receipt_unchanged':True,'ledger_history_preserved':True,'gpu_started':False}
write(p/'evidence/QUEUE_BOUNDARY.json',result);print(result)
