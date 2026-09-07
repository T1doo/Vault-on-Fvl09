"""Main-owned finite serial display queue; failures stop, never retry silently."""
import argparse,json,os,re,signal,subprocess,sys,time
from pathlib import Path
from goal_pilot48_v1.runtime import budget
from goal_pilot48_v1.runtime.issue_hd_state_render_v2 import build_manifest,CAPS
from goal_pilot48_v1.runtime.issue_one_sided_micro import checked,sha
from goal_pilot48_v1.hd_state_replay_v1.catalog import catalog
from goal_pilot48_v1.runtime.reconcile_display import main as reconcile

ROOT=budget.ROOT;HERE=Path(__file__).resolve().parent;VAULT=ROOT.parents[2]
PLAN=HERE/'PLAN.json';CURRENT=HERE/'CURRENT.json';EVENTS=HERE/'events.jsonl'
LOG=VAULT/'数据构造/正式数据构造日志.md'
PY=Path('/nfs_share/lijunhui/Robotwin2/env/bin/python')

def job_name(item):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',item['label']):raise ValueError('unsafe display label')
    name='p48_hd_render_queue_'+item['label'].lower().replace('-','_')+'_001'
    if len(('/nfs_share/lijunhui/Robotwin2/cache/p48/'+name+'/tmp').encode())>100:raise ValueError('cache path too long')
    return name

def emit(kind,**data):
    value={'kind':kind,'unix_time':time.time(),**data}
    budget.append(EVENTS,value);budget.atomic(CURRENT,value);print(json.dumps(value,ensure_ascii=False),flush=True)

def successful_labels():
    result=set();terminals=set(budget.snapshot()['terminal_jobs'])
    for path in (ROOT/'jobs').glob('p48_hd_render_*.json'):
        m=checked(path,'manifest_sha256');job=m['jobs'][0]
        if job['job_id'] not in terminals:continue
        target=Path(job['output_namespace'])/'goal_terminal.json'
        if not target.exists():continue
        terminal=checked(target)
        if terminal['pass'] and (terminal.get('runtime_result') or {}).get('render_pass'):
            result.add(m['render_item']['label'])
    return result

def prepare():
    if PLAN.exists():raise FileExistsError('immutable queue plan exists')
    done=successful_labels();items=[i for i in catalog() if i['label'] not in done]
    if len({job_name(i) for i in items})!=len(items):raise ValueError('queue namespace collision')
    value={'schema_version':'finite_native_HD_display_queue_v1','items':items,'max_jobs':len(items),
           'excluded_successful_labels':sorted(done),'caps_per_job':CAPS,
           'max_concurrent_GPU_jobs':1,'no_automatic_retry':True,
           'source_files':{str(p):sha(p) for folder in (ROOT/'hd_state_replay_v1',ROOT/'hd_state_replay_v2') for p in folder.glob('*.py')}}
    value['source_files'][str(Path(__file__).resolve())]=sha(__file__)
    value['receipt_sha256']=budget.digest(value);budget.atomic(PLAN,value)
    print('prepared',len(items),'display jobs; no reservations',flush=True)

def git(args,**kwargs):
    return subprocess.run(['git','-C',str(VAULT),*args],check=True,timeout=120,**kwargs)

def publish_issuance(job_id):
    staged=subprocess.run(['git','-C',str(VAULT),'diff','--cached','--quiet'],timeout=30).returncode
    if staged:raise RuntimeError('unexpected staged files; do not absorb others changes')
    paths=[ROOT/'jobs'/f'{job_id}.json',ROOT/'STATE.json',ROOT/'budget_ledger.jsonl',ROOT/'attempts.jsonl',CURRENT,EVENTS]
    git(['add','--',*[str(p.relative_to(VAULT)) for p in paths if p.exists()]])
    git(['commit','-m','Issue saved-state HD display '+job_id])
    git(['push','origin','main'])

def run():
    plan=checked(PLAN)
    if subprocess.check_output(['git','-C',str(VAULT),'branch','--show-current'],text=True,timeout=30).strip()!='main':raise ValueError('private main branch required')
    if subprocess.check_output(['git','-C',str(VAULT),'remote','get-url','origin'],text=True,timeout=30).strip()!='https://github.com/T1doo/Vault-on-Fvl09.git':raise ValueError('private Vault remote required')
    if plan['max_jobs']!=len(plan['items']) or plan['caps_per_job']!=CAPS:raise ValueError('queue bounds differ')
    if budget.snapshot()['active_reservations']:raise ValueError('finish current task before starting queue')
    for path,expected in plan['source_files'].items():
        if sha(path)!=expected:raise ValueError('frozen renderer changed')
    for index,item in enumerate(plan['items']):
        if (HERE/'STOP_AFTER_CURRENT').exists():emit('STOP_REQUESTED',next_index=index);return
        # The main agent must not write the ledger concurrently with this queue.
        log_tail=LOG.read_text(encoding='utf-8').splitlines()[-6:]
        status=subprocess.check_output(['git','-C',str(VAULT),'status','--porcelain'],text=True,timeout=30)
        job_id=job_name(item)
        preview={'kind':'RESERVE','job_id':job_id,'reserved':CAPS,'event_sha256':'PREVALIDATION_ONLY'}
        build_manifest(job_id,preview,item)
        reservation=budget.reserve(job_id,CAPS,'finite serial HD queue, no task actions/solver/collection')
        m=build_manifest(job_id,reservation,item);m.pop('manifest_sha256')
        m['input_files'][str(PLAN)]=sha(PLAN);m['source_files'][str(Path(__file__).resolve())]=sha(__file__)
        m['queue_index']=index;m['manifest_sha256']=budget.digest(m)
        path=ROOT/'jobs'/f'{job_id}.json';budget.atomic(path,m)
        emit('ISSUED',index=index,total=len(plan['items']),job_id=job_id,label=item['label'],
             manifest_sha256=m['manifest_sha256'],log_tail_checked=True,git_status_checked=True)
        subprocess.run([str(PY),m['guard_script_path'],'--manifest',str(path),'--preflight-only'],check=True,timeout=120)
        publish_issuance(job_id)
        scheduler=ROOT.parent/'endpoint_idle_wave_scheduler_v1.py'
        proc=subprocess.Popen([str(PY),str(scheduler),'--manifest',str(path)],start_new_session=True)
        emit('SCHEDULER_RUNNING',index=index,job_id=job_id,scheduler_pid=proc.pid)
        try:
            logged=False
            while proc.poll() is None:
                start_path=Path(m['guard_directory'])/f'{job_id}.start.json'
                if not logged and start_path.exists():
                    start=checked(start_path)
                    if start['manifest_sha256']!=m['manifest_sha256']:raise ValueError('Guard start binding mismatch')
                    state=budget.read(ROOT/'STATE.json')
                    state['running']={'job_id':job_id,'scheduler_pid':proc.pid,'guard_pid':start['guard_pid'],
                                      'physical_gpu_index':start['physical_gpu_index'],'gpu_uuid':start['gpu_uuid'],'queue_index':index}
                    budget.atomic(ROOT/'STATE.json',state)
                    emit('GUARD_STARTED',**state['running']);logged=True
                time.sleep(2)
            rc=proc.returncode
        except BaseException:
            # This process group was created by this queue, not selected by GPU.
            if proc.poll() is None:
                try:os.killpg(proc.pid,signal.SIGINT)
                except ProcessLookupError:pass
                try:proc.wait(timeout=90)
                except subprocess.TimeoutExpired:emit('INTERRUPTED_CLEANUP_REQUIRES_REVIEW',job_id=job_id)
            raise
        terminal_path=Path(m['guard_directory'])/f'{job_id}.terminal.json'
        if not terminal_path.exists():
            state=budget.read(ROOT/'STATE.json');state['running']=None;budget.atomic(ROOT/'STATE.json',state)
            emit('STOPPED_NO_GUARD_TERMINAL',job_id=job_id,returncode=rc);return
        reconcile(job_id)
        goal_path=Path(m['jobs'][0]['output_namespace'])/'goal_terminal.json'
        result=checked(goal_path) if goal_path.exists() else None
        if rc or result is None or not result['pass'] or not result['runtime_result']['render_pass']:
            emit('STOPPED_RENDER_FAILURE',job_id=job_id,returncode=rc);return
        emit('RENDERED_PENDING_VISUAL_REVIEW',index=index,job_id=job_id,label=item['label'],
             terminal_receipt_sha256=result['receipt_sha256'])
    emit('QUEUE_RENDERING_COMPLETE_PENDING_VISUAL_REVIEW',count=len(plan['items']))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    def interrupt(*_):raise KeyboardInterrupt('queue interrupted')
    signal.signal(signal.SIGTERM,interrupt)
    try:prepare() if args.prepare else run()
    except BaseException as exc:
        if not args.prepare:emit('QUEUE_STOPPED',error=type(exc).__name__,message=str(exc))
        raise
