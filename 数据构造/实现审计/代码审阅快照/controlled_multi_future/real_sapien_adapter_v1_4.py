"""Real SAPIEN strict-prefix adapter identity for runtime-v3_4."""

from __future__ import annotations

from .real_sapien_adapter_v1_3 import RoboTwinRealSapienStrictPrefixAdapterV1_3


ADAPTER_VERSION_V1_4 = "RoboTwinRealSapienStrictPrefixAdapterV1_4"
GENERATOR_VERSION_V1_4 = "controlled_multi_future_joint_scene_v3_4_adapter_v1_4"


class RoboTwinRealSapienStrictPrefixAdapterV1_4(
    RoboTwinRealSapienStrictPrefixAdapterV1_3
):
    """Use the v3_4 family-local contracts without changing shared lifecycle."""

    @staticmethod
    def _mark_v1_3_context(scene):
        # Override the inherited marker while retaining the exact same capture
        # and lifecycle implementations.
        scene._cmf_adapter_version = ADAPTER_VERSION_V1_4
        scene._cmf_generator_version = GENERATOR_VERSION_V1_4

    def verify(self, scene, program, rollout_result):
        value = super().verify(scene, program, rollout_result)
        value["strict_prefix_adapter_version"] = ADAPTER_VERSION_V1_4
        value["implementation_version"] = "controlled_multi_future_runtime_v3_4"
        return value


__all__ = ["RoboTwinRealSapienStrictPrefixAdapterV1_4"]
