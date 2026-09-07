"""Serialization-only fix; original predicates, values and actions unchanged."""
import types
import numpy as np
from goal_pilot48_v1.f2_on_beside_runtime_v1 import runtime as old,gates

def json_values(value):
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,np.ndarray):return json_values(value.tolist())
    if isinstance(value,dict):return {k:json_values(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [json_values(v) for v in value]
    return value

class LiveBackend(old.LiveBackend):
    def final_gate(self):
        return self.models.save('original_final_gate',json_values(gates.final(self.scene,self.spec,self.transport)))

def run(*args,**kwargs):
    ns=dict(old.run.__globals__);ns['LiveBackend']=LiveBackend
    if kwargs.get('relation')=='on':
        from goal_pilot48_v1.f2_on_release_revision_v1.runtime import build_targets,validate
        ns.update(build_targets=build_targets,validate=validate)
    fn=types.FunctionType(old.run.__code__,ns,old.run.__name__,old.run.__defaults__,old.run.__closure__)
    fn.__kwdefaults__=old.run.__kwdefaults__;return fn(*args,**kwargs)
