"""Real-SAPIEN adapter for any frozen F4 template qualification candidate."""

from __future__ import annotations

from .f4_template_qualification_v1 import IMPLEMENTATION_VERSION
from .real_sapien_adapter_f4_selected_layout_v2 import (
    RoboTwinRealSapienF4SelectedLayoutV2Adapter,
)


ADAPTER_VERSION = "RoboTwinRealSapienF4TemplateQualificationV1Adapter"
GENERATOR_VERSION = "controlled_multi_future_f4_template_qualification_v1_adapter"


class RoboTwinRealSapienF4TemplateQualificationV1Adapter(
    RoboTwinRealSapienF4SelectedLayoutV2Adapter
):
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
    "ADAPTER_VERSION",
    "GENERATOR_VERSION",
    "RoboTwinRealSapienF4TemplateQualificationV1Adapter",
]
