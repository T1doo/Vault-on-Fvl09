"""Render and inspect one deterministic nonformal F1--F4 joint scene."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
import traceback

import numpy as np
from PIL import Image
import sapien
import yaml

from envs._GLOBAL_CONFIGS import CONFIGS_PATH
from envs._base_task import Base_Task
from envs.utils import create_actor, create_box, create_visual_box, rand_create_sapien_urdf_obj
from .lifecycle import cleanup_status, initialize_cleanup_fields, managed_scene


def _embodiment_config(robot_file):
    with open(Path(robot_file) / "config.yml", "r", encoding="utf-8") as handle:
        return yaml.load(handle.read(), Loader=yaml.FullLoader)


def _args(family: str, output: Path):
    with open(Path(CONFIGS_PATH) / "demo_clean.yml", "r", encoding="utf-8") as handle:
        args = yaml.load(handle.read(), Loader=yaml.FullLoader)
    with open(Path(CONFIGS_PATH) / "_embodiment_config.yml", "r", encoding="utf-8") as handle:
        embodiments = yaml.load(handle.read(), Loader=yaml.FullLoader)
    robot_file = embodiments["aloha-agilex"]["file_path"]
    args.update({
        "task_name": f"cmf_{family.lower()}_scene_inspection",
        "task_config": "nonformal_audit_probe",
        "save_path": str(output),
        "now_ep_num": 0,
        "seed": 20260827,
        "need_plan": True,
        "save_data": False,
        "collect_data": False,
        "render_freq": 0,
        "save_freq": None,
        "left_robot_file": robot_file,
        "right_robot_file": robot_file,
        "dual_arm_embodied": True,
        "embodiment_name": "aloha-agilex",
        "left_embodiment_config": _embodiment_config(robot_file),
        "right_embodiment_config": _embodiment_config(robot_file),
    })
    return args


class AuditScene(Base_Task):
    family_id = "unset"

    def setup_demo(self, **kwargs):
        super()._init_task_env_(**kwargs)

    def _box(self, name, xyz, color, half=0.022, static=False):
        actor = create_box(self, sapien.Pose(xyz), (half, half, half), color=color, is_static=static, name=name)
        actor.set_name(name)
        return actor

    def runtime_actor_info(self):
        info = {}
        for role, actor in self.role_actors.items():
            entity = actor.actor if hasattr(actor, "actor") else actor
            components = []
            for component in entity.get_components():
                item = {"type": type(component).__name__}
                if hasattr(component, "mass"):
                    item["mass"] = float(component.mass)
                if hasattr(component, "get_collision_shapes"):
                    item["collision_shape_count"] = len(component.get_collision_shapes())
                components.append(item)
            pose = entity.get_pose()
            info[role] = {"name": entity.get_name(), "pose": pose.p.tolist() + pose.q.tolist(), "components": components}
        return info


class F1Scene(AuditScene):
    family_id = "F1"

    def load_actors(self):
        self.red = self._box("f1_red_block", [-0.20, 0.02, 0.762], (1, 0, 0))
        self.green = self._box("f1_green_block", [-0.11, 0.02, 0.762], (0, 1, 0))
        self.blue = self._box("f1_blue_block", [-0.02, 0.02, 0.762], (0, 0, 1))
        self.box = create_actor(self, sapien.Pose([-0.08, -0.16, 0.78], [0.5, 0.5, 0.5, 0.5]), "062_plasticbox", convex=True, is_static=True, model_id=3)
        self.box.set_name("f1_common_plasticbox")
        self.role_actors = {"red": self.red, "green": self.green, "blue": self.blue, "common_box": self.box}


class F2Scene(AuditScene):
    family_id = "F2"

    def load_actors(self):
        q = [0.5, 0.5, 0.5, 0.5]
        self.can = create_actor(self, sapien.Pose([-0.24, 0.03, 0.79], q), "071_can", convex=True, model_id=1)
        self.can.set_name("f2_main_can")
        self.can.set_mass(0.05)
        self.box = create_actor(self, sapien.Pose([-0.17, -0.17, 0.78], q), "062_plasticbox", convex=True, is_static=True, model_id=3)
        self.box.set_name("f2_plasticbox")
        self.scale = create_actor(self, sapien.Pose([0.00, -0.17, 0.77], q), "072_electronicscale", convex=True, is_static=True, model_id=0)
        self.scale.set_name("f2_scale")
        self.stand = create_actor(self, sapien.Pose([0.17, -0.17, 0.77], [0.707, 0.707, 0, 0]), "074_displaystand", convex=True, is_static=True, model_id=3)
        self.stand.set_name("f2_stand")
        self.role_actors = {"main_can": self.can, "box": self.box, "scale": self.scale, "stand": self.stand}


class F2PotScene(AuditScene):
    family_id = "F2"

    def load_actors(self):
        q = [0.5, 0.5, 0.5, 0.5]
        self.can = create_actor(self, sapien.Pose([-0.24, 0.03, 0.79], q), "071_can", convex=True, model_id=1)
        self.can.set_name("f2_main_can")
        self.can.set_mass(0.05)
        self.box = create_actor(self, sapien.Pose([-0.17, -0.17, 0.78], q), "062_plasticbox", convex=True, is_static=True, model_id=3)
        self.box.set_name("f2_plasticbox")
        self.scale = create_actor(self, sapien.Pose([0.00, -0.17, 0.77], q), "072_electronicscale", convex=True, is_static=True, model_id=0)
        self.scale.set_name("f2_scale")
        self.pot = rand_create_sapien_urdf_obj(
            scene=self,
            modelname="060_kitchenpot",
            modelid=0,
            xlim=[0.18, 0.18],
            ylim=[0.02, 0.02],
            qpos=[0, 0, 0, 1],
            rotate_rand=False,
            fix_root_link=True,
        )
        self.pot.set_name("f2_reference_kitchenpot")
        self.role_actors = {"main_can": self.can, "box": self.box, "scale": self.scale, "pot": self.pot}


class F3Scene(AuditScene):
    family_id = "F3"

    def load_actors(self):
        self.pad = create_box(self, sapien.Pose([-0.18, -0.06, 0.745]), (0.07, 0.07, 0.005), color=(0.4, 0.4, 0.4), is_static=True, name="f3_original_pad")
        self.bottle = create_actor(self, sapien.Pose([-0.18, -0.06, 0.785], [0, 0, 1, 0]), "001_bottle", convex=True, model_id=13)
        self.bottle.set_name("f3_main_bottle")
        self.bottle.set_mass(0.01)
        self.central_marker = create_visual_box(self, sapien.Pose([0.0, -0.05, 0.95]), (0.015, 0.015, 0.015), color=(1, 1, 0), name="f3_central_marker")
        self.role_actors = {"original_pad": self.pad, "bottle": self.bottle, "central_marker": self.central_marker}


class F4Scene(AuditScene):
    family_id = "F4"

    def load_actors(self):
        self.common_x = self._box("f4_common_x", [-0.25, 0.06, 0.762], (1, 1, 0))
        self.a = self._box("f4_object_a", [-0.15, 0.06, 0.762], (1, 0, 0))
        self.b = self._box("f4_object_b", [-0.05, 0.06, 0.762], (0, 1, 0))
        self.c = self._box("f4_object_c", [0.05, 0.06, 0.762], (0, 0, 1))
        self.tray = create_actor(self, sapien.Pose([0.23, 0.02, 0.76], [0.706527, 0.706483, -0.0291356, -0.0291767]), "008_tray", convex=True, is_static=True, model_id=0)
        self.tray.set_name("f4_common_tray")
        self.slot_a = create_visual_box(self, sapien.Pose([-0.15, -0.17, 0.742]), (0.035, 0.035, 0.002), color=(0.7, 0.2, 0.2), name="f4_slot_a")
        self.slot_b = create_visual_box(self, sapien.Pose([0.0, -0.17, 0.742]), (0.035, 0.035, 0.002), color=(0.2, 0.7, 0.2), name="f4_slot_b")
        self.slot_c = create_visual_box(self, sapien.Pose([0.15, -0.17, 0.742]), (0.035, 0.035, 0.002), color=(0.2, 0.2, 0.7), name="f4_slot_c")
        self.role_actors = {"common_x": self.common_x, "A": self.a, "B": self.b, "C": self.c, "common_tray": self.tray, "slot_A": self.slot_a, "slot_B": self.slot_b, "slot_C": self.slot_c}


SCENES = {"F1": F1Scene, "F2": F2Scene, "F2_POT": F2PotScene, "F3": F3Scene, "F4": F4Scene}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=tuple(SCENES), required=True)
    parser.add_argument("--physical-index", type=int, choices=tuple(range(8)), required=True)
    parser.add_argument("--expected-uuid", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    receipt = {"schema_version": "cmf_scene_inspection_v2", "purpose": "implementation_audit", "formal_data": False, "stage0_data": False, "attempt_limit": 1, "timeout_seconds": 600, "family": args.family, "physical_gpu_index": args.physical_index, "expected_gpu_uuid": args.expected_uuid, "pid": os.getpid(), "status": "running"}
    initialize_cleanup_fields(receipt)
    try:
        if os.environ.get("CUDA_VISIBLE_DEVICES") != args.expected_uuid:
            raise RuntimeError("CUDA_VISIBLE_DEVICES does not match expected UUID")
        args.output.mkdir(parents=True, exist_ok=False)
        with managed_scene(SCENES[args.family], _args(args.family, args.output), receipt, args.family) as scene:
            scene._update_render()
            scene.cameras.update_picture()
            rgb = scene.cameras.get_rgb()
            image_files = {}
            for camera_name, camera_data in rgb.items():
                if camera_name in ("head_camera", "front_camera"):
                    path = args.output / f"{camera_name}.png"
                    Image.fromarray(camera_data["rgb"]).save(path)
                    image_files[camera_name] = str(path)
            receipt.update({"status": "passed_nonformal_scene_inspection", "images": image_files, "runtime_actor_info": scene.runtime_actor_info(), "camera_names": sorted(rgb), "scene_timestep": 1 / 250, "partial_output_status": "images_and_runtime_actor_info_complete"})
        code = 0
    except BaseException as exc:
        receipt.update({"status": "failed_nonformal_scene_inspection", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        code = 1
    finally:
        receipt["status"] = cleanup_status(receipt, receipt["status"])
        receipt["elapsed_seconds"] = time.time() - started
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
