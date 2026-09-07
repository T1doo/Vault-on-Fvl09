"""Local two-scene counters versus actual V3 CHARGE ledger, no mutators."""
import json
from pathlib import Path
from .runtime import run as execute
from .spec import CAPS,digest
def reconcile(result,counts,events):
    totals={k:0 for k in CAPS};methods={}
    for e in events:
        if e['kind']!='CHARGE':continue
        key=e['resource'];n=e['amount']
        if key not in totals or type(n) is not int or n<=0:raise ValueError('invalid meter charge')
        totals[key]+=n
        if totals[key]!=e['total']:raise ValueError('meter cumulative total mismatch')
        if key=='solver_problems':methods[e.get('method','')]=methods.get(e.get('method',''),0)+n
    expected={'solver_problems':result.get('trajectory_queries'),'fresh_scenes':result.get('fresh_scene_attempts'),
      'action_scenes':result.get('action_scenes_observed'),'collection_attempts':result.get('collection_attempts')}
    valid=all(type(n) is int and 0<=n<=CAPS[k] for k,n in expected.items()) and expected==counts==totals and result.get('ik_problem_attempts')==0
    valid=valid and all(k.startswith('MotionGen.') for k in methods) and sum(methods.values())==counts['solver_problems']
    return {'pass':bool(valid),'local_counts':expected,'live_counts':counts,'event_totals':totals,'solver_methods':methods}
def run(manifest,*,meter):
    if meter is None or any(meter.counts.values()):raise ValueError('fresh live meter required')
    r=execute(manifest);out=Path(manifest['jobs'][0]['output_namespace'])
    try:
        events=[json.loads(s) for s in (meter.out/'events.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
        audit=reconcile(r,dict(meter.counts),events)
    except Exception as exc:audit={'pass':False,'error':{'type':type(exc).__name__,'message':str(exc)}}
    value=dict(r);value.pop('receipt_sha256');value.update(local_terminal_receipt_sha256=r['receipt_sha256'],meter_audit=audit)
    value['accounting_complete']=bool(r['accounting_complete'] and audit['pass']);value['pass']=bool(r['pass'] and value['accounting_complete'])
    value['scientific_route_pass']=bool(r['scientific_route_pass'] and value['pass']);value['receipt_sha256']=digest(value)
    from realization_utf8_io_v1 import write_new
    write_new(out/'meter_checked_terminal.json',value);return value
