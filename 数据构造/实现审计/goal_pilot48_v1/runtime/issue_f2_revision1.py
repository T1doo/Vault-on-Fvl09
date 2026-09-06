"""Main-only new layout issuance; consumed parent job is never reissued."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from budget import ROOT,read,digest,reserve,atomic
from issue import sha

def main(job_id):
    from goal_pilot48_v1.f2_inward_runtime_v2.dependencies import additional_bindings
    additions=additional_bindings()
    m=read(ROOT/'jobs/p48_f2_inward_001.json');m.pop('manifest_sha256')
    for field in ('source_files','input_files'):
        for p,h in m[field].items():
            if sha(p)!=h:raise ValueError('parent dependency changed '+p)
        m[field].update(additions['additional_'+field])
    m['source_files'][str(Path(__file__).resolve())]=sha(__file__)
    parent_result=Path('/nfs_share/lijunhui/Robotwin2/datasets/p48_f2_inward_001/goal_terminal.json')
    m['input_files'][str(parent_result)]=sha(parent_result)
    out=ROOT/'jobs'/(job_id+'.json');dest=parent_result.parent.parent/job_id
    guard=dest.with_name(job_id+'_guard')
    if any(p.exists() for p in (out,dest,guard,dest.with_name(job_id+'_meter'))):
        raise FileExistsError('used job namespace')
    m.update(additions['manifest_fields'])
    m.update(run_id=job_id,guard_directory=str(guard),evidence_based_revision=1,
             failure_class='F2_constrained_endpoint_failure',parent_job_id='p48_f2_inward_001')
    m['new_layout_lineage']={**additions['manifest_fields'],
        'old_inside_success_not_adopted':True,'new_current_anchor_required_for_future_collection':True,
        'held_state_restoration_is_planner_only':True}
    m['jobs'][0].update(job_id=job_id,output_namespace=str(dest),
        **{k:additions[k] for k in ('runtime_module','runtime_file','test_module','resource_caps')})
    e=reserve(job_id,m['reserved'],'F2 one evidence-driven endpoint layout revision1, unchanged 3IK/4route/0physical')
    m['reservation_event_sha256']=e['event_sha256'];m['manifest_sha256']=digest(m)
    atomic(out,m);print(out)

if __name__=='__main__':main(sys.argv[1])
