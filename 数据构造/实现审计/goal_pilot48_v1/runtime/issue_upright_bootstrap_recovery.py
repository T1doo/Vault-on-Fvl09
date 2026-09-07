"""Pure finite setup-boundary repair issuance, preserving the failed scene."""
from pathlib import Path
from .issue_upright_hd_video import build_manifest as hd_manifest, ROOT, W, CAPS, checked, sha, digest
PARENT = 'p48_f3_upright_qualification_hd_001'

def build_manifest(job_id, reservation):
    manifest = hd_manifest(job_id, reservation)
    manifest.pop('manifest_sha256')
    prior_path = ROOT/'jobs'/f'{PARENT}.json'
    prior = checked(prior_path, 'manifest_sha256')
    for table in ('source_files','input_files'):
        for path, expected in prior[table].items():
            if sha(path) != expected:
                raise ValueError('consumed qualification source/evidence changed')
    data = W/'Robotwin2/datasets'/PARENT
    goal_path = data/'goal_terminal.json'
    guard_path = data.with_name(PARENT+'_guard')/f'{PARENT}.terminal.json'
    goal, guard = checked(goal_path), checked(guard_path)
    for receipt in (goal,guard):
        if receipt['job_id'] != PARENT or receipt['manifest_sha256'] != prior['manifest_sha256']:
            raise ValueError('failed scene identity mismatch')
    expected = dict(solver_problems=0,fresh_scenes=1,action_scenes=0,collection_attempts=0)
    if not goal['accounting_complete'] or goal['resource_counts'] != expected or goal['pass']:
        raise ValueError('not the reviewed setup-only failure')
    result = goal['runtime_result']
    if result['error']['message'] != 'task action before current/anchor/trace' or result['standing_gate'] is not None:
        raise ValueError('different failure; do not reuse setup recovery')
    if not (guard['task_owned_cleanup_pass'] and guard['gpu_returned_to_idle_baseline'] and guard['lease_released']):
        raise ValueError('resource cleanup unresolved')
    folder = ROOT/'f3_upright_bootstrap_recovery_v1'
    if not all((folder/name).is_file() for name in ('runtime.py','test_all.py')):
        raise ValueError('bootstrap repair runtime/tests not delivered')
    for path in folder.glob('*.py'):
        manifest['source_files'][str(path)] = sha(path)
    manifest['source_files'][str(Path(__file__).resolve())] = sha(Path(__file__))
    for path in (prior_path,goal_path,guard_path,data/'qualification_terminal.json'):
        manifest['input_files'][str(path)] = sha(path)
    manifest.update(bootstrap_recovery_of=PARENT, failure_class='F3_INITIALIZATION_ACTION_SCOPE',
                    evidence_based_revision=1, failed_setup_scene_count_retained=1,
                    maximum_round_fresh_scenes_after_this_attempt=2,
                    second_successful_confirmation_not_authorized_here=True,
                    parent_failure_receipt_sha256=goal['receipt_sha256'],
                    physics_and_video_configuration_unchanged=True)
    manifest['jobs'][0].update(runtime_module='goal_pilot48_v1.f3_upright_bootstrap_recovery_v1.runtime',
                              runtime_file=str(folder/'runtime.py'),
                              test_module='goal_pilot48_v1.f3_upright_bootstrap_recovery_v1.test_all')
    manifest['manifest_sha256'] = digest(manifest)
    return manifest
