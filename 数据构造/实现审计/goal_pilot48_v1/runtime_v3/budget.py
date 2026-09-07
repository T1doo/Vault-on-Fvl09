"""Single-owner append-only Goal reservations and reconciled consumption."""
import fcntl,hashlib,json,os,time,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
KEYS=('solver_problems','fresh_scenes','action_scenes','collection_attempts','gpu_lease_seconds')
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def atomic(p,v):
    p=Path(p);tmp=p.with_name(p.name+'.tmp.'+str(os.getpid()));data=(json.dumps(v,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
    fd=os.open(tmp,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        if tmp.exists():tmp.unlink()
def append(p,v):
    b=(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')
    with Path(p).open('ab',buffering=0) as f:f.write(b);os.fsync(f.fileno())
def rows():
    p=ROOT/'budget_ledger.jsonl';out=[];previous=None
    if p.exists():
        for line in p.read_text(encoding='utf-8').splitlines():
            if not line:continue
            v=json.loads(line);h=v.pop('event_sha256');assert v['previous_event_sha256']==previous and digest(v)==h;v['event_sha256']=h;out.append(v);previous=h
    return out
def snapshot(events=None):
    events=rows() if events is None else events;caps=read(ROOT/'CONTRACT.json')['caps'];used={k:0 for k in KEYS};active={};terminal={}
    for e in events:
        if e['kind']=='RESERVE':
            if e['job_id'] in active or e['job_id'] in terminal:raise ValueError('duplicate job id')
            active[e['job_id']]=e['reserved']
        elif e['kind']=='RECONCILE':
            reservation=active.pop(e['job_id']);actual=e['actual']
            if any(type(actual[k]) not in (int,float) or actual[k]<0 or actual[k]>reservation[k] for k in KEYS):raise ValueError('unknown/over-reservation consumption')
            for k in KEYS:used[k]+=actual[k]
            terminal[e['job_id']]=e
    reserved={k:sum(a[k] for a in active.values()) for k in KEYS}
    return {'caps':caps,'used':used,'reserved':reserved,'remaining':{k:caps[k]-used[k]-reserved[k] for k in KEYS},'active_reservations':active,'terminal_jobs':list(terminal)}
def transact(kind,job_id,**payload):
    with (ROOT/'budget.lock').open('a+') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX);events=rows();snap=snapshot(events)
        if kind=='RESERVE':
            r=payload['reserved']
            if snap['active_reservations']:raise ValueError('only one GPU job reservation at a time')
            if set(r)!=set(KEYS) or any(type(r[k]) not in (int,float) or r[k]<0 or r[k]>snap['remaining'][k] for k in KEYS):raise ValueError('reservation exceeds remaining Goal budget')
        event={'kind':kind,'job_id':job_id,'unix_time':time.time(),'previous_event_sha256':events[-1]['event_sha256'] if events else None,**payload};event['event_sha256']=digest(event)
        checked=snapshot(events+[event]);append(ROOT/'budget_ledger.jsonl',event)
        state=read(ROOT/'STATE.json');state['budget']=checked;state['last_budget_event_sha256']=event['event_sha256'];atomic(ROOT/'STATE.json',state)
        return event
def reserve(job_id,reserved,scope):return transact('RESERVE',job_id,reserved=reserved,scope=scope,issuance='ISSUED_UNDER_USER_GOAL')
def reconcile(job_id,actual,evidence):return transact('RECONCILE',job_id,actual=actual,evidence=evidence)
