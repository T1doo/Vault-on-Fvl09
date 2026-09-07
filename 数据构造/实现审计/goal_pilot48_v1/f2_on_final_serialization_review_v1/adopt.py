"""Main's append-only single-relation qualification, never pilot registration."""
from pathlib import Path
from .recover_v2 import run
from .recover import OUT, D, A, load, sha, digest

def checked(path, key='receipt_sha256'):
    value = load(path)
    body = dict(value)
    expected = body.pop(key)
    if digest(body) != expected:
        raise ValueError('receipt hash mismatch: '+str(path))
    return value

def build():
    review_path = OUT/'RECOVERY_REVIEW_002.json'
    review = checked(review_path)
    if run() != review:
        raise ValueError('independent real-trace recomputation differs')
    for path, expected in review['files'].items():
        if sha(path) != expected:
            raise ValueError('source/evidence drift: '+path)
    if not review['derived_final_predicates_pass'] or not review['original_error_reproduced']:
        raise ValueError('final recovery failed')
    goal = checked(D/'goal_terminal.json')
    guard_path = D.with_name(D.name+'_guard')/(D.name+'.terminal.json')
    guard = checked(guard_path)
    manifest_path = A/'goal_pilot48_v1/jobs'/f'{D.name}.json'
    manifest = checked(manifest_path, 'manifest_sha256')
    for receipt in (goal, guard):
        if receipt['job_id'] != D.name or receipt['manifest_sha256'] != manifest['manifest_sha256']:
            raise ValueError('job identity mismatch')
    if not (goal['pass'] and goal['accounting_complete'] and guard['task_owned_cleanup_pass']
            and guard['gpu_returned_to_idle_baseline'] and guard['lease_released']):
        raise ValueError('accounting or resource release incomplete')
    if goal['resource_counts'] != dict(solver_problems=4, fresh_scenes=1, action_scenes=1, collection_attempts=0):
        raise ValueError('qualification counts differ')
    branch = goal['runtime_result']['branch']
    if not branch['pass'] or branch['high_level_state_checks'] != 6:
        raise ValueError('branch infrastructure incomplete')
    if not branch['replay']['prefix_end_equivalent']:
        raise ValueError('canonical replay not equivalent')
    result = {
        'schema_version':'f2_on_append_only_qualification_adoption_v1',
        'job_id':D.name, 'relation':'on', 'qualification_pass':True,
        'original_goal_scientific_route_pass':goal['runtime_result']['scientific_route_pass'],
        'original_terminals_preserved':True, 'original_final_predicates_recomputed':True,
        'recovery_review_receipt_sha256':review['receipt_sha256'],
        'goal_receipt_sha256':goal['receipt_sha256'], 'guard_receipt_sha256':guard['receipt_sha256'],
        'new_physical_execution':False, 'new_raw_trajectories':0, 'new_accepted_roots':0,
        'pilot_input_acceptance':False, 'whole_F2_three_relation_root_pass':False,
        'scope':'only on suffix after the recorded actual canonical replay; no inside/beside inheritance',
        'files':{str(p):sha(p) for p in (review_path,D/'goal_terminal.json',guard_path,manifest_path,Path(__file__))},
    }
    result['receipt_sha256'] = digest(result)
    return result

if __name__ == '__main__':
    from realization_utf8_io_v1 import write_new
    result = build()
    write_new(OUT/'MAIN_QUALIFICATION_ADOPTION_001.json', result)
    print(result['receipt_sha256'])
