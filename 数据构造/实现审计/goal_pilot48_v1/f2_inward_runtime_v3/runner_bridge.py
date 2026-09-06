import json
from pathlib import Path
from .runtime import run as execute
from .contract import digest
from goal_pilot48_v1.f2_inward_runtime_v1.runner_bridge import reconcile_meter

def run(manifest):
    r=execute(manifest);out=Path(manifest['jobs'][0]['output_namespace'])
    try:
        events=[json.loads(line) for line in (out.parent/(out.name+'_meter')/'events.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
        audit=reconcile_meter(r,events)
    except Exception as e:audit={'pass':False,'error_type':type(e).__name__,'error':str(e)}
    v=dict(r);v.pop('receipt_sha256');v.update(parent_runtime_receipt_sha256=r['receipt_sha256'],runtime_version='f2_fixed_layout_U_route_revision1_v3',meter_crosscheck=audit)
    v['accounting_complete']=bool(r['accounting_complete'] and audit['pass']);v['pass']=bool(r['pass'] and v['accounting_complete']);v['receipt_sha256']=digest(v)
    from realization_utf8_io_v1 import write_new
    write_new(out/'f2_meter_crosschecked_terminal.json',v);return v
