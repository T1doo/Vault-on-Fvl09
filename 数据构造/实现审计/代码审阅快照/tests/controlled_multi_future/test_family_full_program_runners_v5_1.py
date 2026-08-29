import copy
import unittest
from unittest import mock

import numpy as np

from controlled_multi_future.families import F1ObjectSelection, F3MotionOrder, F4SubtaskOrder
from controlled_multi_future.family_runners_v3_1 import (
    _actor_geometry_center_pose,
    _actor_half_extents,
    _actor_local_geometry_bounds,
    get_family_runner,
)
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
                self.assertAlmostEqual(by_id["target_lift_mid"][2] - by_id["target_grasp"][2], 0.04)
                self.assertAlmostEqual(by_id["target_lift"][2] - by_id["target_lift_mid"][2], 0.04)

    def test_project_procedural_half_extents_override_create_box_config_scaling(self):
        actor = Actor([0.0, 0.0, 0.0])
        actor.config = {
            "extents": [0.022, 0.022, 0.022],
            "scale": [0.022, 0.022, 0.022],
        }
        actor._cmf_half_extents = np.asarray([0.022, 0.022, 0.022])
        actor._cmf_geometry_source = "AuditScene._box create_box half_size argument"
        np.testing.assert_allclose(_actor_half_extents(actor), [0.022, 0.022, 0.022])

    def test_asset_local_aabb_center_is_scaled_and_composed_with_actor_pose(self):
        actor = Actor([1.0, 2.0, 3.0])
        actor.config = {
            "center": [-8.985256604840808e-05, 0.9513497755527056, -0.0011933646434538318],
            "extents": [1.3016794444495572, 1.9314033284100605, 1.3055743868648846],
            "scale": [0.05, 0.05, 0.05],
        }
        center, half = _actor_local_geometry_bounds(actor)
        np.testing.assert_allclose(
            center,
            np.asarray(actor.config["center"]) * np.asarray(actor.config["scale"]),
        )
        np.testing.assert_allclose(
            half,
            np.asarray(actor.config["extents"])
            * np.asarray(actor.config["scale"])
            / 2.0,
        )
        geometry_pose = _actor_geometry_center_pose(actor)
        np.testing.assert_allclose(geometry_pose[:3], actor.pose.p + center)

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
        scene._cmf_planned_root_slot_spec = {
            "arm": "right",
            "scene_layout": {
                "branch_neutral_pose": [
                    0.15,
                    -0.02,
                    0.95,
                    0.5243570072481656,
                    -0.47439082845243685,
                    0.4743935067167858,
                    0.5243604405510669,
                ],
            },
        }
        runner = get_family_runner("F4")
        envelope = {
            "selected_gripper_links": ["finger"],
            "gripper_below_eef_envelope_m": 0.05,
        }
        with mock.patch(
            "controlled_multi_future.family_runners_v3_1._gripper_below_eef_envelope",
            return_value=envelope,
        ), mock.patch("controlled_multi_future.family_runners_v3_1._arm_tag", side_effect=lambda arm: arm):
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

            right_targets, right_extra = runner.build_targets(
                scene,
                F4SubtaskOrder().checked_provisional_programs()[0],
                {
                    "variant_id": "route1_minimum_height_segmented",
                    "execution_scope": "common_x_route_repair",
                },
            )
            self.assertEqual(right_extra["execution_arm"], "right")
            self.assertEqual(right_extra["gripper_envelope_evidence"]["gripper_below_eef_envelope_m"], 0.05)
            self.assertEqual(right_targets[-1]["pose"][:3].tolist(), [0.15, -0.02, 0.95])

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
