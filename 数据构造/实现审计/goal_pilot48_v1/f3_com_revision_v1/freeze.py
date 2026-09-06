import copy,json,sys,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计')
O=Path(__file__).parent
sys.path[:0]=[str(A/'new_recipe_prereqs_v1'),str(A),str(A/'代码审阅快照')]
from realization_utf8_io_v1 import write_new
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def seal(v):return {**v,'receipt_sha256':hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()}
def main():
    p=A/'F3_GEOMETRY_TOPDOWN_PROPOSAL_V1_20260906.json'
    old=next(x for x in json.loads(p.read_text())['proposals'] if x['parent_recipe_id']=='f3-final-pose-v3-r3063')
    source=Path('/nfs_share/lijunhui/Robotwin2/datasets/p48_f3_micro_001/scene_binding.json')
    initial=json.loads(source.read_text())['actual_bottle_pose']
    full=Rotation.from_quat(np.array(initial)[[4,5,6,3]]).apply([0,.0131,0])
    shift=full.copy();shift[2]=0
    shift*=.0131/np.linalg.norm(shift)
    pose=np.array(old['desired_actual_flange_world_pose']);pose[:3]+=shift
    pre=pose.copy();pre[2]+=.12
    # Do not copy old successful geometry fields onto a moved recipe.
    proposal={k:copy.deepcopy(old[k]) for k in ('parent_recipe_id','approach_direction_table','bottle_dominant_axis_table','jaw_direction_table')}
    proposal.update({'proposal_id':'f3-r3063-com-station-plus13p1mm-v1',
        'parent_topdown_proposal_id':old['proposal_id'],'parent_file_sha256':sha(p),
        'parent_proposal_sha256':seal(old)['receipt_sha256'],
        'desired_actual_flange_world_pose':pose.tolist(),'desired_pregrasp_world_pose':pre.tolist(),
        'initial_bottle_pose':initial,'initial_bottle_pose_source_sha256':sha(source),
        'raw_local_y_shift_world_m':full.tolist(),'height_preserving_world_shift_m':shift.tolist(),
        'shift_rule':'normalize XY projection of initial measured bottle local+y; length13.1mm, deltaZ0',
        'pregrasp_distance_m':.12,'close_normalized':.5,'hold_frames':250,'lift_m':.025,
        'mass_friction_velocity_thresholds_unchanged':True,'gpu_execution_performed':False,
        'new_scenes':0,'IK_queries':0,'physical_attempts':0})
    recipe=seal(proposal);write_new(O/'recipe.json',recipe)
    import closure,inner
    closure.run([proposal],O/'closure.json')
    inner.run([proposal],O/'inner.json')
    finalize()
def finalize():
    p=A/'F3_GEOMETRY_TOPDOWN_PROPOSAL_V1_20260906.json'
    old=next(x for x in json.loads(p.read_text())['proposals'] if x['parent_recipe_id']=='f3-final-pose-v3-r3063')
    pose=np.array(json.loads((O/'recipe.json').read_text())['desired_actual_flange_world_pose'])
    a=json.loads((O/'closure.json').read_text());b=json.loads((O/'inner.json').read_text())
    passed=a['results'][0]['CPU_necessary_gate_pass'] and b['results'][0]['necessary_inner_surface_gate_pass']
    write_new(O/'cpu_audit.json',seal({'pass':bool(passed),'recipe_sha256':sha(O/'recipe.json'),
        'closure_sha256':sha(O/'closure.json'),'inner_sha256':sha(O/'inner.json'),
        'source_bindings':{str(p):sha(p) for p in [A/'new_recipe_prereqs_v1/f3_closure.py',A/'new_recipe_prereqs_v1/goal_mapping.py',A/'f3_inner_surface_cross_section_v1.py']},
        'same_height':bool(pose[2]==old['desired_actual_flange_world_pose'][2]),
        'same_orientation':np.array_equal(pose[3:],old['desired_actual_flange_world_pose'][3:]),
        'new_scenes':0,'IK_queries':0,'physical_attempts':0,'physical_grasp_verified':False,
        'scope':'sampled necessary geometric closure and original Robot goal roundtrip only'}))
    print('CPU_PASS',passed)
if __name__=='__main__':main()
