"""Real SAPIEN adapter identity for Stage 0 smoke v1.1.

The v1.1 adapter changes only implementation/provenance identity. Scene,
planner, controller, verifier, camera, physics and raw-stream behavior remain
inherited from the reviewed v1.6 adapter.
"""

from __future__ import annotations

from .real_sapien_adapter_v1_6 import RoboTwinRealSapienStage0SmokeAdapterV1_6


ADAPTER_VERSION_V1_7 = "RoboTwinRealSapienStrictPrefixAdapterV1_7"
GENERATOR_VERSION_V1_7 = (
    "controlled_multi_future_stage0_smoke_v1_1_adapter_v1_7"
)
IMPLEMENTATION_VERSION_V1_1 = "controlled_multi_future_stage0_smoke_v1_1"


class RoboTwinRealSapienStage0SmokeAdapterV1_7(
    RoboTwinRealSapienStage0SmokeAdapterV1_6
):
    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = ADAPTER_VERSION_V1_7
        scene._cmf_generator_version = GENERATOR_VERSION_V1_7

    def verify(self, scene, program, rollout_result):
        value = super().verify(scene, program, rollout_result)
        value["strict_prefix_adapter_version"] = ADAPTER_VERSION_V1_7
        value["implementation_version"] = IMPLEMENTATION_VERSION_V1_1
        value["stage0_data"] = True
        value["formal_data"] = False
        return value


__all__ = [
    "ADAPTER_VERSION_V1_7",
    "GENERATOR_VERSION_V1_7",
    "IMPLEMENTATION_VERSION_V1_1",
    "RoboTwinRealSapienStage0SmokeAdapterV1_7",
]
