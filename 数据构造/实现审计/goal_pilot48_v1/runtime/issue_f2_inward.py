"""Main-thread issuer; importing/building does not reserve or publish a job.

Only the main scheduler may call issue(job_id). CPU tests call build_manifest
with a synthetic reservation and never touch the Goal ledger.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A = ROOT.parent
W = Path('/nfs_share/lijunhui')
P = W / 'Robotwin2/project/RoboTwin'
CAPS = {'solver_problems': 7, 'fresh_scenes': 1, 'action_scenes': 0, 'collection_attempts': 0, 'gpu_lease_seconds': 1980}

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()

def _add(mapping, paths):
    for path in paths:
        p = Path(path).resolve()
        if not p.is_relative_to(W) or not p.is_file():
            raise ValueError('missing/outside binding: ' + str(path))
        mapping[str(p)] = sha(p)

def bindings():
    """Own dynamic imports plus full active Python/CuRobo source closure.

    This is source/config/asset binding, not a claim of a lock on every third
    party installed distribution or system driver. Guard environment and actual
    GPU cache/kinematics checks remain independently mandatory.
    """
    parent_path = A / 'F2_ENDPOINT_REMAINING_SCENE_MANIFEST_V1_1_20260906.json'
    parent = read(parent_path)
    sources = dict(parent['source_files'])
    inputs = dict(parent['input_files'])
    # Reject changed parent dependencies rather than silently blessing new bytes.
    for table in (sources, inputs):
        for path, expected in table.items():
            if sha(path) != expected:
                raise ValueError('retained F2 dependency changed: ' + path)
    for folder in (ROOT / 'runtime', ROOT / 'f2_inward_runtime_v1', A / 'f2_f3_model_bridge_v1_1', A / 'f2_endpoint_constraint_runtime_v1_1', A / 'f2_bounded_transit_runtime_v1', A / 'support_pair_collision_v1'):
        _add(sources, folder.glob('*.py'))
    _add(sources, [A / 'f2_inward_binding_and_route_state_v1.py', A / 'f2_inward_prereqs_v1.py', A / 'f2_controlled_insertion_route_gate_run1_runtime_v1/job_runner.py', A / 'realization_utf8_io_v1.py',
                   W / 'Robotwin2/production_micro_gate_v1/job_runner.py', W / 'Robotwin2/production_micro_gate_v1/guarded_launcher.py'])
    # envs imports helpers transitively and transforms.py extracts Robot methods;
    # bind the source tree instead of only a short list of visible entry points.
    _add(sources, (P / 'envs').rglob('*.py'))
    _add(sources, (P / 'controlled_multi_future').rglob('*.py'))
    _add(inputs, [p for p in (P / 'task_config').rglob('*') if p.is_file() and p.suffix in ('.yml', '.yaml', '.json')])
    curobo = P / 'envs/curobo/src/curobo'
    _add(inputs, [p for p in curobo.rglob('*') if p.is_file() and p.suffix in ('.yml', '.yaml', '.cu', '.cuh', '.cpp', '.h')])
    _add(inputs, [parent_path, ROOT / 'CONTRACT.json', ROOT / 'USER_GOAL_SOURCE.md',
                  A / 'EXTERNAL_NEW_F2_F3_F4B_DECISION_20260906.yaml',
                  A / 'F2_ENDPOINT_DIAGNOSIS_AND_ONE_LAYOUT_PROPOSAL_V1_20260906.json',
                  A / 'F2_INWARD_NEW_BINDING_ROUTE_STATE_CONTRACT_V1_20260906.json',
                  A / 'F2_INWARD_COMPLETE_CPU_PREREQUISITES_V1_20260906.json',
                  A / 'F2_INWARD_PROPOSAL_CPU_GEOMETRY_V1_20260906.json'])
    sealed = W / 'Robotwin2/datasets/controlled_multi_future_f2_top_contact_root_v1/f2-top-contact-development-rpc-root-v1-run1/root'
    _add(inputs, [sealed / 'planned_root_slot_spec.json', sealed / 'canonical_prefix_reference_trace.npz',
                  sealed / 'suffix_preflight/F2-inside/preflight_boundary_receipt.json',
                  sealed / 'suffix_preflight/F2-inside/controller_partial_evidence.json',
                  sealed / 'suffix_preflight/F2-beside/controller_partial_evidence.json'])
    # CPU preflight reads these actual native captures, not only derived booleans.
    old = W / 'Robotwin2/datasets/f2_endpoint_constraint_remaining_v1_1'
    _add(inputs, [old / 'live_model_capture.json', old / 'world_geometry.json'])
    for asset, idx in (('071_can', 0), ('062_plasticbox', 2), ('072_electronicscale', 0), ('074_displaystand', 0)):
        folder = P / 'assets/objects' / asset
        _add(inputs, [folder / ('model_data' + str(idx) + '.json'), folder / 'collision' / ('base' + str(idx) + '.glb'), folder / 'visual' / ('base' + str(idx) + '.glb')])
        if (folder / 'points_info.json').exists():
            _add(inputs, [folder / 'points_info.json'])
    # Robot URDF and referenced meshes/configuration are modest and fixed.
    _add(inputs, [p for p in (P / 'assets/embodiments/aloha-agilex').rglob('*') if p.is_file() and p.suffix.lower() in ('.yml', '.yaml', '.urdf', '.stl', '.obj', '.dae', '.mtl', '.glb')])
    return sources, inputs, parent

def build_manifest(job_id, reservation):
    if not re.fullmatch(r'p48_f2_[a-z0-9_]+', job_id):
        raise ValueError('F2 namespaced job ID required')
    if reservation.get('job_id') != job_id or reservation.get('reserved') != CAPS or reservation.get('kind') != 'RESERVE':
        raise ValueError('exact reservation required')
    c = read(ROOT / 'CONTRACT.json')
    check = dict(c); h = check.pop('receipt_sha256')
    if digest(check) != h or not c['adopted_by_user_goal'] or sha(ROOT / 'USER_GOAL_SOURCE.md') != c['source_file_sha256']:
        raise ValueError('Goal source/contract mismatch')
    sources, inputs, parent = bindings()
    lineage = read(A / 'F2_INWARD_NEW_BINDING_ROUTE_STATE_CONTRACT_V1_20260906.json')
    from goal_pilot48_v1.f2_inward_runtime_v1.contract import build_contract
    actual = build_contract()
    if actual['binding'] != lineage['binding'] or actual['planned'] != lineage['planned'] or actual['inward_goals'] != lineage['goals']:
        raise ValueError('actual runtime construction differs from frozen new-layout lineage')
    runtime = ROOT / 'runtime'
    m = {'schema_version': 'cmf_goal_subjob_manifest_v1', 'goal_id': c['goal_id'], 'goal_contract_receipt_sha256': h,
         'issuance': 'ISSUED_UNDER_USER_GOAL', 'approved': True, 'gpu_execution_authorized': True,
         'physical_execution_authorized': False, 'allowed_physical_gpu_indices': list(range(8)), 'gpu_jobs_serial': True,
         'formal_360_authorized': False, 'training_authorized': False, 'stage0_reopened': False, 'stage1_authorized': False,
         'pilot_input_authorized': False, 'run_id': job_id, 'reservation_event_sha256': reservation['event_sha256'], 'reserved': dict(CAPS),
         'guard_directory': str(W / 'Robotwin2/datasets' / (job_id + '_guard')), 'cache_directory': str(W / 'Robotwin2/cache/p48'),
         'implementation_source_sha256': parent['implementation_source_sha256'], 'robotwin_tracked_head': parent['robotwin_tracked_head'],
         'source_files': sources, 'input_files': inputs,
         'initialization_policy': 'skip dummy MotionGen.warmup, log separately; lazy actual solve; no unmetered task solve',
         'new_layout_lineage': {'binding_sha256': lineage['binding']['binding_sha256'], 'planned_root_slot_spec_sha256': lineage['planned']['planned_root_slot_spec_sha256'],
                                'parent_binding_sha256': lineage['binding']['parent_binding_sha256'], 'old_inside_success_not_adopted': True,
                                'new_current_anchor_required_for_future_collection': True, 'held_state_restoration_is_planner_only': True},
         'jobs': [{'job_id': job_id, 'family': 'F2', 'kind': 'F2_INWARD_PLANNER_GATE',
                   'runtime_module': 'goal_pilot48_v1.f2_inward_runtime_v1.runner_bridge', 'runtime_file': str(ROOT / 'f2_inward_runtime_v1/runner_bridge.py'),
                   'test_module': 'goal_pilot48_v1.f2_inward_runtime_v1.test_issuer',
                   'output_namespace': str(W / 'Robotwin2/datasets' / job_id), 'timeout_seconds': 1800,
                   'resource_caps': {k: v for k, v in CAPS.items() if k != 'gpu_lease_seconds'}}]}
    for role, name in (('guard', 'guarded_launcher.py'), ('runner', 'job_runner.py')):
        m[role + '_script_path'] = str(runtime / name)
        m[role + '_script_sha256'] = sha(runtime / name)
    m['manifest_sha256'] = digest(m)
    return m

def issue(job_id):
    """Explicit main-scheduler mutation: preflight first, reserve once, publish."""
    from goal_pilot48_v1.runtime.budget import reserve
    from realization_utf8_io_v1 import write_new
    path = ROOT / 'jobs' / (job_id + '.json')
    namespaces = [path, W / 'Robotwin2/datasets' / job_id,
                  W / 'Robotwin2/datasets' / (job_id + '_guard'),
                  W / 'Robotwin2/datasets' / (job_id + '_meter'),
                  W / 'Robotwin2/cache/p48' / job_id]
    if any(p.exists() for p in namespaces):
        raise FileExistsError('F2 job namespace consumed')
    stub = {'kind': 'RESERVE', 'job_id': job_id, 'reserved': dict(CAPS), 'event_sha256': 'pending_main_reservation'}
    m = build_manifest(job_id, stub)
    event = reserve(job_id, dict(CAPS), 'F2 single inward layout: fixed C/U/D IK then carry/release U/D/U/N; no physical/action/collection')
    m.pop('manifest_sha256')
    m['reservation_event_sha256'] = event['event_sha256']
    m['manifest_sha256'] = digest(m)
    write_new(path, m)
    return m

if __name__ == '__main__':
    print(json.dumps(issue(sys.argv[1]), ensure_ascii=False, indent=2))
