"""Adapter identity for the post-Stage-0 F4 planner-only audit."""

from __future__ import annotations

from .real_sapien_adapter_v1_5 import RoboTwinRealSapienStrictPrefixAdapterV1_5


IMPLEMENTATION_VERSION = "controlled_multi_future_post_stage0_f4_v1"
ADAPTER_VERSION = "RoboTwinRealSapienStrictPrefixAdapterPostStage0F4V1"
GENERATOR_VERSION = "controlled_multi_future_post_stage0_f4_adapter_v1"


class RoboTwinRealSapienPostStage0F4AdapterV1(
    RoboTwinRealSapienStrictPrefixAdapterV1_5
):
    def __init__(self, **kwargs):
        if kwargs.get("family") != "F4":
            raise ValueError("post-Stage-0 F4 adapter requires family F4")
        super().__init__(**kwargs)

    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = ADAPTER_VERSION
        scene._cmf_generator_version = GENERATOR_VERSION

    def verify(self, scene, program, rollout_result):
        value = super().verify(scene, program, rollout_result)
        value["strict_prefix_adapter_version"] = ADAPTER_VERSION
        value["implementation_version"] = IMPLEMENTATION_VERSION
        return value


__all__ = [
    "IMPLEMENTATION_VERSION",
    "RoboTwinRealSapienPostStage0F4AdapterV1",
]
