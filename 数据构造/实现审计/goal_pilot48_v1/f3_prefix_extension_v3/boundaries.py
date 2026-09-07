"""Private hooks record actual trace indices/poses, never substitute final pose."""
import copy,types,inspect,ast
from goal_pilot48_v1.f3_runtime_v5 import micro
def record(scene,label,row=None):
    from controlled_multi_future.geometry import relative_pose
    row=len(scene.trace)-1 if row is None else int(row)
    if not 0<=row<len(scene.trace):raise ValueError('boundary outside actual trace')
    value=scene.trace[row];key='f3_extension_'+label
    if key in scene.markers and scene.markers[key]!=row:raise ValueError('immutable boundary marker changed')
    scene.markers[key]=row
    if not hasattr(scene,'_cmf_extension_boundaries'):scene._cmf_extension_boundaries={}
    result={'trace_row':row,'step_index':int(value['step_index']),'timestamp':float(value['timestamp']),
        'actual_eef':list(value['eef']),'actual_actor_pose':list(value['actor_pose']),
        'relative_pose':relative_pose(value['eef'],value['actor_pose']).tolist(),'pose_source':'exact recorded boundary row'}
    if label in scene._cmf_extension_boundaries and scene._cmf_extension_boundaries[label]!=result:raise ValueError('boundary evidence changed')
    scene._cmf_extension_boundaries[label]=result;return result
def execute_micro(scene,proposal,out):
    env=dict(micro.__dict__)
    def attach(s,path):
        record(s,'post_close')
        return micro.attach_closed_bottle_model(s,path)
    def postlift(rows,**kw):
        # The exact executed segment end is read from its receipt, not current pose.
        record(scene,'micro_lift_end',kw['lift_receipt']['end_trace_row'])
        value=micro.audit_micro_lift_trace(rows,**kw);record(scene,'micro_confirmation_end');return value
    env['attach_closed_bottle_model']=attach;env['audit_micro_lift_trace']=postlift
    env['_execute_inner']=types.FunctionType(micro._execute_inner.__code__,env)
    return types.FunctionType(micro.execute.__code__,env)(scene,proposal,out)

def tail_with_markers(original,env):
    tree=ast.parse(inspect.getsource(original))
    names={'post_lift_transform':'post_lift8cm','post_clearance_transform':'post_clearance_raise',
        'post_center_transform':'post_center_high','pre_shared_v_transform':'pre_shared_V',
        'post_shared_transform':'post_shared_V','acceptance_transform':'acceptance_end'}
    class Add(ast.NodeTransformer):
        count=0
        def visit_Assign(self,node):
            label=names.get(node.targets[0].id) if len(node.targets)==1 and isinstance(node.targets[0],ast.Name) else None
            if label is None:return node
            self.count+=1
            return [node,ast.Expr(value=ast.Call(func=ast.Name(id='_record_boundary',ctx=ast.Load()),args=[ast.Name(id='scene',ctx=ast.Load()),ast.Constant(label)],keywords=[]))]
    transformer=Add();tree=transformer.visit(tree)
    if transformer.count!=6:raise ValueError('locked F3 boundary hook AST mismatch')
    env=dict(env);env['_record_boundary']=record;exec(compile(ast.fix_missing_locations(tree),__file__,'exec'),env)
    return env[original.__name__]
