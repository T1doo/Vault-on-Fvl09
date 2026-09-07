"""Original physical prefix Gates, isolated model-aware planning schedule."""
import ast,copy,inspect

def compile_prefix_method(parent_module,preplan,postclose_plan,restore_fullworld=lambda scene:None):
    source=inspect.getsource(parent_module.F2TopContactRootControllerV1.plan_and_execute_canonical_prefix)
    import textwrap
    node=ast.parse(textwrap.dedent(source)).body[0]
    changed=0
    for n in ast.walk(node):
        if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='_plan_chain':
            n.value=ast.Call(func=ast.Name(id='_GOAL_PREPLAN',ctx=ast.Load()),args=[ast.Name(id='scene',ctx=ast.Load()),ast.Name(id='targets',ctx=ast.Load())],keywords=[]);changed+=1
        if isinstance(n,ast.Compare) and isinstance(n.left,ast.Call) and isinstance(n.left.func,ast.Name) and n.left.func.id=='len' and any(isinstance(x,ast.Constant) and x.value==3 for x in n.comparators):
            for x in n.comparators:
                if isinstance(x,ast.Constant) and x.value==3:x.value=2;changed+=1
    for i,n in enumerate(node.body):
        if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name) and n.value.func.value.id=='executions' and n.value.func.attr=='append':
            node.body.insert(i,ast.Assign(targets=[ast.Name(id='planned',ctx=ast.Store())],value=ast.Call(func=ast.Name(id='_GOAL_POSTCLOSE_PLAN',ctx=ast.Load()),args=[ast.Name(id=x,ctx=ast.Load()) for x in ('scene','planned','targets')],keywords=[])));changed+=1;break
    for i,n in enumerate(node.body):
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='post_lift' for t in n.targets):
            node.body.insert(i,ast.Expr(value=ast.Call(func=ast.Name(id='_GOAL_RESTORE_FULLWORLD',ctx=ast.Load()),args=[ast.Name(id='scene',ctx=ast.Load())],keywords=[])));changed+=1;break
    if changed!=4:raise ValueError('original prefix function shape changed')
    tree=ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[]));ns=dict(vars(parent_module));ns.update(_GOAL_PREPLAN=preplan,_GOAL_POSTCLOSE_PLAN=postclose_plan,_GOAL_RESTORE_FULLWORLD=restore_fullworld)
    exec(compile(tree,'F2_goal_private_prefix_schedule_v1','exec'),ns)
    return ns[node.name],ast.unparse(tree)

def make_controller(binding):
    from controlled_multi_future import f2_top_contact_root_runtime_v1 as parent
    from controlled_multi_future.f2_asset_bound_runtime_v3 import F2AssetBoundControllerV3
    from .prefix_models import preplan,postclose_plan,restore_fullworld
    method,_=compile_prefix_method(parent,preplan,postclose_plan,restore_fullworld)
    class GoalPrefixQualificationController(parent.F2TopContactRootControllerV1):
        def __init__(self):
            # Existing planner_only permits real canonical-prefix generation,
            # then stops before physical suffix/root acceptance. Keep the
            # provisional binding provisional; never fabricate selected=True.
            F2AssetBoundControllerV3.__init__(self,binding,planner_only=True)
            proposal=parent.build_f2_top_contact_development_root_proposal_v1()
            self.recipe=copy.deepcopy(proposal['selected_candidate']['full_recipe'])
            self.proposal_sha256=proposal['proposal_sha256']
        def canonical_prefix_contract(self,programs):
            result=super().canonical_prefix_contract(programs)
            result['prefix_id']='f2_goal_fresh_top_contact8_lift12cm_prefix_v1'
            result['planner_model_schedule']='static_open_then_actual_postclose_attached_can'
            return result
        def plan_suffix_from_actual_prefix_end_state(self,*args,**kwargs):
            raise RuntimeError('prefix qualification cannot dispatch root suffixes')
        def execute_frozen_suffix_spec(self,*args,**kwargs):
            raise RuntimeError('prefix qualification cannot collect or release a branch')
    GoalPrefixQualificationController.plan_and_execute_canonical_prefix=method
    return GoalPrefixQualificationController()
