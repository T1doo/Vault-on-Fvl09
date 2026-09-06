"""One fixed pregrasp route and 13 native open-hand geometry samples."""
import copy,json,sys,hashlib
from pathlib import Path
import numpy as np
import transforms3d as t3d
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');O=Path(__file__).parent;D=Path('/nfs_share/lijunhui/Robotwin2/datasets')
sys.path[:0]=[str(A/'new_recipe_prereqs_v1'),str(A/'f3_model_replay_v1'),str(A),str(A/'代码审阅快照')]
from replay import hand_shapes,link_world,matrix,exact_shape_pairs
from goal_mapping import cpu_views,roundtrip
from realization_utf8_io_v1 import write_new
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def seal(v):return {**v,'receipt_sha256':hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()}
def main():
    height=json.loads((O/'recipe.json').read_text())
    oldpath=D/'p48_f3_micro_004/route_pregrasp.plan.json';old=json.loads(oldpath.read_text())
    target=np.array(height['desired_pregrasp_world_pose']);start=np.array(old['actual_goal'])
    assert np.allclose(target[[0,1,3,4,5,6]],start[[0,1,3,4,5,6]],atol=1e-12)
    assert abs(target[2]-start[2]-.012)<1e-12
    route=seal({'schema_version':'p48_f3_pregrasp_via_successful_lower_pose_v1','height_recipe_id':height['proposal_id'],
        'intermediate_actual_pregrasp_pose':start.tolist(),'height_pregrasp_pose':target.tolist(),
        'source_successful_plan':str(oldpath),'source_plan_sha256':sha(oldpath),
        'source_successful_window_sha256':sha(D/'p48_f3_micro_004/route_pregrasp.full_window.json'),
        'max_single_queries':4,'new_scene_budget':1,'pregrasp_route_revision':1,'postlift_roll_recipe_revision':3,
        'fixed_stages':['route_pregrasp','pregrasp','grasp','lift25'],'no_retry_or_target_sweep':True})
    assert json.loads((D/'p48_f3_micro_004/route_pregrasp.full_window.json').read_text())['pass']
    write_new(O/'route_spec.json',route)
    saved=json.loads((D/'f3_model_conformance_v1/f3-final-pose-v3-r3063/initial_geometry.json').read_text())
    base=json.loads((D/'f3_remaining_model_scene_v1_1/remaining_scene/f3-final-pose-v3-r3063/initial_geometry.json').read_text())['solver_base_binding']['base_link_world_pose'];B=matrix(base)
    parent=D/'f3_zero_scene_solver_replay_v1/f3-final-pose-v3-r3063'
    state=json.loads((parent/'planned_grasp_endpoint.json').read_text())['state'];world=json.loads((parent/'planned_grasp_endpoint.geometry.json').read_text())['shapes']
    original=link_world('fl_link6',state['named_qpos'],base);hand=hand_shapes(saved,state,base);robot,planner=cpu_views(base);rows=[]
    for f in np.linspace(0,1,13):
        pose=start.copy();pose[:3]=(1-f)*start[:3]+f*target[:3];desired=matrix(pose);transformed=[]
        for s in hand:
            n=copy.deepcopy(s);T=np.linalg.inv(B)@desired@np.linalg.inv(original)@B@matrix(s['solver_pose']);n['solver_pose']=np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist();transformed.append(n)
        pairs=exact_shape_pairs(transformed,[s for s in world if s['role'] in ('table','pad','bottle')])
        bad=[p for p in pairs if p['mesh_intersection'] and p['physical_collision_filter_enabled']]
        rows.append({'fraction':float(f),'actual_pose':pose.tolist(),'pairs':pairs,'pass':not bad,'roundtrip':roundtrip(robot,planner,pose)})
    write_new(O/'route_geometry_audit.json',seal({'pass':all(r['pass'] for r in rows),'rows':rows,'route_spec_sha256':sha(O/'route_spec.json'),
        'sampled_hand_only_not_full_arm_or_actual_plan':True,'new_scenes':0,'IK_queries':0,'physical_attempts':0}))
    print('geometry pass',all(r['pass'] for r in rows))
if __name__=='__main__':main()
