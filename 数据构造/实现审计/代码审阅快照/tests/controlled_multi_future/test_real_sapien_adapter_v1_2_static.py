import copy
import inspect
import unittest

import numpy as np

from controlled_multi_future.a0_activity_monitor_v2 import (
    ActivityMonitorError,
    activity_entry_point_registry_artifact,
    canonical_json_sha256,
    validate_activity_receipt_v2,
)
from controlled_multi_future.current_hasher import build_current_hashes_v2
from controlled_multi_future.real_sapien_adapter_v1_2 import (
    ADAPTER_VERSION,
    ROLE_ASSETS_V1_2,
    RoboTwinRealSapienPilotRootAdapterV1_2,
    RoboTwinSceneContextV1_2,
    _asset_hash_v1_2,
    _initialize_a0_native_planner_counters,
    procedural_asset_spec_sha256,
    _runtime_sleep_state,
)
from controlled_multi_future.runtime_v3_1_contracts import F3_PAD_HALF_SIZE_M


def camera_configuration(source="runtime"):
    camera = {
        "resolution": [2, 2],
        "intrinsics_or_fov": np.eye(3).tolist(),
        "extrinsics": np.eye(4).tolist(),
        "mount_link": "world",
        "near_far": [0.1, 100.0],
        "field_sources": {
            "resolution": source,
            "intrinsics_or_fov": source,
            "extrinsics": source,
            "mount_link": source,
            "near_far": "declared_config",
        },
    }
    return {
        "camera_names": ["head", "left", "right"],
        "cameras": {name: copy.deepcopy(camera) for name in ("head", "left", "right")},
        "renderer_version": "test",
        "renderer_version_source": source,
        "render_settings": {"shader": "rt"},
        "render_settings_source": "declared_config",
    }


def physical_entities(friction_source="scene_default_declared_config"):
    return {
        "block": {
            "role": "block",
            "actor_name": "block",
            "modelname": "project_rgb_block",
            "model_id": "red",
            "visual_asset_hash": "a" * 64,
            "collision_asset_hash": "b" * 64,
            "scale": [1, 1, 1],
            "static_or_dynamic": "dynamic",
            "mass": 0.1,
            "mass_source": "runtime_rigid_component",
            "friction": {"static": 0.5, "dynamic": 0.5, "source": friction_source},
            "collision_mode": "box",
            "procedural_asset_spec_sha256": "c" * 64,
            "procedural_creation": {"half_size": [0.022] * 3, "color_rgb": [1, 0, 0]},
            "pose": [0, 0, 0, 1, 0, 0, 0],
            "linear_velocity": [0, 0, 0],
            "angular_velocity": [0, 0, 0],
            "sleep_state": True,
        }
    }


def current(camera_source="runtime", friction_source="scene_default_declared_config"):
    return build_current_hashes_v2(
        head_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
        wrist_rgb={"left": np.zeros((2, 2, 3), dtype=np.uint8), "right": np.zeros((2, 2, 3), dtype=np.uint8)},
        model_visible_robot_state=np.zeros(4),
        gripper_actual_state=np.zeros(2),
        visible_object_roles={"block": {"name": "red block"}},
        camera_configuration=camera_configuration(camera_source),
        physical_entities=physical_entities(friction_source),
        scene_seed=1,
        generator_version="test",
        simulation_configuration={"simulator_timestep_seconds": 0.004, "control_steps_per_action": 1},
        source_commit="test",
    )


def zero_activity(timestep=0.004):
    registry = activity_entry_point_registry_artifact()
    entries = sorted(f"{item['owner']}.{item['attribute']}" for item in registry["entries"])
    payload = {
        "schema_version": "cmf_a0_activity_audit_v2",
        "scene_instance_id": "scene",
        "phase": "A0_pristine",
        "monitor_boundary": {
            "monitor_started": True,
            "monitor_stopped": True,
            "monitor_start_step": 0,
            "monitor_end_step": 0,
            "monitor_start_monotonic_time": 1.0,
            "monitor_end_monotonic_time": 2.0,
        },
        "setup_activity": {
            "setup_demo_completed": True,
            "setup_activity_source": "test",
            "setup_take_action_count_if_available": 0,
            "setup_planner_query_count_if_available": None,
            "native_planner_counters_required": False,
            "canonical_settle_steps": 60,
            "canonical_settle_is_control_action": False,
            "simulator_timestep_seconds": timestep,
            "control_steps_per_action": 1,
            "effective_action_interval_seconds": timestep,
            "timestep_source": "test",
        },
        "post_setup_activity": {
            "planner_query_delta": 0,
            "planner_query_record_delta": 0,
            "controlled_action_delta": 0,
            "instrumented_control_call_delta": 0,
            "instrumented_planner_wrapper_delta": 0,
            "take_action_count_delta": 0,
            "trace_row_delta": None,
            "physics_step_delta": 0,
            "renderer_update_delta": 2,
            "native_planner_query_count_delta_if_available": None,
            "native_planner_record_delta_if_available": None,
        },
        "instrumentation": {
            "entry_point_registry_sha256": registry["registry_sha256"],
            "wrapped_entry_points": entries,
            "all_registry_entry_points": entries,
            "missing_expected_entry_points": [],
            "wrapper_installation_pass": True,
            "wrapper_restoration_pass": True,
            "counter_sources": {"synthetic": True},
        },
        "limits": {"planner_query_limit": 0, "controlled_action_limit": 0, "physics_step_limit": 0},
    }
    payload["activity_receipt_sha256"] = canonical_json_sha256(payload)
    return payload


class RealSapienAdapterV1_2StaticTest(unittest.TestCase):
    def test_f3_pad_impact_revision_is_bound_into_asset_registry(self):
        self.assertEqual(F3_PAD_HALF_SIZE_M, (0.11, 0.145, 0.005))
        self.assertEqual(
            ROLE_ASSETS_V1_2["F3"]["original_pad"]["procedural_creation"]["half_size"],
            list(F3_PAD_HALF_SIZE_M),
        )

    def test_a0_native_planner_ledger_is_initialized_without_trace(self):
        scene = type("Scene", (), {})()
        receipt = _initialize_a0_native_planner_counters(scene)
        self.assertEqual(scene.planner_query_count, 0)
        self.assertEqual(scene.planner_queries, [])
        self.assertFalse(receipt["trace_initialized"])
        scene.planner_query_count = 1
        with self.assertRaises(ActivityMonitorError):
            _initialize_a0_native_planner_counters(scene)

    def test_sleep_state_supports_fvl05_bool_property_and_callable(self):
        property_component = type("PropertyComponent", (), {"is_sleeping": True})()
        callable_component = type("CallableComponent", (), {"is_sleeping": lambda self: False})()
        self.assertTrue(_runtime_sleep_state(property_component))
        self.assertFalse(_runtime_sleep_state(callable_component))
        self.assertEqual(_runtime_sleep_state(None), "not_dynamic")
        invalid_component = type("InvalidComponent", (), {"is_sleeping": "unknown"})()
        with self.assertRaises(TypeError):
            _runtime_sleep_state(invalid_component)

    def test_import_is_lazy_and_context_orders_monitor_after_setup_settle(self):
        module_source = inspect.getsource(inspect.getmodule(RoboTwinRealSapienPilotRootAdapterV1_2))
        prefix = module_source.split("class RoboTwinSceneContextV1_2", 1)[0]
        self.assertNotIn("import sapien", prefix)
        source = inspect.getsource(RoboTwinSceneContextV1_2.__enter__)
        self.assertLess(source.index("scene.setup_demo"), source.index("for _ in range(CANONICAL_SETTLE_STEPS)"))
        self.assertLess(source.index("for _ in range(CANONICAL_SETTLE_STEPS)"), source.index("self._monitor.start()"))
        self.assertEqual(ADAPTER_VERSION, "RoboTwinRealSapienPilotRootAdapterV1_2")

    def test_project_procedural_parameters_are_part_of_asset_hash(self):
        spec = copy.deepcopy(ROLE_ASSETS_V1_2["F1"]["red"])
        first = _asset_hash_v1_2(spec, "visual")
        first_spec = procedural_asset_spec_sha256(spec)
        spec["procedural_creation"]["half_size"][0] += 0.001
        self.assertNotEqual(first, _asset_hash_v1_2(spec, "visual"))
        self.assertNotEqual(first_spec, procedural_asset_spec_sha256(spec))

    def test_camera_source_changes_visible_current_hash(self):
        first = current(camera_source="runtime")
        second = current(camera_source="declared_config")
        self.assertNotEqual(first["model_visible_aggregate_sha256"], second["model_visible_aggregate_sha256"])
        self.assertNotEqual(first["aggregate_sha256"], second["aggregate_sha256"])

    def test_physics_metadata_source_changes_hidden_hash(self):
        first = current(friction_source="scene_default_declared_config")
        second = current(friction_source="actor_material")
        self.assertNotEqual(first["hidden_physical_aggregate_sha256"], second["hidden_physical_aggregate_sha256"])
        self.assertEqual(first["aggregate_sha256"], second["aggregate_sha256"])

    def test_wrong_timestep_fails_a0_activity_validation(self):
        with self.assertRaisesRegex(ActivityMonitorError, "timestep"):
            validate_activity_receipt_v2(
                zero_activity(0.005),
                expected_scene_instance_id="scene",
                expected_phase="A0_pristine",
            )

    def test_activity_finish_requires_scene_phase_and_context_binding(self):
        adapter = object.__new__(RoboTwinRealSapienPilotRootAdapterV1_2)
        scene = type("Scene", (), {"_cmf_scene_instance_id": "other"})()
        with self.assertRaises(ActivityMonitorError):
            adapter.finish_a0_activity_monitor(
                scene,
                phase="A0_pristine",
                scene_instance_id="scene",
            )


if __name__ == "__main__":
    unittest.main()
