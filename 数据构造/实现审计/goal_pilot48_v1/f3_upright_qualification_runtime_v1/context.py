"""Private old lifecycle with only the F3 scene factory replaced."""
import ast,inspect,types,copy
from .native import A
def restore_step_hook(scene):
    if scene is not None and hasattr(scene,'_cmf_original_scene_step'):
        raw=scene._cmf_original_scene_step;owner=getattr(raw,'__self__',None) or getattr(scene,'scene',None)
        if owner is None:raise RuntimeError('cannot restore owned native scene step hook')
        owner.step=raw;del scene._cmf_original_scene_step
class Counts:
    def __init__(self):self.scenes=0;self.actions=0;self.setup_depth=0;self.action_seen=False;self.IK=0;self.MG=0;self.steps=0
    def setup(self):
        if self.scenes>=1:raise RuntimeError('one fresh scene cap before setup')
        self.scenes+=1
    def action(self,scene):
        if self.setup_depth:return
        if not getattr(scene,'trace',None):raise RuntimeError('task action before current/anchor/trace')
        if not self.action_seen:self.actions+=1;self.action_seen=True
    def ik(self):
        if self.IK>=3:raise RuntimeError('three independent IK cap')
        self.IK+=1
    def step(self):
        if self.steps>=6000:raise RuntimeError('qualification6000 physical-step cap before step')
        self.steps+=1
def make(spec,out,counts):
    from goal_pilot48_v1.f3_upright_design_v1.scene import make_scene_class
    from controlled_multi_future.real_sapien_adapter_v1_2 import RoboTwinSceneContextV1_2,RoboTwinRealSapienPilotRootAdapterV1_2
    from controlled_multi_future.probes.action_feasibility_v2 import _scene_resources
    from controlled_multi_future.real_sapien_adapter_high_level_v1 import _PinnedSapienRenderDeviceContextV1
    base_scene=make_scene_class(spec)
    class CountedUpright(base_scene):
        def setup_scene(self,*a,**k):
            counts.setup();result=super().setup_scene(*a,**k)
            self._cmf_original_scene_step=self.scene.step
            raw=self._cmf_original_scene_step
            def step():counts.step();return raw()
            self.scene.step=step;return result
        def _init_task_env_(self,*a,**k):
            counts.setup_depth+=1
            try:return super()._init_task_env_(*a,**k)
            finally:counts.setup_depth-=1
        def take_dense_action(self,*a,**k):counts.action(self);return super().take_dense_action(*a,**k)
        def move(self,*a,**k):counts.action(self);return super().move(*a,**k)
    def resources():
        classes,args=_scene_resources();classes=dict(classes);classes['F3']=CountedUpright;return classes,args
    source=ast.parse(inspect.getsource(RoboTwinSceneContextV1_2.__enter__).lstrip())
    class Replace(ast.NodeTransformer):
        count=0
        def visit_ImportFrom(self,node):
            if any(n.name=='_scene_resources' for n in node.names):
                self.count+=1;return ast.Assign(targets=[ast.Name(id='_scene_resources',ctx=ast.Store())],value=ast.Name(id='_upright_resources',ctx=ast.Load()))
            return node
    replace=Replace();source=replace.visit(source)
    if replace.count!=1:raise ValueError('exact scene factory import mismatch')
    env=dict(RoboTwinSceneContextV1_2.__enter__.__globals__);env['_upright_resources']=resources
    exec(compile(ast.fix_missing_locations(source),__file__,'exec'),env)
    class Context(RoboTwinSceneContextV1_2):
        def __exit__(self,*args):
            restore_step_hook(getattr(self,'_scene',None))
            return super().__exit__(*args)
    bound_enter=env['__enter__']
    def enter(self):
        try:return bound_enter(self)
        except BaseException:
            restore_step_hook(getattr(self,'_scene',None));raise
    Context.__enter__=enter
    adapter=RoboTwinRealSapienPilotRootAdapterV1_2(family='F3',output_root=out/'adapter',expected_implementation_source_sha256='3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7')
    ctx=Context(family='F3',planned_spec=copy.deepcopy(spec),phase='UPRIGHT_B_QUALIFICATION_V1',program=None,output_root=out/'adapter',
        sealed_implementation_source_sha256=adapter._sealed_implementation_source_sha256,sealed_source_binding='upright_B_design:'+spec['receipt_sha256'])
    return adapter,_PinnedSapienRenderDeviceContextV1(ctx)
