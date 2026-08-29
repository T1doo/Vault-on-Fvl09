import copy
import unittest

import numpy as np

from controlled_multi_future.f4_right_workspace_layout_v4 import LAYOUT
from controlled_multi_future.f4_uniform_block_carry_midpoint_v3 import (
    F4_ALLOWED_OBJECT_ORDERS,
    F4_COMMON_SEGMENT_IDS,
    F4_SEGMENTED_BLOCK_SUFFIXES,
    F4_UNIFORM_BLOCK_CARRY_VERSION,
    audit_nominal_uniform_block_carry_geometry,
    build_uniform_carry_midpoint,
    expand_uniform_f4_block_carry_targets,
    validate_uniform_f4_block_carry_targets,
)


QUATERNION = np.asarray(
    [
        0.5243540196282083,
        -0.4743987085448014,
        0.4743957735598284,
        0.5243542480607336,
    ],
    dtype=np.float64,
)


class F4UniformBlockCarryMidpointV3Test(unittest.TestCase):
    def legacy_targets(self, order=("A", "B", "C")):
        common = [
            {
                "segment_id": segment_id,
                "pose": [0.0, 0.0, 0.95, *QUATERNION],
            }
            for segment_id in F4_COMMON_SEGMENT_IDS
        ]
        x_source = {"A": 0.15999926796226707, "B": 0.28, "C": 0.40}
        x_target = {"A": 0.14999967983036247, "B": 0.30, "C": 0.41}
        groups = []
        flattened = []
        for role in order:
            lift = np.asarray(
                [x_source[role], 0.008026192029675513, 0.9814017753160367, *QUATERNION]
            )
            preplace = np.asarray(
                [x_target[role], 0.1480258387231436, 0.9834013175523649, *QUATERNION]
            )
            poses = {
                "pregrasp": lift + np.asarray([0.0, 0.0, -0.01, 0, 0, 0, 0]),
                "grasp": lift + np.asarray([0.0, 0.0, -0.10, 0, 0, 0, 0]),
                "lift": lift,
                "preplace": preplace,
                "release": preplace + np.asarray([0.0, 0.0, -0.10, 0, 0, 0, 0]),
                "neutral": np.asarray([0.15, -0.02, 0.95, *QUATERNION]),
            }
            targets = [
                {"segment_id": f"{role}_{suffix}", "pose": poses[suffix].tolist()}
                for suffix in (
                    "pregrasp",
                    "grasp",
                    "lift",
                    "preplace",
                    "release",
                    "neutral",
                )
            ]
            groups.append(
                {
                    "role": role,
                    "targets": targets,
                    "grasp_contract": {"arm": "right"},
                }
            )
            flattened.extend(copy.deepcopy(targets))
        return common + flattened, {
            "execution_arm": "right",
            "object_order": list(order),
            "object_target_groups": groups,
            "common_grasp_contract": {"arm": "right"},
            "tray_pose_changed": False,
        }

    def test_exact_r2_a_midpoint_splits_failed_transition(self):
        lift = [
            0.15999926796226707,
            0.008026192029675513,
            0.9814017753160367,
            *QUATERNION,
        ]
        preplace = [
            0.14999967983036247,
            0.1480258387231436,
            0.9834013175523649,
            *QUATERNION,
        ]
        midpoint, audit = build_uniform_carry_midpoint(lift, preplace)
        np.testing.assert_array_equal(
            midpoint,
            [
                0.15499947389631477,
                0.07802601537640955,
                0.9834013175523649,
                *QUATERNION,
            ],
        )
        self.assertAlmostEqual(
            audit["direct_lift_to_preplace_distance_m"], 0.14037054892768097
        )
        self.assertAlmostEqual(
            audit["lift_to_carry_mid_distance_m"], 0.07020663343609893
        )
        self.assertAlmostEqual(
            audit["carry_mid_to_preplace_distance_m"], 0.07017815336182553
        )

    def test_expansion_is_uniform_for_every_frozen_program_order(self):
        for order in F4_ALLOWED_OBJECT_ORDERS:
            with self.subTest(order=order):
                targets, extra = self.legacy_targets(order)
                original_targets = copy.deepcopy(targets)
                original_extra = copy.deepcopy(extra)
                revised, revised_extra = expand_uniform_f4_block_carry_targets(
                    targets, extra
                )
                self.assertEqual(targets, original_targets)
                self.assertEqual(extra, original_extra)
                self.assertEqual(len(revised), 9 + 3 * 7)
                self.assertEqual(
                    [item["segment_id"] for item in revised[:9]],
                    list(F4_COMMON_SEGMENT_IDS),
                )
                self.assertEqual(
                    revised_extra["block_carry_route_version"],
                    F4_UNIFORM_BLOCK_CARRY_VERSION,
                )
                self.assertFalse(
                    revised_extra["block_carry_route_audit"][
                        "branch_specific_condition"
                    ]
                )
                for index, (role, group) in enumerate(
                    zip(order, revised_extra["object_target_groups"])
                ):
                    self.assertEqual(group["target_start_index"], index * 7)
                    self.assertEqual(
                        [item["segment_id"] for item in group["targets"]],
                        [f"{role}_{suffix}" for suffix in F4_SEGMENTED_BLOCK_SUFFIXES],
                    )
                validation = validate_uniform_f4_block_carry_targets(
                    revised, revised_extra
                )
                self.assertTrue(validation["pass"])
                for field in (
                    "scene_layout_changed",
                    "tray_pose_changed",
                    "executing_arm_changed",
                    "common_prefix_changed",
                    "program_changed",
                    "verifier_changed",
                    "branch_specific_condition",
                ):
                    self.assertFalse(validation[field])

    def test_validation_rejects_role_specific_or_malformed_routes(self):
        targets, extra = self.legacy_targets()
        revised, revised_extra = expand_uniform_f4_block_carry_targets(
            targets, extra
        )
        malformed = copy.deepcopy(revised_extra)
        malformed["object_target_groups"][0]["targets"][3]["pose"][0] += 1e-6
        with self.assertRaisesRegex(ValueError, "midpoint differs"):
            validate_uniform_f4_block_carry_targets(revised, malformed)

        wrong_order = copy.deepcopy(revised_extra)
        group = wrong_order["object_target_groups"][0]["targets"]
        group[3], group[4] = group[4], group[3]
        with self.assertRaisesRegex(ValueError, "target order changed"):
            validate_uniform_f4_block_carry_targets(revised, wrong_order)

        legacy_bad_quaternion, legacy_extra = self.legacy_targets()
        legacy_extra["object_target_groups"][0]["targets"][3]["pose"][3:] = [
            1.0,
            0.0,
            0.0,
            0.0,
        ]
        legacy_bad_quaternion[12]["pose"][3:] = [1.0, 0.0, 0.0, 0.0]
        with self.assertRaisesRegex(ValueError, "orientations differ"):
            expand_uniform_f4_block_carry_targets(
                legacy_bad_quaternion, legacy_extra
            )

    def test_nominal_frozen_layout_swept_block_geometry_passes(self):
        receipt = audit_nominal_uniform_block_carry_geometry(
            object_poses=LAYOUT["object_poses"],
            slot_poses=LAYOUT["slot_poses"],
        )
        self.assertTrue(receipt["pass"])
        self.assertEqual(set(receipt["roles"]), {"A", "B", "C"})
        self.assertAlmostEqual(
            receipt["minimum_vertical_surface_clearance_m"], 0.056, places=12
        )
        for role, item in receipt["roles"].items():
            self.assertTrue(item["pass"], role)
            self.assertTrue(item["all_waypoints_inside_table"], role)
            self.assertEqual(
                item["swept_non_target_collisions"],
                {"lift_to_carry_mid": [], "carry_mid_to_preplace": []},
            )
        self.assertIn("CuRobo", receipt["official_planner_authority"])
        for field in (
            "scene_layout_changed",
            "tray_pose_changed",
            "executing_arm_changed",
            "common_prefix_changed",
            "program_changed",
            "verifier_changed",
        ):
            self.assertFalse(receipt[field])


if __name__ == "__main__":
    unittest.main()
