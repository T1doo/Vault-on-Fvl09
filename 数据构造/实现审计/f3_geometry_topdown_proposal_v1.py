"""One analytical top-down grasp per failed parent; CPU geometry only, not IK."""
import copy,json,sys,hashlib
from pathlib import Path
import numpy as np
import transforms3d as t3d
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';D=W/'Robotwin2/datasets'
sys.path.insert(0,str(A/'f3_model_replay_v1'))
from replay import hand_shapes,matrix,link_world,exact_shape_pairs
from realization_utf8_io_v1 import write_new

def vertices(s):
    T=matrix(s['solver_pose']);return np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3]

def run():
    saved=json.loads((D/'f3_model_conformance_v1/f3-final-pose-v3-r3063/initial_geometry.json').read_text(encoding='utf-8'))
    base=json.loads((D/'f3_remaining_model_scene_v1_1/remaining_scene/f3-final-pose-v3-r3063/initial_geometry.json').read_text(encoding='utf-8'))['solver_base_binding']['base_link_world_pose'];B=matrix(base);rows=[]
    for recipe in ('f3-final-pose-v3-r3063','f3-final-pose-v3-r1401'):
        parent=D/'f3_zero_scene_solver_replay_v1'/recipe/'planned_grasp_endpoint.json';row=json.loads(parent.read_text(encoding='utf-8'));state=row['state'];old=link_world('fl_link6',state['named_qpos'],base)
        world=json.loads(parent.with_name('planned_grasp_endpoint.geometry.json').read_text(encoding='utf-8'))['shapes'];bottle=[s for s in world if s['role']=='bottle']
        hand=hand_shapes(saved,state,base)
        # The two native jaw shapes, transformed to the actual flange frame.
        local=[]
        for s in hand:
            T=np.linalg.inv(old)@B@matrix(s['solver_pose']);v=np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3]
            if s['role'] in ('fl_link7','fl_link8'):local.append((v.min(0)+v.max(0))/2)
        pinch=np.mean(local,axis=0)
        bv=np.concatenate([vertices(s)@B[:3,:3].T+B[:3,3] for s in bottle]);low=bv.min(0);high=bv.max(0)
        # Both parents have a lying bottle, its dominant length axis is table Y.
        if int(np.argmax(high-low))!=1:raise ValueError('proposal requires audited Y-long bottle')
        R=np.column_stack(([0,0,-1],[1,0,0],[0,-1,0]));target=(low+high)/2
        old_pinch=old[:3,:3]@pinch+old[:3,3];target[1]=old_pinch[1]
        if not low[1]+.02<target[1]<high[1]-.02:raise ValueError('old grasp station outside bottle body')
        desired=np.eye(4);desired[:3,:3]=R;desired[:3,3]=target-R@pinch
        transformed=[]
        for s in hand:
            n=copy.deepcopy(s);T=np.linalg.inv(B)@desired@np.linalg.inv(old)@B@matrix(s['solver_pose']);n['solver_pose']=np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist();transformed.append(n)
        supports=[s for s in world if s['role'] in ('table','pad')]
        # One analytic lift clears actual support top, no pose/yaw grid search.
        minimum=min((vertices(s)@B[:3,:3].T+B[:3,3])[:,2].min() for s in transformed)
        padtop=max((vertices(s)@B[:3,:3].T+B[:3,3])[:,2].max() for s in supports if s['role']=='pad')
        dz=max(0.,padtop+.008-minimum);desired[2,3]+=dz
        for s in transformed:
            T=B@matrix(s['solver_pose']);T[2,3]+=dz;T=np.linalg.inv(B)@T;s['solver_pose']=np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist()
        pairs=exact_shape_pairs(transformed,supports+bottle);invalid=[p for p in pairs if p['definite_open_grasp_geometry_violation'] and p['physical_collision_filter_enabled']]
        rows.append({'parent_recipe_id':recipe,'parent_endpoint_file':str(parent),'parent_endpoint_sha256':hashlib.sha256(parent.read_bytes()).hexdigest(),
            'proposal_id':recipe+'-topdown-geometry-v1','desired_actual_flange_world_pose':np.r_[desired[:3,3],t3d.quaternions.mat2quat(desired[:3,:3])].tolist(),
            'pose_is_NOT_legacy_reported_goal':True,'jaw_direction_table':'X','approach_direction_table':'-Z','bottle_dominant_axis_table':'Y',
            'proposed_geometric_support_margin_m':.008,'analytic_support_lift_m':dz,'open_hand_exact_pairs':pairs,'open_hand_no_definite_overlap':not invalid,
            'closed_grasp_retention_not_verified':True,'IK_reachability_not_tested':True,'full_arm_path_not_tested':True,
            'next_gate':'invert/validate legacy goal mapping; actual open-state model IK/endpoint, full-window preclose and original postlift micro; requires new recipe approval',
            'gpu_execution_authorized':False,'physical_execution_authorized':False})
    out={'schema_version':'cmf_f3_geometry_topdown_proposal_v1','status':'CPU_GEOMETRY_PROPOSAL_NOT_QUALIFIED','proposals':rows,'new_scenes':0,'new_queries':0,'physical_attempts':0,'new_raw':0}
    write_new(A/'F3_GEOMETRY_TOPDOWN_PROPOSAL_V1_20260906.json',out);print(json.dumps([{k:r[k] for k in ('proposal_id','analytic_support_lift_m','open_hand_no_definite_overlap')} for r in rows]))

if __name__=='__main__':run()
