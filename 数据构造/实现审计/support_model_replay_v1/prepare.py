"""Reconstruct fixed world and held-object transform from actual saved state."""
import copy,json,sys,hashlib
from pathlib import Path
import numpy as np
import transforms3d as t3d
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';D=W/'Robotwin2/datasets/f3_r3063_bootstrap_replacement_v1'
sys.path.insert(1,str(A/'f3_model_replay_v1'));sys.path.insert(2,str(A/'f2_f3_model_bridge_v1_1'));sys.path.insert(3,str(A))
from kinematics_cpu import link_world
from geometry import matrix,digest
from realization_utf8_io_v1 import write_new
def prepare():
    model=json.loads((D/'postclose_attached_model.json').read_text(encoding='utf-8'));plan=json.loads((D/'lift25.plan.json').read_text(encoding='utf-8'));witness=json.loads((A/'F3_POSTCLOSE_SUPPORT_MODEL_CPU_AUDIT_V1_20260906.json').read_text(encoding='utf-8'))
    base=json.loads((W/'Robotwin2/datasets/f3_remaining_model_scene_v1_1/remaining_scene/f3-final-pose-v3-r3063/initial_geometry.json').read_text())['solver_base_binding']['base_link_world_pose'];B=matrix(base);named=dict(zip(model['actual_joint_names'],model['actual_qpos']));eef=link_world('fl_link6',named,base)
    with np.load(D/'physical_trace.npz',allow_pickle=False) as z:
        assert np.array_equal(z['joint_qpos'][-1],model['actual_qpos'])
        assert np.linalg.norm(eef[:3,3]-z['eef_pose'][-1,:3])<1e-5
        assert np.max(np.abs(eef[:3,:3]-t3d.quaternions.quat2mat(z['eef_pose'][-1,3:])))<1e-5
        actual_actor=z['object_pose'][-1];actual_eef=z['eef_pose'][-1]
    assert np.array_equal(actual_actor,model['native_bottle_shapes'][0]['actor_world_pose'])
    expect=np.asarray(actual_eef).copy();expect[2]+=.025;assert np.array_equal(expect,plan['actual_goal'])
    original=json.loads((W/'Robotwin2/datasets/f3_new_topdown_qualification_v1/f3-final-pose-v3-r3063-topdown-geometry-v1/geometry.json').read_text())['shapes'];shapes=[]
    for s in original:
        if s['role']=='bottle':continue
        n=copy.deepcopy(s)
        actor=link_world(s['role'],named,base) if s['role'].startswith('fr_link') else matrix(s['actor_world_pose'])
        T=np.linalg.inv(B)@actor@matrix(s['shape_local_pose']);n['solver_pose']=np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist();shapes.append(n)
    vertices=[]
    for s in model['native_bottle_shapes']:
        L=matrix(s['shape_local_pose']);vertices.append(np.asarray(s['vertices'])@L[:3,:3].T+L[:3,3])
    value={'schema_version':'cmf_fixed_actual_postclose_model_replay_input_v1','robot_config':model['robot_config'],'world_export':{'shapes':shapes,'geometry_sha256':digest(shapes)},'world_base_pose':base,
        'named_qpos':named,'actual_joint_names':model['actual_joint_names'],'actual_qpos':model['actual_qpos'],'desired_actual_goal':plan['actual_goal'],'reported_command':plan['reported_command'],
        'actual_postclose_actor_pose':actual_actor.tolist(),'actual_postclose_eef_pose':actual_eef.tolist(),'eef_to_actor_matrix':(np.linalg.inv(eef)@matrix(actual_actor)).tolist(),'native_actor_vertices':np.concatenate(vertices).tolist(),
        'support_witness':witness,'pad_top_world_z_m':witness['pad_top_world_z_m'],'FK_trace_validation_pass':True,'new_scenes':0}
    return value
if __name__=='__main__':
    value=prepare();write_new(A/'F3_POSTCLOSE_REPLAY_INPUT_V1_20260906.json',value);print('fixed actual state/world/target prepared; no Scene/GPU')
