import types
from goal_pilot48_v1.f2_goal_root_runtime_v1 import runner_bridge as parent
from .runtime import run as execute
def run(manifest,*,meter):
    ns=dict(parent.run.__globals__);ns['execute']=execute
    fn=types.FunctionType(parent.run.__code__,ns,'run',parent.run.__defaults__,parent.run.__closure__)
    return fn(manifest,meter=meter)
