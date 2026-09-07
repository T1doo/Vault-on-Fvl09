"""Reconcile display-only jobs without calling them scientific collection passes."""
import math
import sys
from pathlib import Path
from . import budget
from .issue_one_sided_micro import checked,sha

def main(job_id):
    prior=[r for r in budget.rows() if r['kind']=='RECONCILE' and r['job_id']==job_id]
    if prior:
        print('already reconciled',prior[0]['event_sha256']);return
    m=checked(budget.ROOT/'jobs'/f'{job_id}.json','manifest_sha256');job=m['jobs'][0]
    if job['kind']!='HD_SAVED_STATE_RENDER' or job['family']!='DISPLAY':raise ValueError('not display-only')
    out=Path(job['output_namespace']);guard_path=Path(m['guard_directory'])/f'{job_id}.terminal.json'
    guard=checked(guard_path)
    if guard['job_id']!=job_id or guard['manifest_sha256']!=m['manifest_sha256']:raise ValueError('Guard identity mismatch')
    if not guard['task_owned_cleanup_pass']:raise ValueError('owned cleanup not verified')
    if guard['child_pid'] is None:
        counts={k:0 for k in budget.KEYS if k!='gpu_lease_seconds'};terminal=None;status='DISPLAY_NO_CHILD'
    else:
        terminal=checked(out/'goal_terminal.json')
        if terminal['job_id']!=job_id or terminal['manifest_sha256']!=m['manifest_sha256']:raise ValueError('terminal identity mismatch')
        if not guard['gpu_returned_to_idle_baseline']:raise ValueError('GPU baseline not released')
        if not terminal['accounting_complete']:raise ValueError('unknown resource usage')
        import json
        events=[json.loads(line) for line in (out.with_name(out.name+'_meter')/'events.jsonl').read_text(encoding='utf-8').splitlines()]
        counts={k:sum(e['amount'] for e in events if e['kind']=='CHARGE' and e['resource']==k) for k in budget.KEYS if k!='gpu_lease_seconds'}
        if counts!=terminal['resource_counts'] or events[-1]['kind']!='METER_CLOSED':raise ValueError('meter mismatch')
        if any(counts[k]!=0 for k in ('solver_problems','action_scenes','collection_attempts')):raise ValueError('display performed task operations')
        passed=terminal['pass'] and terminal['runtime_result'].get('render_pass') is True
        status='DISPLAY_RENDER_COMPLETED_PENDING_VISUAL_REVIEW' if passed else 'DISPLAY_RENDER_FAILED'
    counts['gpu_lease_seconds']=math.ceil(guard['elapsed_seconds'])+1
    evidence={'guard_path':str(guard_path),'guard_receipt_sha256':guard['receipt_sha256'],
              'goal_terminal_sha256':sha(out/'goal_terminal.json') if terminal else None,
              'display_only_not_scientific_acceptance':True,'raw_guard_elapsed_seconds':guard['elapsed_seconds']}
    event=budget.reconcile(job_id,counts,evidence)
    budget.append(budget.ROOT/'attempts.jsonl',{'job_id':job_id,'status':status,'counts':counts,'reconciliation_event_sha256':event['event_sha256']})
    state=budget.read(budget.ROOT/'STATE.json');state['running']=None;state['last_job']={'job_id':job_id,'status':status,'counts':counts}
    budget.atomic(budget.ROOT/'STATE.json',state)
    print(status,counts)

if __name__=='__main__':main(sys.argv[1])
