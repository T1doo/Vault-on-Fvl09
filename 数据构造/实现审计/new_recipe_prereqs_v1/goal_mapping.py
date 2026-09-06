"""Inverse goal adapter verified against the locked original Robot entry."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import transforms3d as t3d
import yaml
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');sys.path.insert(1,str(A/'f2_f3_model_bridge_v1_1'))
from transforms import P,TOOL,GOAL,ORIGINAL_LEFT_CALL,planner_view,reported_eef_goal_to_solver_goal
from geometry import matrix
def cpu_views(base):
    cfg=yaml.safe_load((P/'assets/embodiments/aloha-agilex/config.yml').read_text(encoding='utf-8'));pcfg=yaml.safe_load((P/'assets/embodiments/aloha-agilex/curobo_left.yml').read_text(encoding='utf-8'))
    robot=SimpleNamespace(left_gripper_bias=cfg['gripper_bias'],left_inv_delta_matrix=np.linalg.inv(cfg['delta_matrix']),communication_flag=False)
    robot._trans_from_gripper_to_endlink=lambda target,arm_tag:TOOL(robot,target,arm_tag)
    planner=planner_view(cfg['robot_pose'][0],pcfg['planner']['frame_bias'],'aloha-agilex/curobo_left.yml');planner._cmf_solver_base_world_pose=base
    planner.plan_path=lambda q,pose,constraint_pose,arms_tag:GOAL(planner,q,pose,constraint_pose,arms_tag);robot.left_planner=planner
    return robot,planner
def reported_command_to_actual_solver_goal(robot,planner,command):
    return reported_eef_goal_to_solver_goal(robot,planner,command)
def actual_flange_goal_to_reported_command(robot,planner,actual_world_pose):
    desired=np.linalg.inv(matrix(planner._cmf_solver_base_world_pose))@matrix(actual_world_pose)
    identity=reported_eef_goal_to_solver_goal(robot,planner,[0,0,0,1,0,0,0])
    # Original orientation is L * R_reported * inv_delta. Translation is affine
    # for fixed R_reported, including the original gripper tool offset.
    delta=np.linalg.inv(robot.left_inv_delta_matrix);L=t3d.quaternions.quat2mat(identity[3:])@delta
    R=L.T@desired[:3,:3]@delta;q=t3d.quaternions.mat2quat(R)
    b=reported_eef_goal_to_solver_goal(robot,planner,np.r_[np.zeros(3),q])[:3]
    columns=[reported_eef_goal_to_solver_goal(robot,planner,np.r_[np.eye(3)[i],q])[:3]-b for i in range(3)]
    position=np.linalg.solve(np.column_stack(columns),desired[:3,3]-b)
    return np.r_[position,q]
def roundtrip(robot,planner,actual):
    reported=actual_flange_goal_to_reported_command(robot,planner,actual)
    # Invoke actual AST-extracted original Robot.left_plan_path, not inverse's
    # own helper, so old tool + planner dispatch remains the external reference.
    observed=ORIGINAL_LEFT_CALL(robot,reported,last_qpos=np.zeros(38));expected=np.linalg.inv(matrix(planner._cmf_solver_base_world_pose))@matrix(actual)
    R=t3d.quaternions.quat2mat(observed[3:]);angular=np.arccos(np.clip((np.trace(R.T@expected[:3,:3])-1)/2,-1,1));pos=np.linalg.norm(observed[:3]-expected[:3,3])
    assert pos<1e-9 and angular<1e-7
    return {'reported_command':reported.tolist(),'original_entry_solver_goal':observed.tolist(),'position_error_m':float(pos),'orientation_error_rad':float(angular),'quaternion_sign_equivalent_comparison':True,'pass':True}
