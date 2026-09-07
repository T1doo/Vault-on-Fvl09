"""One new Goal-scoped interface repair; neither failed scene is erased."""
from pathlib import Path
from .issue_upright_hd_video import build_manifest as hd_manifest, ROOT, W, CAPS, checked, sha, digest

PARENT = 'p48_f3_upright_qualification_bootstrap_001'

def build_manifest(job_id, reservation):
    m = hd_manifest(job_id, reservation)
    m.pop('manifest_sha256')
    prior_path = ROOT/'jobs'/f'{PARENT}.json'
    prior = checked(prior_path, 'manifest_sha256')
    for table in ('source_files', 'input_files'):
        for path, expected in prior[table].items():
            if sha(path) != expected:
                raise ValueError('prior execution binding changed')
    data = W/'Robotwin2/datasets'/PARENT
    goal_path = data/'goal_terminal.json'
    guard_path = data.with_name(PARENT+'_guard')/f'{PARENT}.terminal.json'
    goal, guard = checked(goal_path), checked(guard_path)
    for receipt in (goal, guard):
        if receipt['job_id'] != PARENT or receipt['manifest_sha256'] != prior['manifest_sha256']:
            raise ValueError('prior job identity mismatch')
    if goal['pass'] or not goal['accounting_complete'] or goal['resource_counts'] != dict(solver_problems=0,fresh_scenes=1,action_scenes=0,collection_attempts=0):
        raise ValueError('not the exact interface failure')
    r = goal['runtime_result']
    if r['error']['type'] != 'AttributeError' or r['error']['message'] != "'CountedUpright' object has no attribute '_contacts'" or r['standing_gate'] is not None:
        raise ValueError('different failure; no unchanged retries')
    if not (guard['task_owned_cleanup_pass'] and guard['gpu_returned_to_idle_baseline'] and guard['lease_released']):
        raise ValueError('prior resources not released')
    folder = ROOT/'f3_upright_trace_recovery_v1'
    for name in ('runtime.py','test_all.py','capability_audit.py','IMPACT.md'):
        if not (folder/name).is_file():
            raise ValueError('incomplete trace recovery review')
    for path in folder.glob('*.py'):
        m['source_files'][str(path)] = sha(path)
    m['source_files'][str(Path(__file__).resolve())] = sha(Path(__file__))
    for path in (folder/'IMPACT.md',prior_path,goal_path,guard_path,data/'qualification_terminal.json'):
        m['input_files'][str(path)] = sha(path)
    # Audited live inheritance source, not a historical review snapshot.
    for name in ('scene_inspection.py','action_feasibility_v2.py','runtime_trace.py'):
        path = W/'Robotwin2/project/RoboTwin/controlled_multi_future/probes'/name
        m['source_files'][str(path)] = sha(path)
    m.update(trace_recovery_of=PARENT,failed_setup_scene_count_retained=2,
             new_finite_recovery_scope=True,second_successful_confirmation_not_authorized_here=True,
             previous_two_scene_envelope_exhausted=True,maximum_upright_lineage_scenes_after_this_attempt=3,
             failure_class='F3_SCENE_INTERFACE_WIRING',evidence_based_revision=2,
             parent_failure_receipt_sha256=goal['receipt_sha256'],
             physical_design_and_thresholds_unchanged=True)
    m['jobs'][0].update(runtime_module='goal_pilot48_v1.f3_upright_trace_recovery_v1.runtime',
                       runtime_file=str(folder/'runtime.py'),
                       test_module='goal_pilot48_v1.f3_upright_trace_recovery_v1.test_all')
    m['manifest_sha256'] = digest(m)
    return m
