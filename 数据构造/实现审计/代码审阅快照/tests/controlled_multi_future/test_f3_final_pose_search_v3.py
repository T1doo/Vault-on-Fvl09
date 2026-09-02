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
from controlled_multi_future.official_raw_pose_generation_v1 import (
    OFFICIAL_GENERATOR_VERSION,
)


def raw_receipt(recipe, actor_pose, pregrasp, grasp):
    value = {
        "schema_version": "cmf_official_raw_pose_generation_v1",
        "official_generator_version": OFFICIAL_GENERATOR_VERSION,
        "family": "F3",
        "recipe_id": recipe["recipe_id"],
        "recipe_sha256": recipe["recipe_sha256"],
        "asset": recipe["asset"],
        "main_object_model_id": None,
        "arm": recipe["arm"],
        "contact_point_id": recipe["official_contact_point_id"],
        "rotation_candidate_index": recipe[
            "official_rotation_candidate_index"
        ],
        "pregrasp_distance_m": recipe["pregrasp_distance_m"],
        "target_distance_m": recipe["target_distance_m"],
        "actor_pose": actor_pose,
        "actor_pose_sha256": canonical_hash_json(actor_pose),
        "ordered_rotation_candidate_count": 10,
        "ordered_rotation_candidates_sha256": canonical_hash_json(
            list(range(10))
        ),
        "selected_raw_pregrasp_pose": pregrasp,
        "selected_raw_grasp_pose": grasp,
        "raw_pregrasp_sha256": canonical_hash_json(pregrasp),
        "raw_grasp_sha256": canonical_hash_json(grasp),
        "source_calls": [
            "actor.get_contact_point(contact_id, matrix/list)",
            "scene.robot.create_target_pose_list(..., ROTATE_NUM=10)",
        ],
        "external_raw_pose_input_allowed": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


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
            raw_pose_generation_receipt=raw_receipt(
                recipe, actor, raw_pregrasp, raw_grasp
            ),
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
            raw_pose_generation_receipt=raw_receipt(
                recipe,
                [0, 0, 0.8, 1, 0, 0, 0],
                [0, -0.1, 0.9, 1, 0, 0, 0],
                [0, -0.04, 0.9, 1, 0, 0, 0],
            ),
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
