import copy
import unittest

from controlled_multi_future.a0_activity_monitor_v2 import (
    ACTIVITY_SCHEMA_VERSION,
    A0PostSetupActivityMonitorV2,
    ActivityMonitorBoundaryError,
    ActivityMonitorError,
    ActivityMonitorInstallationError,
    ActivityMonitorRestorationError,
    activity_entry_point_registry_artifact,
    canonical_json_sha256,
    validate_activity_receipt_v2,
)


class BackendScene:
    def __init__(self):
        self.steps = 0

    def step(self):
        self.steps += 1

    def get_timestep(self):
        return 0.004


class DummyRobot:
    pass


class DummyCameras:
    pass


class DummyTask:
    def __init__(self):
        self.scene = BackendScene()
        self.robot = DummyRobot()
        self.cameras = DummyCameras()
        self.take_action_cnt = 0
        self.fail_restore_attribute = None

    def __delattr__(self, name):
        if name == self.fail_restore_attribute:
            raise RuntimeError("synthetic restoration failure")
        return super().__delattr__(name)


def _method(name):
    def value(self, *args, **kwargs):
        if name == "take_action":
            self.take_action_cnt += 1
        return {"name": name, "args": args, "kwargs": kwargs}

    value.__name__ = name
    return value


TASK_METHODS = (
    "delay",
    "set_gripper",
    "together_close_gripper",
    "together_open_gripper",
    "left_move_to_pose",
    "right_move_to_pose",
    "together_move_to_pose",
    "move",
    "grasp_actor",
    "place_actor",
    "move_by_displacement",
    "move_to_pose",
    "close_gripper",
    "open_gripper",
    "back_to_origin",
    "take_dense_action",
    "take_action",
    "_reserve_planner_query",
    "_update_render",
)
ROBOT_METHODS = (
    "left_plan_grippers",
    "right_plan_grippers",
    "left_plan_multi_path",
    "right_plan_multi_path",
    "left_plan_path",
    "right_plan_path",
    "set_arm_joints",
    "set_gripper",
    "move_to_homestate",
    "set_planner",
    "update_world_pcd",
)
for _name in TASK_METHODS:
    setattr(DummyTask, _name, _method(_name))
for _name in ROBOT_METHODS:
    setattr(DummyRobot, _name, _method(_name))
setattr(DummyCameras, "update_picture", _method("update_picture"))


def setup_activity():
    return {
        "setup_demo_completed": True,
        "setup_activity_source": "synthetic setup before monitor",
        "setup_take_action_count_if_available": 0,
        "setup_planner_query_count_if_available": None,
        "native_planner_counters_required": False,
        "canonical_settle_steps": 60,
        "canonical_settle_is_control_action": False,
        "simulator_timestep_seconds": 0.004,
        "control_steps_per_action": 1,
        "effective_action_interval_seconds": 0.004,
        "timestep_source": "synthetic",
    }


def reseal(receipt):
    receipt = copy.deepcopy(receipt)
    receipt.pop("activity_receipt_sha256", None)
    receipt["activity_receipt_sha256"] = canonical_json_sha256(receipt)
    return receipt


class A0ActivityMonitorV2Test(unittest.TestCase):
    def monitor(self, task=None, **kwargs):
        return A0PostSetupActivityMonitorV2(
            task or DummyTask(),
            scene_instance_id=kwargs.pop("scene_instance_id", "scene-1"),
            phase=kwargs.pop("phase", "A0_pristine"),
            setup_activity=kwargs.pop("setup_activity", setup_activity()),
            **kwargs,
        )

    def stopped_receipt(self):
        monitor = self.monitor()
        monitor.start()
        receipt = monitor.stop()
        validate_activity_receipt_v2(
            receipt,
            expected_scene_instance_id="scene-1",
            expected_phase="A0_pristine",
        )
        return receipt

    def test_trace_absent_does_not_hide_controlled_method(self):
        task = DummyTask()
        self.assertFalse(hasattr(task, "trace"))
        monitor = self.monitor(task)
        monitor.start()
        task.move_to_pose("left", [0] * 7)
        receipt = monitor.stop()
        self.assertIsNone(receipt["post_setup_activity"]["trace_row_delta"])
        self.assertEqual(receipt["post_setup_activity"]["controlled_action_delta"], 1)
        with self.assertRaisesRegex(ActivityMonitorError, "controlled_action_delta"):
            validate_activity_receipt_v2(receipt, expected_scene_instance_id="scene-1", expected_phase="A0_pristine")

    def test_take_dense_gripper_and_planner_each_fail(self):
        for method, owner in (
            ("take_dense_action", "task"),
            ("open_gripper", "task"),
            ("left_plan_path", "robot"),
        ):
            with self.subTest(method=method):
                task = DummyTask()
                monitor = self.monitor(task)
                monitor.start()
                getattr(getattr(task, owner), method)() if owner != "task" else getattr(task, method)()
                receipt = monitor.stop()
                with self.assertRaises(ActivityMonitorError):
                    validate_activity_receipt_v2(
                        receipt,
                        expected_scene_instance_id="scene-1",
                        expected_phase="A0_pristine",
                    )

    def test_physics_step_fails_but_renderer_only_is_recorded_and_allowed(self):
        task = DummyTask()
        monitor = self.monitor(task)
        monitor.start()
        task._update_render()
        task.cameras.update_picture()
        receipt = monitor.stop()
        self.assertEqual(receipt["post_setup_activity"]["renderer_update_delta"], 2)
        validate_activity_receipt_v2(receipt, expected_scene_instance_id="scene-1", expected_phase="A0_pristine")

        task = DummyTask()
        monitor = self.monitor(task)
        monitor.start()
        task.scene.step()
        receipt = monitor.stop()
        with self.assertRaisesRegex(ActivityMonitorError, "physics_step_delta"):
            validate_activity_receipt_v2(receipt, expected_scene_instance_id="scene-1", expected_phase="A0_pristine")

    def test_setup_activity_before_monitor_is_not_counted(self):
        task = DummyTask()
        task.take_dense_action({"setup": True})
        task.scene.step()
        monitor = self.monitor(task)
        monitor.start()
        receipt = monitor.stop()
        self.assertEqual(receipt["post_setup_activity"]["controlled_action_delta"], 0)
        self.assertEqual(receipt["post_setup_activity"]["physics_step_delta"], 0)
        self.assertEqual(receipt["setup_activity"]["canonical_settle_steps"], 60)
        validate_activity_receipt_v2(receipt, expected_scene_instance_id="scene-1", expected_phase="A0_pristine")

    def test_count_record_mismatch_and_tamper_fail(self):
        receipt = self.stopped_receipt()
        receipt["post_setup_activity"]["planner_query_record_delta"] = 1
        receipt = reseal(receipt)
        with self.assertRaises(ActivityMonitorError):
            validate_activity_receipt_v2(receipt, expected_scene_instance_id="scene-1", expected_phase="A0_pristine")

    def test_native_planner_delta_nonzero_fails(self):
        receipt = self.stopped_receipt()
        receipt["post_setup_activity"]["native_planner_query_count_delta_if_available"] = 1
        receipt["post_setup_activity"]["native_planner_record_delta_if_available"] = 1
        with self.assertRaisesRegex(ActivityMonitorError, "native planner query"):
            validate_activity_receipt_v2(
                reseal(receipt),
                expected_scene_instance_id="scene-1",
                expected_phase="A0_pristine",
            )

    def test_native_planner_record_delta_nonzero_fails(self):
        receipt = self.stopped_receipt()
        receipt["post_setup_activity"]["native_planner_query_count_delta_if_available"] = 0
        receipt["post_setup_activity"]["native_planner_record_delta_if_available"] = 1
        with self.assertRaisesRegex(ActivityMonitorError, "native planner record"):
            validate_activity_receipt_v2(
                reseal(receipt),
                expected_scene_instance_id="scene-1",
                expected_phase="A0_pristine",
            )

    def test_real_adapter_requires_native_planner_counters(self):
        receipt = self.stopped_receipt()
        receipt["setup_activity"]["native_planner_counters_required"] = True
        with self.assertRaisesRegex(ActivityMonitorError, "requires both native planner counters"):
            validate_activity_receipt_v2(
                reseal(receipt),
                expected_scene_instance_id="scene-1",
                expected_phase="A0_pristine",
            )

    def test_physics_limit_mismatch_fails(self):
        receipt = self.stopped_receipt()
        receipt["limits"]["physics_step_limit"] = 1
        with self.assertRaisesRegex(ActivityMonitorError, "frozen zero limits"):
            validate_activity_receipt_v2(
                reseal(receipt),
                expected_scene_instance_id="scene-1",
                expected_phase="A0_pristine",
            )

    def test_sapien_float_timestep_representation_is_accepted_but_real_mismatch_fails(self):
        receipt = self.stopped_receipt()
        receipt["setup_activity"]["simulator_timestep_seconds"] = 0.004000000189989805
        receipt["setup_activity"]["effective_action_interval_seconds"] = 0.004000000189989805
        validate_activity_receipt_v2(
            reseal(receipt),
            expected_scene_instance_id="scene-1",
            expected_phase="A0_pristine",
        )
        receipt["setup_activity"]["simulator_timestep_seconds"] = 0.004001
        with self.assertRaisesRegex(ActivityMonitorError, "represent 0.004"):
            validate_activity_receipt_v2(
                reseal(receipt),
                expected_scene_instance_id="scene-1",
                expected_phase="A0_pristine",
            )

    def test_missing_old_unbound_and_incomplete_receipts_fail(self):
        with self.assertRaises(ActivityMonitorError):
            validate_activity_receipt_v2(None, expected_scene_instance_id="scene-1", expected_phase="A0_pristine")
        receipt = self.stopped_receipt()
        for mutation in ("schema", "scene", "phase", "not_started", "not_stopped"):
            with self.subTest(mutation=mutation):
                value = copy.deepcopy(receipt)
                if mutation == "schema":
                    value["schema_version"] = "cmf_a0_activity_audit_v1"
                elif mutation == "scene":
                    value["scene_instance_id"] = "other"
                elif mutation == "phase":
                    value["phase"] = "A0_fresh_1"
                elif mutation == "not_started":
                    value["monitor_boundary"]["monitor_started"] = False
                else:
                    value["monitor_boundary"]["monitor_stopped"] = False
                value = reseal(value)
                with self.assertRaises(ActivityMonitorError):
                    validate_activity_receipt_v2(value, expected_scene_instance_id="scene-1", expected_phase="A0_pristine")

    def test_wrapper_installation_and_restoration_fail_closed(self):
        registry = ({"owner": "task", "attribute": "missing", "category": "controlled_action", "required": True},)
        monitor = self.monitor(registry=registry)
        with self.assertRaises(ActivityMonitorInstallationError):
            monitor.start()

        task = DummyTask()
        monitor = self.monitor(task)
        monitor.start()
        task.fail_restore_attribute = "move_to_pose"
        with self.assertRaises(ActivityMonitorRestorationError) as caught:
            monitor.stop()
        self.assertFalse(caught.exception.receipt["instrumentation"]["wrapper_restoration_pass"])

    def test_monitor_boundary_and_registry_are_sealed(self):
        monitor = self.monitor()
        with self.assertRaises(ActivityMonitorBoundaryError):
            monitor.stop()
        monitor.start()
        with self.assertRaises(ActivityMonitorBoundaryError):
            monitor.start()
        monitor.stop()
        with self.assertRaises(ActivityMonitorBoundaryError):
            monitor.stop()
        registry = activity_entry_point_registry_artifact()
        self.assertEqual(len(registry["registry_sha256"]), 64)
        self.assertFalse(registry["trace_is_authoritative_for_zero_action"])


if __name__ == "__main__":
    unittest.main()
