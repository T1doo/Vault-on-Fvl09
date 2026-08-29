"""Concrete RoboTwin/SAPIEN adapter for runtime-v3_1.

Importing this module does not construct a renderer or initialize CUDA.  SAPIEN
scene classes are imported lazily inside the scene context.  GPU execution is
still disabled by the runtime-v3_1 authorization contract.
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import traceback
from typing import Any, Mapping

import numpy as np

from .anchor import capture_physical_anchor_v2
from .current_hasher import build_current_hashes_v2, hash_json
from .families import F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from .probes.runtime_trace import _dual_entity_values, _gripper_joint_qpos, _rigid_velocity
from .root_orchestrator_v1_1 import RealSapienPilotRootAdapterV1_1, SceneHandleV1_1


SOURCE_COMMIT = "c3ddfa8b97d5519efa828b075999bd0006778e5e"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


FAMILY_CLASSES = {
    "F1": F1ObjectSelection,
    "F2": F2TargetRelation,
    "F3": F3MotionOrder,
    "F4": F4SubtaskOrder,
}


ROLE_ASSETS = {
    "F1": {
        "red": {"modelname": "project_rgb_block", "model_id": "red", "static_or_dynamic": "dynamic", "collision_mode": "box"},
        "green": {"modelname": "project_rgb_block", "model_id": "green", "static_or_dynamic": "dynamic", "collision_mode": "box"},
        "blue": {"modelname": "project_rgb_block", "model_id": "blue", "static_or_dynamic": "dynamic", "collision_mode": "box"},
        "common_box": {"modelname": "062_plasticbox", "model_id": 3, "static_or_dynamic": "static", "collision_mode": "multiple_convex"},
    },
    "F2": {
        "main_can": {"modelname": "071_can", "model_id": 1, "static_or_dynamic": "dynamic", "collision_mode": "multiple_convex"},
        "box": {"modelname": "062_plasticbox", "model_id": 2, "static_or_dynamic": "static", "collision_mode": "multiple_convex"},
        "scale": {"modelname": "072_electronicscale", "model_id": 0, "static_or_dynamic": "static", "collision_mode": "multiple_convex"},
        "stand": {"modelname": "074_displaystand", "model_id": 3, "static_or_dynamic": "static", "collision_mode": "multiple_convex"},
    },
    "F3": {
        "original_pad": {"modelname": "project_pad_box", "model_id": "f3_pad", "static_or_dynamic": "static", "collision_mode": "box"},
        "bottle": {"modelname": "001_bottle", "model_id": 13, "static_or_dynamic": "dynamic", "collision_mode": "multiple_convex"},
        "central_marker": {"modelname": "project_visual_marker", "model_id": "f3_center", "static_or_dynamic": "kinematic", "collision_mode": "visual_only"},
    },
    "F4": {
        "common_x": {"modelname": "project_rgb_block", "model_id": "yellow", "static_or_dynamic": "dynamic", "collision_mode": "box"},
        "A": {"modelname": "project_rgb_block", "model_id": "red", "static_or_dynamic": "dynamic", "collision_mode": "box"},
        "B": {"modelname": "project_rgb_block", "model_id": "green", "static_or_dynamic": "dynamic", "collision_mode": "box"},
        "C": {"modelname": "project_rgb_block", "model_id": "blue", "static_or_dynamic": "dynamic", "collision_mode": "box"},
        "common_tray": {"modelname": "008_tray", "model_id": 0, "static_or_dynamic": "static", "collision_mode": "multiple_convex"},
        "slot_A": {"modelname": "project_visual_slot", "model_id": "A", "static_or_dynamic": "kinematic", "collision_mode": "visual_only"},
        "slot_B": {"modelname": "project_visual_slot", "model_id": "B", "static_or_dynamic": "kinematic", "collision_mode": "visual_only"},
        "slot_C": {"modelname": "project_visual_slot", "model_id": "C", "static_or_dynamic": "kinematic", "collision_mode": "visual_only"},
    },
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def implementation_source_sha256() -> str:
    digest = hashlib.sha256()
    source_root = Path(__file__).resolve().parent
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(source_root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _asset_hash(modelname: str, model_id: Any, kind: str) -> str:
    if modelname.startswith("project_"):
        return hash_json({"source": "RoboTwin create_box/create_visual_box", "modelname": modelname, "model_id": model_id, "kind": kind})
    root = PROJECT_ROOT / "assets" / "objects" / modelname
    candidates = [
        root / kind / f"base{model_id}.glb",
        root / kind / f"textured{model_id}.obj",
        root / f"base{model_id}.glb",
        root / f"textured{model_id}.obj",
    ]
    path = next((item for item in candidates if item.is_file()), None)
    if path is None:
        raise FileNotFoundError(f"no {kind} asset for {modelname}/base{model_id}")
    return _sha256_file(path)


def _entity(actor):
    return actor.actor if hasattr(actor, "actor") else actor


def _pose(actor) -> list[float]:
    value = actor.get_pose()
    return np.asarray(value.p.tolist() + value.q.tolist(), dtype=np.float64).tolist()


def _dynamic_component(actor):
    entity = _entity(actor)
    for component in entity.get_components():
        if hasattr(component, "mass") and hasattr(component, "is_sleeping"):
            return component
    return None


def _planner_process_ids(scene) -> set[int]:
    robot = getattr(scene, "robot", None)
    result = set()
    if robot is not None:
        for name in ("left_proc", "right_proc"):
            process = getattr(robot, name, None)
            if process is not None and process.pid is not None:
                result.add(int(process.pid))
    return result


def _stop_owned_planner_processes(scene) -> list[int]:
    robot = getattr(scene, "robot", None)
    remaining = []
    if robot is None:
        return remaining
    for arm in ("left", "right"):
        process = getattr(robot, f"{arm}_proc", None)
        connection = getattr(robot, f"{arm}_conn", None)
        if process is None:
            continue
        if process.is_alive() and connection is not None:
            try:
                connection.send({"cmd": "exit"})
            except BaseException:
                pass
        process.join(timeout=5)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
        if process.is_alive():
            remaining.append(int(process.pid))
    return remaining


class RoboTwinSceneContextV1_1:
    """Unique scene lifecycle with scene-bound cleanup evidence."""

    counter = 0

    def __init__(self, *, family: str, planned_spec: Mapping[str, Any], phase: str, program, output_root: Path):
        type(self).counter += 1
        self.family = family
        self.phase = phase
        self.program = program
        self.planned_spec = dict(planned_spec)
        self.output_root = output_root
        self.scene_instance_id = f"{family.lower()}-{phase.replace(':', '_')}-{type(self).counter:06d}"
        self.handle = SceneHandleV1_1(scene_instance_id=self.scene_instance_id)
        self.cleanup_receipt = None
        self._scene = None

    def __enter__(self):
        from .probes.action_feasibility_v2 import _scene_resources

        scenes, scene_args = _scene_resources()
        scene = None
        try:
            scene = scenes[self.family]()
            self._scene = scene
            args = scene_args(self.family, self.output_root / self.scene_instance_id)
            args["seed"] = int(self.planned_spec["seed"])
            scene._cmf_planned_root_slot_spec = deepcopy(self.planned_spec)
            scene.setup_demo(**args)
            for _ in range(60):
                scene.scene.step()
            scene._cmf_setup_kwargs = dict(args)
            scene._cmf_canonical_settle_steps = 60
            scene._cmf_scene_instance_id = self.scene_instance_id
            self.handle.scene = scene
            return self.handle
        except BaseException:
            cleanup_error = None
            remaining = []
            if scene is not None:
                try:
                    remaining = _stop_owned_planner_processes(scene)
                    scene.close_env(clear_cache=True)
                except BaseException as cleanup_exc:
                    cleanup_error = {"type": type(cleanup_exc).__name__, "message": str(cleanup_exc), "traceback": traceback.format_exc()}
            self.cleanup_receipt = {
                "scene_instance_id": self.scene_instance_id,
                "scene_created": scene is not None,
                "scene_cleanup_attempted": scene is not None,
                "scene_cleanup_succeeded": scene is not None and cleanup_error is None and not remaining,
                "cleanup_safety_pass": cleanup_error is None and not remaining,
                "orphan_process_count": len(remaining),
                "cleanup_error": cleanup_error,
                "failure_phase": "scene_enter",
            }
            self.handle.cleanup_receipt = dict(self.cleanup_receipt)
            raise

    def __exit__(self, exc_type, exc, tb):
        cleanup_error = None
        remaining = []
        attempted = self._scene is not None
        if self._scene is not None:
            try:
                remaining = _stop_owned_planner_processes(self._scene)
                self._scene.close_env(clear_cache=True)
            except BaseException as cleanup_exc:
                cleanup_error = {"type": type(cleanup_exc).__name__, "message": str(cleanup_exc), "traceback": traceback.format_exc()}
        self.cleanup_receipt = {
            "scene_instance_id": self.scene_instance_id,
            "scene_created": self._scene is not None,
            "scene_cleanup_attempted": attempted,
            "scene_cleanup_succeeded": attempted and cleanup_error is None and not remaining,
            "cleanup_safety_pass": attempted and cleanup_error is None and not remaining,
            "orphan_process_count": len(remaining),
            "cleanup_error": cleanup_error,
            "owned_planner_process_ids": sorted(_planner_process_ids(self._scene)) if self._scene is not None else [],
            "outer_gpu_release_audit_required": True,
        }
        self.handle.cleanup_receipt = dict(self.cleanup_receipt)
        return False


class RoboTwinRealSapienPilotRootAdapterV1_1(RealSapienPilotRootAdapterV1_1):
    """Concrete adapter; family behavior is delegated to reviewed v3_1 runners."""

    def __init__(self, *, family: str, output_root: Path):
        if family not in FAMILY_CLASSES:
            raise ValueError(f"unsupported family {family}")
        self.family = family
        self.output_root = Path(output_root)
        from .family_runners_v3_1 import get_family_runner

        self.runner = get_family_runner(family)

    def scene(self, planned_root_slot_spec, *, phase, program=None):
        if planned_root_slot_spec.get("family") != self.family:
            raise ValueError("planned root family does not match adapter")
        return RoboTwinSceneContextV1_1(
            family=self.family,
            planned_spec=planned_root_slot_spec,
            phase=phase,
            program=program,
            output_root=self.output_root,
        )

    def _entity_payloads(self, scene):
        registry = ROLE_ASSETS[self.family]
        payloads = {}
        for role, actor in scene.role_actors.items():
            spec = registry[role]
            dynamic = _dynamic_component(actor)
            linear, linear_measured = _rigid_velocity(actor, "linear_velocity")
            angular, angular_measured = _rigid_velocity(actor, "angular_velocity")
            config = getattr(actor, "config", None) or {}
            scale = config.get("scale", [1, 1, 1])
            scale = np.asarray(scale, dtype=np.float64).reshape(-1)
            if scale.size == 1:
                scale = np.repeat(scale, 3)
            payloads[role] = {
                "role": role,
                "actor_name": _entity(actor).get_name(),
                "modelname": spec["modelname"],
                "model_id": spec["model_id"],
                "visual_asset_hash": _asset_hash(spec["modelname"], spec["model_id"], "visual"),
                "collision_asset_hash": _asset_hash(spec["modelname"], spec["model_id"], "collision"),
                "scale": scale.tolist(),
                "static_or_dynamic": spec["static_or_dynamic"],
                "mass": float(dynamic.mass) if dynamic is not None else 0.0,
                "friction": {"static": 0.5, "dynamic": 0.5},
                "collision_mode": spec["collision_mode"],
                "pose": _pose(actor),
                "linear_velocity": linear.tolist(),
                "angular_velocity": angular.tolist(),
                "sleep_state": bool(dynamic.is_sleeping()) if dynamic is not None else "not_dynamic",
                "velocity_source": {"linear_measured": linear_measured, "angular_measured": angular_measured},
            }
        return payloads

    @staticmethod
    def _camera_configuration(scene, rgb):
        config = scene.cameras.get_config()
        cameras = {}
        mount_links = {
            "head_camera": "world",
            "left_camera": scene.robot.left_camera.get_name(),
            "right_camera": scene.robot.right_camera.get_name(),
        }
        for name in ("head_camera", "left_camera", "right_camera"):
            item = config[name]
            height, width = rgb[name]["rgb"].shape[:2]
            cameras[name] = {
                "resolution": [width, height],
                "intrinsics_or_fov": np.asarray(item["intrinsic_cv"], dtype=np.float64).tolist(),
                "extrinsics": np.asarray(item["extrinsic_cv"], dtype=np.float64).tolist(),
                "mount_link": mount_links[name],
                "near_far": [0.1, 100.0],
            }
        try:
            import sapien

            renderer_version = getattr(sapien, "__version__", "sapien-version-unavailable")
        except BaseException:
            renderer_version = "sapien-version-unavailable"
        return {
            "camera_names": ["head_camera", "left_camera", "right_camera"],
            "cameras": cameras,
            "renderer_version": renderer_version,
            "render_settings": {"shader": "rt", "samples_per_pixel": 32, "path_depth": 8, "denoiser": "oidn"},
        }

    def capture_current(self, scene):
        scene._update_render()
        scene.cameras.update_picture()
        rgb = scene.cameras.get_rgb()
        required = {"head_camera", "left_camera", "right_camera"}
        if not required.issubset(rgb):
            raise RuntimeError(f"current capture missing cameras: {sorted(required - set(rgb))}")
        physical_entities = self._entity_payloads(scene)
        robot_state = np.concatenate((_dual_entity_values(scene.robot, "get_qpos"), _dual_entity_values(scene.robot, "get_qvel")))
        gripper_qpos = np.concatenate((_gripper_joint_qpos(scene.robot, "left"), _gripper_joint_qpos(scene.robot, "right")))
        visible_roles = {
            role: {"model_visible_name": role, "actor_name": item["actor_name"], "modelname": item["modelname"], "model_id": item["model_id"]}
            for role, item in physical_entities.items()
        }
        timestep = float(scene.scene.get_timestep())
        implementation_hash = implementation_source_sha256()
        return build_current_hashes_v2(
            head_rgb=rgb["head_camera"]["rgb"],
            wrist_rgb={"left": rgb["left_camera"]["rgb"], "right": rgb["right_camera"]["rgb"]},
            model_visible_robot_state=robot_state,
            gripper_actual_state=gripper_qpos,
            visible_object_roles=visible_roles,
            camera_configuration=self._camera_configuration(scene, rgb),
            physical_entities=physical_entities,
            scene_seed=int(scene._cmf_setup_kwargs["seed"]),
            generator_version="controlled_multi_future_joint_scene_v3_1",
            simulation_configuration={
                "simulator_timestep_seconds": timestep,
                "control_steps_per_action": 1,
                "solver_config_source": "RoboTwin Base_Task.setup_scene default sapien.SceneConfig",
                "canonical_settle_steps": int(scene._cmf_canonical_settle_steps),
                "default_static_friction": float(scene._cmf_setup_kwargs.get("static_friction", 0.5)),
                "default_dynamic_friction": float(scene._cmf_setup_kwargs.get("dynamic_friction", 0.5)),
                "default_restitution": float(scene._cmf_setup_kwargs.get("restitution", 0.0)),
                "implementation_source_sha256": implementation_hash,
            },
            source_commit=SOURCE_COMMIT,
        )

    def capture_anchor(self, scene):
        entities = self._entity_payloads(scene)
        actor_states = {
            role: {
                "pose": item["pose"],
                "linear_velocity": item["linear_velocity"],
                "angular_velocity": item["angular_velocity"],
                "sleep_state": item["sleep_state"],
            }
            for role, item in entities.items()
            if item["static_or_dynamic"] == "dynamic"
        }
        facility_poses = {
            role: item["pose"]
            for role, item in entities.items()
            if item["static_or_dynamic"] != "dynamic"
        }
        drive_targets = np.concatenate(tuple(
            np.asarray([float(np.asarray(joint.get_drive_target()).reshape(-1)[0]) for joint in entity.get_active_joints()])
            for entity in (scene.robot.left_entity, scene.robot.right_entity)
        ))
        gripper_qpos = np.concatenate((_gripper_joint_qpos(scene.robot, "left"), _gripper_joint_qpos(scene.robot, "right")))
        timestep = float(scene.scene.get_timestep())
        implementation_hash = implementation_source_sha256()
        entity_physics_registry = {
            role: {
                key: item[key]
                for key in (
                    "role",
                    "actor_name",
                    "modelname",
                    "model_id",
                    "visual_asset_hash",
                    "collision_asset_hash",
                    "scale",
                    "static_or_dynamic",
                    "mass",
                    "friction",
                    "collision_mode",
                )
            }
            for role, item in entities.items()
        }
        return capture_physical_anchor_v2(
            robot_qpos=_dual_entity_values(scene.robot, "get_qpos"),
            robot_qvel=_dual_entity_values(scene.robot, "get_qvel"),
            robot_drive_target=drive_targets,
            gripper_joint_qpos=gripper_qpos,
            actor_states=actor_states,
            facility_poses=facility_poses,
            physics_config={
                "simulator_timestep_seconds": timestep,
                "control_steps_per_action": 1,
                "solver_config_source": "RoboTwin Base_Task.setup_scene default sapien.SceneConfig",
                "canonical_settle_steps": int(scene._cmf_canonical_settle_steps),
                "default_material": {"static_friction": 0.5, "dynamic_friction": 0.5, "restitution": 0.0},
                "entity_physics_registry": entity_physics_registry,
                "implementation_source_sha256": implementation_hash,
            },
            source_commit=SOURCE_COMMIT,
            metadata={
                "family": self.family,
                "seed": int(scene._cmf_setup_kwargs["seed"]),
                "generator_version": "controlled_multi_future_joint_scene_v3_1",
            },
        )

    @staticmethod
    def capture_a0_activity_audit(scene):
        """Prove that A0 performed setup settling only, not planning/actions."""

        planner_queries = getattr(scene, "planner_queries", [])
        trace = getattr(scene, "trace", [])
        if planner_queries is None:
            planner_queries = []
        if trace is None:
            trace = []
        planner_query_count = int(getattr(scene, "planner_query_count", 0))
        planner_query_record_count = len(planner_queries)
        trace_row_count = len(trace)
        trace_was_initialized = hasattr(scene, "trace")
        action_execution_count = max(0, trace_row_count - 1) if trace_was_initialized else 0
        return {
            "schema_version": "cmf_a0_activity_audit_v1",
            "planner_query_count": planner_query_count,
            "planner_query_record_count": planner_query_record_count,
            "action_execution_count": action_execution_count,
            "trace_row_count": trace_row_count,
            "trace_was_initialized": trace_was_initialized,
            "canonical_settle_steps": int(getattr(scene, "_cmf_canonical_settle_steps", 0)),
            "canonical_settle_is_control_action": False,
            "canonical_settle_source": "RoboTwinSceneContextV1_1 scene.step before current/anchor capture",
        }

    def build_programs(self, pristine_scene):
        return FAMILY_CLASSES[self.family]().checked_provisional_programs()

    def task_trees(self, programs):
        program_ids = [item["program_id"] for item in programs]
        return {
            "observable": {"root": {"compatible_programs": program_ids, "evidence": "current scene roles and visible facilities"}},
            "oracle": {"root": {"compatible_programs": program_ids, "evidence": "audit-only full task tree"}},
        }

    def canonical_prefix(self, programs):
        return self.runner.canonical_prefix(programs)

    def audit_task_physical_feasibility(self, disposable_scene, program):
        return self.runner.audit_task_physical_feasibility(disposable_scene, program)

    def planner_audit_variants(self, frozen_program):
        return self.runner.planner_audit_variants(frozen_program)

    def audit_planner_solvability(self, disposable_scene, frozen_program, planner_variant):
        return self.runner.audit_planner_solvability(disposable_scene, frozen_program, planner_variant)

    def rollout(self, fresh_scene, frozen_program, realization_spec):
        return self.runner.rollout(fresh_scene, frozen_program, realization_spec, anchor_capture=self.capture_anchor)

    def verify(self, fresh_scene, frozen_program, rollout_result):
        return self.runner.verify(fresh_scene, frozen_program, rollout_result)
