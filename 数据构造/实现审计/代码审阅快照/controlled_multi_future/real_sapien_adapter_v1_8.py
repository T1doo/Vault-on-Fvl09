"""Stage-0 v1.2 identity for the F2 frozen-layout slot replacement."""

from __future__ import annotations

from .real_sapien_adapter_v1_7 import RoboTwinRealSapienStage0SmokeAdapterV1_7


ADAPTER_VERSION_V1_8 = "RoboTwinRealSapienStrictPrefixAdapterV1_8"
GENERATOR_VERSION_V1_8 = (
    "controlled_multi_future_stage0_smoke_v1_2_adapter_v1_8"
)
IMPLEMENTATION_VERSION_V1_2 = "controlled_multi_future_stage0_smoke_v1_2"


class RoboTwinRealSapienF2ReplacementAdapterV1_8(
    RoboTwinRealSapienStage0SmokeAdapterV1_7
):
    def __init__(self, **kwargs):
        if kwargs.get("family") != "F2":
            raise ValueError("v1.8 replacement adapter is F2-only")
        super().__init__(**kwargs)

    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = ADAPTER_VERSION_V1_8
        scene._cmf_generator_version = GENERATOR_VERSION_V1_8

    def verify(self, scene, program, rollout_result):
        value = super().verify(scene, program, rollout_result)
        value["strict_prefix_adapter_version"] = ADAPTER_VERSION_V1_8
        value["implementation_version"] = IMPLEMENTATION_VERSION_V1_2
        value["stage0_f2_replacement"] = True
        value["stage0_data"] = True
        value["formal_data"] = False
        return value


__all__ = [
    "ADAPTER_VERSION_V1_8",
    "GENERATOR_VERSION_V1_8",
    "IMPLEMENTATION_VERSION_V1_2",
    "RoboTwinRealSapienF2ReplacementAdapterV1_8",
]
