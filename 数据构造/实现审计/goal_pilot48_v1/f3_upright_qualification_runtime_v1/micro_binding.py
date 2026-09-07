"""Private V6 micro: new fixed side pregrasp and complete native control screen."""
import ast,inspect,types
from pathlib import Path
import numpy as np
from goal_pilot48_v1.f3_runtime_v6 import micro as old
from .native import capture,Checker,pad_escape_token
def execute(scene,targets,spec,out):
    from model_apply import runtime_joint_state
    from realization_utf8_io_v1 import write_new
    checks=[]
    def full_check(s,controls,stage,directory):
        names,q=runtime_joint_state(s);snapshot=capture(s,s.robot.left_planner._cmf_solver_base_world_pose,names,q)
        write_new(directory/(stage+'.full_native_snapshot.json'),snapshot)
        carried=stage=='lift25';allow=pad_escape_token(s,snapshot) if carried else False
        result=Checker(snapshot).check(controls['position'],list(s.robot.left_planner.motion_gen.kinematics.joint_names),carried=carried,allow_pad_escape=allow)
        result['stage']=stage;checks.append(result);return result
    tree=ast.parse(inspect.getsource(old._execute_inner));changed=0
    class Replace(ast.NodeTransformer):
        count=0
        def visit_ImportFrom(self,node):
            if node.module=='goal_pilot48_v1.f3_native_self_pair_v1.checker':return None
            return node
        def visit_Call(self,node):
            if isinstance(node.func,ast.Name) and node.func.id=='check_controls':
                self.count+=1
                return ast.Call(func=ast.Name(id='_full_native_check',ctx=ast.Load()),args=[ast.Name(id='scene',ctx=ast.Load()),ast.Subscript(value=ast.Subscript(value=ast.Name(id='planned',ctx=ast.Load()),slice=ast.Constant('controls'),ctx=ast.Load()),slice=ast.Constant(0),ctx=ast.Load()),ast.Name(id='stage',ctx=ast.Load()),ast.Name(id='out',ctx=ast.Load())],keywords=[])
            return self.generic_visit(node)
    replace=Replace();tree=replace.visit(tree)
    if replace.count!=1:raise ValueError('micro native-screen binding AST mismatch')
    env=dict(old.__dict__);env['_full_native_check']=full_check
    exec(compile(ast.fix_missing_locations(tree),__file__,'exec'),env)
    # Original micro overrides pregrasp from this explicit field, not its old Z offset.
    proposal={'proposal_id':spec['slot_id'],'desired_actual_flange_world_pose':targets['grasp'],'_route_pregrasp_pose':targets['pregrasp']}
    fn=types.FunctionType(old.execute.__code__,env)
    result=fn(scene,proposal,out)
    result['native_full_arm_controls_pass']=len(checks)==3 and all(c['pass'] for c in checks)
    result['native_full_arm_stage_checks']=checks
    if result.get('pass') and not result['native_full_arm_controls_pass']:result['pass']=False;result['earliest_failed_stage']='native_full_arm_checks_incomplete'
    return result
