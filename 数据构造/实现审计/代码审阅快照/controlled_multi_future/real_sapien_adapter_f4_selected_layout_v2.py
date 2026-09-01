"""Adapter identity and rendered-current visibility for F4 selected layout V2."""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from .canonical_artifact import canonical_hash_json as hash_json
from .f4_layout_candidate_search_v2 import IMPLEMENTATION_VERSION
from .real_sapien_adapter_closure_f4_v2 import (
    RoboTwinRealSapienClosureF4V2Adapter,
)
from .real_sapien_adapter_v1_1 import _entity


ADAPTER_VERSION = "RoboTwinRealSapienF4SelectedLayoutV2Adapter"
GENERATOR_VERSION = "controlled_multi_future_post_stage0_f4_selected_layout_v2_adapter"


def _per_scene_id(actor: Any) -> int:
    entity = _entity(actor)
    for name in ("get_per_scene_id", "per_scene_id"):
        value = getattr(entity, name, None)
        value = value() if callable(value) else value
        if isinstance(value, (int, np.integer)) and int(value) >= 0:
            return int(value)
    raise RuntimeError(f"actor {entity.get_name()} lacks a per-scene segmentation ID")


def _model_visible_cameras(scene) -> dict[str, Any]:
    cameras = scene.cameras
    result = {}
    if cameras.collect_wrist_camera:
        result["left_camera"] = cameras.left_camera
        result["right_camera"] = cameras.right_camera
    for camera, name in zip(cameras.static_camera_list, cameras.static_camera_name):
        if name == "head_camera" and not cameras.collect_head_camera:
            continue
        if name == "head_camera":
            result[name] = camera
    required = {"head_camera", "left_camera", "right_camera"}
    if set(result) != required:
        raise RuntimeError(
            f"F4 visibility camera set changed: {sorted(result)}"
        )
    return result


class RoboTwinRealSapienF4SelectedLayoutV2Adapter(
    RoboTwinRealSapienClosureF4V2Adapter
):
    def __init__(self, **kwargs):
        if kwargs.get("family") != "F4":
            raise ValueError("F4 selected-layout V2 adapter requires F4")
        super().__init__(**kwargs)

    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = ADAPTER_VERSION
        scene._cmf_generator_version = GENERATOR_VERSION

    def audit_current_rendered_visibility(self, scene, *, phase: str) -> dict:
        """Require every declared F4 scene role in at least one current camera.

        ``capture_current`` immediately before this call updates rendering and
        takes all three model-visible pictures.  We read the raw actor-ID
        segmentation buffer rather than the colorized helper output.
        """

        cameras = _model_visible_cameras(scene)
        actor_ids = {
            role: _per_scene_id(actor) for role, actor in scene.role_actors.items()
        }
        per_camera = {}
        role_pixels = {role: {} for role in actor_ids}
        for camera_name, camera in cameras.items():
            labels = np.asarray(camera.get_picture("Segmentation"))
            if labels.ndim != 3 or labels.shape[2] < 2:
                raise RuntimeError("F4 actor segmentation buffer shape changed")
            actor_plane = labels[..., 1].astype(np.int64, copy=False)
            per_camera[camera_name] = {
                "height": int(actor_plane.shape[0]),
                "width": int(actor_plane.shape[1]),
                "actor_plane_dtype": str(actor_plane.dtype),
                "actor_plane_sha256": hashlib.sha256(
                    np.ascontiguousarray(actor_plane).tobytes()
                ).hexdigest(),
            }
            for role, actor_id in actor_ids.items():
                role_pixels[role][camera_name] = int(np.count_nonzero(actor_plane == actor_id))
        checks = {
            "exact_model_visible_camera_set": set(per_camera)
            == {"head_camera", "left_camera", "right_camera"},
            "all_scene_roles_have_actor_ids": set(actor_ids) == set(scene.role_actors),
            "every_scene_role_has_rendered_pixels": all(
                max(counts.values(), default=0) > 0 for counts in role_pixels.values()
            ),
        }
        result = {
            "schema_version": "cmf_f4_rendered_current_actor_visibility_v2",
            "phase": str(phase),
            "required_roles": list(actor_ids),
            "actor_per_scene_ids": actor_ids,
            "role_pixel_counts_by_camera": role_pixels,
            "camera_buffers": per_camera,
            "checks": checks,
            "pass": all(checks.values()),
            "cpu_frustum_is_only_a_necessary_condition": True,
            "rendered_actor_segmentation_is_authoritative_for_visibility": True,
        }
        result["receipt_sha256"] = hash_json(result)
        return result

    def verify(self, scene, program, rollout_result):
        value = super().verify(scene, program, rollout_result)
        value["strict_prefix_adapter_version"] = ADAPTER_VERSION
        value["implementation_version"] = IMPLEMENTATION_VERSION
        return value


__all__ = [
    "ADAPTER_VERSION",
    "GENERATOR_VERSION",
    "RoboTwinRealSapienF4SelectedLayoutV2Adapter",
]
