import inspect
import unittest

import numpy as np

from controlled_multi_future.family_runners_v3_1 import F4RunnerV3_1
from controlled_multi_future.project_cube_grasp_pose_v1 import (
    FROZEN_CUBE_HALF_EXTENTS_M,
    FROZEN_LOCAL_GRASP_POSE_WXYZ,
    build_project_cube_grasp_poses,
)


class ProjectCubeGraspPoseV1Test(unittest.TestCase):
    def test_abc_use_one_finite_right_arm_local_transform(self):
        poses = {
            "A": [0.07, 0.08, 0.762, 1, 0, 0, 0],
            "B": [-0.08, 0.08, 0.762, 1, 0, 0, 0],
            "C": [-0.23, 0.08, 0.762, 1, 0, 0, 0],
        }
        outputs = {}
        for role, actor_pose in poses.items():
            pregrasp, grasp, contract = build_project_cube_grasp_poses(
                actor_pose,
                cube_half_extents_m=FROZEN_CUBE_HALF_EXTENTS_M,
                arm="right",
                pregrasp_distance_m=0.09,
            )
            self.assertEqual(pregrasp.shape, (7,))
            self.assertEqual(grasp.shape, (7,))
            self.assertTrue(np.all(np.isfinite(pregrasp)))
            self.assertTrue(np.all(np.isfinite(grasp)))
            outputs[role] = (pregrasp, grasp, contract)
        self.assertEqual(
            len({item[2]["grasp_contract_sha256"] for item in outputs.values()}),
            1,
        )
        self.assertEqual(
            len({tuple(item[1][3:]) for item in outputs.values()}),
            1,
        )
        for role, (_, grasp, _) in outputs.items():
            actor = np.asarray(poses[role], dtype=np.float64)
            np.testing.assert_allclose(
                grasp[:3] - actor[:3],
                FROZEN_LOCAL_GRASP_POSE_WXYZ[:3],
                atol=1e-12,
                rtol=0.0,
            )

    def test_invalid_arm_pose_and_geometry_fail_closed(self):
        actor = [0, 0, 0.762, 1, 0, 0, 0]
        with self.assertRaisesRegex(ValueError, "right arm"):
            build_project_cube_grasp_poses(
                actor,
                cube_half_extents_m=FROZEN_CUBE_HALF_EXTENTS_M,
                arm="left",
                pregrasp_distance_m=0.09,
            )
        with self.assertRaisesRegex(ValueError, "shape"):
            build_project_cube_grasp_poses(
                -1,
                cube_half_extents_m=FROZEN_CUBE_HALF_EXTENTS_M,
                arm="right",
                pregrasp_distance_m=0.09,
            )
        with self.assertRaisesRegex(ValueError, "half extents"):
            build_project_cube_grasp_poses(
                actor,
                cube_half_extents_m=[0.02, 0.02, 0.02],
                arm="right",
                pregrasp_distance_m=0.09,
            )

    def test_f4_rollout_executes_frozen_block_targets(self):
        source = inspect.getsource(F4RunnerV3_1.rollout)
        self.assertNotIn("scene.grasp_actor(actor", source)
        self.assertIn('group_targets[0]["pose"]', source)
        self.assertIn('group_targets[1]["pose"]', source)
        self.assertIn('group_targets[2]["pose"]', source)
        self.assertIn('group_targets[3]["pose"]', source)
        self.assertIn('group_targets[4]["pose"]', source)
        self.assertIn('group_targets[5]["pose"]', source)


if __name__ == "__main__":
    unittest.main()
