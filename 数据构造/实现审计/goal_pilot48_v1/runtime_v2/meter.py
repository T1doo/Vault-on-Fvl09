"""Goal-level counts survive trace resets; only root solver calls are charged."""
import functools,inspect,json,os,time,math
from pathlib import Path
from contextlib import contextmanager
class Meter:
    def __init__(self,out,caps):
        self.out=Path(out);self.out.mkdir(parents=True,exist_ok=True);self.caps=caps;self.counts={'solver_problems':0,'fresh_scenes':0,'action_scenes':0,'collection_attempts':0};self.depth=0;self.warmups_skipped=0;self.active_actions=set();self.patches=[];self.scene_ids={};self.setup_depth=0;self.setup_action_calls=0;self.model_constructions=0
        self.closed=False;self.collection_hooks=[];self.collection_profile=None
    def configure_collection_contract(self,manifest):
        if self.closed:raise RuntimeError('meter closed')
        job=manifest['jobs'][0]
        if job.get('family')=='F1':raise ValueError('F1 namespaced dense actions not audited in runtime_v2; new F1 jobs rejected')
        self.collection_profile=manifest.get('implementation_source_sha256')
        if job['resource_caps']['collection_attempts']>0 and job.get('requires_live_meter') is not True:
            raise ValueError('collection job must receive live meter')
    def _hook(self,adapter,profile):
        from goal_pilot48_v1.collection_meter_review_v1.helper import CollectionHook
        if self.closed:raise RuntimeError('meter closed')
        if getattr(adapter,'family',None)=='F1':raise ValueError('F1 active dense-action coverage is not proven')
        if self.collection_profile is None or profile!=self.collection_profile:raise ValueError('collection profile differs from job source')
        hook=CollectionHook(adapter,self,source_profile_sha256=profile);self.collection_hooks.append(hook);return hook
    @contextmanager
    def instrument_adapter(self,adapter,*,source_profile_sha256):
        hook=self._hook(adapter,source_profile_sha256)
        try:yield adapter
        finally:hook.close()
    @contextmanager
    def instrument_collector_factory(self,pipeline,*,profile_for_cell):
        if self.closed:raise RuntimeError('meter closed')
        original=pipeline.make_adapter;hooks=[]
        def factory(cell,output):
            if self.closed:raise RuntimeError('meter closed')
            adapter=original(cell,output);hooks.append(self._hook(adapter,profile_for_cell(cell)));return adapter
        pipeline.make_adapter=factory
        try:yield
        finally:
            if pipeline.make_adapter is not factory:raise RuntimeError('collector factory changed while instrumented')
            pipeline.make_adapter=original
            for hook in reversed(hooks):hook.close()
    def event(self,kind,**fields):
        if self.closed:raise RuntimeError('meter closed')
        row={'kind':kind,'unix_time':time.time(),**fields};data=(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')
        with (self.out/'events.jsonl').open('ab',buffering=0) as f:f.write(data);os.fsync(f.fileno())
    def charge(self,key,n=1,**fields):
        if self.closed:raise RuntimeError('meter closed')
        if self.counts[key]+n>self.caps[key]:raise RuntimeError('Goal subjob cap exceeded before action: '+key)
        self.counts[key]+=n;self.event('CHARGE',resource=key,amount=n,total=self.counts[key],**fields)
    def solver(self,fn,*,kind):
        @functools.wraps(fn)
        def call(*args,**kwargs):
            root=self.depth==0
            if root:
                bound=inspect.signature(fn).bind_partial(*args,**kwargs).arguments
                goal=bound.get('goal_pose',bound.get('goal_state',None));count=1
                if goal is not None:
                    values=getattr(goal,'position',None)
                    if values is not None and len(values.shape)>1:count=math.prod(values.shape[:-1])
                self.charge('solver_problems',count,method=kind)
            self.depth+=1
            try:return fn(*args,**kwargs)
            finally:self.depth-=1
        return call
    def patch(self,owner,name,value):
        original=getattr(owner,name);self.patches.append((owner,name,original));setattr(owner,name,value)
    def install(self):
        if self.closed:raise RuntimeError('meter closed')
        from curobo.wrap.reacher.motion_gen import MotionGen
        from curobo.wrap.reacher.ik_solver import IKSolver
        from envs._base_task import Base_Task
        from controlled_multi_future.probes.runtime_trace import DenseTraceMixin
        def skip_warmup(*a,**kw):
            self.warmups_skipped+=1;self.event('MODEL_WARMUP_SKIPPED',reason='dummy goals only; actual planning performs lazy initialization',ordinal=self.warmups_skipped)
        self.patch(MotionGen,'warmup',skip_warmup)
        constructor=MotionGen.__init__
        @functools.wraps(constructor)
        def construct(obj,*a,**kw):
            self.model_constructions+=1;return constructor(obj,*a,**kw)
        self.patch(MotionGen,'__init__',construct)
        for name in ('plan_single','plan_single_js','plan_batch','plan_goalset','plan_batch_goalset','plan_batch_env','plan_batch_env_goalset'):
            if hasattr(MotionGen,name):self.patch(MotionGen,name,self.solver(getattr(MotionGen,name),kind='MotionGen.'+name))
        for name in ('solve_single','solve_batch','solve_goalset','solve_batch_goalset'):
            if hasattr(IKSolver,name):self.patch(IKSolver,name,self.solver(getattr(IKSolver,name),kind='IKSolver.'+name))
        setup=Base_Task.setup_scene
        @functools.wraps(setup)
        def setup_scene(scene,*a,**kw):
            self.charge('fresh_scenes',phase='Base_Task.setup_scene entry');self.scene_ids[id(scene)]=self.counts['fresh_scenes'];return setup(scene,*a,**kw)
        self.patch(Base_Task,'setup_scene',setup_scene)
        init=Base_Task._init_task_env_
        @functools.wraps(init)
        def initialize(scene,*a,**kw):
            self.setup_depth+=1
            try:
                result=init(scene,*a,**kw)
                if getattr(scene.robot,'communication_flag',False):raise RuntimeError('Goal meter requires inprocess planner or an explicitly instrumented worker')
                return result
            finally:self.setup_depth-=1
        self.patch(Base_Task,'_init_task_env_',initialize)
        for cls,name in ((DenseTraceMixin,'take_dense_action'),(Base_Task,'move')):
            old=getattr(cls,name)
            def wrapper(scene,*a,__old=old,**kw):
                # setup homing/open are separately observed, but task action
                # scenes start only after the collector initialized its trace.
                sid=self.scene_ids.get(id(scene))
                if not hasattr(scene,'trace'):
                    if self.setup_depth:self.setup_action_calls+=1
                    else:raise RuntimeError('task action before trace initialization')
                elif (id(scene),sid) not in self.active_actions:
                    if sid is None:raise RuntimeError('action scene was not recorded at creation')
                    self.charge('action_scenes',scene_ordinal=sid);self.active_actions.add((id(scene),sid))
                return __old(scene,*a,**kw)
            self.patch(cls,name,wrapper)
        return self
    def close(self):
        if self.closed:return
        hook_errors=[]
        for hook in reversed(self.collection_hooks):
            try:hook.close()
            except BaseException as exc:hook_errors.append({'type':type(exc).__name__,'message':str(exc)})
        for owner,name,original in reversed(self.patches):setattr(owner,name,original)
        self.patches=[];self.event('METER_CLOSED',counts=self.counts,warmups_skipped=self.warmups_skipped,model_constructions=self.model_constructions,setup_action_calls=self.setup_action_calls,collection_hook_errors=hook_errors)
        self.closed=True
        if hook_errors:raise RuntimeError('collection hooks did not close safely')
