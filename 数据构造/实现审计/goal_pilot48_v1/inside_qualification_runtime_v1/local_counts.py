"""Independent local call-entry counts; temporary hooks restore on exit."""
import functools

class LocalCounts:
    def __init__(self,base=None,trace=None):
        self.base,self.trace=base,trace;self.scenes={};self.actions=set();self.patches=[]
    def patch(self,owner,name,fn):
        old=getattr(owner,name);self.patches.append((owner,name,old,fn));setattr(owner,name,fn)
    def __enter__(self):
        if self.base is None:
            from envs._base_task import Base_Task
            from controlled_multi_future.probes.runtime_trace import DenseTraceMixin
            self.base,self.trace=Base_Task,DenseTraceMixin
        setup=self.base.setup_scene
        @functools.wraps(setup)
        def enter(scene,*args,**kwargs):
            if id(scene) in self.scenes:raise RuntimeError('qualification attempted second setup on same scene')
            self.scenes[id(scene)]=scene
            if len(self.scenes)>1:raise RuntimeError('qualification attempted second fresh scene')
            return setup(scene,*args,**kwargs)
        self.patch(self.base,'setup_scene',enter)
        for owner,name in ((self.trace,'replay_effective_setpoint_step'),(self.trace,'take_dense_action'),(self.base,'move')):
            old=getattr(owner,name)
            @functools.wraps(old)
            def action(scene,*args,_original=old,**kwargs):
                if hasattr(scene,'trace'):
                    if id(scene) not in self.scenes:raise RuntimeError('local action before actual scene setup')
                    self.actions.add(id(scene))
                return _original(scene,*args,**kwargs)
            self.patch(owner,name,action)
        return self
    def __exit__(self,*args):
        errors=[]
        for owner,name,old,ours in reversed(self.patches):
            if getattr(owner,name) is not ours:errors.append(name)
            else:setattr(owner,name,old)
        self.patches=[]
        if errors:raise RuntimeError('local counter hook ownership changed: '+str(errors))
        return False
    def snapshot(self):
        queries=[getattr(scene,'planner_query_count',0) for scene in self.scenes.values()]
        if any(type(n) is not int or n<0 for n in queries):raise ValueError('invalid local planner counter')
        return {'fresh_scene_attempts':len(self.scenes),'action_scenes_observed':len(self.actions),'trajectory_queries':sum(queries),
          'ik_problem_attempts':0,'collection_attempts':0}
