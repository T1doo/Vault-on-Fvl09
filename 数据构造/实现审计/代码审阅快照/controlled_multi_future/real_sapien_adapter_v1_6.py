"""Real SAPIEN adapter identity for controlled Stage 0 smoke v1."""

from __future__ import annotations

from .real_sapien_adapter_v1_5 import RoboTwinRealSapienStrictPrefixAdapterV1_5


ADAPTER_VERSION_V1_6 = "RoboTwinRealSapienStrictPrefixAdapterV1_6"
GENERATOR_VERSION_V1_6 = "controlled_multi_future_stage0_smoke_v1_adapter_v1_6"


class RoboTwinRealSapienStage0SmokeAdapterV1_6(
    RoboTwinRealSapienStrictPrefixAdapterV1_5
):
    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = ADAPTER_VERSION_V1_6
        scene._cmf_generator_version = GENERATOR_VERSION_V1_6

    def verify(self, scene, program, rollout_result):
        value = super().verify(scene, program, rollout_result)
        value["strict_prefix_adapter_version"] = ADAPTER_VERSION_V1_6
        value["implementation_version"] = "controlled_multi_future_stage0_smoke_v1"
        value["stage0_data"] = True
        value["formal_data"] = False
        return value


__all__ = ["RoboTwinRealSapienStage0SmokeAdapterV1_6"]
