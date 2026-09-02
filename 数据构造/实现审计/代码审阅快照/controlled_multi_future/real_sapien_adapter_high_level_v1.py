"""Real-scene adapters for high-level candidate qualification.

The adapters only bind scene identity, assets, layout, and rendered-current
evidence.  Candidate execution is performed by the bounded high-level runners,
not by the legacy family root controllers.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json
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
RENDER_DEVICE_BINDING_SCHEMA = "cmf_sapien_render_device_binding_v1"


def _normalize_pci_bus_id(value: str) -> str:
    parts = str(value).strip().lower().split(":")
    if len(parts) != 3 or "." not in parts[2]:
        raise ValueError("invalid PCI bus ID")
    domain = parts[0][-4:].zfill(4)
    bus = parts[1].zfill(2)
    device, function = parts[2].split(".", 1)
    return f"{domain}:{bus}:{device.zfill(2)}.{function}"


def _selected_nvidia_device_v1() -> dict[str, Any]:
    expected_uuid = os.environ.get("CUDA_VISIBLE_DEVICES")
    physical_text = os.environ.get("CMF_GPU_GUARD_PHYSICAL_INDEX")
    if not expected_uuid or physical_text is None:
        raise RuntimeError("render binding lacks Guard GPU environment")
    physical_index = int(physical_text)
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,uuid,pci.bus_id",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
    )
    rows = []
    for line in completed.stdout.splitlines():
        fields = [item.strip() for item in line.split(",")]
        if len(fields) != 3:
            raise RuntimeError("nvidia-smi render binding row changed")
        rows.append(
            {
                "physical_index": int(fields[0]),
                "uuid": fields[1],
                "pci_bus_id": _normalize_pci_bus_id(fields[2]),
            }
        )
    matches = [
        item
        for item in rows
        if item["physical_index"] == physical_index
        and item["uuid"] == expected_uuid
    ]
    if len(matches) != 1:
        raise RuntimeError("Guard physical index/UUID does not map to one PCI device")
    return matches[0]


def _build_render_device_binding_receipt_v1(
    *,
    selected: Mapping[str, Any],
    device: Any,
    legacy_renderer_pinned: bool,
) -> dict[str, Any]:
    actual_pci = _normalize_pci_bus_id(device.pci_string)
    checks = {
        "logical_device_alias_is_cuda_0": True,
        "render_device_can_render": device.can_render() is True,
        "render_device_is_cuda": device.is_cuda() is True,
        "render_device_pci_matches_selected_uuid_pci": actual_pci
        == selected["pci_bus_id"],
        "legacy_sapien_renderer_pinned_to_logical_cuda_0":
        legacy_renderer_pinned is True,
    }
    value = {
        "schema_version": RENDER_DEVICE_BINDING_SCHEMA,
        "logical_device_alias": "cuda:0",
        "selected_physical_gpu_index": selected["physical_index"],
        "selected_gpu_uuid": selected["uuid"],
        "selected_gpu_pci_bus_id": selected["pci_bus_id"],
        "render_device_name": device.name,
        "render_device_cuda_id": int(device.cuda_id),
        "render_device_pci_bus_id": actual_pci,
        "legacy_sapien_renderer_pinned": bool(legacy_renderer_pinned),
        "checks": checks,
        "pass": all(checks.values()),
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


class _PinnedSapienRenderDeviceContextV1:
    def __init__(self, inner):
        self.inner = inner

    @property
    def cleanup_receipt(self):
        return self.inner.cleanup_receipt

    def __enter__(self):
        import sapien.core as sapien

        selected = _selected_nvidia_device_v1()
        original_create_scene = sapien.Engine.create_scene
        original_legacy_renderer = sapien.SapienRenderer
        created: dict[str, Any] = {}

        def create_legacy_renderer_on_selected_device(*args, **kwargs):
            if args or kwargs:
                raise RuntimeError(
                    "legacy SapienRenderer arguments changed from reviewed Base_Task"
                )
            created["legacy_renderer_pinned"] = True
            return sapien.render.SapienRenderer(sapien.Device("cuda:0"))

        def create_scene_on_selected_device(engine, config):
            sapien.physx.set_scene_config(config)
            device = sapien.Device("cuda:0")
            render_system = sapien.render.RenderSystem(device)
            binding = _build_render_device_binding_receipt_v1(
                selected=selected,
                device=render_system.device,
                legacy_renderer_pinned=created.get(
                    "legacy_renderer_pinned", False
                ),
            )
            if binding["pass"] is not True:
                raise RuntimeError("SAPIEN render device differs from selected Guard GPU")
            created["binding"] = binding
            return sapien.Scene(
                [sapien.physx.PhysxCpuSystem(), render_system]
            )

        sapien.SapienRenderer = create_legacy_renderer_on_selected_device
        sapien.Engine.create_scene = create_scene_on_selected_device
        try:
            handle = self.inner.__enter__()
        finally:
            sapien.Engine.create_scene = original_create_scene
            sapien.SapienRenderer = original_legacy_renderer
        binding = created.get("binding")
        if not isinstance(binding, Mapping) or binding.get("pass") is not True:
            self.inner.__exit__(RuntimeError, RuntimeError("missing render binding"), None)
            raise RuntimeError("SAPIEN scene lacks selected render-device binding")
        handle.scene._cmf_render_device_binding_v1 = dict(binding)
        return handle

    def __exit__(self, exc_type, exc, tb):
        return self.inner.__exit__(exc_type, exc, tb)


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

    def scene(self, planned_root_slot_spec, *, phase, program=None):
        inner = super().scene(
            planned_root_slot_spec, phase=phase, program=program
        )
        return _PinnedSapienRenderDeviceContextV1(inner)


__all__ = [
    "F2_ADAPTER_VERSION",
    "F3_ADAPTER_VERSION",
    "F4_ADAPTER_VERSION",
    "RENDER_DEVICE_BINDING_SCHEMA",
    "RoboTwinRealSapienF2HierarchicalStageAV1Adapter",
    "RoboTwinRealSapienF3AssetGraspV2Adapter",
    "RoboTwinRealSapienF4HierarchicalStageAV1Adapter",
    "_PinnedSapienRenderDeviceContextV1",
    "_build_render_device_binding_receipt_v1",
    "_normalize_pci_bus_id",
    "_selected_nvidia_device_v1",
]
