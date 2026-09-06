"""Revision1 dispatcher retains complete F2 meter reconciliation."""
import json
from pathlib import Path
from .contract import digest
from .runtime import run as execute
from goal_pilot48_v1.f2_inward_runtime_v1.runner_bridge import reconcile_meter

def run(manifest):
    result = execute(manifest)
    out = Path(manifest['jobs'][0]['output_namespace'])
    meter_path = out.parent / (out.name + '_meter') / 'events.jsonl'
    try:
        events = [json.loads(line) for line in meter_path.read_text(encoding='utf-8').splitlines() if line.strip()]
        audit = reconcile_meter(result, events)
    except Exception as exc:
        audit = {'pass': False, 'errors': [{'type': type(exc).__name__, 'message': str(exc)}]}
    returned = dict(result)
    returned['parent_runtime_receipt_sha256'] = result['receipt_sha256']
    returned.pop('receipt_sha256')
    returned['runtime_version'] = 'f2_inward_runtime_v2_revision1'
    returned['meter_crosscheck'] = audit
    returned['accounting_complete'] = bool(result['accounting_complete'] and audit['pass'])
    returned['pass'] = bool(result['pass'] and returned['accounting_complete'])
    returned['receipt_sha256'] = digest(returned)
    from realization_utf8_io_v1 import write_new
    write_new(out / 'f2_meter_crosschecked_terminal.json', returned)
    return returned
