import copy
import unittest
from unittest import mock

import numpy as np

from controlled_multi_future.families import F1ObjectSelection, F3MotionOrder, F4SubtaskOrder
from controlled_multi_future.family_runners_v3_1 import _actor_half_extents, get_family_runner
from controlled_multi_future.root_orchestrator_v1_1 import compare_three_branch_final_state_payloads


class Pose:
    def __init__(self, p, q=(1.0, 0.0, 0.0, 0.0)):
        self.p = np.asarray(p, dtype=np.float64)
        self.q = np.asarray(q, dtype=np.float64)


class Actor:
    def __init__(self, p):
        self.pose = Pose(p)

    def get_pose(self):
        return self.pose


class Robot:
    left_original_pose = np.asarray([-0.3, 0.0, 0.9, 1.0, 0.0, 0.0, 0.0])


class Scene:
    def __init__(self):
        self.robot = Robot()
        self.bottle = Actor([-0.2, 0.0, 0.77])
        self.common_x = Actor([-0.25, 0.06, 0.762])
        self.a = Actor([-0.15, 0.06, 0.762])
        self.b = Actor([0.0, 0.06, 0.762])
        self.c = Actor([0.15, 0.06, 0.762])
        self.slot_a = Actor([-0.15, -0.17, 0.742])
        self.slot_b = Actor([0.0, -0.17, 0.742])
        self.slot_c = Actor([0.15, -0.17, 0.742])
        self.tray = Actor([0.23, -0.05, 0.75])

    def choose_grasp_pose(self, actor, **kwargs):
        center = np.concatenate((actor.get_pose().p + np.asarray([0.0, 0.0, 0.08]), [1.0, 0.0, 0.0, 0.0]))
        pre = center.copy()
        pre[2] += 0.09
        return pre, center


class FamilyFullProgramRunnersV5_1Test(unittest.TestCase):
    def test_f1_v3_2_uses_one_fair_segmented_lift_for_all_roles(self):
        scene = Scene()
        scene.red = Actor([-0.20, 0.02, 0.762])
        scene.green = Actor([-0.11, 0.02, 0.762])
        scene.blue = Actor([-0.02, 0.02, 0.762])
        scene.box = Actor([-0.08, -0.16, 0.78])
        runner = get_family_runner("F1")
        with mock.patch("controlled_multi_future.family_runners_v3_1._arm_tag_left", return_value="left"):
            for program in F1ObjectSelection().checked_provisional_programs():
                targets, _ = runner.build_targets(scene, program, {"variant_id": "default"})
                by_id = {item["segment_id"]: item["pose"] for item in targets}
                self.assertEqual(len(targets), 11)
                self.assertLessEqual(len(targets), 12)
                self.assertAlmostEqual(by_id["target_lift_mid"][2] - by_id["target_grasp"][2], 0.06)
                self.assertAlmostEqual(by_id["target_lift"][2] - by_id["target_lift_mid"][2], 0.06)

    def test_project_procedural_half_extents_override_create_box_config_scaling(self):
        actor = Actor([0.0, 0.0, 0.0])
        actor.config = {
            "extents": [0.022, 0.022, 0.022],
            "scale": [0.022, 0.022, 0.022],
        }
        actor._cmf_half_extents = np.asarray([0.022, 0.022, 0.022])
        actor._cmf_geometry_source = "AuditScene._box create_box half_size argument"
        np.testing.assert_allclose(_actor_half_extents(actor), [0.022, 0.022, 0.022])

    def test_f3_builds_frozen_full_orders_and_separate_diagnosis(self):
        scene = Scene()
        runner = get_family_runner("F3")
        with mock.patch("controlled_multi_future.family_runners_v3_1._arm_tag_left", return_value="left"):
            for program in F3MotionOrder().checked_provisional_programs():
                targets, extra = runner.build_targets(scene, program, {"variant_id": "default"})
                self.assertEqual(extra["event_order"], program["program_id"].split("-", 1)[1])
                self.assertEqual(extra["execution_scope"], "f3_full_program_nonformal_root")
                self.assertEqual(len(targets), 20)
            program = F3MotionOrder().checked_provisional_programs()[1]
            targets, extra = runner.build_targets(
                scene,
                program,
                {"variant_id": "default", "execution_scope": "release_diagnosis"},
            )
        self.assertEqual(extra["event_order"], "VH")
        self.assertEqual(extra["execution_scope"], "f3_release_diagnosis_VH_only")
        self.assertEqual(len(targets), 14)

    def test_f4_full_targets_follow_each_program_and_repair_is_common_only(self):
        scene = Scene()
        runner = get_family_runner("F4")
        envelope = {
            "selected_gripper_links": ["finger"],
            "gripper_below_eef_envelope_m": 0.05,
        }
        with mock.patch(
            "controlled_multi_future.family_runners_v3_1._left_gripper_below_eef_envelope",
            return_value=envelope,
        ), mock.patch("controlled_multi_future.family_runners_v3_1._arm_tag_left", return_value="left"):
            for program in F4SubtaskOrder().checked_provisional_programs():
                targets, extra = runner.build_targets(
                    scene,
                    program,
                    {"variant_id": "route1_minimum_height_segmented"},
                )
                expected = [step["object"] for step in program["steps"][1:]]
                self.assertEqual(extra["object_order"], expected)
                self.assertEqual([item["role"] for item in extra["object_target_groups"]], expected)
                self.assertEqual(extra["execution_scope"], "f4_full_program_nonformal_root")
                self.assertEqual(len(targets), 27)
            targets, extra = runner.build_targets(
                scene,
                F4SubtaskOrder().checked_provisional_programs()[0],
                {
                    "variant_id": "route1_minimum_height_segmented",
                    "execution_scope": "common_x_route_repair",
                },
            )
            self.assertEqual(extra["execution_scope"], "f4_common_x_route_repair_only")
            self.assertEqual(extra["object_target_groups"], [])
            self.assertEqual(len(targets), 9)
            target_by_id = {item["segment_id"]: item["pose"] for item in targets}
            self.assertGreaterEqual(
                target_by_id["common_safe_vertical"][2],
                target_by_id["common_lift"][2],
            )
            self.assertGreaterEqual(
                target_by_id["common_center_high"][2],
                target_by_id["common_lift"][2],
            )
            self.assertTrue(extra["carry_envelope"]["selected_height_not_below_lift"])
            route2_targets, route2_extra = runner.build_targets(
                scene,
                F4SubtaskOrder().checked_provisional_programs()[0],
                {
                    "variant_id": "route2_carry_neutral_fallback",
                    "execution_scope": "common_x_route_repair",
                },
            )
            route2_by_id = {item["segment_id"]: item["pose"] for item in route2_targets}
            self.assertGreaterEqual(
                route2_by_id["common_carry_neutral"][2],
                route2_by_id["common_lift"][2],
            )
            self.assertTrue(route2_extra["carry_envelope"]["selected_height_not_below_lift"])

    def test_final_state_comparison_is_pose_aware_and_fail_closed(self):
        base = {
            "bottle_pose": [0.0, 0.0, 0.8, 1.0, 0.0, 0.0, 0.0],
            "left_eef_pose": [0.0, 0.0, 0.9, 1.0, 0.0, 0.0, 0.0],
            "left_gripper_open": True,
        }
        branches = [
            {"final_state_equivalence_payload": copy.deepcopy(base)} for _ in range(3)
        ]
        branches[1]["final_state_equivalence_payload"]["bottle_pose"][3] = -1.0
        self.assertTrue(compare_three_branch_final_state_payloads(branches)["equivalent"])
        branches[2]["final_state_equivalence_payload"]["bottle_pose"][0] = 0.05
        self.assertFalse(compare_three_branch_final_state_payloads(branches)["equivalent"])


if __name__ == "__main__":
    unittest.main()
