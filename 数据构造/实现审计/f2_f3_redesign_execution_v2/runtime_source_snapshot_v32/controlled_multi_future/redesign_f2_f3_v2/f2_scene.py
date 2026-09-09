"""RoboTwin scene binding for the new F2 open-bottomed-box line."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import sapien

from envs.utils import create_box, create_visual_box
from ..probes.runtime_trace import DenseTraceMixin
from ..probes.scene_inspection import AuditScene
from .factory import build_actor, load_model_spec
from .scene import NativeAssetHandle


class RedesignF2Scene(DenseTraceMixin, AuditScene):
    family_id = "F2"

    def setup_demo(self, **kwargs):
        self._cmf_f2_layout_id = str(kwargs.pop("f2_layout_id", "v1"))
        self._cmf_scene_variant = str(kwargs.pop("scene_variant", "A"))
        if self._cmf_scene_variant not in {"A", "B"}:
            raise ValueError("scene_variant must be A or B")
        super().setup_demo(**kwargs)

    def load_actors(self):
        shift_x = 0.040 if self._cmf_scene_variant == "B" else 0.0
        source_x = -0.22 + shift_x
        can_origin_z = 0.755
        q_upright = [0.7071067811865476, 0.7071067811865476, 0.0, 0.0]
        self.box_center = np.asarray([-0.08 + shift_x, -0.18, 0.755], dtype=np.float64)
        scale_half = (0.06, 0.06, 0.005)
        stand_half = (0.05, 0.05, 0.035)
        if self._cmf_f2_layout_id in {"v2", "v3", "v4_beside_y_workspace", "v5_beside_y_lower"}:
            # Move the whole box slightly left and tighten the scale footprint
            # so scale/stand are disjoint while the three relations remain
            # inside/on/beside in the same table frame.
            box_x = -0.12 if self._cmf_f2_layout_id == "v2" else (-0.24 if self._cmf_f2_layout_id == "v5_beside_y_lower" else -0.18)
            self.box_center[0] = box_x + shift_x
            scale_half = (0.04, 0.06, 0.005)
        # Five static pieces: bottom, two side walls and two end walls.  The
        # top remains open so the closed and opened gripper sweeps are explicit.
        self.box_bottom = create_box(self, sapien.Pose(self.box_center.tolist()), (0.12, 0.12, 0.005), color=(0.35, 0.35, 0.35), is_static=True, name="f2_redesign_box_bottom")
        wall_z = 0.805
        self.box_left = create_box(self, sapien.Pose([self.box_center[0] - 0.115, self.box_center[1], wall_z]), (0.005, 0.12, 0.05), color=(0.42, 0.42, 0.42), is_static=True, name="f2_redesign_box_left_wall")
        self.box_right = create_box(self, sapien.Pose([self.box_center[0] + 0.115, self.box_center[1], wall_z]), (0.005, 0.12, 0.05), color=(0.42, 0.42, 0.42), is_static=True, name="f2_redesign_box_right_wall")
        self.box_front = create_box(self, sapien.Pose([self.box_center[0], self.box_center[1] - 0.115, wall_z]), (0.12, 0.005, 0.05), color=(0.42, 0.42, 0.42), is_static=True, name="f2_redesign_box_front_wall")
        self.box_back = create_box(self, sapien.Pose([self.box_center[0], self.box_center[1] + 0.115, wall_z]), (0.12, 0.005, 0.05), color=(0.42, 0.42, 0.42), is_static=True, name="f2_redesign_box_back_wall")
        self.box_pieces = (self.box_bottom, self.box_left, self.box_right, self.box_front, self.box_back)
        asset_root = Path("/nfs_share/lijunhui/Robotwin2/project/RoboTwin/assets")
        spec = load_model_spec(asset_root, "071_can", model_id=0, asset_id="f2_can_v2")
        entity = build_actor(self.scene, spec, sapien.Pose([source_x, 0.02, can_origin_z], q_upright), convex=True, dynamic=True, name="f2_redesign_can")
        self.can = NativeAssetHandle(entity, spec)
        self.can.set_name("f2_redesign_can")
        if self._cmf_f2_layout_id == "v2":
            self.scale_center = np.asarray([0.00 + shift_x, -0.18, 0.755], dtype=np.float64)
            self.stand_center = np.asarray([0.12 + shift_x, -0.18, 0.79], dtype=np.float64)
        elif self._cmf_f2_layout_id == "v3":
            self.scale_center = np.asarray([-0.02 + shift_x, -0.18, 0.755], dtype=np.float64)
            self.stand_center = np.asarray([0.08 + shift_x, -0.18, 0.79], dtype=np.float64)
        elif self._cmf_f2_layout_id == "v4_beside_y_workspace":
            self.scale_center = np.asarray([-0.02 + shift_x, -0.18, 0.755], dtype=np.float64)
            self.stand_center = np.asarray([0.06 + shift_x, 0.08, 0.79], dtype=np.float64)
        elif self._cmf_f2_layout_id == "v5_beside_y_lower":
            self.scale_center = np.asarray([-0.02 + shift_x, -0.18, 0.755], dtype=np.float64)
            self.stand_center = np.asarray([0.14 + shift_x, -0.06, 0.79], dtype=np.float64)
        elif self._cmf_f2_layout_id == "v1":
            self.scale_center = np.asarray([0.08 + shift_x, -0.18, 0.755], dtype=np.float64)
            self.stand_center = np.asarray([0.23 + shift_x, -0.18, 0.79], dtype=np.float64)
        else:
            raise ValueError(f"unknown F2 layout id: {self._cmf_f2_layout_id}")
        self.scale = create_box(self, sapien.Pose(self.scale_center.tolist()), scale_half, color=(0.20, 0.20, 0.20), is_static=True, name="f2_redesign_scale")
        self.stand = create_box(self, sapien.Pose(self.stand_center.tolist()), stand_half, color=(0.20, 0.20, 0.30), is_static=True, name="f2_redesign_stand")
        self.beside_target_xy = np.asarray(
            [0.06 + shift_x, -0.18] if self._cmf_f2_layout_id == "v5_beside_y_lower" else [0.06, -0.04],
            dtype=np.float64,
        )
        self.central_marker = create_visual_box(self, sapien.Pose([self.box_center[0], self.box_center[1], 0.92]), (0.01, 0.01, 0.01), color=(1, 1, 0), name="f2_redesign_marker")
        self.role_actors = {
            "main_can": self.can,
            "box_bottom": self.box_bottom,
            "box_left": self.box_left,
            "box_right": self.box_right,
            "box_front": self.box_front,
            "box_back": self.box_back,
            "scale": self.scale,
            "stand": self.stand,
            "central_marker": self.central_marker,
            "table": self.table,
            "wall": self.wall,
        }
        self._cmf_redesign_asset_spec = spec.to_receipt()
        self._cmf_f2_box_contract = {
            "schema_version": "cmf_f2_open_box_contract_v1",
            "layout_id": self._cmf_f2_layout_id,
            "interior_lower_m": [float(self.box_center[0] - 0.11), float(self.box_center[1] - 0.11), 0.755],
            "interior_upper_m": [float(self.box_center[0] + 0.11), float(self.box_center[1] + 0.11), 0.855],
            "bottom_identity": "f2_redesign_box_bottom",
            "wall_names": ["f2_redesign_box_left_wall", "f2_redesign_box_right_wall", "f2_redesign_box_front_wall", "f2_redesign_box_back_wall"],
            "dynamic_can": True,
            "whole_box_collision_disabled": False,
            "scale_center_m": self.scale_center.tolist(),
            "stand_center_m": self.stand_center.tolist(),
            "beside_target_xy_m": self.beside_target_xy.tolist(),
        }
