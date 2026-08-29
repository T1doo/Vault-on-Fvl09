import unittest

import numpy as np

from controlled_multi_future.family_runners_v3_1 import (
    _motiongen_audit_value,
    _plan_arm,
)

from controlled_multi_future.planner_dtype_v3_2 import (
    GEOMETRY_DTYPE,
    PLANNER_DTYPE,
    geometry_array,
    normalize_planner_control,
    planner_array,
    planner_dtype_receipt,
)


class PlannerDtypeV3_2Test(unittest.TestCase):
    def test_motiongen_nonfinite_values_are_json_safe_tagged(self):
        import json

        value = _motiongen_audit_value(
            np.asarray([np.nan, np.inf, -np.inf, 0.25], dtype=np.float64)
        )
        self.assertEqual(
            value[:3],
            [
                {"kind": "nonfinite", "value": "nan"},
                {"kind": "nonfinite", "value": "+inf"},
                {"kind": "nonfinite", "value": "-inf"},
            ],
        )
        self.assertEqual(value[3], 0.25)
        json.dumps(value, allow_nan=False)

    def test_motiongen_failure_side_channel_is_receipted_and_restored(self):
        class Scalar:
            def __init__(self, value):
                self.value = value

            def item(self):
                return self.value

        class Result:
            success = Scalar(False)
            status = "IK_FAIL"
            valid_query = Scalar(True)
            attempts = Scalar(10)
            used_graph = Scalar(False)
            position_error = np.asarray([0.012], dtype=np.float32)
            rotation_error = np.asarray([0.034], dtype=np.float32)
            solve_time = Scalar(0.2)
            total_time = Scalar(0.3)

        class MotionGen:
            def plan_single(self, *args, **kwargs):
                return Result()

        class Planner:
            def __init__(self):
                self.motion_gen = MotionGen()

        class Robot:
            def __init__(self):
                self.left_planner = Planner()

            def left_plan_path(self, pose, *, last_qpos):
                self.left_planner.motion_gen.plan_single(None, None, None)
                return {"status": "Fail"}

        class Scene:
            def __init__(self):
                self.robot = Robot()
                self.planner_query_count = 0
                self.planner_query_limit = 4
                self.planner_queries = []

            def _reserve_planner_query(self):
                self.planner_query_count += 1
                return self.planner_query_count

        scene = Scene()
        original = scene.robot.left_planner.motion_gen.plan_single.__func__
        result = _plan_arm(
            scene,
            [0.0, 0.0, 0.9, 1.0, 0.0, 0.0, 0.0],
            last_qpos=np.zeros(7, dtype=np.float32),
            source="side-channel-test",
            arm="left",
        )
        self.assertEqual(result["status"], "Fail")
        receipt = scene.planner_queries[0]
        self.assertTrue(receipt["motiongen_side_channel_available"])
        self.assertEqual(receipt["motiongen_side_channel_call_count"], 1)
        fields = receipt["motiongen_result_side_channel"][0]["fields"]
        self.assertEqual(fields["status"], "IK_FAIL")
        self.assertFalse(fields["success"])
        self.assertEqual(fields["attempts"], 10)
        self.assertEqual(fields["position_error"], 0.012000000104308128)
        self.assertIs(
            scene.robot.left_planner.motion_gen.plan_single.__func__, original
        )
        self.assertNotIn(
            "plan_single", vars(scene.robot.left_planner.motion_gen)
        )
        self.assertTrue(receipt["motiongen_wrapper_restoration_succeeded"])

    def test_nonzero_float64_inputs_become_float32_at_planner_boundary(self):
        qpos = np.asarray([0.25, -0.5, 1.25], dtype=np.float64)
        pose = np.asarray([0.1, -0.2, 0.9, 1.0, 0.0, 0.0, 0.0], dtype=np.float64)
        self.assertEqual(planner_array(qpos).dtype, PLANNER_DTYPE)
        self.assertEqual(planner_array(pose, shape=(7,)).dtype, PLANNER_DTYPE)
        self.assertTrue(np.any(planner_array(qpos) != 0))

    def test_control_position_velocity_and_audit_geometry_are_explicit(self):
        control = normalize_planner_control(
            {
                "status": "Success",
                "position": np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float64),
                "velocity": np.asarray([[0.01, 0.02], [0.03, 0.04]], dtype=np.float64),
            }
        )
        self.assertEqual(control["position"].dtype, PLANNER_DTYPE)
        self.assertEqual(control["velocity"].dtype, PLANNER_DTYPE)
        self.assertEqual(geometry_array(control["position"]).dtype, GEOMETRY_DTYPE)
        receipt = planner_dtype_receipt(qpos=[0.1], goal_pose=[0, 0, 1, 1, 0, 0, 0], control=control)
        self.assertEqual(receipt["qpos"]["dtype"], "float32")
        self.assertEqual(receipt["goal_pose"]["dtype"], "float32")
        self.assertEqual(receipt["control"]["position"]["dtype"], "float32")


if __name__ == "__main__":
    unittest.main()
