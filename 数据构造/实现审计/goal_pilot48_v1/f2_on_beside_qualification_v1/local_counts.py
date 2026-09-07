"""Private monotonic two-scene counter, independent of Goal solver meter."""
import functools,weakref
class LocalCounts:
    def __init__(self,base=None,trace=None):
        self.base,self.trace=base,trace;self.scenes={};self.actions=set();self.patches=[]
        self.scene_ordinals={};self.seen={};self.completed=[];self.total_scenes=0;self.count_errors=[]
    def patch(self,owner,name,fn):
        old=getattr(owner,name);self.patches.append((owner,name,old,fn));setattr(owner,name,fn)
    def __enter__(self):
        if self.base is None:
            from envs._base_task import Base_Task
            from controlled_multi_future.probes.runtime_trace import DenseTraceMixin
            self.base,self.trace=Base_Task,DenseTraceMixin
        original=self.base.setup_scene
        @functools.wraps(original)
        def setup(scene,*a,**kw):
            prior=self.seen.get(id(scene))
            if prior is not None and prior() is scene:raise RuntimeError('same-scene setup repetition')
            if self.total_scenes>=2:raise RuntimeError('two-scene cap exceeded')
            reference=weakref.ref(scene)
            self.total_scenes+=1
            self.scenes[id(scene)]=scene
            self.scene_ordinals[id(scene)]=self.total_scenes;self.seen[id(scene)]=reference
            return original(scene,*a,**kw)
        self.patch(self.base,'setup_scene',setup)
        for owner,name in ((self.base,'move'),(self.trace,'take_dense_action'),(self.trace,'replay_effective_setpoint_step')):
            previous=getattr(owner,name)
            @functools.wraps(previous)
            def action(scene,*a,_original=previous,**kw):
                if hasattr(scene,'trace'):
                    if id(scene) not in self.scenes:raise RuntimeError('action before registered setup')
                    self.actions.add(self.scene_ordinals[id(scene)])
                return _original(scene,*a,**kw)
            self.patch(owner,name,action)
        return self
    def __exit__(self,*a):
        errors=[]
        for owner,name,old,ours in reversed(self.patches):
            if getattr(owner,name) is not ours:errors.append(name)
            else:setattr(owner,name,old)
        self.patches=[]
        if errors:raise RuntimeError('local hook ownership changed '+str(errors))
        return False
    def retire_completed(self):
        """Called only after a branch has saved evidence and completed cleanup."""
        for key,scene in list(self.scenes.items()):
            value=getattr(scene,'planner_query_count',0)
            ordinal=self.scene_ordinals.pop(key)
            if type(value) is not int or value<0:
                self.count_errors.append({'scene_ordinal':ordinal,'reason':'invalid_final_query_counter'})
                value=None
            self.completed.append({'scene_ordinal':ordinal,'trajectory_queries':value})
            del self.scenes[key]
        if self.count_errors:raise ValueError('unknown retired local solver counter')
    def snapshot(self):
        if self.count_errors:raise ValueError('unknown retired local solver counter')
        values=[r['trajectory_queries'] for r in self.completed]+[getattr(s,'planner_query_count',0) for s in self.scenes.values()]
        if any(type(v) is not int or v<0 for v in values):raise ValueError('unknown local solver counter')
        if len(values)!=self.total_scenes:raise ValueError('local scene history incomplete')
        return {'fresh_scene_attempts':self.total_scenes,'action_scenes_observed':len(self.actions),'trajectory_queries':sum(values),
          'ik_problem_attempts':0,'collection_attempts':0}
