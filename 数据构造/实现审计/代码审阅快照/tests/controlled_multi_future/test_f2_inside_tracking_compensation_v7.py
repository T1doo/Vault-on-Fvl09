import copy
import json
import unittest

import numpy as np

from controlled_multi_future.anchor import quaternion_angular_error
from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.f2_inside_tracking_compensation_v7 import (
    MINIMUM_RIM_CLEARANCE_M,
    PROGRAM_ID,
    R6_DESIRED_PRE_RELEASE_ACTOR_POSE,
    R6_ORIGINAL_FIRST_EEF_COMMAND,
    R6_ORIGINAL_TARGETS,
    R6_REALIZED_PRE_RELEASE_ACTOR_POSE,
    R6_REALIZED_PRE_RELEASE_EEF_POSE,
    R6_TARGET_SHA256,
    build_f2_inside_alignment_diagnostic_v7,
    build_f2_inside_tracking_compensation_v7,
    validate_f2_inside_tracking_compensation_receipt_v7,
)
from controlled_multi_future.geometry import matrix_pose, pose_matrix


DESIRED_ROUTE = {
    "relation": "inside",
    "release_target_index": 0,
    "target_actor_pose": [
        -0.2901713007200062,
        -0.15267864896059247,
        0.8432698593315743,
        7.850462293418875e-17,
        -0.7071067811865476,
        7.850462293418875e-17,
        -0.7071067811865475,
    ],
    "pre_release_actor_pose": list(R6_DESIRED_PRE_RELEASE_ACTOR_POSE),
    "final_target_fit": {
        "cavity_lower": [
            -0.07824613475799559,
            0.02176539531350136,
            -0.07823097729682921,
        ],
        "cavity_upper": [
            0.07775386524200455,
            0.10476539531350136,
            0.07776902270317093,
        ],
        "local_corner_max": [
            0.04803894845225601,
            0.09580738142474032,
            0.03240838237479299,
        ],
        "local_corner_min": [
            -0.048531217968247026,
            0.030723409202262464,
            -0.032870336968451264,
        ],
        "pass_true_cavity_obb": True,
    },
    "targets": [copy.deepcopy(item) for item in R6_ORIGINAL_TARGETS],
}


def build():
    return build_f2_inside_tracking_compensation_v7(
        program_id=PROGRAM_ID,
        original_targets=copy.deepcopy(R6_ORIGINAL_TARGETS),
        desired_route=copy.deepcopy(DESIRED_ROUTE),
    )


class F2InsideTrackingCompensationV7Test(unittest.TestCase):
    def test_se3_formula_cancels_the_frozen_systematic_error(self):
        targets, receipt = build()
        desired = np.asarray(R6_ORIGINAL_FIRST_EEF_COMMAND, dtype=np.float64)
        realized = np.asarray(R6_REALIZED_PRE_RELEASE_EEF_POSE, dtype=np.float64)
        compensated = np.asarray(targets[0]["pose"], dtype=np.float64)
        observed_world_error = pose_matrix(realized) @ np.linalg.inv(
            pose_matrix(desired)
        )
        ideal_realized = matrix_pose(
            observed_world_error @ pose_matrix(compensated)
        )
        self.assertLess(np.linalg.norm(ideal_realized[:3] - desired[:3]), 1e-12)
        self.assertLess(
            quaternion_angular_error(ideal_realized[3:], desired[3:]), 1e-12
        )
        self.assertEqual(
            receipt["formula"]["runtime_adaptation"], False
        )
        self.assertFalse(
            receipt["formula"]["r7_outcome_may_change_compensation"]
        )

    def test_only_target_zero_changes_and_desired_route_is_untouched(self):
        original = copy.deepcopy(R6_ORIGINAL_TARGETS)
        route = copy.deepcopy(DESIRED_ROUTE)
        route_hash = hash_json(route)
        targets, receipt = build_f2_inside_tracking_compensation_v7(
            program_id=PROGRAM_ID,
            original_targets=original,
            desired_route=route,
        )
        self.assertEqual(receipt["changed_target_indices"], [0])
        self.assertNotEqual(hash_json(targets[0]), R6_TARGET_SHA256[0])
        self.assertEqual(hash_json(targets[1]), R6_TARGET_SHA256[1])
        self.assertEqual(hash_json(targets[2]), R6_TARGET_SHA256[2])
        self.assertEqual(route_hash, hash_json(route))
        self.assertEqual(
            tuple(item["segment_id"] for item in targets),
            tuple(item["segment_id"] for item in R6_ORIGINAL_TARGETS),
        )
        self.assertFalse(receipt["desired_route_semantics_mutated"])
        self.assertFalse(receipt["scientific_target_changed"])
        self.assertFalse(receipt["cavity_changed"])
        self.assertEqual(receipt["planner_query_count_delta"], 0)

    def test_current_retreat_and_rest_may_vary_but_remain_byte_equal(self):
        targets = copy.deepcopy(R6_ORIGINAL_TARGETS)
        route = copy.deepcopy(DESIRED_ROUTE)
        targets[1]["pose"][0] += 1e-6
        targets[2]["pose"][1] -= 1e-6
        route["targets"] = copy.deepcopy(targets)
        output, receipt = build_f2_inside_tracking_compensation_v7(
            program_id=PROGRAM_ID,
            original_targets=targets,
            desired_route=route,
        )
        self.assertEqual(output[1], targets[1])
        self.assertEqual(output[2], targets[2])
        self.assertEqual(receipt["changed_target_indices"], [0])
        self.assertEqual(
            receipt["input_targets_match_exact_r6_evidence"],
            [True, False, False],
        )

    def test_compensated_command_has_only_0_641mm_rim_headroom(self):
        _, receipt = build()
        audit = receipt["compensated_command_geometry_audit"]
        self.assertTrue(audit["pass"])
        self.assertTrue(audit["checks"]["opening_projection_inside"])
        self.assertGreaterEqual(
            audit["rim_clearance_m"], MINIMUM_RIM_CLEARANCE_M
        )
        self.assertAlmostEqual(audit["rim_clearance_m"], 0.020640680694863814)
        self.assertAlmostEqual(
            audit["rim_clearance_headroom_over_20mm_m"],
            0.000640680694863814,
        )

    def test_receipt_is_json_safe_self_hashed_and_tamper_detected(self):
        _, receipt = build()
        json.dumps(receipt, allow_nan=False)
        self.assertEqual(len(receipt["receipt_sha256"]), 64)
        self.assertEqual(
            validate_f2_inside_tracking_compensation_receipt_v7(receipt),
            receipt,
        )
        tampered = copy.deepcopy(receipt)
        tampered["changed_target_indices"] = [0, 1]
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_f2_inside_tracking_compensation_receipt_v7(tampered)

    def test_alignment_is_diagnostic_only_and_r6_misses_reference(self):
        _, compensation = build()
        r6 = build_f2_inside_alignment_diagnostic_v7(
            realized_eef_pose=R6_REALIZED_PRE_RELEASE_EEF_POSE,
            realized_actor_pose=R6_REALIZED_PRE_RELEASE_ACTOR_POSE,
            desired_eef_pose=R6_ORIGINAL_FIRST_EEF_COMMAND,
            desired_actor_pose=R6_DESIRED_PRE_RELEASE_ACTOR_POSE,
            compensation_receipt_sha256=compensation["receipt_sha256"],
        )
        self.assertFalse(r6["reference_comparison"]["eef_within_reference"])
        self.assertFalse(r6["reference_comparison"]["actor_within_reference"])
        self.assertTrue(r6["diagnostic_only"])
        self.assertFalse(r6["hard_gate"])
        self.assertFalse(r6["scientific_threshold_added"])
        self.assertFalse(r6["attempt_stop_condition_changed"])

        ideal = build_f2_inside_alignment_diagnostic_v7(
            realized_eef_pose=R6_ORIGINAL_FIRST_EEF_COMMAND,
            realized_actor_pose=R6_DESIRED_PRE_RELEASE_ACTOR_POSE,
            desired_eef_pose=R6_ORIGINAL_FIRST_EEF_COMMAND,
            desired_actor_pose=R6_DESIRED_PRE_RELEASE_ACTOR_POSE,
            compensation_receipt_sha256=compensation["receipt_sha256"],
        )
        self.assertTrue(ideal["reference_comparison"]["eef_within_reference"])
        self.assertTrue(ideal["reference_comparison"]["actor_within_reference"])

    def test_helper_refuses_on_beside_and_leaves_inputs_unchanged(self):
        for program_id in ("F2-on", "F2-beside"):
            with self.subTest(program_id=program_id):
                targets = copy.deepcopy(R6_ORIGINAL_TARGETS)
                route = copy.deepcopy(DESIRED_ROUTE)
                targets_before = copy.deepcopy(targets)
                route_before = copy.deepcopy(route)
                with self.assertRaisesRegex(ValueError, "inside-only"):
                    build_f2_inside_tracking_compensation_v7(
                        program_id=program_id,
                        original_targets=targets,
                        desired_route=route,
                    )
                self.assertEqual(targets, targets_before)
                self.assertEqual(route, route_before)

    def test_actor_and_eef_derivations_are_consistent_and_frozen(self):
        targets, receipt = build()
        consistency = receipt["actor_eef_derivation_consistency"]
        self.assertTrue(consistency["pass"])
        self.assertLess(
            consistency["position_error_m"], consistency["position_atol_m"]
        )
        self.assertLess(
            consistency["orientation_error_rad"],
            consistency["orientation_atol_rad"],
        )
        np.testing.assert_allclose(
            targets[0]["pose"],
            [
                -0.28812338400652177,
                -0.3473733292264533,
                0.930685147856833,
                0.6539396113143634,
                0.310157936702657,
                0.24979562519322943,
                0.6432473744125923,
            ],
            atol=1e-12,
            rtol=0.0,
        )


if __name__ == "__main__":
    unittest.main()
