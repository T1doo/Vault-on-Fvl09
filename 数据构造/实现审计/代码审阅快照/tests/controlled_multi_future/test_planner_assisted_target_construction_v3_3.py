import inspect
import unittest
from unittest.mock import patch

import numpy as np

from controlled_multi_future.family_runners_v3_3 import (
    F1ControllerV3_3,
    _audited_planner_assisted_target_construction,
)


class _Entity:
    def get_qpos(self):
        return np.zeros(6, dtype=np.float64)


class _Robot:
    def __init__(self):
        self.left_entity = _Entity()
        self.right_entity = _Entity()

    def left_plan_multi_path(self, targets, *args, **kwargs):
        return {"status": ["Success"] + ["Fail"] * (len(targets) - 1)}

    def right_plan_multi_path(self, targets, *args, **kwargs):
        return {"status": ["Success"] + ["Fail"] * (len(targets) - 1)}


class _Actor:
    def iter_contact_points(self):
        return iter((index, None) for index in range(4))

    def get_name(self):
        return "rgb-block"


class _Scene:
    def __init__(self):
        self.robot = _Robot()
        self.planner_queries = []
        self.planner_query_count = 0
        self.planner_query_limit = 16

    def _reserve_planner_query(self):
        if self.planner_query_count >= self.planner_query_limit:
            raise RuntimeError("planner budget exceeded")
        self.planner_query_count += 1
        return self.planner_query_count


class PlannerAssistedTargetConstructionV3_3Test(unittest.TestCase):
    def test_callback_selected_pose_is_bound_to_exact_contact_and_candidate(self):
        scene = _Scene()
        actor = _Actor()

        def callback():
            batches = []
            for contact_id, _ in actor.iter_contact_points():
                candidates = [
                    np.full(7, contact_id * 100 + candidate_id, dtype=np.float64)
                    for candidate_id in range(10)
                ]
                batches.append(candidates)
                scene.robot.left_plan_multi_path(candidates)
            return batches[3][0], np.ones(7, dtype=np.float64)

        with patch(
            "controlled_multi_future.family_runners_v3_3._planner_reset",
            return_value={"reset_performed": True},
        ):
            _, audit = _audited_planner_assisted_target_construction(
                scene,
                actor,
                arm="left",
                variant_id="selected-pose-binding",
                callback=callback,
            )
        self.assertEqual(audit["callback_selected_pose_match_count"], 1)
        self.assertEqual(audit["callback_selected_contact_point_id"], 3)
        self.assertEqual(
            audit["callback_selected_candidate_index_within_batch"], 0
        )
        self.assertEqual(
            audit["callback_selected_candidate_planner_status"], "Success"
        )

    def test_non_pose_structured_callback_remains_compatible_for_f1(self):
        scene = _Scene()
        actor = _Actor()

        def callback():
            for _ in actor.iter_contact_points():
                scene.robot.left_plan_multi_path([np.zeros(7)] * 10)
            return ([{"segment_id": str(index)} for index in range(7)], {"extra": True})

        with patch(
            "controlled_multi_future.family_runners_v3_3._planner_reset",
            return_value={"reset_performed": True},
        ):
            value, audit = _audited_planner_assisted_target_construction(
                scene,
                actor,
                arm="left",
                variant_id="f1-structured-callback",
                callback=callback,
            )
        self.assertEqual(len(value[0]), 7)
        self.assertIsNone(audit["callback_selected_pregrasp_pose"])
        self.assertEqual(audit["callback_selected_pose_match_count"], 0)

    def test_four_cube_contact_batches_are_counted_and_wrapper_is_restored(self):
        scene = _Scene()
        actor = _Actor()
        original = scene.robot.left_plan_multi_path.__func__

        def callback():
            for _ in actor.iter_contact_points():
                candidates = [np.full(7, value, dtype=np.float64) for value in range(10)]
                scene.robot.left_plan_multi_path(candidates)
            return "selected"

        with patch(
            "controlled_multi_future.family_runners_v3_3._planner_reset",
            return_value={"reset_performed": True},
        ):
            value, audit = _audited_planner_assisted_target_construction(
                scene,
                actor,
                arm="left",
                variant_id="test",
                callback=callback,
            )
        self.assertEqual(value, "selected")
        self.assertEqual(audit["batch_call_count"], 4)
        self.assertEqual(audit["internal_pose_candidate_count"], 40)
        self.assertEqual(scene.planner_query_count, 4)
        self.assertEqual(len(scene.planner_queries), 4)
        self.assertTrue(all(item["batch_size"] == 10 for item in scene.planner_queries))
        self.assertIs(scene.robot.left_plan_multi_path.__func__, original)

    def test_right_arm_and_preexisting_instance_override_are_restored(self):
        scene = _Scene()
        actor = _Actor()

        def override(targets, *args, **kwargs):
            return {"status": ["Success"] + ["Fail"] * (len(targets) - 1)}

        scene.robot.right_plan_multi_path = override

        def callback():
            for _ in actor.iter_contact_points():
                scene.robot.right_plan_multi_path([np.zeros(7)] * 10)
            return "right-selected"

        with patch(
            "controlled_multi_future.family_runners_v3_3._planner_reset",
            return_value={"reset_performed": True},
        ):
            value, audit = _audited_planner_assisted_target_construction(
                scene,
                actor,
                arm="right",
                variant_id="right-test",
                callback=callback,
            )
        self.assertEqual(value, "right-selected")
        self.assertEqual(audit["batch_call_count"], 4)
        self.assertIs(scene.robot.right_plan_multi_path, override)

    def test_batch_exception_is_receipted_and_wrapper_is_restored(self):
        scene = _Scene()
        actor = _Actor()
        original = scene.robot.left_plan_multi_path.__func__

        def failing(_targets, *args, **kwargs):
            raise RuntimeError("planner exploded")

        scene.robot.left_plan_multi_path = failing

        def callback():
            scene.robot.left_plan_multi_path([np.zeros(7)] * 10)

        with patch(
            "controlled_multi_future.family_runners_v3_3._planner_reset",
            return_value={"reset_performed": True},
        ), self.assertRaisesRegex(RuntimeError, "planner exploded"):
            _audited_planner_assisted_target_construction(
                scene,
                actor,
                arm="left",
                variant_id="exception-test",
                callback=callback,
            )
        self.assertEqual(scene.planner_query_count, 1)
        self.assertEqual(scene.planner_queries[0]["status"], "Exception")
        self.assertIs(scene.robot.left_plan_multi_path, failing)
        del scene.robot.left_plan_multi_path
        self.assertIs(scene.robot.left_plan_multi_path.__func__, original)

    def test_f1_revision2_has_no_blue_specific_target_condition(self):
        source = inspect.getsource(F1ControllerV3_3.plan_suffix_from_actual_prefix_end_state)
        self.assertIn("build_uniform_carry_hub_targets", source)
        self.assertIn("target_construction_planner_audit", source)
        self.assertNotIn('role == "blue"', source)
        self.assertNotIn("role == 'blue'", source)
        execute_source = inspect.getsource(F1ControllerV3_3.execute_frozen_suffix_spec)
        self.assertLess(
            execute_source.index("F1 frozen revision-2 suffix segment order changed"),
            execute_source.index("_execute_cached_segment"),
        )
        for segment_id in (
            "target_lift_mid",
            "target_lift",
            "carry_hub_low",
            "carry_hub_high",
            "safe_horizontal",
            "preplace",
            "release",
            "retreat",
            "rest",
        ):
            self.assertIn(f'"{segment_id}"', execute_source)
        self.assertIn('row["role_actor_angular_velocities"][role]', execute_source)


if __name__ == "__main__":
    unittest.main()
