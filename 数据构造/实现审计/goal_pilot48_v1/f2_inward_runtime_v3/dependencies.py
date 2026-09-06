import hashlib,json
from pathlib import Path
from .contract import A,PROPOSAL,manifest_lineage
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def additional_bindings():
    root=Path(__file__).parent;source={str(p):sha(p) for p in root.glob('*.py')}
    evidence=json.loads(PROPOSAL.read_text(encoding='utf-8'))
    # Preserve the exact reviewed evidence sources, do not silently rehash
    # changed derivation inputs as if they were the same completed CPU audit.
    for p,h in evidence['source_files'].items():
        if sha(p)!=h:raise ValueError('U evidence source changed: '+p)
        source[p]=h
    inputs={str(PROPOSAL):sha(PROPOSAL)}
    for p,h in evidence['input_files'].items():
        if sha(p)!=h:raise ValueError('U evidence input changed: '+p)
        inputs[p]=h
    return {'additional_source_files':source,'additional_input_files':inputs,'manifest_fields':manifest_lineage(),
      'base_dependencies_required':'retain and validate all p48_f2_revision1_001 bindings, including v1/v2 mechanics and helpers',
      'runtime_module':'goal_pilot48_v1.f2_inward_runtime_v3.runner_bridge','runtime_file':str(root/'runner_bridge.py'),
      'test_module':'goal_pilot48_v1.f2_inward_runtime_v3.test_cpu',
      'resource_caps':{'solver_problems':7,'fresh_scenes':1,'action_scenes':0,'collection_attempts':0}}
