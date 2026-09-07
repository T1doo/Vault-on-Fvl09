import types
from .runtime import run as execute
from .spec import CAPS
from goal_pilot48_v1.f2_on_beside_qualification_v1 import runner_bridge as old
def reconcile(*args,**kwargs):
    ns=dict(old.reconcile.__globals__);ns['CAPS']=CAPS
    fn=types.FunctionType(old.reconcile.__code__,ns,old.reconcile.__name__,old.reconcile.__defaults__,old.reconcile.__closure__)
    return fn(*args,**kwargs)
def run(manifest,*,meter):
    ns=dict(old.run.__globals__);ns.update(execute=execute,reconcile=reconcile)
    fn=types.FunctionType(old.run.__code__,ns,old.run.__name__,old.run.__defaults__,old.run.__closure__)
    return fn(manifest,meter=meter)
