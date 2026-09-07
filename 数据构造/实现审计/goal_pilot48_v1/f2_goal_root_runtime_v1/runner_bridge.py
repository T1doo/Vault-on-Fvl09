"""F2 prefix counter audit using the supplied runtime_v2 live Meter."""
import json
from pathlib import Path
from .spec import digest
from .prefix_runner import run as execute

def reconcile(result,counts,events):
    methods={};totals=dict(solver_problems=0,fresh_scenes=0,action_scenes=0,collection_attempts=0)
    for e in events:
        if e['kind']!='CHARGE':continue
        key=e['resource'];amount=e['amount']
        if key not in totals or type(amount) is not int or amount<=0:raise ValueError('invalid meter charge')
        totals[key]+=amount
        if e['total']!=totals[key]:raise ValueError('meter event total mismatch')
        if key=='solver_problems':methods[e.get('method','')]=methods.get(e.get('method',''),0)+amount
    expected=dict(solver_problems=result.get('trajectory_queries'),fresh_scenes=result.get('fresh_scene_attempts'),
                  action_scenes=result.get('action_scenes_observed'),collection_attempts=0)
    valid=all(type(x) is int and x>=0 for x in expected.values())
    valid=valid and expected==counts==totals and result.get('ik_problem_attempts')==0 and result.get('collection_attempts')==0
    valid=valid and all(k.startswith('MotionGen.') for k in methods) and sum(methods.values())==counts['solver_problems']
    valid=valid and all(counts[k]<=cap for k,cap in dict(solver_problems=3,fresh_scenes=1,action_scenes=1,collection_attempts=0).items())
    return {'pass':bool(valid),'expected':expected,'live_counts':dict(counts),'event_counts':totals,'solver_methods':methods,'IK_calls_allowed':0}

def run(manifest,*,meter):
    if meter is None:raise ValueError('prefix requires the runtime_v2 live meter')
    r=execute(manifest);out=Path(manifest['jobs'][0]['output_namespace'])
    try:
        events=[json.loads(line) for line in (meter.out/'events.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
        audit=reconcile(r,dict(meter.counts),events)
    except Exception as exc:audit={'pass':False,'error_type':type(exc).__name__,'error':str(exc)}
    v=dict(r);v.pop('receipt_sha256');v.update(parent_runtime_receipt_sha256=r['receipt_sha256'],meter_audit=audit)
    v['accounting_complete']=bool(r['accounting_complete'] and audit['pass']);v['pass']=bool(r['pass'] and v['accounting_complete'])
    v['scientific_route_pass']=bool(r['scientific_route_pass'] and v['pass']);v['receipt_sha256']=digest(v)
    from realization_utf8_io_v1 import write_new
    write_new(out/'prefix_meter_checked_terminal.json',v);return v
