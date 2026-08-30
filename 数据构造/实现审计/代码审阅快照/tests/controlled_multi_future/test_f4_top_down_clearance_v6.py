import copy
import json
import unittest

import numpy as np

from controlled_multi_future.f4_right_workspace_layout_v4 import LAYOUT
from controlled_multi_future.f4_top_down_clearance_v6 import (
    F4_BLOCK_ROLES,
    FROZEN_OFFSET_MARGIN_OVER_DERIVED_M,
    GRASP_HEIGHT_OFFSET_M,
    MICRO_LIFT_DISTANCE_M,
    R5_ADDITIONAL_CLEARANCE_DELTA_M,
    R5_COLLISION_EQUILIBRIUM_TARGET_GAP_M,
    R5_DERIVED_MINIMUM_GRASP_OFFSET_M,
    R5_LOWEST_FINGER_TABLE_CONTACT_Z_M,
    R5_REALIZED_COLLISION_EQUILIBRIUM_EEF_Z_M,
    R5_TABLE_TOP_Z_M,
    R5_TOP_DOWN_GRASP_TARGET_Z_M,
    REQUIRED_FINGER_TABLE_CLEARANCE_M,
    build_uniform_f4_top_down_clearance_contract_v6,
    r5_clearance_derivation_receipt,
    validate_uniform_f4_top_down_clearance_contract_v6,
)


R5_A_POSE = [
    0.15999959409236908,
    0.02000034973025322,
    0.7620004415512085,
    1.0,
    -9.675601177150384e-06,
    -4.463726781978039e-06,
    9.824091193877393e-07,
]


def _poses():
    value = copy.deepcopy(LAYOUT["object_poses"])
    value["A"] = list(R5_A_POSE)
    return value


class F4TopDownClearanceV6Test(unittest.TestCase):
    def test_r5_evidence_derives_one_bounded_16mm_offset(self):
        evidence = r5_clearance_derivation_receipt()
        self.assertTrue(evidence["pass"])
        self.assertAlmostEqual(
            R5_COLLISION_EQUILIBRIUM_TARGET_GAP_M,
            R5_REALIZED_COLLISION_EQUILIBRIUM_EEF_Z_M
            - R5_TOP_DOWN_GRASP_TARGET_Z_M,
        )
        self.assertAlmostEqual(
            R5_ADDITIONAL_CLEARANCE_DELTA_M,
            R5_TABLE_TOP_Z_M
            + REQUIRED_FINGER_TABLE_CLEARANCE_M
            - R5_LOWEST_FINGER_TABLE_CONTACT_Z_M,
        )
        self.assertAlmostEqual(
            R5_DERIVED_MINIMUM_GRASP_OFFSET_M,
            0.01563771395321989,
        )
        self.assertEqual(GRASP_HEIGHT_OFFSET_M, 0.016)
        self.assertGreaterEqual(
            GRASP_HEIGHT_OFFSET_M, R5_DERIVED_MINIMUM_GRASP_OFFSET_M
        )
        self.assertGreater(FROZEN_OFFSET_MARGIN_OVER_DERIVED_M, 0.0)
        self.assertLess(FROZEN_OFFSET_MARGIN_OVER_DERIVED_M, 0.001)
        self.assertEqual(evidence["cube_full_size_m"], [0.044, 0.044, 0.044])
        json.dumps(evidence, allow_nan=False)

    def test_uniform_abc_targets_preserve_xy_quaternion_and_approach_vector(self):
        poses = _poses()
        original = copy.deepcopy(poses)
        receipt = build_uniform_f4_top_down_clearance_contract_v6(
            object_poses=poses
        )
        self.assertEqual(poses, original)
        self.assertTrue(receipt["pass"])
        self.assertEqual(receipt["uniform_roles"], list(F4_BLOCK_ROLES))
        self.assertEqual(len(receipt["groups"]), 3)
        self.assertEqual(
            len(
                {
                    group["grasp_contract"]["grasp_contract_sha256"]
                    for group in receipt["groups"]
                }
            ),
            1,
        )
        for group in receipt["groups"]:
            role = group["role"]
            self.assertEqual(
                [item["segment_id"] for item in group["targets"]],
                [
                    f"{role}_pregrasp",
                    f"{role}_grasp",
                    f"{role}_micro_lift",
                ],
            )
            legacy_pre = np.asarray(group["legacy_targets"][0]["pose"])
            legacy_grasp = np.asarray(group["legacy_targets"][1]["pose"])
            shifted_pre = np.asarray(group["targets"][0]["pose"])
            shifted_grasp = np.asarray(group["targets"][1]["pose"])
            micro = np.asarray(group["targets"][2]["pose"])
            np.testing.assert_array_equal(shifted_pre[:2], legacy_pre[:2])
            np.testing.assert_array_equal(shifted_grasp[:2], legacy_grasp[:2])
            np.testing.assert_array_equal(shifted_pre[3:], legacy_pre[3:])
            np.testing.assert_array_equal(shifted_grasp[3:], legacy_grasp[3:])
            np.testing.assert_allclose(
                shifted_pre[:3] - legacy_pre[:3],
                [0.0, 0.0, 0.016],
                rtol=0.0,
                atol=1e-12,
            )
            np.testing.assert_allclose(
                shifted_grasp[:3] - legacy_grasp[:3],
                [0.0, 0.0, 0.016],
                rtol=0.0,
                atol=1e-12,
            )
            np.testing.assert_allclose(
                shifted_pre[:3] - shifted_grasp[:3],
                legacy_pre[:3] - legacy_grasp[:3],
                rtol=0.0,
                atol=1e-12,
            )
            np.testing.assert_allclose(
                micro[:3] - shifted_grasp[:3],
                [0.0, 0.0, MICRO_LIFT_DISTANCE_M],
                rtol=0.0,
                atol=1e-12,
            )
            self.assertTrue(group["pass"], role)

    def test_exact_r5_a_geometry_predicts_table_clearance_and_cube_overlap(self):
        receipt = build_uniform_f4_top_down_clearance_contract_v6(
            object_poses=_poses()
        )
        group = next(item for item in receipt["groups"] if item["role"] == "A")
        legacy_grasp = np.asarray(group["legacy_targets"][1]["pose"])
        shifted_grasp = np.asarray(group["targets"][1]["pose"])
        self.assertAlmostEqual(legacy_grasp[2], R5_TOP_DOWN_GRASP_TARGET_Z_M)
        self.assertAlmostEqual(
            shifted_grasp[2], R5_TOP_DOWN_GRASP_TARGET_Z_M + 0.016
        )
        geometry = group["predicted_geometry"]
        self.assertAlmostEqual(
            geometry["predicted_lowest_finger_z_m"],
            0.7423622860467801,
        )
        self.assertAlmostEqual(
            geometry["predicted_table_clearance_m"],
            0.002362286046780126,
        )
        self.assertGreaterEqual(
            geometry["predicted_table_clearance_m"],
            REQUIRED_FINGER_TABLE_CLEARANCE_M,
        )
        self.assertAlmostEqual(
            geometry["predicted_cube_vertical_overlap_m"],
            0.04163815550442843,
        )
        self.assertGreater(geometry["predicted_cube_vertical_overlap_m"], 0.0)
        self.assertTrue(geometry["runtime_collision_authority_required"])

    def test_contract_preserves_science_and_does_not_relax_gates(self):
        receipt = build_uniform_f4_top_down_clearance_contract_v6(
            object_poses=_poses()
        )
        for field in (
            "scene_layout_changed",
            "common_prefix_changed",
            "program_changed",
            "collision_gate_relaxed",
            "verifier_threshold_changed",
        ):
            self.assertFalse(receipt[field])
        self.assertTrue(receipt["diagnostic_only"])
        self.assertTrue(receipt["runtime_ik_collision_contact_required"])
        self.assertFalse(receipt["formal_data"])
        self.assertFalse(receipt["stage0_data"])

    def test_receipt_is_json_safe_self_hashed_and_tamper_evident(self):
        receipt = build_uniform_f4_top_down_clearance_contract_v6(
            object_poses=_poses()
        )
        json.dumps(receipt, allow_nan=False)
        self.assertEqual(
            receipt,
            validate_uniform_f4_top_down_clearance_contract_v6(receipt),
        )
        tampered = copy.deepcopy(receipt)
        tampered["groups"][0]["targets"][1]["pose"][2] += 0.001
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_uniform_f4_top_down_clearance_contract_v6(tampered)

    def test_invalid_arm_roles_and_nonfinite_pose_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "right arm"):
            build_uniform_f4_top_down_clearance_contract_v6(
                object_poses=_poses(), arm="left"
            )
        bad_roles = _poses()
        bad_roles.pop("C")
        with self.assertRaisesRegex(ValueError, "exactly A/B/C"):
            build_uniform_f4_top_down_clearance_contract_v6(
                object_poses=bad_roles
            )
        nonfinite = _poses()
        nonfinite["A"][2] = np.nan
        with self.assertRaisesRegex(ValueError, "finite"):
            build_uniform_f4_top_down_clearance_contract_v6(
                object_poses=nonfinite
            )


if __name__ == "__main__":
    unittest.main()
