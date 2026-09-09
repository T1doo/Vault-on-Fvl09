"""RoboTwin scene binding for the new F3 vertical bottle line."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
import sapien

from envs.utils import create_box, create_visual_box
from ..probes.runtime_trace import DenseTraceMixin
from ..probes.scene_inspection import AuditScene
from .factory import ModelSpec, build_actor, load_model_spec


class NativeAssetHandle:
    """Small read-only compatibility handle around a native SAPIEN entity."""

    def __init__(self, entity: Any, spec: ModelSpec):
        self.actor = entity
        self.spec = spec
        self.config = {
            "center": list(spec.center),
            "extents": list(spec.unscaled_extents),
            "scale": list(spec.effective_scale),
            "contact_points_pose": [self._local_matrix(spec.semantic_points.get("contact_0", (0.0, 0.0, 0.0)))],
            "functional_matrix": [self._local_matrix(spec.semantic_points.get("functional_0", (0.0, 0.0, 0.0)))],
        }

    @staticmethod
    def _local_matrix(point):
        matrix = np.eye(4, dtype=np.float64)
        matrix[:3, 3] = np.asarray(point, dtype=np.float64)
        return matrix.tolist()

    def get_pose(self):
        return self.actor.get_pose()

    def get_name(self):
        return self.actor.get_name()

    def set_name(self, name):
        self.actor.set_name(name)

    def get_contact_point(self, index: int, ret: str = "list"):
        if index != 0:
            return None
        local = np.asarray(self.config["contact_points_pose"][0], dtype=np.float64)
        world = self.actor.get_pose().to_transformation_matrix() @ local
        if ret == "matrix":
            return world
        if ret == "list":
            import transforms3d as t3d

            return world[:3, 3].tolist() + t3d.quaternions.mat2quat(world[:3, :3]).tolist()
        import transforms3d as t3d

        return sapien.Pose(world[:3, 3], t3d.quaternions.mat2quat(world[:3, :3]))

    def iter_contact_points(self, ret: str = "list"):
        yield 0, self.get_contact_point(0, ret)

    def get_functional_point(self, index: int = 0, ret: str = "list"):
        local = np.asarray(self.config["functional_matrix"][0], dtype=np.float64)
        world = self.actor.get_pose().to_transformation_matrix() @ local
        if ret == "matrix":
            return world
        if ret == "list":
            import transforms3d as t3d

            return world[:3, 3].tolist() + t3d.quaternions.mat2quat(world[:3, :3]).tolist()
        import transforms3d as t3d

        return sapien.Pose(world[:3, 3], t3d.quaternions.mat2quat(world[:3, :3]))


class RedesignF3Scene(DenseTraceMixin, AuditScene):
    """Base_Task robot scene with a new native 114_bottle:model_data1 asset."""

    family_id = "F3"

    def setup_demo(self, **kwargs):
        self._cmf_scene_variant = str(kwargs.pop("scene_variant", "A"))
        if self._cmf_scene_variant not in {"A", "B"}:
            raise ValueError("scene_variant must be A or B")
        super().setup_demo(**kwargs)

    def load_actors(self):
        shift_x = 0.040 if self._cmf_scene_variant == "B" else 0.0
        source_x = -0.18 + shift_x
        pad_center_z = 0.745
        self.pad = create_box(
            self,
            sapien.Pose([source_x, -0.06, pad_center_z]),
            (0.075, 0.075, 0.005),
            color=(0.4, 0.4, 0.4),
            is_static=True,
            name="f3_redesign_support_pad",
        )
        asset_root = Path("/nfs_share/lijunhui/Robotwin2/project/RoboTwin/assets")
        spec = load_model_spec(asset_root, "114_bottle", model_id=1, asset_id="f3_bottle_v1")
        # model_data1's long axis is local Y; rotate it upright into table Z.
        pose = sapien.Pose([source_x, -0.06, pad_center_z + 0.005], [0.7071067811865476, 0.7071067811865476, 0.0, 0.0])
        entity = build_actor(self.scene, spec, pose, convex=True, dynamic=True, name="f3_redesign_bottle")
        self.bottle = NativeAssetHandle(entity, spec)
        self.bottle.set_name("f3_redesign_bottle")
        self.central_marker = create_visual_box(
            self,
            sapien.Pose([shift_x, -0.05, 0.95]),
            (0.015, 0.015, 0.015),
            color=(1, 1, 0),
            name="f3_redesign_central_marker",
        )
        self.role_actors = {
            "original_pad": self.pad,
            "bottle": self.bottle,
            "central_marker": self.central_marker,
            "table": self.table,
            "wall": self.wall,
        }
        self._cmf_redesign_asset_spec = spec.to_receipt()
