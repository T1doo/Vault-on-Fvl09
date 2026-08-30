import copy
import json
import unittest

import numpy as np

from controlled_multi_future.anchor import quaternion_angular_error
from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.f2_inside_tracking_compensation_v7 import (
    R6_DESIRED_PRE_RELEASE_ACTOR_POSE,
    R6_ORIGINAL_FIRST_EEF_COMMAND,
    R6_ORIGINAL_TARGETS,
    R6_REALIZED_PRE_RELEASE_ACTOR_POSE,
    R6_TARGET_SHA256,
)
from controlled_multi_future.f2_inside_xy_tracking_compensation_v8 import (
    EXPECTED_XY_ONLY_ACTOR_COMMAND_POSE,
    EXPECTED_XY_ONLY_FIRST_EEF_COMMAND_POSE,
    PROGRAM_ID,
    R7_EVIDENCE,
    R7_FULL_SE3_COMPENSATED_ACTOR_POSE,
    R7_FULL_SE3_COMPENSATED_EEF_POSE,
    build_f2_inside_xy_tracking_compensation_v8,
    validate_f2_inside_xy_tracking_compensation_receipt_v8,
)
from controlled_multi_future.geometry import matrix_pose, pose_matrix, relative_pose


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
    return build_f2_inside_xy_tracking_compensation_v8(
        program_id=PROGRAM_ID,
        original_targets=copy.deepcopy(R6_ORIGINAL_TARGETS),
        desired_route=copy.deepcopy(DESIRED_ROUTE),
    )


class F2InsideXYTrackingCompensationV8Test(unittest.TestCase):
    def test_formula_takes_full_actor_xy_and_preserves_desired_z_quaternion(self):
        _, receipt = build()
        desired = np.asarray(R6_DESIRED_PRE_RELEASE_ACTOR_POSE, dtype=np.float64)
        realized = np.asarray(R6_REALIZED_PRE_RELEASE_ACTOR_POSE, dtype=np.float64)
        full = matrix_pose(
            pose_matrix(desired)
            @ np.linalg.inv(pose_matrix(realized))
            @ pose_matrix(desired)
        )
        xy_actor = np.asarray(receipt["xy_only_actor_command_pose"])
        np.testing.assert_allclose(
            full,
            R7_FULL_SE3_COMPENSATED_ACTOR_POSE,
            atol=1e-12,
            rtol=0.0,
        )
        np.testing.assert_allclose(xy_actor[:2], full[:2], atol=0.0, rtol=0.0)
        np.testing.assert_array_equal(xy_actor[2:], desired[2:])
        self.assertTrue(
            all(receipt["preserved_components"].values())
        )

    def test_frozen_t_eef_actor_inversion_produces_the_unique_expected_eef(self):
        targets, receipt = build()
        desired_actor = np.asarray(
            R6_DESIRED_PRE_RELEASE_ACTOR_POSE, dtype=np.float64
        )
        original_eef = np.asarray(
            R6_ORIGINAL_FIRST_EEF_COMMAND, dtype=np.float64
        )
        frozen_grasp = relative_pose(original_eef, desired_actor)
        expected = matrix_pose(
            pose_matrix(EXPECTED_XY_ONLY_ACTOR_COMMAND_POSE)
            @ np.linalg.inv(pose_matrix(frozen_grasp))
        )
        np.testing.assert_allclose(
            targets[0]["pose"],
            EXPECTED_XY_ONLY_FIRST_EEF_COMMAND_POSE,
            atol=1e-12,
            rtol=0.0,
        )
        np.testing.assert_allclose(targets[0]["pose"], expected, atol=1e-12)
        np.testing.assert_allclose(
            receipt["frozen_t_eef_actor"], frozen_grasp, atol=1e-12
        )
        self.assertTrue(receipt["actor_eef_derivation_consistency"]["pass"])

    def test_only_target_zero_changes_without_search_fallback_or_adaptation(self):
        original = copy.deepcopy(R6_ORIGINAL_TARGETS)
        route = copy.deepcopy(DESIRED_ROUTE)
        route_hash = hash_json(route)
        targets, receipt = build_f2_inside_xy_tracking_compensation_v8(
            program_id=PROGRAM_ID,
            original_targets=original,
            desired_route=route,
        )
        self.assertEqual(receipt["changed_target_indices"], [0])
        self.assertNotEqual(hash_json(targets[0]), R6_TARGET_SHA256[0])
        self.assertEqual(targets[1], original[1])
        self.assertEqual(targets[2], original[2])
        self.assertEqual(hash_json(route), route_hash)
        self.assertEqual(receipt["unique_candidate_count"], 1)
        self.assertFalse(receipt["candidate_search"])
        self.assertFalse(receipt["fallback"])
        self.assertFalse(receipt["online_adaptation"])
        self.assertFalse(receipt["runtime_artifact_read"])
        self.assertFalse(receipt["on_beside_affected"])
        self.assertFalse(receipt["desired_route_semantics_mutated"])
        self.assertFalse(receipt["scientific_target_changed"])
        self.assertFalse(receipt["cavity_changed"])
        self.assertFalse(receipt["verifier_threshold_changed"])

    def test_r7_full_se3_endpoint_is_explicitly_abandoned(self):
        targets, receipt = build()
        self.assertTrue(receipt["r7_full_se3_endpoint_abandoned"])
        self.assertFalse(receipt["r7_full_se3_target_reused"])
        self.assertFalse(
            np.allclose(targets[0]["pose"], R7_FULL_SE3_COMPENSATED_EEF_POSE)
        )
        self.assertAlmostEqual(
            targets[0]["pose"][2], R6_ORIGINAL_FIRST_EEF_COMMAND[2]
        )
        self.assertLess(
            quaternion_angular_error(
                targets[0]["pose"][3:], R6_ORIGINAL_FIRST_EEF_COMMAND[3:]
            ),
            1e-12,
        )

    def test_command_and_predicted_diagnostic_geometry_are_frozen(self):
        _, receipt = build()
        command = receipt["xy_only_command_geometry_audit"]
        self.assertTrue(command["pass"])
        self.assertTrue(command["checks"]["opening_projection_inside"])
        self.assertAlmostEqual(command["rim_clearance_m"], 0.02595801388876108)
        self.assertAlmostEqual(
            command["rim_clearance_headroom_over_20mm_m"],
            0.00595801388876108,
        )
        diagnostic = receipt["predicted_repeated_r6_tracking_error_diagnostic"]
        self.assertTrue(diagnostic["diagnostic_only"])
        self.assertFalse(diagnostic["hard_gate"])
        self.assertFalse(diagnostic["future_outcome_claimed"])
        self.assertAlmostEqual(
            diagnostic["position_error_to_desired_m"],
            0.0025668280322569286,
        )
        self.assertTrue(diagnostic["geometry_audit"]["pass"])
        self.assertAlmostEqual(
            diagnostic["geometry_audit"]["rim_clearance_m"],
            0.02246414387352981,
        )

    def test_r6_and_r7_immutable_evidence_hashes_are_bound(self):
        _, receipt = build()
        r6 = receipt["source_evidence"]["revision6"]
        r7 = receipt["source_evidence"]["revision7"]
        self.assertEqual(
            r6["evidence_tree_sha256"],
            "3e23874fc20c7fa7bacaa2d5ed3ce84e9d13fd4c53415671863b06809f2ec487",
        )
        self.assertEqual(r7, R7_EVIDENCE)
        self.assertEqual(
            r7["evidence_tree_sha256"],
            "3cc23996b115d3f23cc3aa2a551ffd2ad7543d7b072fa7581e50027292641cca",
        )
        self.assertEqual(
            r7["inside_preflight_receipt_file_sha256"],
            "c9700a9ab244d3961bd0c818d681b75dfc6975896c48475513bba4e0d1f545a7",
        )
        self.assertEqual(r7["inside_failure_status"], "MotionGenStatus.IK_FAIL")
        self.assertFalse(r7["normal_planner_false_partial_receipt_was_persisted"])

    def test_receipt_is_json_safe_self_hashed_and_tamper_fails_closed(self):
        _, receipt = build()
        json.dumps(receipt, ensure_ascii=False, allow_nan=False)
        self.assertEqual(
            validate_f2_inside_xy_tracking_compensation_receipt_v8(receipt),
            receipt,
        )
        tampered = copy.deepcopy(receipt)
        tampered["candidate_search"] = True
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_f2_inside_xy_tracking_compensation_receipt_v8(tampered)

        rehashed = copy.deepcopy(receipt)
        rehashed.pop("receipt_sha256")
        rehashed["source_evidence"]["revision7"]["evidence_file_count"] = 29
        payload = json.dumps(
            rehashed,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        import hashlib

        rehashed["receipt_sha256"] = hashlib.sha256(payload).hexdigest()
        with self.assertRaisesRegex(ValueError, "evidence binding"):
            validate_f2_inside_xy_tracking_compensation_receipt_v8(rehashed)

    def test_helper_refuses_on_beside_and_semantic_tamper_without_mutation(self):
        for program_id in ("F2-on", "F2-beside"):
            targets = copy.deepcopy(R6_ORIGINAL_TARGETS)
            route = copy.deepcopy(DESIRED_ROUTE)
            targets_before = copy.deepcopy(targets)
            route_before = copy.deepcopy(route)
            with self.assertRaisesRegex(ValueError, "inside-only"):
                build_f2_inside_xy_tracking_compensation_v8(
                    program_id=program_id,
                    original_targets=targets,
                    desired_route=route,
                )
            self.assertEqual(targets, targets_before)
            self.assertEqual(route, route_before)

        tampered_route = copy.deepcopy(DESIRED_ROUTE)
        tampered_route["final_target_fit"]["cavity_upper"][0] += 1e-3
        with self.assertRaisesRegex(ValueError, "cavity fit changed"):
            build_f2_inside_xy_tracking_compensation_v8(
                program_id=PROGRAM_ID,
                original_targets=copy.deepcopy(R6_ORIGINAL_TARGETS),
                desired_route=tampered_route,
            )


if __name__ == "__main__":
    unittest.main()
