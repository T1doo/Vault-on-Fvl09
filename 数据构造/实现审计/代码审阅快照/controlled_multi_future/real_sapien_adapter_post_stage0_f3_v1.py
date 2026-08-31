"""Adapter identity for the bounded post-Stage-0 F3 prefix diagnostic."""

from __future__ import annotations

from .f3_contact_preserving_prefix_v11 import (
    IMPLEMENTATION_VERSION,
    build_f3_contact_preserving_prefix_contract_v11,
)
from .real_sapien_adapter_v1_5 import RoboTwinRealSapienStrictPrefixAdapterV1_5


ADAPTER_VERSION = "RoboTwinRealSapienStrictPrefixAdapterPostStage0F3V1"
GENERATOR_VERSION = "controlled_multi_future_post_stage0_f3_adapter_v1"


class RoboTwinRealSapienPostStage0F3AdapterV1(
    RoboTwinRealSapienStrictPrefixAdapterV1_5
):
    def __init__(self, **kwargs):
        if kwargs.get("family") != "F3":
            raise ValueError("post-Stage-0 F3 adapter requires family F3")
        super().__init__(**kwargs)
        self.controller_v3_3.f3_shared_prefix_repair_v11 = (
            build_f3_contact_preserving_prefix_contract_v11()
        )

    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = ADAPTER_VERSION
        scene._cmf_generator_version = GENERATOR_VERSION

    def verify(self, scene, program, rollout_result):
        value = super().verify(scene, program, rollout_result)
        value["strict_prefix_adapter_version"] = ADAPTER_VERSION
        value["implementation_version"] = IMPLEMENTATION_VERSION
        return value


__all__ = ["RoboTwinRealSapienPostStage0F3AdapterV1"]
