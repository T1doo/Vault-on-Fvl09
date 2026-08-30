"""Real SAPIEN adapter identity for one-shot runtime-v3_4_1."""

from __future__ import annotations

from .real_sapien_adapter_v1_4 import RoboTwinRealSapienStrictPrefixAdapterV1_4


ADAPTER_VERSION_V1_5 = "RoboTwinRealSapienStrictPrefixAdapterV1_5"
GENERATOR_VERSION_V1_5 = "controlled_multi_future_joint_scene_v3_4_1_adapter_v1_5"


class RoboTwinRealSapienStrictPrefixAdapterV1_5(
    RoboTwinRealSapienStrictPrefixAdapterV1_4
):
    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = ADAPTER_VERSION_V1_5
        scene._cmf_generator_version = GENERATOR_VERSION_V1_5

    def verify(self, scene, program, rollout_result):
        value = super().verify(scene, program, rollout_result)
        value["strict_prefix_adapter_version"] = ADAPTER_VERSION_V1_5
        value["implementation_version"] = (
            "controlled_multi_future_runtime_v3_4_1"
        )
        return value


__all__ = ["RoboTwinRealSapienStrictPrefixAdapterV1_5"]
