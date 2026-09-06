"""Additional bindings for the main-thread issuer; no reservation/publication."""
import hashlib
from pathlib import Path
from .contract import A, PROPOSAL, PROPOSAL_SHA, manifest_lineage

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def additional_bindings():
    root = Path(__file__).parent
    review = root.parent / 'f2_inward_failure_review_v1'
    source = {str(p): sha(p) for p in root.glob('*.py')}
    # Bind both runtime dependencies and the proposal's derivation provenance.
    for p in [review / 'analyze.py', review / 'propose.py', review / 'test_cpu.py',
              A / 'f3_model_replay_v1/kinematics_cpu.py']:
        source[str(p)] = sha(p)
    inputs = {str(p): sha(p) for p in [PROPOSAL, review / 'analysis_v1_1.json', review / 'REPORT.md']}
    if inputs[str(PROPOSAL)] != PROPOSAL_SHA:
        raise ValueError('revision proposal changed')
    return {'additional_source_files': source, 'additional_input_files': inputs, 'manifest_fields': manifest_lineage(),
            'base_dependencies_required': 'retain all source_files/input_files from p48_f2_inward_001; validate bytes before adding these',
            'runtime_module': 'goal_pilot48_v1.f2_inward_runtime_v2.runner_bridge',
            'runtime_file': str(root / 'runner_bridge.py'), 'test_module': 'goal_pilot48_v1.f2_inward_runtime_v2.test_cpu',
            'resource_caps': {'solver_problems': 7, 'fresh_scenes': 1, 'action_scenes': 0, 'collection_attempts': 0}}
