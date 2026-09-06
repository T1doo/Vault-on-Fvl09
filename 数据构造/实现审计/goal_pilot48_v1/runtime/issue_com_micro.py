"""Finite Goal subjob for one pre-frozen evidence-driven COM station revision."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from budget import ROOT,read,digest,atomic,reserve
from issue import sha
def main(job_id):
    caps={'solver_problems':3,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0,'gpu_lease_seconds':1080};e=reserve(job_id,caps,'F3 postlift-roll revision1: one COM-aligned station, no threshold/physics/speed changes')
    m=read(ROOT/'jobs/p48_f3_micro_001.json');m.pop('manifest_sha256');m.update(run_id=job_id,reservation_event_sha256=e['event_sha256'],reserved=caps,guard_directory='/nfs_share/lijunhui/Robotwin2/datasets/'+job_id+'_guard',recipe_spec_path=str(ROOT/'f3_com_revision_v1/recipe.json'),failure_class='postlift_roll',evidence_based_revision=1)
    job=m['jobs'][0];job.update(job_id=job_id,runtime_module='goal_pilot48_v1.f3_runtime_v2.micro',runtime_file=str(ROOT/'f3_runtime_v2/micro.py'),test_module='goal_pilot48_v1.f3_runtime_v2.test_lifecycle',output_namespace='/nfs_share/lijunhui/Robotwin2/datasets/'+job_id)
    m['source_files']={p:h for p,h in m['source_files'].items() if '/f3_runtime_v1/' not in p}
    for folder in (ROOT/'runtime',ROOT/'f3_runtime_v2',ROOT/'f3_com_revision_v1'):
        for p in folder.glob('*.py'):m['source_files'][str(p)]=sha(p)
    for p in [ROOT/'f3_com_revision_v1/recipe.json',ROOT/'f3_com_revision_v1/cpu_audit.json',ROOT/'f3_slip_audit_v1/analysis.json']:m['input_files'][str(p)]=sha(p)
    for role,name in [('guard','guarded_launcher.py'),('runner','job_runner.py')]:m[role+'_script_sha256']=sha(ROOT/'runtime'/name)
    m['manifest_sha256']=digest(m);out=ROOT/'jobs'/(job_id+'.json')
    if out.exists():raise FileExistsError('job manifest already issued')
    atomic(out,m);print(out)
if __name__=='__main__':main(sys.argv[1])
