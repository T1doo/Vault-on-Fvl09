"""Last stability revision: one fixed +12mm total height, no sweep."""
import copy,json,sys,hashlib,importlib.util
from pathlib import Path
import numpy as np
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');O=Path(__file__).parent;G=O.parent
sys.path[:0]=[str(G/'f3_com_revision_v1'),str(A/'new_recipe_prereqs_v1'),str(A),str(A/'代码审阅快照')]
from realization_utf8_io_v1 import write_new
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def seal(v):return {**v,'receipt_sha256':hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()}
def main():
    pp=G/'f3_contact_height_revision_v1/recipe.json';parent=json.loads(pp.read_text());p=copy.deepcopy(parent);p.pop('receipt_sha256')
    p.update({'proposal_id':'f3-r3063-com-contact-height-plus12mm-v3','parent_revision_id':parent['proposal_id'],
        'parent_revision_file_sha256':sha(pp),'parent_revision_receipt_sha256':parent['receipt_sha256'],
        'unique_revision_delta_world_m':[0,0,.002],'total_height_delta_from_original_topdown_m':.012,
        'stability_recipe_revision':3,'last_stability_revision':True,'fourth_stability_revision_allowed':False,
        'inherited_station_fields_are_parent_XY_only':True,'lift_m':.025})
    for k in ('desired_actual_flange_world_pose','desired_pregrasp_world_pose'):p[k][2]+=.002
    write_new(O/'recipe.json',seal(p))
    import closure,inner
    closure.run([p],O/'closure.json');inner.run([p],O/'inner.json')
    cl=json.loads((O/'closure.json').read_text());inn=json.loads((O/'inner.json').read_text())
    passed=cl['results'][0]['CPU_necessary_gate_pass'] and inn['results'][0]['necessary_inner_surface_gate_pass']
    write_new(O/'cpu_audit.json',seal({'pass':bool(passed),'recipe_file_sha256':sha(O/'recipe.json'),
        'closure_sha256':sha(O/'closure.json'),'inner_sha256':sha(O/'inner.json'),'new_scenes':0,'IK_queries':0,'physical_attempts':0,
        'actual_above_COM_grasp_proven':False,'one_fixed_height_only':True,'same_gate_physics_lift25':True}))
    print('fixed12mm CPU necessary gate',passed)
if __name__=='__main__':main()
