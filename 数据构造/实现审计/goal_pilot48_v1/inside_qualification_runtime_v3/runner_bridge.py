from goal_pilot48_v1.inside_qualification_runtime_v1 import runner_bridge as old
from goal_pilot48_v1.f2_controlled_inside_runtime_v3.runtime import private
from .runtime import run as execute

def run(manifest,*,meter):return private(old.run,execute=execute)(manifest,meter=meter)
