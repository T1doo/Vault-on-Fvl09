"""F2-only accounting tightening without changing the frozen common runner."""
import json
from pathlib import Path
from .contract import A, digest

KEYS = ('solver_problems', 'fresh_scenes', 'action_scenes', 'collection_attempts')

def reconcile_meter(result, events):
    counts = dict.fromkeys(KEYS, 0)
    methods = {}
    errors = []
    for row in events:
        if row['kind'] != 'CHARGE':
            continue
        key, amount = row.get('resource'), row.get('amount')
        if key not in counts or type(amount) is not int or amount <= 0:
            raise ValueError('unknown/nonintegral meter charge')
        counts[key] += amount
        if row.get('total') != counts[key]:
            raise ValueError('meter charge sequence mismatch')
        if key == 'solver_problems':
            method = row.get('method', '')
            methods[method] = methods.get(method, 0) + amount
    ik = result.get('ik_problem_attempts')
    trajectory = result.get('trajectory_queries')
    scenes = result.get('fresh_scene_attempts')
    known = all(type(x) is int and x >= 0 for x in (ik, trajectory, scenes))
    if not known:
        errors.append('runtime count unknown')
    else:
        expected = dict(zip(KEYS, (ik + trajectory, scenes, 0, 0)))
        if counts != expected:
            errors.append('runtime/meter aggregate disagreement')
        ik_meter = sum(v for k, v in methods.items() if k.startswith('IKSolver.'))
        trajectory_meter = sum(v for k, v in methods.items() if k.startswith('MotionGen.'))
        if ik_meter != ik or trajectory_meter != trajectory or ik_meter + trajectory_meter != counts['solver_problems']:
            errors.append('IK/trajectory method partition disagreement')
        if ik > 3 or trajectory > 4 or scenes > 1:
            errors.append('F2 exact cap exceeded')
    if result.get('physical_execution_count') != 0 or result.get('collection_calls') != 0 or result.get('new_raw_trajectories') != 0 or result.get('new_roots') != 0:
        errors.append('planner-only boundary violation')
    if not result.get('accounting_complete'):
        errors.append('runtime ledger incomplete')
    return {'pass': not errors, 'counts': counts, 'solver_methods': methods, 'errors': errors,
            'inner_motiongen_IK_not_double_counted': True}

def run(manifest):
    from .runtime import run as execute
    result = execute(manifest)
    out = Path(manifest['jobs'][0]['output_namespace'])
    meter_path = out.parent / (out.name + '_meter') / 'events.jsonl'
    try:
        events = [json.loads(line) for line in meter_path.read_text(encoding='utf-8').splitlines() if line.strip()]
        audit = reconcile_meter(result, events)
    except Exception as exc:
        audit = {'pass': False, 'errors': [{'type': type(exc).__name__, 'message': str(exc)}]}
    # The historical scientific runtime terminal remains immutable; this is
    # an append-only stricter receipt consumed by generic job_runner.py.
    returned = dict(result)
    returned['parent_runtime_receipt_sha256'] = result['receipt_sha256']
    returned.pop('receipt_sha256')
    returned['meter_crosscheck'] = audit
    returned['accounting_complete'] = bool(result['accounting_complete'] and audit['pass'])
    returned['pass'] = bool(result['pass'] and returned['accounting_complete'])
    returned['receipt_sha256'] = digest(returned)
    from realization_utf8_io_v1 import write_new
    write_new(out / 'f2_meter_crosschecked_terminal.json', returned)
    return returned
