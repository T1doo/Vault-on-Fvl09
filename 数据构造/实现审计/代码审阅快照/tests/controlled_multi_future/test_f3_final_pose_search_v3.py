import copy
import unittest

from controlled_multi_future.canonical_artifact import canonical_hash_json
from controlled_multi_future.f3_final_pose_search_v3 import (
    EXPECTED_RECIPE_COUNT,
    assert_f3_applied_pose_matches_qualification_v3,
    build_f3_final_pose_recipe_universe_v3,
    build_f3_targets_from_qualified_final_pose_v3,
    freeze_f3_final_pose_v3,
    validate_f3_final_pose_qualification_v3,
)
from controlled_multi_future.high_level_planner_runner_v1 import (
    build_f3_level1_targets_v1,
)


class F3FinalPoseSearchV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.universe = build_f3_final_pose_recipe_universe_v3()

    def test_cartesian_universe_is_complete_and_decoupled(self):
        recipes = self.universe["recipes"]
        self.assertEqual(len(recipes), EXPECTED_RECIPE_COUNT)
        self.assertEqual(self.universe["selected_asset_model_ids"], [15, 5, 4, 13])
        axes = self.universe["axes"]
        self.assertEqual(axes["arms"], ["left", "right"])
        self.assertEqual(axes["regions"], ["lower_body", "upper_body"])
        self.assertEqual(axes["official_contact_point_ids"], list(range(8)))
        self.assertEqual(axes["official_rotation_candidate_indices"], list(range(10)))
        self.assertEqual(axes["pregrasp_distances_m"], [0.06, 0.09, 0.12])
        for region in axes["regions"]:
            for arm in axes["arms"]:
                self.assertTrue(
                    any(
                        item["grasp_region"] == region and item["arm"] == arm
                        for item in recipes
                    )
                )

    def test_legacy_post_qualification_shift_builder_is_disabled(self):
        with self.assertRaisesRegex(RuntimeError, "mutated.*after planner"):
            build_f3_level1_targets_v1(object(), {})

    def test_region_is_applied_before_final_pose_freeze(self):
        recipe = self.universe["recipes"][0]
        actor = [0.0, 0.0, 0.8, 1.0, 0.0, 0.0, 0.0]
        raw_pregrasp = [0.0, -0.10, 0.9, 1.0, 0.0, 0.0, 0.0]
        raw_grasp = [0.0, -0.04, 0.9, 1.0, 0.0, 0.0, 0.0]
        frozen = freeze_f3_final_pose_v3(
            recipe,
            actor_pose=actor,
            raw_official_pregrasp_pose=raw_pregrasp,
            raw_official_grasp_pose=raw_grasp,
            raw_rotation_candidate_index=recipe[
                "official_rotation_candidate_index"
            ],
        )
        self.assertTrue(frozen["region_applied_before_planner_qualification"])
        self.assertNotEqual(
            frozen["raw_official_pose_hashes"]["pregrasp"],
            frozen["final_goal_pose_hashes"]["pregrasp"],
        )
        payload = {
            "schema_version": "test_f3_final_qualification_v3",
            "recipe_sha256": recipe["recipe_sha256"],
            "final_pose_freeze_sha256": frozen["final_pose_freeze_sha256"],
            "ordered_planner_input_sha256": frozen[
                "ordered_final_planner_input_sha256"
            ],
            "goal_pose_hashes": frozen["final_goal_pose_hashes"],
            "planner_statuses": {
                "pregrasp": "Success",
                "grasp": "Success",
                "lift": "Success",
            },
            "ik_collision_planner_checked": True,
            "post_qualification_pose_mutation": False,
        }
        payload["receipt_sha256"] = canonical_hash_json(payload)
        checked = validate_f3_final_pose_qualification_v3(
            recipe, frozen, payload
        )
        self.assertTrue(checked["pass"])
        targets = build_f3_targets_from_qualified_final_pose_v3(
            recipe, frozen, payload
        )
        self.assertTrue(targets["final_pregrasp_grasp_lift_exactly_reused"])
        self.assertEqual(
            [item["pose"] for item in targets["targets"][:3]],
            [
                frozen["final_goal_poses"]["pregrasp"],
                frozen["final_goal_poses"]["grasp"],
                frozen["final_goal_poses"]["lift"],
            ],
        )
        applied = assert_f3_applied_pose_matches_qualification_v3(
            frozen, frozen["final_goal_poses"]
        )
        self.assertTrue(applied["pass"])
        changed = copy.deepcopy(frozen["final_goal_poses"])
        changed["pregrasp"][0] += 1e-6
        with self.assertRaisesRegex(ValueError, "changed after"):
            assert_f3_applied_pose_matches_qualification_v3(frozen, changed)

    def test_final_qualification_fails_if_any_pose_or_status_differs(self):
        recipe = self.universe["recipes"][1]
        frozen = freeze_f3_final_pose_v3(
            recipe,
            actor_pose=[0, 0, 0.8, 1, 0, 0, 0],
            raw_official_pregrasp_pose=[0, -0.1, 0.9, 1, 0, 0, 0],
            raw_official_grasp_pose=[0, -0.04, 0.9, 1, 0, 0, 0],
            raw_rotation_candidate_index=recipe[
                "official_rotation_candidate_index"
            ],
        )
        payload = {
            "recipe_sha256": recipe["recipe_sha256"],
            "final_pose_freeze_sha256": frozen["final_pose_freeze_sha256"],
            "ordered_planner_input_sha256": frozen[
                "ordered_final_planner_input_sha256"
            ],
            "goal_pose_hashes": frozen["final_goal_pose_hashes"],
            "planner_statuses": {
                "pregrasp": "Failure",
                "grasp": "Success",
                "lift": "Success",
            },
            "ik_collision_planner_checked": True,
            "post_qualification_pose_mutation": False,
        }
        payload["receipt_sha256"] = canonical_hash_json(payload)
        self.assertFalse(
            validate_f3_final_pose_qualification_v3(
                recipe, frozen, payload
            )["pass"]
        )


if __name__ == "__main__":
    unittest.main()
