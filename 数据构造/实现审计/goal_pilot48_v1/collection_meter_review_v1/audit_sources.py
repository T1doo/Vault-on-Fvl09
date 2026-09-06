"""Read-only evidence for actual collection entry points and profile mismatch."""
import ast
import hashlib
import json
from pathlib import Path
W = Path('/nfs_share/lijunhui')
A = W / 'Vault-on-Fvl09/数据构造/实现审计'
P = W / 'Robotwin2/project/RoboTwin/controlled_multi_future'

def audit():
    paths = [P / 'root_orchestrator_v1_2.py', P / 'root_orchestrator_v1_1.py', P / 'real_sapien_adapter_v1_2.py',
             A / 'realization_batch_runtime_v1_3/pipeline.py', A / 'realization_batch_runtime_v1_3/catalog.py',
             A / 'realization_parent_f1_bridge_cpu_v1.py', A / 'goal_pilot48_v1/runtime/meter.py']
    records = []
    for path in paths:
        text = path.read_text(encoding='utf-8'); tree = ast.parse(text)
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, 'attr', None) in ('scene', '_scene_call'):
                phase = next((k.value for k in node.keywords if k.arg == 'phase'), None)
                found.append({'line': node.lineno, 'method': node.func.attr, 'phase_expression': None if phase is None else ast.unparse(phase)})
        records.append({'path': str(path), 'file_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(), 'scene_dispatch': found})
    meter = paths[-1].read_text(encoding='utf-8')
    assert "charge('collection_attempts'" not in meter
    return {'schema_version': 'collection_entry_source_audit_v1', 'records': records,
            'frozen_goal_meter_has_collection_charge_hook': False,
            'new_helper_gpu_executions': 0, 'new_helper_installed_in_frozen_runtime': False}

if __name__ == '__main__': print(json.dumps(audit(), ensure_ascii=False, indent=2))
