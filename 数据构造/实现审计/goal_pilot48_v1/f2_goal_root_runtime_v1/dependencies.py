"""Prefix-only source/spec bindings for a future main-thread issuer."""
import hashlib,json
from pathlib import Path
from .spec import A,W,build_prefix_spec,digest
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def additional_bindings():
    root=Path(__file__).parent;source={str(p):sha(p) for p in root.glob('*.py')}
    data=W/'Robotwin2/datasets/p48_f2_u_route_001'
    evidence=[data/n for n in ('goal_terminal.json','job_terminal.json','live_capture.json','carried_robot_config.json','world_geometry.json')]
    parent=W/'Robotwin2/datasets/controlled_multi_future_f2_top_contact_root_v1/f2-top-contact-development-rpc-root-v1-run1/root'
    evidence += [parent/'canonical_prefix_reference_trace.npz',parent/'canonical_prefix_artifact/canonical_prefix_artifact.json',root/'postclose_cpu_audit.json']
    for p in (A/'f3_model_replay_v1/kinematics_cpu.py',A/'goal_pilot48_v1/f2_inward_failure_review_v1/analyze.py'):
        source[str(p)]=sha(p)
    return {'additional_source_files':source,'additional_input_files':{str(p):sha(p) for p in evidence},
      'manifest_fields':{'f2_goal_prefix_spec_sha256':digest(build_prefix_spec())},
      'parent_dependencies_required':'retain and validate all p48_f2_u_route_001 sources and inputs',
      'runtime_module':'goal_pilot48_v1.f2_goal_root_runtime_v1.runner_bridge','runtime_file':str(root/'runner_bridge.py'),
      'test_module':'goal_pilot48_v1.f2_goal_root_runtime_v1.test_issuer','resource_caps':build_prefix_spec()['resource_caps'],
      'requires_live_meter':True,
      'full_root_dispatch_enabled':False,'GPU_prefix_model_sequence_validation_pending':True}
