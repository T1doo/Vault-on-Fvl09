"""Real-SAPIEN adapter binding one frozen F3 qualification grasp."""

from __future__ import annotations

from typing import Any, Mapping

from .f3_grasp_qualification_v1 import (
    IMPLEMENTATION_VERSION,
    build_f3_selected_grasp_contract_v1,
)
from .real_sapien_adapter_v1_5 import RoboTwinRealSapienStrictPrefixAdapterV1_5


ADAPTER_VERSION = "RoboTwinRealSapienF3GraspQualificationV1Adapter"
GENERATOR_VERSION = "controlled_multi_future_f3_grasp_qualification_v1_adapter"


class RoboTwinRealSapienF3GraspQualificationV1Adapter(
    RoboTwinRealSapienStrictPrefixAdapterV1_5
):
    def __init__(self, *, selected_grasp_candidate: Mapping[str, Any], **kwargs):
        if kwargs.get("family") != "F3":
            raise ValueError("F3 grasp qualification adapter requires F3")
        contract = build_f3_selected_grasp_contract_v1(selected_grasp_candidate)
        super().__init__(**kwargs)
        controller = self.controller_v3_3
        if getattr(controller, "f3_shared_prefix_repair_v11", None) is not None:
            raise ValueError("F3 qualification cannot coexist with v11")
        if getattr(controller, "f3_common_grasp_prefix_v2", None) is not None:
            raise ValueError("F3 qualification cannot coexist with CommonGraspPrefixV2")
        existing = getattr(controller, "f3_selected_stable_grasp_contract_v1", None)
        if existing is not None and existing != contract:
            raise ValueError("F3 controller already carries a different qualification grasp")
        controller.f3_selected_stable_grasp_contract_v1 = contract
        self.selected_grasp_contract_v1 = contract

    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = ADAPTER_VERSION
        scene._cmf_generator_version = GENERATOR_VERSION

    def verify(self, scene, program, rollout_result):
        value = super().verify(scene, program, rollout_result)
        value["strict_prefix_adapter_version"] = ADAPTER_VERSION
        value["implementation_version"] = IMPLEMENTATION_VERSION
        value["f3_selected_stable_grasp_contract_sha256"] = (
            self.selected_grasp_contract_v1["contract_sha256"]
        )
        return value


__all__ = [
    "ADAPTER_VERSION",
    "GENERATOR_VERSION",
    "RoboTwinRealSapienF3GraspQualificationV1Adapter",
]
