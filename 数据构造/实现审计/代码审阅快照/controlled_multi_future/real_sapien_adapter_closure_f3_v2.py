"""Adapter identity for Closure-V1 F3CommonGraspPrefixV2."""
from __future__ import annotations
from .f3_common_grasp_prefix_v2 import IMPLEMENTATION_VERSION, build_f3_common_grasp_prefix_v2
from .real_sapien_adapter_v1_5 import RoboTwinRealSapienStrictPrefixAdapterV1_5
ADAPTER_VERSION="RoboTwinRealSapienClosureF3V2Adapter"
GENERATOR_VERSION="controlled_multi_future_post_stage0_closure_f3_v2_adapter"
class RoboTwinRealSapienClosureF3V2Adapter(RoboTwinRealSapienStrictPrefixAdapterV1_5):
    def __init__(self,**kwargs):
        if kwargs.get("family")!="F3": raise ValueError("Closure F3 V2 adapter requires F3")
        super().__init__(**kwargs); self.controller_v3_3.f3_common_grasp_prefix_v2=build_f3_common_grasp_prefix_v2()
    @staticmethod
    def _mark_v1_3_context(scene): scene._cmf_adapter_version=ADAPTER_VERSION; scene._cmf_generator_version=GENERATOR_VERSION
    def verify(self,scene,program,rollout_result):
        value=super().verify(scene,program,rollout_result); value["strict_prefix_adapter_version"]=ADAPTER_VERSION; value["implementation_version"]=IMPLEMENTATION_VERSION; return value
__all__=["RoboTwinRealSapienClosureF3V2Adapter"]
