"""Adapter identity for the interface-fixed F3CommonGraspPrefixV2_1."""

from __future__ import annotations

from .f3_common_grasp_prefix_v2 import (
    build_f3_common_grasp_prefix_v2,
    validate_f3_common_grasp_prefix_v2,
)
from .f3_common_grasp_prefix_v2_1 import IMPLEMENTATION_VERSION
from .real_sapien_adapter_v1_5 import RoboTwinRealSapienStrictPrefixAdapterV1_5


ADAPTER_VERSION = "RoboTwinRealSapienClosureF3V2_1Adapter"
GENERATOR_VERSION = "controlled_multi_future_post_stage0_closure_f3_v2_1_adapter"


class RoboTwinRealSapienClosureF3V2_1Adapter(
    RoboTwinRealSapienStrictPrefixAdapterV1_5
):
    def __init__(self, **kwargs):
        if kwargs.get("family") != "F3":
            raise ValueError("Closure F3 V2_1 adapter requires F3")
        super().__init__(**kwargs)
        controller = self.controller_v3_3
        if getattr(controller, "f3_shared_prefix_repair_v11", None) is not None:
            raise ValueError("Closure F3 V2_1 cannot reuse a controller with v11 bound")
        expected = build_f3_common_grasp_prefix_v2()
        existing = getattr(controller, "f3_common_grasp_prefix_v2", None)
        if existing is not None and validate_f3_common_grasp_prefix_v2(existing) != expected:
            raise ValueError("Closure F3 V2_1 controller has a different V2 contract")
        controller.f3_common_grasp_prefix_v2 = expected

    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = ADAPTER_VERSION
        scene._cmf_generator_version = GENERATOR_VERSION

    def verify(self, scene, program, rollout_result):
        value = super().verify(scene, program, rollout_result)
        value["strict_prefix_adapter_version"] = ADAPTER_VERSION
        value["implementation_version"] = IMPLEMENTATION_VERSION
        return value


__all__ = ["RoboTwinRealSapienClosureF3V2_1Adapter"]
