"""Private live-meter setup-boundary repair; immutable B/HD execution reused."""
import types
from goal_pilot48_v1.f3_upright_qualification_runtime_v1.context import Counts as OriginalCounts
from goal_pilot48_v1.f3_upright_hd_video_wrapper_v2 import runtime as hd


class Counts(OriginalCounts):
    def __init__(self, meter):
        super().__init__()
        self.live_meter = meter
        self.initialization_action_calls = 0

    def action(self, scene):
        depth = getattr(self.live_meter, 'setup_depth', None)
        if type(depth) is not int or depth < 0:
            raise RuntimeError('invalid actual live-meter initialization depth')
        if depth > 0:
            self.initialization_action_calls += 1
            return
        # Intentionally do not trust the inherited local setup_depth: direct
        # super calls bypass that override, whereas the live Base_Task hook runs.
        if not getattr(scene, 'trace', None):
            raise RuntimeError('task action before current/anchor/trace')
        if not self.action_seen:
            self.actions += 1
            self.action_seen = True


def private_hd_runner(meter):
    base = types.ModuleType('private_upright_live_setup_boundary')
    base.__dict__.update(hd.base.__dict__)
    base.Counts = lambda: Counts(meter)
    env = dict(hd.__dict__)
    env['base'] = base
    return types.FunctionType(hd.run.__code__, env)


def run(manifest, *, meter):
    if (manifest.get('bootstrap_recovery_of') != 'p48_f3_upright_qualification_hd_001'
            or manifest.get('failed_setup_scene_count_retained') != 1
            or manifest.get('second_successful_confirmation_not_authorized_here') is not True):
        raise ValueError('exact finite initialization recovery scope required')
    return private_hd_runner(meter)(manifest, meter=meter)
