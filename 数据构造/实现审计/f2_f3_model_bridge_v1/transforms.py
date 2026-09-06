"""Exact locked RoboTwin tool/world transforms without importing CUDA modules."""
import ast,copy,hashlib
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import transforms3d as t3d
P=Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin')

class Pose:
    def __init__(self,p,q):self.p=np.asarray(p,dtype=np.float64);self.q=np.asarray(q,dtype=np.float64)

def method(path,cls,name):
    source=path.read_text(encoding='utf-8');tree=ast.parse(source)
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name==cls)
    return copy.deepcopy(next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name==name))

def compile_method(node):
    tree=ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[]))
    ns={'np':np,'t3d':t3d,'deepcopy':copy.deepcopy,'sapien':SimpleNamespace(Pose=Pose),
        'CuroboPose':SimpleNamespace(from_list=lambda values:np.asarray(values,dtype=np.float64))}
    exec(compile(tree,'locked_RoboTwin_transform_extraction','exec'),ns)
    return ns[node.name]

TOOL=compile_method(method(P/'envs/robot/robot.py','Robot','_trans_from_gripper_to_endlink'))
WORLD=compile_method(method(P/'envs/robot/planner.py','CuroboPlanner','_trans_from_world_to_base'))
node=method(P/'envs/robot/planner.py','CuroboPlanner','plan_path')
stop=next(i for i,n in enumerate(node.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='goal_pose_of_ee' for t in n.targets))
node.body=node.body[:stop+1]+[ast.Return(value=ast.Name(id='goal_pose_of_ee',ctx=ast.Load()))]
GOAL=compile_method(node)
ORIGINAL_LEFT_CALL=compile_method(method(P/'envs/robot/robot.py','Robot','left_plan_path'))

def planner_view(origin_pose,frame_bias,yml_path):
    p=SimpleNamespace(robot_origion_pose=Pose(origin_pose[:3],origin_pose[3:]),frame_bias=list(frame_bias),yml_path=str(yml_path))
    p._trans_from_world_to_base=lambda base,target:WORLD(p,base,target)
    return p

def world_obstacle_to_solver_frame(planner,world_pose,arm='left'):
    pose=Pose(world_pose[:3],world_pose[3:])
    return GOAL(planner,None,pose,arms_tag=arm)

def reported_eef_goal_to_solver_goal(robot,planner,goal,arm='left'):
    endlink=TOOL(robot,np.asarray(goal,dtype=np.float64),arm_tag=arm)
    return GOAL(planner,None,endlink,arms_tag=arm)

def full_joint_state_to_solver_joint_state(qpos,all_names,solver_names,*,round_like_original=True):
    q=np.asarray(qpos,dtype=np.float64).reshape(-1)
    if len(q)!=len(all_names) or len(set(all_names))!=len(all_names) or len(set(solver_names))!=len(solver_names):raise ValueError('joint name/state shape or duplicates')
    indices={name:i for i,name in enumerate(all_names)}
    if any(name not in indices for name in solver_names):raise ValueError('missing solver joint')
    out=np.asarray([q[indices[name]] for name in solver_names])
    if round_like_original:out=np.asarray([round(float(v),5) for v in out])
    return out.astype(np.float32)

def source_bindings():
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (P/'envs/robot/robot.py',P/'envs/robot/planner.py')}
