"""Issue one evidence-bound segmented approach; no change to the grasp recipe."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from budget import ROOT, read, digest, atomic, reserve
from issue import sha

def main(job_id):
    m = read(ROOT / 'jobs/p48_f3_micro_003.json')
    m.pop('manifest_sha256')
    folder = ROOT / 'f3_runtime_v3'
    route = read(folder / 'route_spec.json')
    payload = dict(route)
    receipt = payload.pop('receipt_sha256')
    if digest(payload) != receipt or route['max_single_queries'] != 4:
        raise ValueError('route spec invalid')
    out = ROOT / 'jobs' / (job_id + '.json')
    destination = Path('/nfs_share/lijunhui/Robotwin2/datasets') / job_id
    guard = destination.with_name(job_id + '_guard')
    if any(p.exists() for p in (out, destination, guard)):
        raise FileExistsError('job namespace already used')
    caps = dict(m['reserved'], solver_problems=4)
    m.update(run_id=job_id, reserved=caps, guard_directory=str(guard),
             route_spec_path=str(folder / 'route_spec.json'), pregrasp_route_revision=1)
    m['jobs'][0].update(job_id=job_id, output_namespace=str(destination),
        runtime_module='goal_pilot48_v1.f3_runtime_v3.micro',
        runtime_file=str(folder / 'micro.py'), test_module='goal_pilot48_v1.f3_runtime_v3.test_all',
        resource_caps={k:v for k,v in caps.items() if k != 'gpu_lease_seconds'})
    for p in [Path(__file__), *folder.glob('*.py')]:
        m['source_files'][str(p.resolve())] = sha(p)
    for p in folder.glob('*.json'):
        m['input_files'][str(p)] = sha(p)
    for field in ('source_files','input_files'):
        for p,h in m[field].items():
            if sha(p) != h:
                raise ValueError('bound dependency changed: ' + p)
    e = reserve(job_id, caps, 'F3 fixed-height recipe revision2, single segmented pregrasp route revision1')
    m['reservation_event_sha256'] = e['event_sha256']
    m['manifest_sha256'] = digest(m)
    atomic(out,m)
    print(out)

if __name__ == '__main__':
    main(sys.argv[1])
