"""Versioned single-relation wrapper; no changes to consumed wrapper source."""
import types
from goal_pilot48_v1.f2_single_relation_qualification_v1 import runtime as old
from .runtime import run as suffix_run
def run(manifest):
    ns=dict(old.run.__globals__);ns['suffix_callable']=lambda relation:suffix_run
    fn=types.FunctionType(old.run.__code__,ns,old.run.__name__,old.run.__defaults__,old.run.__closure__)
    return fn(manifest)
