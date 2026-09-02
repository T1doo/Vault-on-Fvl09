import copy
import unittest
from unittest.mock import patch

import numpy as np

from controlled_multi_future.f3_final_pose_search_v3 import (
    build_f3_final_pose_recipe_universe_v3,
)
from controlled_multi_future.official_raw_pose_generation_v1 import (
    generate_official_raw_pose_receipt_v1,
    validate_official_raw_pose_receipt_v1,
)


class Pose:
    p = [0.1, -0.2, 0.8]
    q = [1.0, 0.0, 0.0, 0.0]


class Actor:
    def get_pose(self):
        return Pose()

    def get_contact_point(self, contact_id, kind):
        if kind == "matrix":
            value = np.eye(4)
            value[:3, 3] = [0.1, -0.2, 0.85]
            return value
        if kind == "list":
            return [0.1, -0.2, 0.85]
        raise AssertionError(kind)


class Robot:
    def create_target_pose_list(self, base, center, arm):
        return [list(base) for _ in range(10)]


class Scene:
    robot = Robot()


class OfficialRawPoseGenerationV1Tests(unittest.TestCase):
    def test_official_generator_receipt_binds_all_recipe_inputs(self):
        recipe = build_f3_final_pose_recipe_universe_v3()["recipes"][17]
        with patch(
            "controlled_multi_future.official_raw_pose_generation_v1._arm_tag",
            return_value="left",
        ):
            receipt = generate_official_raw_pose_receipt_v1(
                Scene(), Actor(), recipe, family="F3"
            )
        validation = validate_official_raw_pose_receipt_v1(
            receipt, recipe, family="F3"
        )
        self.assertTrue(validation["pass"], validation)
        self.assertEqual(receipt["ordered_rotation_candidate_count"], 10)
        self.assertFalse(receipt["external_raw_pose_input_allowed"])
        tampered = copy.deepcopy(receipt)
        tampered["contact_point_id"] += 1
        self.assertFalse(
            validate_official_raw_pose_receipt_v1(
                tampered, recipe, family="F3"
            )["pass"]
        )


if __name__ == "__main__":
    unittest.main()
