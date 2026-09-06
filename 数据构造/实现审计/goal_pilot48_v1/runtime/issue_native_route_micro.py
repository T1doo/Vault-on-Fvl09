"""One route2 micro using the unchanged final stability recipe and native gate."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from budget import ROOT,read,digest,reserve,atomic
from issue import sha

def main(job_id):
    m=read(ROOT/'jobs/p48_f3_micro_005.json');m.pop('manifest_sha256')
    folder=ROOT/'f3_runtime_v4';native=ROOT/'f3_native_self_pair_v1'
    route=read(folder/'route_spec.json');body=dict(route);h=body.pop('receipt_sha256')
    if digest(body)!=h or route['max_single_queries']!=3 or route['postlift_roll_recipe_revision']!=3:
        raise ValueError('frozen route2 binding')
    out=ROOT/'jobs'/(job_id+'.json');dest=Path('/nfs_share/lijunhui/Robotwin2/datasets')/job_id
    guard=dest.with_name(job_id+'_guard')
    if any(p.exists() for p in (out,dest,guard,dest.with_name(job_id+'_meter'))):
        raise FileExistsError('used job namespace')
    caps=dict(m['reserved'],solver_problems=3)
    m.update(run_id=job_id,reserved=caps,guard_directory=str(guard),
             route_spec_path=str(folder/'route_spec.json'),pregrasp_route_revision=2)
    m['jobs'][0].update(job_id=job_id,output_namespace=str(dest),
        runtime_module='goal_pilot48_v1.f3_runtime_v4.micro',runtime_file=str(folder/'micro.py'),
        test_module='goal_pilot48_v1.f3_runtime_v4.test_all',
        resource_caps={k:v for k,v in caps.items() if k!='gpu_lease_seconds'})
    for p in [Path(__file__),*(folder.glob('*.py')),*(native.glob('*.py')),
              ROOT.parent/'f3_model_replay_v1/kinematics_cpu.py']:
        m['source_files'][str(p.resolve())]=sha(p)
    for p in [*folder.glob('*.json'),*native.glob('*.json')]:m['input_files'][str(p)]=sha(p)
    m['input_files'].update(route['sources'])
    for field in ('source_files','input_files'):
        for p,expected in m[field].items():
            if sha(p)!=expected:raise ValueError('changed bound file '+p)
    e=reserve(job_id,caps,'F3 final stability recipe3 unchanged; route2 low pregrasp and actual native self-pair pre-execution screen')
    m['reservation_event_sha256']=e['event_sha256'];m['manifest_sha256']=digest(m)
    atomic(out,m);print(out)

if __name__=='__main__':main(sys.argv[1])
