import unittest

import numpy as np

from controlled_multi_future.f3_clearance_route_v3 import (
    F3_CARRY_TIME_DILATION_FACTOR,
    F3_CENTRAL_HOLD_STEPS,
    F3_CENTRAL_XY_M,
    F3_GRASP_BOUNDARIES,
    F3_H_NOMINAL_AMPLITUDE_M,
    F3_PROGRAMS,
    F3_PAD_HALF_EXTENTS_M,
    F3_V_NOMINAL_AMPLITUDE_M,
    FROZEN_CONTACT_POINT_ID,
    FROZEN_ROTATION_CANDIDATE_INDEX,
    audit_f3_free_space_event_contacts,
    audit_f3_grasp_boundary_stability,
    build_f3_clearance_height_audit,
    build_f3_clearance_route_targets,
    frozen_f3_grasp_contract,
    time_dilate_f3_carry_control_2x,
)


class F3ClearanceRouteV3Test(unittest.TestCase):
    def test_science_and_single_grasp_contract_are_frozen(self):
        self.assertEqual(F3_V_NOMINAL_AMPLITUDE_M, 0.055)
        self.assertEqual(F3_H_NOMINAL_AMPLITUDE_M, 0.050)
        self.assertEqual(F3_PROGRAMS, ("VVHH", "VHVH", "VHHV"))
        contract = frozen_f3_grasp_contract()
        self.assertEqual(contract["arm"], "left")
        self.assertEqual(contract["asset"], {"modelname": "001_bottle", "model_id": 13})
        self.assertEqual(FROZEN_CONTACT_POINT_ID, 3)
        self.assertEqual(FROZEN_ROTATION_CANDIDATE_INDEX, 0)
        self.assertEqual(contract["contact_point_id"], 3)
        self.assertEqual(contract["rotation_candidate_index"], 0)
        self.assertFalse(contract["fallback_allowed"])
        self.assertFalse(contract["automatic_retry"])
        self.assertEqual(len(contract["contract_sha256"]), 64)
        self.assertEqual(contract, frozen_f3_grasp_contract())

    def test_r2_bottle_envelope_implies_clearance_center_above_0996m(self):
        self.assertEqual(F3_PAD_HALF_EXTENTS_M, (0.11, 0.145, 0.005))
        self.assertAlmostEqual(0.745 + F3_PAD_HALF_EXTENTS_M[2], 0.750)
        post_lift_z = 0.9881075620651245
        bottle_below = post_lift_z - 0.8266738187083645
        audit = build_f3_clearance_height_audit(
            table_top_z_m=0.74,
            pad_top_z_m=0.75,
            post_lift_eef_z_m=post_lift_z,
            bottle_below_eef_m=bottle_below,
            gripper_below_eef_m=0.15,
        )
        self.assertTrue(audit["pass"])
        self.assertAlmostEqual(
            audit["selected_central_eef_z_m"], 0.99643374335676, places=14
        )
        self.assertAlmostEqual(
            audit["negative_v_endpoint_eef_z_m"], 0.94143374335676, places=14
        )
        self.assertAlmostEqual(
            audit["predicted_compound_lowest_z_m"], 0.78, places=14
        )
        self.assertAlmostEqual(
            audit["predicted_achieved_clearance_m"], 0.03, places=14
        )

    def test_gripper_envelope_can_only_raise_the_selected_height(self):
        bottle_dominant = build_f3_clearance_height_audit(
            table_top_z_m=0.74,
            pad_top_z_m=0.75,
            post_lift_eef_z_m=0.90,
            bottle_below_eef_m=0.10,
            gripper_below_eef_m=0.08,
        )
        gripper_dominant = build_f3_clearance_height_audit(
            table_top_z_m=0.74,
            pad_top_z_m=0.75,
            post_lift_eef_z_m=0.90,
            bottle_below_eef_m=0.10,
            gripper_below_eef_m=0.18,
        )
        self.assertEqual(bottle_dominant["compound_below_eef_m"], 0.10)
        self.assertEqual(gripper_dominant["compound_below_eef_m"], 0.18)
        self.assertGreater(
            gripper_dominant["selected_central_eef_z_m"],
            bottle_dominant["selected_central_eef_z_m"],
        )
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            build_f3_clearance_height_audit(
                table_top_z_m=0.74,
                pad_top_z_m=0.75,
                post_lift_eef_z_m=0.90,
                bottle_below_eef_m=-0.01,
                gripper_below_eef_m=0.10,
            )

    def test_route_is_raise_then_constant_height_horizontal_and_hold(self):
        audit = build_f3_clearance_height_audit(
            table_top_z_m=0.74,
            pad_top_z_m=0.75,
            post_lift_eef_z_m=0.988,
            bottle_below_eef_m=0.162,
            gripper_below_eef_m=0.150,
        )
        post_lift = np.asarray([-.205, .062, .988, .5, -.5, .5, .5])
        route = build_f3_clearance_route_targets(post_lift, audit)
        self.assertTrue(route["pass"])
        self.assertEqual(
            route["route_order"],
            ["f3_prefix_clearance_raise", "f3_prefix_center_high"],
        )
        self.assertEqual(route["central_hold_steps"], F3_CENTRAL_HOLD_STEPS)
        self.assertEqual(route["programs"], list(F3_PROGRAMS))
        self.assertEqual(route["shared_first_event"], "V")
        raise_pose = np.asarray(route["segments"][0]["pose"])
        center_pose = np.asarray(route["segments"][1]["pose"])
        np.testing.assert_array_equal(raise_pose[:2], post_lift[:2])
        np.testing.assert_array_equal(raise_pose[3:], post_lift[3:])
        np.testing.assert_array_equal(center_pose[:2], F3_CENTRAL_XY_M)
        np.testing.assert_array_equal(center_pose[3:], post_lift[3:])
        self.assertGreaterEqual(raise_pose[2], post_lift[2])
        self.assertEqual(center_pose[2], raise_pose[2])
        self.assertEqual(route["segments"][1]["time_dilation_factor"], 2)

    def test_two_x_control_dilation_preserves_position_endpoints(self):
        control = {
            "status": "Success",
            "position": np.asarray([[0.0, 2.0], [2.0, 4.0], [4.0, 8.0]], dtype=np.float32),
            "velocity": np.asarray([[2.0, 4.0], [4.0, 8.0], [6.0, 12.0]], dtype=np.float32),
            "acceleration": np.asarray([[4.0, 8.0], [8.0, 16.0], [12.0, 24.0]], dtype=np.float32),
            "jerk": np.asarray([[8.0, 16.0], [16.0, 32.0], [24.0, 48.0]], dtype=np.float32),
            "source": "synthetic",
        }
        dilated = time_dilate_f3_carry_control_2x(control)
        self.assertEqual(F3_CARRY_TIME_DILATION_FACTOR, 2)
        self.assertEqual(dilated["position"].shape, (5, 2))
        np.testing.assert_array_equal(dilated["position"][0], control["position"][0])
        np.testing.assert_array_equal(dilated["position"][-1], control["position"][-1])
        np.testing.assert_array_equal(dilated["position"][1], [1.0, 3.0])
        np.testing.assert_array_equal(dilated["velocity"][0], [1.0, 2.0])
        np.testing.assert_array_equal(dilated["acceleration"][0], [1.0, 2.0])
        np.testing.assert_array_equal(dilated["jerk"][0], [1.0, 2.0])
        self.assertEqual(dilated["source"], "synthetic")
        self.assertEqual(dilated["_cmf_time_dilation"]["input_step_count"], 3)
        self.assertEqual(dilated["_cmf_time_dilation"]["output_step_count"], 5)
        np.testing.assert_array_equal(control["position"][1], [2.0, 4.0])
        with self.assertRaisesRegex(ValueError, "successful"):
            time_dilate_f3_carry_control_2x({**control, "status": "Fail"})

    def test_external_support_contacts_fail_but_gripper_bottle_contact_is_allowed(self):
        clean = [
            [
                {
                    "body_a": "fl_link7",
                    "body_b": "f3_main_bottle",
                    "point_count": 4,
                    "impulse_norm_sum": 0.1,
                }
            ],
            [],
        ]
        clean_result = audit_f3_free_space_event_contacts(clean)
        self.assertTrue(clean_result["pass"])

        bottle_pad = clean + [
            [{"body_a": "f3_main_bottle", "body_b": "f3_original_pad"}]
        ]
        bottle_result = audit_f3_free_space_event_contacts(bottle_pad)
        self.assertFalse(bottle_result["pass"])
        self.assertEqual(bottle_result["first_bottle_support_contact_frame"], 2)

        finger_table = clean + [[{"body_a": "fl_link8", "body_b": "table"}]]
        finger_result = audit_f3_free_space_event_contacts(finger_table)
        self.assertFalse(finger_result["pass"])
        self.assertEqual(
            finger_result["first_selected_gripper_support_contact_frame"], 2
        )

    def test_all_frozen_grasp_boundaries_are_hard_gated(self):
        stable = {
            name: [0.001 * index, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
            for index, name in enumerate(F3_GRASP_BOUNDARIES)
        }
        stable_result = audit_f3_grasp_boundary_stability(stable)
        self.assertFalse(stable_result["pass"])
        self.assertFalse(
            stable_result["checks"]["all_translation_boundaries_stable"]
        )

        within = {
            name: [0.0005 * index, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
            for index, name in enumerate(F3_GRASP_BOUNDARIES)
        }
        within_result = audit_f3_grasp_boundary_stability(within)
        self.assertTrue(within_result["pass"])

        angle = 0.051
        drifted = dict(within)
        drifted["post_center_high"] = [
            0.0,
            0.0,
            0.0,
            np.cos(angle / 2),
            np.sin(angle / 2),
            0.0,
            0.0,
        ]
        drifted_result = audit_f3_grasp_boundary_stability(drifted)
        self.assertFalse(drifted_result["pass"])
        self.assertFalse(
            drifted_result["per_boundary"]["post_center_high"][
                "orientation_pass"
            ]
        )
        with self.assertRaisesRegex(ValueError, "exactly"):
            audit_f3_grasp_boundary_stability({"post_close": within["post_close"]})


if __name__ == "__main__":
    unittest.main()
