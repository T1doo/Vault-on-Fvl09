"""Hardened concrete RoboTwin adapter with post-setup A0 instrumentation.

This module is additive and lazy: importing it does not import the scene
definitions, construct SAPIEN, initialize a renderer, or touch CUDA.  The old
v1_1 adapter remains unchanged for historical evidence.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import traceback
from typing import Any, Mapping

import numpy as np

from .a0_activity_monitor_v2 import (
    A0PostSetupActivityMonitorV2,
    ActivityMonitorError,
)
from .anchor import capture_physical_anchor_v2
from .current_hasher import build_current_hashes_v2, hash_json
from .probes.runtime_trace import _dual_entity_values, _gripper_joint_qpos, _rigid_velocity
from .real_sapien_adapter_v1_1 import (
    FAMILY_CLASSES,
    ROLE_ASSETS,
    SOURCE_COMMIT,
    RoboTwinRealSapienPilotRootAdapterV1_1,
    _asset_hash,
    _dynamic_component,
    _entity,
    _planner_process_ids,
    _pose,
    _stop_owned_planner_processes,
    implementation_source_sha256,
)
from .root_orchestrator_v1_1 import SceneHandleV1_1


ADAPTER_VERSION = "RoboTwinRealSapienPilotRootAdapterV1_2"
CONTEXT_VERSION = "RoboTwinSceneContextV1_2"
CANONICAL_SETTLE_STEPS = 60
REQUIRED_TIMESTEP_SECONDS = 0.004
CREATE_ACTOR_SOURCE_SHA256 = "6bababee8e70da2460b2bbf47d3b5fbb20ccf73368782a7be596a63c962dce6d"


ROLE_ASSETS_V1_2 = deepcopy(ROLE_ASSETS)


def _procedural(
    *,
    creation_api: str,
    half_size,
    color,
    collision_enabled: bool,
    visual_only: bool,
    is_static: bool | None,
) -> dict:
    return {
        "creation_api": creation_api,
        "creation_api_source": "envs/utils/create_actor.py",
        "creation_api_source_sha256": CREATE_ACTOR_SOURCE_SHA256,
        "half_size": [float(value) for value in half_size],
        "color_rgb": [float(value) for value in color],
        "collision_enabled": bool(collision_enabled),
        "visual_only": bool(visual_only),
        "is_static": is_static,
        "collision_material_source": "scene.default_physical_material" if collision_enabled else "not_applicable",
        "density_or_mass_source": "runtime rigid component mass" if collision_enabled and not is_static else "not_applicable",
        "creation_contract_version": "project_procedural_asset_v2",
    }


for family, role, color in (
    ("F1", "red", (1, 0, 0)),
    ("F1", "green", (0, 1, 0)),
    ("F1", "blue", (0, 0, 1)),
    ("F4", "common_x", (1, 1, 0)),
    ("F4", "A", (1, 0, 0)),
    ("F4", "B", (0, 1, 0)),
    ("F4", "C", (0, 0, 1)),
):
    ROLE_ASSETS_V1_2[family][role]["procedural_creation"] = _procedural(
        creation_api="envs.utils.create_box",
        half_size=(0.022, 0.022, 0.022),
        color=color,
        collision_enabled=True,
        visual_only=False,
        is_static=False,
    )

ROLE_ASSETS_V1_2["F3"]["original_pad"]["procedural_creation"] = _procedural(
    creation_api="envs.utils.create_box",
    half_size=(0.07, 0.07, 0.005),
    color=(0.4, 0.4, 0.4),
    collision_enabled=True,
    visual_only=False,
    is_static=True,
)
ROLE_ASSETS_V1_2["F3"]["central_marker"]["procedural_creation"] = _procedural(
    creation_api="envs.utils.create_visual_box",
    half_size=(0.015, 0.015, 0.015),
    color=(1, 1, 0),
    collision_enabled=False,
    visual_only=True,
    is_static=None,
)
for role, color in (
    ("slot_A", (0.7, 0.2, 0.2)),
    ("slot_B", (0.2, 0.7, 0.2)),
    ("slot_C", (0.2, 0.2, 0.7)),
):
    ROLE_ASSETS_V1_2["F4"][role]["procedural_creation"] = _procedural(
        creation_api="envs.utils.create_visual_box",
        half_size=(0.035, 0.035, 0.002),
        color=color,
        collision_enabled=False,
        visual_only=True,
        is_static=None,
    )


def procedural_asset_spec_sha256(spec: Mapping[str, Any]) -> str | None:
    value = spec.get("procedural_creation")
    return hash_json(value) if isinstance(value, Mapping) else None


def _runtime_sleep_state(dynamic: Any) -> bool | str:
    """Normalize SAPIEN variants exposing ``is_sleeping`` as method/property."""

    if dynamic is None:
        return "not_dynamic"
    value = getattr(dynamic, "is_sleeping", None)
    value = value() if callable(value) else value
    if not isinstance(value, (bool, np.bool_)):
        raise TypeError("runtime rigid component is_sleeping must be a bool or zero-argument callable")
    return bool(value)


def _asset_hash_v1_2(spec: Mapping[str, Any], kind: str) -> str:
    procedural = spec.get("procedural_creation")
    if isinstance(procedural, Mapping):
        return hash_json(
            {
                "source": "project procedural creation parameters",
                "modelname": spec["modelname"],
                "model_id": spec["model_id"],
                "kind": kind,
                "procedural_creation": dict(procedural),
            }
        )
    return _asset_hash(spec["modelname"], spec["model_id"], kind)


def _setup_activity_summary(scene, args: Mapping[str, Any]) -> dict:
    timestep = float(scene.scene.get_timestep())
    return {
        "setup_demo_completed": True,
        "setup_activity_source": (
            "RoboTwin Base_Task._init_task_env_: move_to_homestate, initial together_open_gripper/"
            "take_dense_action, load_actors, check_stable; audited at fixed source commit"
        ),
        "setup_take_action_count_if_available": int(getattr(scene, "take_action_cnt", 0))
        if hasattr(scene, "take_action_cnt")
        else None,
        "setup_planner_query_count_if_available": int(getattr(scene, "planner_query_count", 0))
        if hasattr(scene, "planner_query_count")
        else None,
        "native_planner_counters_required": True,
        "native_planner_counter_source": (
            "RuntimeTraceMixin planner_query_count and planner_queries; both are required for real A0"
        ),
        "setup_dense_action_known_from_call_graph": [
            "Base_Task.together_open_gripper",
            "Base_Task.set_gripper",
            "Robot.left/right_plan_grippers",
            "Base_Task.take_dense_action",
        ],
        "setup_stability_physics_steps_known_from_call_graph": "Base_Task.check_stable: 2000 + 500",
        "canonical_settle_steps": CANONICAL_SETTLE_STEPS,
        "canonical_settle_is_control_action": False,
        "simulator_timestep_seconds": timestep,
        "control_steps_per_action": 1,
        "effective_action_interval_seconds": timestep,
        "timestep_source": "SAPIEN Scene.get_timestep() after Base_Task.setup_scene",
        "static_friction": float(args.get("static_friction", 0.5)),
        "dynamic_friction": float(args.get("dynamic_friction", 0.5)),
        "restitution": float(args.get("restitution", 0.0)),
        "physics_material_source": "declared setup config passed to Base_Task.setup_scene",
    }


class RoboTwinSceneContextV1_2:
    """Unique lifecycle with post-setup instrumentation and restoration audit."""

    counter = 0

    def __init__(self, *, family: str, planned_spec: Mapping[str, Any], phase: str, program, output_root: Path):
        type(self).counter += 1
        self.family = family
        self.phase = phase
        self.program = program
        self.planned_spec = dict(planned_spec)
        self.output_root = Path(output_root)
        self.scene_instance_id = f"{family.lower()}-{phase.replace(':', '_')}-v1_2-{type(self).counter:06d}"
        self.handle = SceneHandleV1_1(scene_instance_id=self.scene_instance_id)
        self.cleanup_receipt = None
        self.activity_receipt = None
        self._scene = None
        self._monitor: A0PostSetupActivityMonitorV2 | None = None

    @property
    def _a0_phase(self) -> bool:
        return self.phase in ("A0_pristine", "A0_fresh_1", "A0_fresh_2", "A0_fresh_3")

    def __enter__(self):
        from .probes.action_feasibility_v2 import _scene_resources

        scenes, scene_args = _scene_resources()
        scene = None
        try:
            scene = scenes[self.family]()
            self._scene = scene
            args = scene_args(self.family, self.output_root / self.scene_instance_id)
            args["seed"] = int(self.planned_spec["seed"])
            scene.setup_demo(**args)
            for _ in range(CANONICAL_SETTLE_STEPS):
                scene.scene.step()
            scene._cmf_setup_kwargs = dict(args)
            scene._cmf_canonical_settle_steps = CANONICAL_SETTLE_STEPS
            scene._cmf_scene_instance_id = self.scene_instance_id
            scene._cmf_adapter_version = ADAPTER_VERSION
            scene._cmf_scene_context_v1_2 = self
            if self._a0_phase:
                self._monitor = A0PostSetupActivityMonitorV2(
                    scene,
                    scene_instance_id=self.scene_instance_id,
                    phase=self.phase,
                    setup_activity=_setup_activity_summary(scene, args),
                )
                scene._cmf_a0_activity_monitor = self._monitor
                self._monitor.start()
            self.handle.scene = scene
            self.handle.activity_receipt = None
            return self.handle
        except BaseException as enter_exc:
            monitor_restoration_error = None
            if self._monitor is not None:
                try:
                    self._monitor.ensure_restored()
                    self.activity_receipt = self._monitor.last_receipt
                except BaseException as exc:
                    monitor_restoration_error = {"type": type(exc).__name__, "message": str(exc)}
            cleanup_error = None
            remaining = []
            if scene is not None:
                try:
                    remaining = _stop_owned_planner_processes(scene)
                    scene.close_env(clear_cache=True)
                except BaseException as cleanup_exc:
                    cleanup_error = {
                        "type": type(cleanup_exc).__name__,
                        "message": str(cleanup_exc),
                        "traceback": traceback.format_exc(),
                    }
            self.cleanup_receipt = {
                "scene_instance_id": self.scene_instance_id,
                "scene_created": scene is not None,
                "scene_cleanup_attempted": scene is not None,
                "scene_cleanup_succeeded": scene is not None and cleanup_error is None and not remaining,
                "cleanup_safety_pass": cleanup_error is None and not remaining,
                "orphan_process_count": len(remaining),
                "cleanup_error": cleanup_error,
                "activity_monitor_restoration_error": monitor_restoration_error,
                "failure_phase": "scene_enter",
                "enter_error_type": type(enter_exc).__name__,
            }
            self.handle.cleanup_receipt = dict(self.cleanup_receipt)
            self.handle.activity_receipt = self.activity_receipt
            raise

    def finish_activity_monitor(self) -> dict:
        if not self._a0_phase or self._monitor is None:
            raise ActivityMonitorError("scene has no active A0 monitor")
        try:
            self.activity_receipt = self._monitor.stop()
        except ActivityMonitorError as exc:
            self.activity_receipt = exc.receipt or self._monitor.last_receipt
            self.handle.activity_receipt = self.activity_receipt
            raise
        self.handle.activity_receipt = dict(self.activity_receipt)
        return dict(self.activity_receipt)

    def __exit__(self, exc_type, exc, tb):
        monitor_error = None
        if self._monitor is not None:
            try:
                if self._monitor.started and not self._monitor.stopped:
                    self.activity_receipt = self._monitor.stop()
                self._monitor.ensure_restored()
            except ActivityMonitorError as monitor_exc:
                self.activity_receipt = monitor_exc.receipt or self._monitor.last_receipt
                monitor_error = {"type": type(monitor_exc).__name__, "message": str(monitor_exc)}
            except BaseException as monitor_exc:
                monitor_error = {"type": type(monitor_exc).__name__, "message": str(monitor_exc)}
        cleanup_error = None
        remaining = []
        attempted = self._scene is not None
        if self._scene is not None:
            try:
                remaining = _stop_owned_planner_processes(self._scene)
                self._scene.close_env(clear_cache=True)
            except BaseException as cleanup_exc:
                cleanup_error = {
                    "type": type(cleanup_exc).__name__,
                    "message": str(cleanup_exc),
                    "traceback": traceback.format_exc(),
                }
        self.cleanup_receipt = {
            "scene_instance_id": self.scene_instance_id,
            "scene_created": self._scene is not None,
            "scene_cleanup_attempted": attempted,
            "scene_cleanup_succeeded": attempted and cleanup_error is None and not remaining,
            "cleanup_safety_pass": attempted and cleanup_error is None and not remaining,
            "orphan_process_count": len(remaining),
            "cleanup_error": cleanup_error,
            "owned_planner_process_ids": sorted(_planner_process_ids(self._scene)) if self._scene is not None else [],
            "activity_monitor_restoration_error": monitor_error,
            "activity_monitor_restoration_succeeded": monitor_error is None,
            "outer_gpu_release_audit_required": True,
        }
        self.handle.cleanup_receipt = dict(self.cleanup_receipt)
        self.handle.activity_receipt = dict(self.activity_receipt) if isinstance(self.activity_receipt, Mapping) else None
        return False


class RoboTwinRealSapienPilotRootAdapterV1_2(RoboTwinRealSapienPilotRootAdapterV1_1):
    """Current concrete adapter with v2 A0 activity and metadata semantics."""

    def scene(self, planned_root_slot_spec, *, phase, program=None):
        if planned_root_slot_spec.get("family") != self.family:
            raise ValueError("planned root family does not match adapter")
        return RoboTwinSceneContextV1_2(
            family=self.family,
            planned_spec=planned_root_slot_spec,
            phase=phase,
            program=program,
            output_root=self.output_root,
        )

    def finish_a0_activity_monitor(self, scene, *, phase: str, scene_instance_id: str) -> dict:
        if getattr(scene, "_cmf_scene_instance_id", None) != scene_instance_id:
            raise ActivityMonitorError("scene instance does not match A0 monitor request")
        monitor = getattr(scene, "_cmf_a0_activity_monitor", None)
        if not isinstance(monitor, A0PostSetupActivityMonitorV2):
            raise ActivityMonitorError("scene lacks A0PostSetupActivityMonitorV2")
        if monitor.phase != phase or monitor.scene_instance_id != scene_instance_id:
            raise ActivityMonitorError("A0 monitor binding mismatch")
        context = getattr(scene, "_cmf_scene_context_v1_2", None)
        if not isinstance(context, RoboTwinSceneContextV1_2):
            raise ActivityMonitorError("scene lacks its bound RoboTwinSceneContextV1_2")
        receipt = context.finish_activity_monitor()
        scene._cmf_a0_activity_receipt = dict(receipt)
        return receipt

    def _entity_payloads(self, scene):
        registry = ROLE_ASSETS_V1_2[self.family]
        setup = getattr(scene, "_cmf_setup_kwargs", {})
        payloads = {}
        for role, actor in scene.role_actors.items():
            spec = registry[role]
            dynamic = _dynamic_component(actor)
            linear, linear_measured = _rigid_velocity(actor, "linear_velocity")
            angular, angular_measured = _rigid_velocity(actor, "angular_velocity")
            config = getattr(actor, "config", None) or {}
            scale = np.asarray(config.get("scale", [1, 1, 1]), dtype=np.float64).reshape(-1)
            if scale.size == 1:
                scale = np.repeat(scale, 3)
            procedural_hash = procedural_asset_spec_sha256(spec)
            if spec["collision_mode"] == "visual_only":
                friction = {"static": None, "dynamic": None, "source": "not_applicable_visual_only"}
            else:
                friction = {
                    "static": float(setup.get("static_friction", 0.5)),
                    "dynamic": float(setup.get("dynamic_friction", 0.5)),
                    "source": "scene_default_declared_config",
                }
            payloads[role] = {
                "role": role,
                "actor_name": _entity(actor).get_name(),
                "modelname": spec["modelname"],
                "model_id": spec["model_id"],
                "visual_asset_hash": _asset_hash_v1_2(spec, "visual"),
                "collision_asset_hash": _asset_hash_v1_2(spec, "collision"),
                "procedural_asset_spec_sha256": procedural_hash,
                "procedural_creation": deepcopy(spec.get("procedural_creation")),
                "scale": scale.tolist(),
                "static_or_dynamic": spec["static_or_dynamic"],
                "mass": float(dynamic.mass) if dynamic is not None else 0.0,
                "mass_source": "runtime_rigid_component" if dynamic is not None else "not_applicable_non_dynamic",
                "friction": friction,
                "collision_mode": spec["collision_mode"],
                "pose": _pose(actor),
                "linear_velocity": linear.tolist(),
                "angular_velocity": angular.tolist(),
                "sleep_state": _runtime_sleep_state(dynamic),
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
                "field_sources": {
                    "resolution": "runtime RGB array shape",
                    "intrinsics_or_fov": "runtime Camera.get_intrinsic_matrix via Camera.get_config",
                    "extrinsics": "runtime Camera.get_extrinsic_matrix via Camera.get_config",
                    "mount_link": "runtime robot camera link name/world declaration",
                    "near_far": "declared_config envs/camera/camera.py Camera.load_camera",
                },
            }
        try:
            import sapien

            renderer_version = getattr(sapien, "__version__", "unavailable")
            renderer_version_source = "runtime sapien package __version__"
        except BaseException:
            renderer_version = "unavailable"
            renderer_version_source = "unavailable"
        return {
            "camera_names": ["head_camera", "left_camera", "right_camera"],
            "cameras": cameras,
            "renderer_version": renderer_version,
            "renderer_version_source": renderer_version_source,
            "render_settings": {"shader": "rt", "samples_per_pixel": 32, "path_depth": 8, "denoiser": "oidn"},
            "render_settings_source": "declared_config Base_Task.setup_scene fixed source commit",
        }

    @staticmethod
    def _simulation_configuration(scene) -> dict:
        setup = scene._cmf_setup_kwargs
        timestep = float(scene.scene.get_timestep())
        return {
            "simulator_timestep_seconds": timestep,
            "control_steps_per_action": 1,
            "effective_action_interval_seconds": timestep,
            "timestep_source": "runtime SAPIEN Scene.get_timestep after Base_Task.setup_scene",
            "solver_config_source": "RoboTwin Base_Task.setup_scene default sapien.SceneConfig",
            "canonical_settle_steps": int(scene._cmf_canonical_settle_steps),
            "canonical_settle_source": "RoboTwinSceneContextV1_2 explicit post-setup scene.step loop",
            "default_static_friction": float(setup.get("static_friction", 0.5)),
            "default_dynamic_friction": float(setup.get("dynamic_friction", 0.5)),
            "default_restitution": float(setup.get("restitution", 0.0)),
            "default_material_source": "declared setup config passed to Base_Task.setup_scene",
            "implementation_source_sha256": implementation_source_sha256(),
            "adapter_version": ADAPTER_VERSION,
        }

    def capture_current(self, scene):
        scene._update_render()
        scene.cameras.update_picture()
        rgb = scene.cameras.get_rgb()
        required = {"head_camera", "left_camera", "right_camera"}
        if not required.issubset(rgb):
            raise RuntimeError(f"current capture missing cameras: {sorted(required - set(rgb))}")
        physical_entities = self._entity_payloads(scene)
        robot_state = np.concatenate(
            (_dual_entity_values(scene.robot, "get_qpos"), _dual_entity_values(scene.robot, "get_qvel"))
        )
        gripper_qpos = np.concatenate(
            (_gripper_joint_qpos(scene.robot, "left"), _gripper_joint_qpos(scene.robot, "right"))
        )
        visible_roles = {
            role: {
                "model_visible_name": role,
                "actor_name": item["actor_name"],
                "modelname": item["modelname"],
                "model_id": item["model_id"],
            }
            for role, item in physical_entities.items()
        }
        return build_current_hashes_v2(
            head_rgb=rgb["head_camera"]["rgb"],
            wrist_rgb={"left": rgb["left_camera"]["rgb"], "right": rgb["right_camera"]["rgb"]},
            model_visible_robot_state=robot_state,
            gripper_actual_state=gripper_qpos,
            visible_object_roles=visible_roles,
            camera_configuration=self._camera_configuration(scene, rgb),
            physical_entities=physical_entities,
            scene_seed=int(scene._cmf_setup_kwargs["seed"]),
            generator_version="controlled_multi_future_joint_scene_v3_1_adapter_v1_2",
            simulation_configuration=self._simulation_configuration(scene),
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
            role: item["pose"] for role, item in entities.items() if item["static_or_dynamic"] != "dynamic"
        }
        drive_targets = np.concatenate(
            tuple(
                np.asarray(
                    [float(np.asarray(joint.get_drive_target()).reshape(-1)[0]) for joint in entity.get_active_joints()]
                )
                for entity in (scene.robot.left_entity, scene.robot.right_entity)
            )
        )
        gripper_qpos = np.concatenate(
            (_gripper_joint_qpos(scene.robot, "left"), _gripper_joint_qpos(scene.robot, "right"))
        )
        entity_registry = {
            role: {
                key: item[key]
                for key in (
                    "role",
                    "actor_name",
                    "modelname",
                    "model_id",
                    "visual_asset_hash",
                    "collision_asset_hash",
                    "procedural_asset_spec_sha256",
                    "procedural_creation",
                    "scale",
                    "static_or_dynamic",
                    "mass",
                    "mass_source",
                    "friction",
                    "collision_mode",
                )
            }
            for role, item in entities.items()
        }
        physics_config = self._simulation_configuration(scene)
        physics_config["entity_physics_registry"] = entity_registry
        return capture_physical_anchor_v2(
            robot_qpos=_dual_entity_values(scene.robot, "get_qpos"),
            robot_qvel=_dual_entity_values(scene.robot, "get_qvel"),
            robot_drive_target=drive_targets,
            gripper_joint_qpos=gripper_qpos,
            actor_states=actor_states,
            facility_poses=facility_poses,
            physics_config=physics_config,
            source_commit=SOURCE_COMMIT,
            metadata={
                "family": self.family,
                "seed": int(scene._cmf_setup_kwargs["seed"]),
                "generator_version": "controlled_multi_future_joint_scene_v3_1_adapter_v1_2",
                "adapter_version": ADAPTER_VERSION,
            },
        )
