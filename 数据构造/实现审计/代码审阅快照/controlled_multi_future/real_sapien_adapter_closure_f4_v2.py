"""Adapter identity for Closure-V1 F4 derivation-interface v2 planner Gate."""
from __future__ import annotations
from .real_sapien_adapter_v1_5 import RoboTwinRealSapienStrictPrefixAdapterV1_5
IMPLEMENTATION_VERSION="controlled_multi_future_post_stage0_closure_f4_v2";ADAPTER_VERSION="RoboTwinRealSapienClosureF4V2Adapter";GENERATOR_VERSION="controlled_multi_future_post_stage0_closure_f4_v2_adapter"
class RoboTwinRealSapienClosureF4V2Adapter(RoboTwinRealSapienStrictPrefixAdapterV1_5):
 def __init__(self,**kwargs):
  if kwargs.get("family")!="F4":raise ValueError("Closure F4 V2 adapter requires F4")
  super().__init__(**kwargs)
 @staticmethod
 def _mark_v1_3_context(scene):scene._cmf_adapter_version=ADAPTER_VERSION;scene._cmf_generator_version=GENERATOR_VERSION
 def verify(self,scene,program,rollout_result):
  v=super().verify(scene,program,rollout_result);v["strict_prefix_adapter_version"]=ADAPTER_VERSION;v["implementation_version"]=IMPLEMENTATION_VERSION;return v
__all__=["IMPLEMENTATION_VERSION","RoboTwinRealSapienClosureF4V2Adapter"]
