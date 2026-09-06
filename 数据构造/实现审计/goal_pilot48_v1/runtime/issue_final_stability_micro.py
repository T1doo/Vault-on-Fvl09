"""Last frozen stability recipe; successful fresh confirmation is not revision4."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from budget import ROOT,read,digest,reserve,atomic
from issue import sha

def checked(path):
    value=read(path);body=dict(value);h=body.pop('receipt_sha256')
    if digest(body)!=h:raise ValueError('bad prerequisite receipt '+str(path))
    return value

def main(job_id):
    folder=ROOT/'f3_contact_height_revision_v2'
    recipe=checked(folder/'recipe.json');audit=checked(folder/'cpu_audit.json')
    route=checked(folder/'route_spec.json')
    if not audit['pass'] or audit['recipe_file_sha256']!=sha(folder/'recipe.json'):
        raise ValueError('recipe prerequisite mismatch')
    if recipe['lift_m']!=.025 or route['height_recipe_id']!=recipe['proposal_id']:
        raise ValueError('fixed 25mm lift / recipe binding changed')
    m=read(ROOT/'jobs/p48_f3_micro_004.json');m.pop('manifest_sha256')
    out=ROOT/'jobs'/(job_id+'.json');dest=Path('/nfs_share/lijunhui/Robotwin2/datasets')/job_id
    guard=dest.with_name(job_id+'_guard')
    if any(p.exists() for p in (out,dest,guard,dest.with_name(job_id+'_meter'))):
        raise FileExistsError('job namespace consumed')
    m.update(run_id=job_id,guard_directory=str(guard),recipe_spec_path=str(folder/'recipe.json'),
             route_spec_path=str(folder/'route_spec.json'),evidence_based_revision=3)
    m['jobs'][0].update(job_id=job_id,output_namespace=str(dest),
                       test_module='goal_pilot48_v1.f3_contact_height_revision_v2.test_runtime_binding')
    for p in [Path(__file__),*folder.glob('*.py')]:m['source_files'][str(p.resolve())]=sha(p)
    for p in [*folder.glob('*.json'),* (ROOT/'f3_lift_margin_audit_v1').glob('*.json'),
              dest.with_name('p48_f3_micro_004')/'goal_terminal.json']:
        m['input_files'][str(p)]=sha(p)
    for field in ('source_files','input_files'):
        for p,h in m[field].items():
            if sha(p)!=h:raise ValueError('changed bound file '+p)
    e=reserve(job_id,m['reserved'],'F3 last stability revision3: total grasp height+12mm, fixed25mm lift, no physics/Gate change')
    m['reservation_event_sha256']=e['event_sha256'];m['manifest_sha256']=digest(m)
    atomic(out,m);print(out)

if __name__=='__main__':main(sys.argv[1])
