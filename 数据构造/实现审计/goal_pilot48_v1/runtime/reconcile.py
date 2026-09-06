"""Main scheduler reconciles independent meter/Guard/terminal before new reserve."""
import sys,json,math,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from budget import ROOT,KEYS,read,digest,reconcile,atomic,append
def checked(p):
    v=read(p);d=dict(v);h=d.pop('receipt_sha256');assert digest(d)==h;return v
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(job_id):
    m=read(ROOT/'jobs'/(job_id+'.json'));job=m['jobs'][0];out=Path(job['output_namespace']);g=checked(Path(m['guard_directory'])/(job_id+'.terminal.json'))
    if not g['task_owned_cleanup_pass']:raise ValueError('cleanup must be independently resolved')
    if g['child_pid'] is None:counts={k:0 for k in KEYS if k!='gpu_lease_seconds'};t=None;status='NO_CHILD_RESOURCE_BLOCK'
    else:
        t=checked(out/'goal_terminal.json')
        if not t['accounting_complete']:raise ValueError('unknown accounting; keep reservation and pause GPU')
        events=[json.loads(x) for x in (out.parent/(out.name+'_meter')/'events.jsonl').read_text(encoding='utf-8').splitlines()]
        counts={k:sum(e['amount'] for e in events if e['kind']=='CHARGE' and e['resource']==k) for k in KEYS if k!='gpu_lease_seconds'}
        if counts!=t['resource_counts'] or events[-1]['kind']!='METER_CLOSED':raise ValueError('independent meter mismatch')
        result=t.get('runtime_result') or {};status='SCIENTIFIC_PASS' if result.get('micro_pass',result.get('scientific_route_pass',False)) else 'SCIENTIFIC_FAILURE' if t['pass'] else 'INFRASTRUCTURE_FAILURE'
    counts['gpu_lease_seconds']=math.ceil(g['elapsed_seconds'])+1
    ev=reconcile(job_id,counts,{'goal_terminal':str(out/'goal_terminal.json') if t else None,'goal_terminal_sha256':sha(out/'goal_terminal.json') if t else None,'guard_path':str(Path(m['guard_directory'])/(job_id+'.terminal.json')),'guard_receipt_sha256':g['receipt_sha256'],'lease_charge_rule':'ceil(guard elapsed)+1 second conservative charge; raw elapsed retained','raw_guard_elapsed_seconds':g['elapsed_seconds']})
    append(ROOT/'attempts.jsonl',{'job_id':job_id,'status':status,'counts':counts,'reconciliation_event_sha256':ev['event_sha256'],'terminal_receipt_sha256':t['receipt_sha256'] if t else None})
    state=read(ROOT/'STATE.json');state['running']=None;state['last_job']={'job_id':job_id,'status':status,'counts':counts};state['last_turn_classification']='progress';atomic(ROOT/'STATE.json',state);print(json.dumps({'job_id':job_id,'status':status,'charged':counts,'budget':state['budget']},ensure_ascii=False))
if __name__=='__main__':main(sys.argv[1])
