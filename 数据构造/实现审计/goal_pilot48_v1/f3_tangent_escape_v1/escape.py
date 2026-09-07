"""Native geometry of a planned lift, using the fresh actual grasp transform."""
import sys
from pathlib import Path
import numpy as np
import transforms3d as t3d
from .policy import audit_lift_escape
def evaluate_controls(position,*,solver_joint_names,actual_joint_names,actual_qpos,base_pose,actor_pose,bottle_shapes,pad_top,witness):
    A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');sys.path.insert(0,str(A/'f3_model_replay_v1'));sys.path.insert(1,str(A/'f2_f3_model_bridge_v1_1'))
    from kinematics_cpu import link_world
    from geometry import matrix
    named=dict(zip(actual_joint_names,actual_qpos));relative=np.linalg.inv(link_world('fl_link6',named,base_pose))@matrix(actor_pose);local=[]
    for s in bottle_shapes:
        T=matrix(s['shape_local_pose']);local.append(np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3])
    local=np.concatenate(local);poses=[];vertices=[]
    for q in np.asarray(position):
        state=dict(named);state.update(dict(zip(solver_joint_names,q)));actor=link_world('fl_link6',state,base_pose)@relative
        poses.append(np.r_[actor[:3,3],t3d.quaternions.mat2quat(actor[:3,:3])]);vertices.append(local@actor[:3,:3].T+actor[:3,3])
    result=audit_lift_escape(vertices,poses,support_plane_z=pad_top,witness=witness)
    result['grasp_transform_source']='fresh actual qpos/FK and actual bottle pose, not previous run target';return result
