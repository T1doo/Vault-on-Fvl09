"""Real-scene adapters for high-level candidate qualification.

The adapters only bind scene identity, assets, layout, and rendered-current
evidence.  Candidate execution is performed by the bounded high-level runners,
not by the legacy family root controllers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .f2_official_asset_compatibility_matrix_v3 import (
    validate_frozen_asset_layout_binding_v3,
)
from .high_level_runtime_specs_v1 import (
    IMPLEMENTATION_VERSION,
    validate_f2_runtime_spec_v1,
    validate_f3_runtime_spec_v1,
    validate_f4_runtime_spec_v1,
)
from .real_sapien_adapter_f4_selected_layout_v2 import (
    RoboTwinRealSapienF4SelectedLayoutV2Adapter,
)
from .real_sapien_adapter_v1_2 import _asset_hash_v1_2
from .real_sapien_adapter_v1_5 import RoboTwinRealSapienStrictPrefixAdapterV1_5


F2_ADAPTER_VERSION = "RoboTwinRealSapienF2HierarchicalStageAV1Adapter"
F3_ADAPTER_VERSION = "RoboTwinRealSapienF3AssetGraspV2Adapter"
F4_ADAPTER_VERSION = "RoboTwinRealSapienF4HierarchicalStageAV1Adapter"


class _HighLevelSpecBindingMixin:
    planned_spec: dict[str, Any]

    def scene(self, planned_root_slot_spec, *, phase, program=None):
        if dict(planned_root_slot_spec) != self.planned_spec:
            raise ValueError("high-level adapter scene spec differs from constructor binding")
        return super().scene(
            planned_root_slot_spec, phase=phase, program=program
        )


class RoboTwinRealSapienF2HierarchicalStageAV1Adapter(
    _HighLevelSpecBindingMixin, RoboTwinRealSapienStrictPrefixAdapterV1_5
):
    def __init__(
        self,
        *,
        output_root: Path,
        expected_implementation_source_sha256: str,
        planned_spec: Mapping[str, Any],
    ):
        self.planned_spec = validate_f2_runtime_spec_v1(planned_spec)
        self.f2_binding = validate_frozen_asset_layout_binding_v3(
            self.planned_spec["f2_asset_layout_binding_v3"]
        )
        super().__init__(
            family="F2",
            output_root=output_root,
            expected_implementation_source_sha256=expected_implementation_source_sha256,
        )

    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = F2_ADAPTER_VERSION
        scene._cmf_generator_version = IMPLEMENTATION_VERSION

    def _entity_payloads(self, scene):
        payloads = super()._entity_payloads(scene)
        key = self.f2_binding["selected_candidate_key"]
        role_specs = {
            "main_can": ("071_can", key["main_object_model_id"]),
            "box": ("062_plasticbox", key["plastic_box_model_id"]),
            "scale": ("072_electronicscale", key["electronic_scale_model_id"]),
            "stand": ("074_displaystand", key["beside_reference_model_id"]),
        }
        for role, (modelname, model_id) in role_specs.items():
            spec = {
                "modelname": modelname,
                "model_id": int(model_id),
                "collision_mode": "multiple_convex",
            }
            payloads[role]["modelname"] = modelname
            payloads[role]["model_id"] = int(model_id)
            payloads[role]["visual_asset_hash"] = _asset_hash_v1_2(spec, "visual")
            payloads[role]["collision_asset_hash"] = _asset_hash_v1_2(
                spec, "collision"
            )
        return payloads


class RoboTwinRealSapienF3AssetGraspV2Adapter(
    _HighLevelSpecBindingMixin, RoboTwinRealSapienStrictPrefixAdapterV1_5
):
    def __init__(
        self,
        *,
        output_root: Path,
        expected_implementation_source_sha256: str,
        planned_spec: Mapping[str, Any],
    ):
        self.planned_spec = validate_f3_runtime_spec_v1(planned_spec)
        self.f3_tuple = self.planned_spec["f3_asset_grasp_tuple_v2"]
        super().__init__(
            family="F3",
            output_root=output_root,
            expected_implementation_source_sha256=expected_implementation_source_sha256,
        )

    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = F3_ADAPTER_VERSION
        scene._cmf_generator_version = IMPLEMENTATION_VERSION

    def _entity_payloads(self, scene):
        payloads = super()._entity_payloads(scene)
        asset = self.f3_tuple["asset"]
        spec = {
            "modelname": asset["modelname"],
            "model_id": int(asset["model_id"]),
            "collision_mode": "multiple_convex",
        }
        payloads["bottle"]["modelname"] = asset["modelname"]
        payloads["bottle"]["model_id"] = int(asset["model_id"])
        payloads["bottle"]["visual_asset_hash"] = _asset_hash_v1_2(spec, "visual")
        payloads["bottle"]["collision_asset_hash"] = _asset_hash_v1_2(
            spec, "collision"
        )
        return payloads


class RoboTwinRealSapienF4HierarchicalStageAV1Adapter(
    _HighLevelSpecBindingMixin, RoboTwinRealSapienF4SelectedLayoutV2Adapter
):
    def __init__(
        self,
        *,
        output_root: Path,
        expected_implementation_source_sha256: str,
        planned_spec: Mapping[str, Any],
    ):
        self.planned_spec = validate_f4_runtime_spec_v1(planned_spec)
        self.f4_candidate = self.planned_spec["f4_source_grasp_candidate_v1"]
        super().__init__(
            family="F4",
            output_root=output_root,
            expected_implementation_source_sha256=expected_implementation_source_sha256,
        )

    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = F4_ADAPTER_VERSION
        scene._cmf_generator_version = IMPLEMENTATION_VERSION


__all__ = [
    "F2_ADAPTER_VERSION",
    "F3_ADAPTER_VERSION",
    "F4_ADAPTER_VERSION",
    "RoboTwinRealSapienF2HierarchicalStageAV1Adapter",
    "RoboTwinRealSapienF3AssetGraspV2Adapter",
    "RoboTwinRealSapienF4HierarchicalStageAV1Adapter",
]
