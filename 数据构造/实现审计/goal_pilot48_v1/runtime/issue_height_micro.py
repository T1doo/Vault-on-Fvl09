"""Main-only issuance: fixed contact-height revision, never a height sweep."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from budget import ROOT, read, digest, atomic, reserve
from issue import sha

def checked(path):
    value = read(path)
    payload = dict(value)
    receipt = payload.pop('receipt_sha256')
    if digest(payload) != receipt:
        raise ValueError('receipt hash mismatch: ' + str(path))
    return value

def main(job_id):
    folder = ROOT / 'f3_contact_height_revision_v1'
    recipe = checked(folder / 'recipe.json')
    audit = checked(folder / 'cpu_audit.json')
    if audit['pass'] is not True or audit['recipe_file_sha256'] != sha(folder / 'recipe.json'):
        raise ValueError('height geometry prerequisite')
    parent = checked(ROOT / 'f3_com_revision_v1/recipe.json')
    delta = [a-b for a,b in zip(recipe['desired_actual_flange_world_pose'], parent['desired_actual_flange_world_pose'])]
    if any(abs(a-b) > 1e-12 for a,b in zip(delta, [0,0,.01,0,0,0,0])):
        raise ValueError('only the preregistered 10mm height revision is permitted')
    m = read(ROOT / 'jobs/p48_f3_micro_002.json')
    m.pop('manifest_sha256')
    out = ROOT / 'jobs' / (job_id + '.json')
    destination = Path('/nfs_share/lijunhui/Robotwin2/datasets') / job_id
    guard = destination.with_name(job_id + '_guard')
    if out.exists() or destination.exists() or guard.exists():
        raise FileExistsError('job namespace already used')
    m['recipe_spec_path'] = str(folder / 'recipe.json')
    m['evidence_based_revision'] = 2
    m['run_id'] = job_id
    m['guard_directory'] = str(guard)
    m['jobs'][0].update(job_id=job_id, output_namespace=str(destination))
    for p in [Path(__file__), *folder.glob('*.py')]:
        m['source_files'][str(p.resolve())] = sha(p)
    for p in [*folder.glob('*.json'), ROOT / 'f3_second_slip_audit_v1/comparison.json',
              destination.with_name('p48_f3_micro_002') / 'goal_terminal.json']:
        m['input_files'][str(p)] = sha(p)
    for field in ('source_files', 'input_files'):
        for p, expected in m[field].items():
            if sha(p) != expected:
                raise ValueError('bound dependency changed before reservation: ' + p)
    event = reserve(job_id, m['reserved'], 'F3 postlift-roll revision2: COM station retained, grasp/pregrasp +10mm only')
    m['reservation_event_sha256'] = event['event_sha256']
    m['manifest_sha256'] = digest(m)
    atomic(out, m)
    print(out)

if __name__ == '__main__':
    main(sys.argv[1])
