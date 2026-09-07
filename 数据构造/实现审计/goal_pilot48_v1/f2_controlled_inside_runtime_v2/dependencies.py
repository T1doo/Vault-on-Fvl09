"""Additive source lock proposal, not an issuer or resource reservation."""
from pathlib import Path
from .spec import A,sha,prefix_lineage,CONTACT,CAPS

def additional_bindings():
    from goal_pilot48_v1.f2_inside_native_floor_v1.dependencies import bindings
    native=bindings();root=Path(__file__).parent
    sources=dict(native['source_files']);sources.update({str(p):sha(p) for p in root.glob('*.py')})
    inputs=dict(native['input_files']);inputs.update(prefix_lineage()['files']);inputs[str(CONTACT)]=sha(CONTACT)
    return {'additional_source_files':sources,'additional_input_files':inputs,
      'parent_manifest_to_verify_and_preserve':str(A/'goal_pilot48_v1/jobs/p48_f2_prefix_clearance_001.json'),
      'caps':CAPS,'high_level_state_check_cap':10,'root_runtime_or_issuer_included':False,
      'parent_all_transitive_sources_and_Guard_identity_must_be_verified_by_future_issuer':True,
      'runtime_file':str(root/'runtime.py'),'test_module':'goal_pilot48_v1.f2_controlled_inside_runtime_v2.test_all'}
