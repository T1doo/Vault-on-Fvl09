"""Pure issuer: approved upright-B first scene only, no reservation writes."""
import re
from pathlib import Path
from .budget import ROOT, read, digest
from .issue_one_sided_micro import checked, sha, W
from goal_pilot48_v1.runtime_v3.migration import bindings

CAPS = dict(solver_problems=6, fresh_scenes=1, action_scenes=1,
            collection_attempts=0, gpu_lease_seconds=1080)
DESIGN = ROOT/'f3_upright_design_v1/design_spec.json'
APPROVAL = ROOT/'USER_F2_CONTACT_F3_UPRIGHT_APPROVAL_V1_20260907.md'

def build_manifest(job_id, reservation):
    if not re.fullmatch(r'p48_f3_upright_qualification_[a-z0-9_]+', job_id):
        raise ValueError('new first-qualification namespace required')
    locations = [ROOT/'jobs'/f'{job_id}.json', W/'Robotwin2/datasets'/job_id,
                 W/'Robotwin2/datasets'/f'{job_id}_guard', W/'Robotwin2/datasets'/f'{job_id}_meter',
                 W/'Robotwin2/cache/p48'/job_id]
    if any(p.exists() for p in locations):
        raise FileExistsError('qualification namespace already used')
    if (reservation.get('kind') != 'RESERVE' or reservation.get('job_id') != job_id
            or reservation.get('reserved') != CAPS or not reservation.get('event_sha256')):
        raise ValueError('exact main-owned reservation required')
    if sha(APPROVAL) != '5eeb6a2998656cec08657cbcbcb2379b544a53a7e0f139509559f2f61ef6fd5e':
        raise ValueError('explicit upright design authority changed')
    design = checked(DESIGN)
    if design['receipt_sha256'] != '1976ee32ab6d53fc6bfdfe2ed949c70614c96cfb7d61529d6014127a0b05436f':
        raise ValueError('unique selected B design changed')
    parent_path = ROOT/'jobs/p48_f3_one_sided_micro_001.json'
    parent = checked(parent_path, 'manifest_sha256')
    migrated = bindings(parent)  # Verify old source/input bytes before extending.
    contract = checked(ROOT/'CONTRACT.json')
    if parent['goal_contract_receipt_sha256'] != contract['receipt_sha256']:
        raise ValueError('Goal mismatch')
    sources, inputs = migrated['source_files'], migrated['input_files']
    def add(table, path, expected=None):
        path = Path(path).resolve()
        if not path.is_relative_to(W):
            raise ValueError('outside workspace')
        value = sha(path)
        if expected is not None and value != expected:
            raise ValueError('design source changed '+str(path))
        if str(path) in table and table[str(path)] != value:
            raise ValueError('source conflict '+str(path))
        table[str(path)] = value
    for path, value in design['source_bindings'].items():
        add(sources, path, value)
    runtime = ROOT/'f3_upright_qualification_runtime_v1'
    for folder in (runtime, ROOT/'f3_upright_design_v1'):
        for path in folder.glob('*.py'): add(sources, path)
        for path in folder.glob('*.json'): add(inputs, path)
    add(sources, Path(__file__))
    add(sources, ROOT/'runtime/test_upright_issuer.py')
    add(sources, W/'Robotwin2/env/lib/python3.10/site-packages/sapien/wrapper/urdf_loader.py')
    for path in (parent_path, APPROVAL, DESIGN): add(inputs, path)
    m = {k:parent[k] for k in ('schema_version','goal_id','goal_contract_receipt_sha256',
         'issuance','implementation_source_sha256','robotwin_tracked_head','initialization_policy','cache_directory')}
    m.update(migrated, run_id=job_id, approved=True, gpu_execution_authorized=True,
             physical_execution_authorized=True, pilot_input_authorized=False,
             formal_360_authorized=False, training_authorized=False, stage0_reopened=False,
             stage1_authorized=False, shared_v_authorized=False, collection_authorized=False,
             allowed_physical_gpu_indices=list(range(8)), gpu_jobs_serial=True,
             reserved=dict(CAPS), reservation_event_sha256=reservation['event_sha256'],
             guard_directory=str(W/'Robotwin2/datasets'/f'{job_id}_guard'),
             upright_design_spec_path=str(DESIGN), upright_design_spec_sha256=sha(DESIGN),
             upright_design_approval_sha256=sha(APPROVAL), first_fresh_only=True,
             confirmation_authorized_by_this_manifest=False,
             original_stability_revision_budget_not_reset=True,
             physical_numeric_thresholds_changed=False)
    m['jobs'] = [dict(job_id=job_id, family='F3', kind='F3_UPRIGHT_QUALIFICATION',
        output_namespace=str(W/'Robotwin2/datasets'/job_id), timeout_seconds=900,
        requires_live_meter=True, runtime_module='goal_pilot48_v1.f3_upright_qualification_runtime_v1.runtime',
        runtime_file=str(runtime/'runtime.py'), test_module='goal_pilot48_v1.f3_upright_qualification_runtime_v1.test_all',
        resource_caps={k:v for k,v in CAPS.items() if k != 'gpu_lease_seconds'})]
    m['manifest_sha256'] = digest(m)
    return m
