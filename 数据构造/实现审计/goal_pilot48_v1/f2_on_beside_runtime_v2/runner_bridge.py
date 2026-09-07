import types
from goal_pilot48_v1.f2_single_relation_qualification_v1 import runner_bridge as old
from .qualification import run as execute
def run(manifest,*,meter):
    ns=dict(old.run.__globals__);ns['execute']=execute
    fn=types.FunctionType(old.run.__code__,ns,old.run.__name__,old.run.__defaults__,old.run.__closure__)
    return fn(manifest,meter=meter)
