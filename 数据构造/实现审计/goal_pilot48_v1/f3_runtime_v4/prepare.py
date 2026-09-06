import json,hashlib,sys
from pathlib import Path
import numpy as np
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');O=Path(__file__).parent;D=Path('/nfs_share/lijunhui/Robotwin2/datasets')
sys.path[:0]=[str(A),str(A/'代码审阅快照')]
from realization_utf8_io_v1 import write_new
from goal_pilot48_v1.f3_native_self_pair_v1.checker import SOURCE,URDF
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    recipe_path=O.parent/'f3_contact_height_revision_v2/recipe.json';recipe=json.loads(recipe_path.read_text())
    plan_path=D/'p48_f3_micro_005/route_pregrasp.plan.json';window_path=D/'p48_f3_micro_005/route_pregrasp.full_window.json'
    plan=json.loads(plan_path.read_text());assert plan['pass'] and json.loads(window_path.read_text())['pass']
    pre=np.array(plan['actual_goal']);grasp=np.array(recipe['desired_actual_flange_world_pose']);assert abs(pre[2]-grasp[2]-.108)<1e-12
    value={'schema_version':'p48_f3_direct_low_pregrasp_route_revision2','height_recipe_id':recipe['proposal_id'],
        'intermediate_actual_pregrasp_pose':pre.tolist(),'this_pose_is_final_pregrasp_not_an_extra_waypoint':True,
        'grasp_actual_pose_unchanged':grasp.tolist(),'actual_approach_distance_m':.108,
        'recipe_original_pregrasp_pose_not_executed':recipe['desired_pregrasp_world_pose'],
        'pregrasp_route_revision':2,'postlift_roll_recipe_revision':3,'max_single_queries':3,
        'physical_parameters_Gates_and_grasp_unchanged':True,'no_fourth_stability_recipe':True,
        'native_controls_gate_pair':['fl_link3','fl_link5'],'sources':{str(p):sha(p) for p in [recipe_path,plan_path,window_path,SOURCE,URDF]},
        'new_grasp_path_native_verified':False,'verification_stage':'after actual GPU plan generation, before each _execute_planned_segment',
        'no_GPU_executed':True}
    value['receipt_sha256']=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    write_new(O/'route_spec.json',value);print(value['receipt_sha256'])
if __name__=='__main__':main()
