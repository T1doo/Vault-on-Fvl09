"""Five fixed joint-geometry samples, no Scene/IK/physical action."""
import copy,json,sys
from pathlib import Path
import numpy as np
import transforms3d as t3d
import yaml
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');W=A.parents[2];D=W/'Robotwin2/datasets'
sys.path.insert(1,str(A/'f3_model_replay_v1'));sys.path.insert(2,str(A))
from replay import hand_shapes,link_world,matrix,exact_shape_pairs
from goal_mapping import cpu_views,roundtrip,P
from realization_utf8_io_v1 import write_new
def run():
    proposals=json.loads((A/'F3_GEOMETRY_TOPDOWN_PROPOSAL_V1_20260906.json').read_text(encoding='utf-8'))['proposals']
    saved=json.loads((D/'f3_model_conformance_v1/f3-final-pose-v3-r3063/initial_geometry.json').read_text(encoding='utf-8'));base=json.loads((D/'f3_remaining_model_scene_v1_1/remaining_scene/f3-final-pose-v3-r3063/initial_geometry.json').read_text(encoding='utf-8'))['solver_base_binding']['base_link_world_pose'];B=matrix(base)
    cfg=yaml.safe_load((P/'assets/embodiments/aloha-agilex/config.yml').read_text(encoding='utf-8'));lo,hi=cfg['gripper_scale'];closed=lo+.5*(hi-lo)
    assert cfg['gripper_name'][0]=={'base':'fl_joint7','mimic':[['fl_joint8',1.,0.]]}
    robot,planner=cpu_views(base);results=[]
    for proposal in proposals:
        parent=D/'f3_zero_scene_solver_replay_v1'/proposal['parent_recipe_id'];state=json.loads((parent/'planned_grasp_endpoint.json').read_text(encoding='utf-8'))['state'];world=json.loads((parent/'planned_grasp_endpoint.geometry.json').read_text(encoding='utf-8'))['shapes']
        desired=matrix(proposal['desired_actual_flange_world_pose']);old=link_world('fl_link6',state['named_qpos'],base);samples=[]
        for fraction in (0.,.25,.5,.75,1.):
            q=copy.deepcopy(state)
            for name in ('fl_joint7','fl_joint8'):q['named_qpos'][name]=(1-fraction)*state['named_qpos'][name]+fraction*closed
            shapes=hand_shapes(saved,q,base);transformed=[]
            for s in shapes:
                n=copy.deepcopy(s);T=np.linalg.inv(B)@desired@np.linalg.inv(old)@B@matrix(s['solver_pose']);n['solver_pose']=np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist();transformed.append(n)
            pairs=exact_shape_pairs(transformed,[s for s in world if s['role'] in ('table','pad','bottle')])
            fingers={name:[p for p in pairs if p['robot_shape'].startswith(name) and p['role']=='bottle'] for name in ('fl_link7','fl_link8')}
            contacts={name:sorted({p['obstacle_shape'] for p in ps if p['mesh_intersection']}) for name,ps in fingers.items()}
            support_bad=[p for p in pairs if p['role'] in ('table','pad') and p['mesh_intersection'] and p['physical_collision_filter_enabled']]
            palm_bad=[p for p in pairs if p['role']=='bottle' and p['robot_shape'].startswith('fl_link6') and p['vertex_penetration_witness_m']>1e-5]
            rest={s['name']:float(s['rest_offset']) for s in transformed+world}
            for p in pairs:p['combined_rest_offset_m']=rest[p['robot_shape']]+rest[p['obstacle_shape']]
            samples.append({'closure_fraction':fraction,'named_finger_qpos':{k:q['named_qpos'][k] for k in ('fl_joint7','fl_joint8')},'pairs':pairs,'finger_bottle_contact_shapes':contacts,
                'finger_min_bottle_gap_m':{n:min(p['surface_distance_m'] for p in ps) for n,ps in fingers.items()},'both_fingers_intersect_same_native_bottle_piece':bool(set(contacts['fl_link7'])&set(contacts['fl_link8'])),
                'forbidden_support_intersections':support_bad,'forbidden_palm_bottle_intersections':palm_bad})
        both=any(s['both_fingers_intersect_same_native_bottle_piece'] for s in samples);safe=all(not s['forbidden_support_intersections'] and not s['forbidden_palm_bottle_intersections'] for s in samples)
        grasp=np.array(proposal['desired_actual_flange_world_pose']);pre=grasp.copy();pre[2]+=.12
        mappings={'grasp':roundtrip(robot,planner,grasp),'pregrasp':roundtrip(robot,planner,pre)}
        negative=grasp.copy();negative[3:]*=-1;roundtrip(robot,planner,negative)
        results.append({'proposal_id':proposal['proposal_id'],'samples':samples,'discrete_samples_not_continuous_proof':True,'stable_grasp_not_proven':True,'mapping_against_original_entry':mappings,
            'close_normalized_command':.5,'close_drive_target_each_joint_m':closed,'joint_mapping_source':'actual Robot.set_gripper gripper_scale + mimic mapping; realized motion still requires physics',
            'both_sides_same_bottle_piece_contact_reachable':both,'sampled_forbidden_geometry_clear':safe,'CPU_necessary_gate_pass':both and safe,
            'on_failure':'stop exact proposal, no height/close changes or GPU','contact_offsets_unchanged':True})
    out={'schema_version':'cmf_f3_new_topdown_closure_prerequisites_v1','results':results,'new_scenes':0,'IK_problems':0,'physical_attempts':0}
    write_new(A/'F3_TOPDOWN_CLOSURE_AND_GOAL_MAPPING_V1_20260906.json',out);print(json.dumps([{k:r[k] for k in ('proposal_id','both_sides_same_bottle_piece_contact_reachable','sampled_forbidden_geometry_clear','CPU_necessary_gate_pass')} for r in results]))
if __name__=='__main__':run()
