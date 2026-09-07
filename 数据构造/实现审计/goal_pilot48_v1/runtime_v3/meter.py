"""V3 additionally meters the actual direct prefix-replay drive operator."""
import functools
from goal_pilot48_v1.runtime_v2.meter import Meter as FrozenMeterV2

class Meter(FrozenMeterV2):
    def install_replay_hook(self,trace_class):
        if self.closed:raise RuntimeError('meter closed')
        original=trace_class.replay_effective_setpoint_step
        @functools.wraps(original)
        def replay(scene,*a,**kw):
            if self.closed:raise RuntimeError('meter closed')
            sid=self.scene_ids.get(id(scene))
            if sid is None or not hasattr(scene,'trace'):
                raise RuntimeError('replay control before metered scene/trace bootstrap')
            if (id(scene),sid) not in self.active_actions:
                self.charge('action_scenes',scene_ordinal=sid,action_entry='DenseTraceMixin.replay_effective_setpoint_step')
                self.active_actions.add((id(scene),sid))
            return original(scene,*a,**kw)
        self.patch(trace_class,'replay_effective_setpoint_step',replay)
    def install(self):
        super().install()
        from controlled_multi_future.probes.runtime_trace import DenseTraceMixin
        self.install_replay_hook(DenseTraceMixin)
        return self
