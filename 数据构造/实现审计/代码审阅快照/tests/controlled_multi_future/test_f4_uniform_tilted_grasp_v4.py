import copy
import unittest

import numpy as np

from controlled_multi_future.f4_right_workspace_layout_v4 import LAYOUT
from controlled_multi_future.f4_uniform_tilted_grasp_v4 import (
    F4_ALLOWED_OBJECT_ORDERS,
    F4_BLOCK_SEGMENT_SUFFIXES,
    FROZEN_CUBE_HALF_EXTENTS_M,
    ROUTE_VERSION,
    TILTED_ACTOR_TO_EEF_TRANSLATION_M,
    TILTED_GRASP_QUATERNION_WXYZ,
    TILTED_TOOL_ROTATION_TABLE,
    TILTED_TOOL_X_TABLE,
    TILT_FROM_TABLE_NEGATIVE_Z_DEGREES,
    audit_uniform_tilted_f4_geometry,
    build_uniform_tilted_block_group,
    build_uniform_tilted_f4_block_groups,
    right_curobo_planner_position,
    uniform_tilted_grasp_contract,
)
from controlled_multi_future.geometry import compose_pose, relative_pose


def _target_actor_poses():
    targets = {}
    for role in ("A", "B", "C"):
        pose = np.asarray(LAYOUT["object_poses"][role], dtype=np.float64).copy()
        pose[:3] = np.asarray(
            LAYOUT["slot_poses"][role][:3], dtype=np.float64
        ) + np.asarray([0.0, 0.0, FROZEN_CUBE_HALF_EXTENTS_M[2]])
        targets[role] = pose.tolist()
    return targets


class F4UniformTiltedGraspV4Test(unittest.TestCase):
    def test_actual_r3_settled_quaternion_roundoff_preserves_target(self):
        source = [
            0.15999959409236908,
            0.02000034973025322,
            0.7620004415512085,
            1.0,
            -9.675601177150384e-06,
            -4.463726781978039e-06,
            9.824091193877393e-07,
        ]
        target = list(source)
        target[:3] = [0.15, 0.16, 0.764]
        group = build_uniform_tilted_block_group(
            role="A",
            actor_pose=source,
            target_actor_pose=target,
            neutral_pose=LAYOUT["branch_neutral_pose"],
        )
        audit = group["route_audit"]
        self.assertTrue(audit["final_actor_target_preserved"])
        self.assertLess(
            audit["final_actor_target_orientation_error_rad"], 1e-7
        )
        self.assertGreater(
            audit["final_actor_target_orientation_error_rad"], 1e-12
        )

    def test_contract_is_one_exact_global_sixty_degree_transform(self):
        contract = uniform_tilted_grasp_contract()
        self.assertEqual(contract["route_version"], ROUTE_VERSION)
        self.assertEqual(contract["arm"], "right")
        self.assertEqual(contract["uniform_roles"], ["A", "B", "C"])
        self.assertEqual(
            contract["tilt_from_table_negative_z_degrees"],
            TILT_FROM_TABLE_NEGATIVE_Z_DEGREES,
        )
        self.assertFalse(contract["role_specific_condition"])
        np.testing.assert_allclose(
            TILTED_TOOL_X_TABLE,
            [0.0, np.sqrt(3.0) / 2.0, -0.5],
            rtol=0.0,
            atol=1e-15,
        )
        np.testing.assert_allclose(
            TILTED_TOOL_ROTATION_TABLE.T @ TILTED_TOOL_ROTATION_TABLE,
            np.eye(3),
            rtol=0.0,
            atol=1e-15,
        )
        self.assertAlmostEqual(np.linalg.det(TILTED_TOOL_ROTATION_TABLE), 1.0)
        np.testing.assert_allclose(
            TILTED_GRASP_QUATERNION_WXYZ,
            [
                0.6830127018922193,
                -0.18301270189221938,
                0.18301270189221938,
                0.6830127018922193,
            ],
            rtol=0.0,
            atol=1e-15,
        )
        np.testing.assert_allclose(
            TILTED_ACTOR_TO_EEF_TRANSLATION_M,
            [0.0, -0.10392304845413262, 0.06],
            rtol=0.0,
            atol=1e-15,
        )
        self.assertEqual(
            contract["grasp_contract_sha256"],
            uniform_tilted_grasp_contract()["grasp_contract_sha256"],
        )

    def test_all_program_orders_use_uniform_groups_and_preserve_actor_targets(self):
        objects = copy.deepcopy(LAYOUT["object_poses"])
        targets = _target_actor_poses()
        neutral = copy.deepcopy(LAYOUT["branch_neutral_pose"])
        original_objects = copy.deepcopy(objects)
        original_targets = copy.deepcopy(targets)
        original_neutral = copy.deepcopy(neutral)

        for order in F4_ALLOWED_OBJECT_ORDERS:
            with self.subTest(order=order):
                built = build_uniform_tilted_f4_block_groups(
                    object_poses=objects,
                    target_actor_poses=targets,
                    neutral_pose=neutral,
                    object_order=order,
                )
                self.assertEqual(
                    [group["role"] for group in built["object_target_groups"]],
                    list(order),
                )
                self.assertEqual(len(built["flattened_targets"]), 21)
                hashes = set()
                for index, group in enumerate(built["object_target_groups"]):
                    role = group["role"]
                    self.assertEqual(group["target_start_index"], index * 7)
                    self.assertEqual(
                        [item["segment_id"] for item in group["targets"]],
                        [
                            f"{role}_{suffix}"
                            for suffix in F4_BLOCK_SEGMENT_SUFFIXES
                        ],
                    )
                    hashes.add(group["grasp_contract"]["grasp_contract_sha256"])
                    self.assertTrue(
                        group["route_audit"]["final_actor_target_preserved"]
                    )
                    poses = {
                        item["segment_id"].removeprefix(f"{role}_"): np.asarray(
                            item["pose"], dtype=np.float64
                        )
                        for item in group["targets"]
                    }
                    eef_to_actor = relative_pose(
                        poses["grasp"], objects[role]
                    )
                    realized_target = compose_pose(
                        poses["release"], eef_to_actor
                    )
                    np.testing.assert_allclose(
                        realized_target,
                        targets[role],
                        rtol=0.0,
                        atol=1e-12,
                    )
                    np.testing.assert_array_equal(
                        poses["neutral"], neutral
                    )
                self.assertEqual(len(hashes), 1)
                self.assertTrue(built["audit"]["actor_final_targets_preserved"])
                for field in (
                    "scene_layout_changed",
                    "tray_pose_changed",
                    "executing_arm_changed",
                    "common_prefix_changed",
                    "program_changed",
                    "verifier_changed",
                    "role_specific_condition",
                ):
                    self.assertFalse(built["audit"][field])

        self.assertEqual(objects, original_objects)
        self.assertEqual(targets, original_targets)
        self.assertEqual(neutral, original_neutral)

    def test_exact_a_targets_move_eef_inward_and_keep_midpoint_structure(self):
        group = build_uniform_tilted_block_group(
            role="A",
            actor_pose=LAYOUT["object_poses"]["A"],
            target_actor_pose=_target_actor_poses()["A"],
            neutral_pose=LAYOUT["branch_neutral_pose"],
        )
        poses = {
            item["segment_id"].removeprefix("A_"): np.asarray(
                item["pose"], dtype=np.float64
            )
            for item in group["targets"]
        }
        expected = {
            "pregrasp": [0.16, -0.1618653347947321, 0.867],
            "grasp": [0.16, -0.08392304845413262, 0.822],
            "lift": [0.16, -0.08392304845413262, 0.922],
            "carry_mid": [0.155, -0.01392304845413259, 0.924],
            "preplace": [0.15, 0.05607695154586743, 0.924],
            "release": [0.15, 0.05607695154586743, 0.824],
        }
        for suffix, xyz in expected.items():
            np.testing.assert_allclose(
                poses[suffix][:3], xyz, rtol=0.0, atol=1e-12
            )
            np.testing.assert_allclose(
                poses[suffix][3:],
                TILTED_GRASP_QUATERNION_WXYZ,
                rtol=0.0,
                atol=1e-12,
            )
        np.testing.assert_allclose(
            poses["carry_mid"][:2],
            0.5 * (poses["lift"][:2] + poses["preplace"][:2]),
            rtol=0.0,
            atol=1e-15,
        )
        self.assertEqual(
            poses["carry_mid"][2],
            max(poses["lift"][2], poses["preplace"][2]),
        )

    def test_frozen_layout_geometry_norm_and_table_clearance_audit_passes(self):
        audit = audit_uniform_tilted_f4_geometry(
            object_poses=LAYOUT["object_poses"],
            target_actor_poses=_target_actor_poses(),
            neutral_pose=LAYOUT["branch_neutral_pose"],
        )
        self.assertTrue(audit["pass"])
        self.assertTrue(audit["runtime_ik_still_required"])
        self.assertTrue(audit["planner_norm_is_not_reachability_proof"])
        self.assertFalse(audit["gripper_mesh_table_clearance_available"])
        self.assertEqual(set(audit["roles"]), {"A", "B", "C"})
        self.assertAlmostEqual(
            audit["r3_failed_a_midpoint_planner_position_norm_m"],
            0.5571321445507876,
        )
        self.assertAlmostEqual(
            audit["maximum_proposed_planner_frame_position_norm_m"],
            0.5197133565135388,
        )
        self.assertLess(
            audit["maximum_proposed_planner_frame_position_norm_m"],
            audit["r3_failed_a_midpoint_planner_position_norm_m"],
        )
        self.assertAlmostEqual(
            audit["minimum_transport_actor_bottom_clearance_m"], 0.10
        )
        self.assertAlmostEqual(
            audit["roles"]["A"]["target_release_actor_bottom_gap_m"],
            0.002,
        )
        for role, receipt in audit["roles"].items():
            self.assertTrue(receipt["pass"], role)
            self.assertTrue(all(receipt["checks"].values()), role)
            self.assertGreaterEqual(
                min(receipt["transport_actor_bottom_clearance_m"].values()),
                0.03,
            )
        for field in (
            "scene_layout_changed",
            "tray_pose_changed",
            "executing_arm_changed",
            "common_prefix_changed",
            "program_changed",
            "verifier_changed",
            "role_specific_condition",
        ):
            self.assertFalse(audit[field])

    def test_invalid_inputs_fail_closed(self):
        target = _target_actor_poses()["A"]
        with self.assertRaisesRegex(ValueError, "right arm"):
            build_uniform_tilted_block_group(
                role="A",
                actor_pose=LAYOUT["object_poses"]["A"],
                target_actor_pose=target,
                neutral_pose=LAYOUT["branch_neutral_pose"],
                arm="left",
            )
        with self.assertRaisesRegex(ValueError, "A, B, or C"):
            build_uniform_tilted_block_group(
                role="X",
                actor_pose=LAYOUT["object_poses"]["A"],
                target_actor_pose=target,
                neutral_pose=LAYOUT["branch_neutral_pose"],
            )
        with self.assertRaisesRegex(ValueError, "half extents"):
            build_uniform_tilted_block_group(
                role="A",
                actor_pose=LAYOUT["object_poses"]["A"],
                target_actor_pose=target,
                neutral_pose=LAYOUT["branch_neutral_pose"],
                cube_half_extents_m=[0.02, 0.02, 0.02],
            )
        with self.assertRaisesRegex(ValueError, "positive"):
            build_uniform_tilted_block_group(
                role="A",
                actor_pose=LAYOUT["object_poses"]["A"],
                target_actor_pose=target,
                neutral_pose=LAYOUT["branch_neutral_pose"],
                pregrasp_distance_m=0.0,
            )
        with self.assertRaisesRegex(ValueError, "exactly A/B/C"):
            build_uniform_tilted_f4_block_groups(
                object_poses={"A": LAYOUT["object_poses"]["A"]},
                target_actor_poses=_target_actor_poses(),
                neutral_pose=LAYOUT["branch_neutral_pose"],
            )
        with self.assertRaisesRegex(ValueError, "ABC, ACB, or BAC"):
            build_uniform_tilted_f4_block_groups(
                object_poses=LAYOUT["object_poses"],
                target_actor_poses=_target_actor_poses(),
                neutral_pose=LAYOUT["branch_neutral_pose"],
                object_order=("C", "B", "A"),
            )
        with self.assertRaisesRegex(ValueError, "finite 3-D"):
            right_curobo_planner_position([0.0, np.nan, 0.0])


if __name__ == "__main__":
    unittest.main()
