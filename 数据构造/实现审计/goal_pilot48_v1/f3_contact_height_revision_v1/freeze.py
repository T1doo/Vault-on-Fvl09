"""Unique shallower-contact revision: exactly +10mm world Z, no sweep."""
import copy,json,sys,hashlib
from pathlib import Path
import numpy as np
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');O=Path(__file__).parent
C=O.parent/'f3_com_revision_v1'
sys.path[:0]=[str(C),str(A/'new_recipe_prereqs_v1'),str(A),str(A/'代码审阅快照')]
from realization_utf8_io_v1 import write_new
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def seal(v):return {**v,'receipt_sha256':hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()}
def main():
    parent=json.loads((C/'recipe.json').read_text());proposal=copy.deepcopy(parent)
    proposal.pop('receipt_sha256');proposal.update({'proposal_id':'f3-r3063-com-contact-height-plus10mm-v2',
        'parent_revision_id':parent['proposal_id'],'parent_revision_file_sha256':sha(C/'recipe.json'),
        'parent_revision_receipt_sha256':parent['receipt_sha256'],'unique_revision_delta_world_m':[0,0,.010],
        'no_height_sweep':True,'actual_contact_height_change_unverified':True,
        'next_trace_required':'measure both actual contact positions relative to actual COM, then unchanged postlift Gate'})
    for key in ('desired_actual_flange_world_pose','desired_pregrasp_world_pose'):proposal[key][2]+=.010
    assert np.array_equal(np.asarray(proposal['desired_actual_flange_world_pose'])[[0,1,3,4,5,6]],np.asarray(parent['desired_actual_flange_world_pose'])[[0,1,3,4,5,6]])
    write_new(O/'recipe.json',seal(proposal))
    import closure,inner
    closure.run([proposal],O/'closure.json');inner.run([proposal],O/'inner.json')
    cl=json.loads((O/'closure.json').read_text());inn=json.loads((O/'inner.json').read_text())
    passed=cl['results'][0]['CPU_necessary_gate_pass'] and inn['results'][0]['necessary_inner_surface_gate_pass']
    write_new(O/'cpu_audit.json',seal({'pass':bool(passed),'recipe_file_sha256':sha(O/'recipe.json'),
        'closure_sha256':sha(O/'closure.json'),'inner_sha256':sha(O/'inner.json'),
        'checker_bindings':{str(p):sha(p) for p in (C/'closure.py',C/'inner.py',A/'new_recipe_prereqs_v1/goal_mapping.py')},
        'new_scenes':0,'IK_queries':0,'physical_attempts':0,'actual_contact_height_verified':False,
        'claim':'five closure samples and original goal roundtrip necessary geometry only',
        'on_failure':'stop unique proposal; no automatic height/close/velocity sweep'}))
    print('CPU_PASS',passed)
if __name__=='__main__':main()
