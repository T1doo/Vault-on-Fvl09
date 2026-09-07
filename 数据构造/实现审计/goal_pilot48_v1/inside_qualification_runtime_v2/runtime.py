from goal_pilot48_v1.inside_qualification_runtime_v1 import runtime as old
from goal_pilot48_v1.f2_controlled_inside_runtime_v3.runtime import private,run as inside_run
from .spec import build_spec

def private_entry():return private(old.run,build_spec=build_spec,inside_run=inside_run)
def run(manifest):return private_entry()(manifest)
